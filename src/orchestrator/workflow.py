"""Workflow orchestration engine for vendor onboarding.

Implements a state machine for tracking form submission status with
parallel execution, dependency management, and checkpoint/resume capability.
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .state_store import StateStore, SQLiteStateStore

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class WorkflowState(Enum):
    """Overall workflow state."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """Represents a single step in the workflow."""
    step_id: str
    name: str
    action: Callable[[], Any]
    dependencies: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding action)."""
        data = asdict(self)
        data.pop('action', None)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], action: Callable[[], Any]) -> 'WorkflowStep':
        """Create from dictionary."""
        data = data.copy()
        data['status'] = StepStatus(data['status'])
        data['action'] = action
        return cls(**data)


class WorkflowOrchestrator:
    """Orchestrates vendor onboarding workflow execution.
    
    Features:
    - State machine for tracking step status
    - Parallel execution for independent steps
    - Dependency management
    - Retry logic with exponential backoff
    - Checkpoint/resume capability
    """
    
    def __init__(
        self,
        workflow_id: Optional[str] = None,
        state_store: Optional[StateStore] = None,
        max_workers: int = 5
    ):
        """Initialize workflow orchestrator.
        
        Args:
            workflow_id: Unique workflow identifier (generated if not provided)
            state_store: State store for persistence (SQLiteStateStore if None)
            max_workers: Maximum number of parallel workers
        """
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.state_store = state_store or SQLiteStateStore()
        self.max_workers = max_workers
        self.steps: Dict[str, WorkflowStep] = {}
        self.state = WorkflowState.PENDING
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.metadata: Dict[str, Any] = {}
    
    def add_step(
        self,
        step_id: str,
        name: str,
        action: Callable[[], Any],
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3
    ) -> None:
        """Add a step to the workflow.
        
        Args:
            step_id: Unique step identifier
            name: Human-readable step name
            action: Callable to execute for this step
            dependencies: List of step IDs that must complete before this step
            max_retries: Maximum retry attempts on failure
        """
        if step_id in self.steps:
            raise ValueError(f"Step {step_id} already exists")
        
        step = WorkflowStep(
            step_id=step_id,
            name=name,
            action=action,
            dependencies=dependencies or [],
            max_retries=max_retries
        )
        self.steps[step_id] = step
        logger.debug(f"Added step {step_id}: {name}")
    
    def _get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute (dependencies satisfied).
        
        Validates that all dependencies exist before checking status.
        Raises ValueError if a dependency is referenced but not found.
        """
        ready = []
        for step in self.steps.values():
            if step.status != StepStatus.PENDING:
                continue
            
            # Validate all dependencies exist
            for dep_id in step.dependencies:
                if dep_id not in self.steps:
                    raise ValueError(
                        f"Step '{step.step_id}' depends on '{dep_id}' which does not exist. "
                        f"Available steps: {list(self.steps.keys())}"
                    )
            
            # Check if all dependencies are completed
            deps_satisfied = all(
                self.steps[dep_id].status == StepStatus.COMPLETED
                for dep_id in step.dependencies
            )
            
            if deps_satisfied:
                ready.append(step)
        
        return ready
    
    def _get_blocked_steps(self) -> List[WorkflowStep]:
        """Get steps blocked by failed dependencies."""
        blocked = []
        for step in self.steps.values():
            if step.status != StepStatus.PENDING:
                continue
            
            # Check if any dependency failed
            has_failed_dep = any(
                self.steps[dep_id].status == StepStatus.FAILED
                for dep_id in step.dependencies
                if dep_id in self.steps
            )
            
            if has_failed_dep:
                blocked.append(step)
        
        return blocked
    
    def _execute_step(self, step: WorkflowStep) -> bool:
        """Execute a single workflow step with retry logic.
        
        Args:
            step: Step to execute
            
        Returns:
            True if step completed successfully
        """
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow().isoformat()
        self._save_state()
        
        logger.info(f"Executing step {step.step_id}: {step.name}")
        
        for attempt in range(step.max_retries + 1):
            try:
                result = step.action()
                step.result = result
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.utcnow().isoformat()
                logger.info(f"Step {step.step_id} completed successfully")
                self._save_state()
                return True
            
            except Exception as e:
                step.retry_count = attempt + 1
                step.error = str(e)
                logger.warning(f"Step {step.step_id} attempt {attempt + 1} failed: {e}")
                
                if attempt < step.max_retries:
                    # Exponential backoff
                    delay = 2 ** attempt
                    logger.info(f"Retrying step {step.step_id} in {delay} seconds...")
                    time.sleep(delay)
                else:
                    step.status = StepStatus.FAILED
                    step.completed_at = datetime.utcnow().isoformat()
                    logger.error(f"Step {step.step_id} failed after {step.max_retries} retries")
                    self._save_state()
                    return False
        
        return False
    
    def _save_state(self) -> None:
        """Save current workflow state to store."""
        self.updated_at = datetime.utcnow().isoformat()
        state = {
            "workflow_id": self.workflow_id,
            "status": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "steps": {sid: step.to_dict() for sid, step in self.steps.items()}
        }
        self.state_store.save_workflow(self.workflow_id, state)
    
    def _load_state(self) -> bool:
        """Load workflow state from store.
        
        Returns:
            True if state was loaded successfully
        """
        state = self.state_store.load_workflow(self.workflow_id)
        if not state:
            return False
        
        self.state = WorkflowState(state["status"])
        self.created_at = state["created_at"]
        self.updated_at = state["updated_at"]
        self.metadata = state.get("metadata", {})
        
        # Steps need to be reconstructed with actions
        # (actions cannot be serialized, so they must be re-registered)
        logger.info(f"Loaded workflow {self.workflow_id} with {len(state['steps'])} steps")
        return True
    
    def run(self, resume: bool = False) -> bool:
        """Execute the workflow.
        
        Args:
            resume: If True, resume from saved state
            
        Returns:
            True if workflow completed successfully
        """
        if resume:
            if not self._load_state():
                logger.warning(f"No saved state found for workflow {self.workflow_id}, starting fresh")
        
        self.state = WorkflowState.RUNNING
        self._save_state()
        
        logger.info(f"Starting workflow {self.workflow_id} with {len(self.steps)} steps")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                # Get ready steps
                ready_steps = self._get_ready_steps()
                
                if not ready_steps:
                    # Check if workflow is complete or blocked
                    pending_steps = [
                        s for s in self.steps.values()
                        if s.status == StepStatus.PENDING
                    ]
                    
                    if not pending_steps:
                        # All steps completed or failed
                        break
                    
                    # Check for blocked steps
                    blocked_steps = self._get_blocked_steps()
                    for step in blocked_steps:
                        step.status = StepStatus.BLOCKED
                        logger.warning(f"Step {step.step_id} blocked by failed dependency")
                    
                    if blocked_steps:
                        self._save_state()
                    
                    # Wait a bit before checking again
                    time.sleep(1)
                    continue
                
                # Execute ready steps in parallel
                futures = {
                    executor.submit(self._execute_step, step): step
                    for step in ready_steps
                }
                
                # Wait for completion
                for future in as_completed(futures):
                    step = futures[future]
                    try:
                        success = future.result()
                        if not success:
                            logger.error(f"Step {step.step_id} failed, checking if workflow can continue")
                    except Exception as e:
                        logger.error(f"Unexpected error in step {step.step_id}: {e}")
                        step.status = StepStatus.FAILED
                        step.error = str(e)
                        self._save_state()
        
        # Determine final workflow state
        failed_steps = [s for s in self.steps.values() if s.status == StepStatus.FAILED]
        blocked_steps = [s for s in self.steps.values() if s.status == StepStatus.BLOCKED]
        
        if failed_steps or blocked_steps:
            self.state = WorkflowState.FAILED
            logger.error(f"Workflow {self.workflow_id} failed: {len(failed_steps)} failed, {len(blocked_steps)} blocked")
        else:
            self.state = WorkflowState.COMPLETED
            logger.info(f"Workflow {self.workflow_id} completed successfully")
        
        self._save_state()
        return self.state == WorkflowState.COMPLETED
    
    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status.
        
        Returns:
            Dictionary with workflow status information
        """
        step_counts = {}
        for status in StepStatus:
            count = sum(1 for s in self.steps.values() if s.status == status)
            step_counts[status.value] = count
        
        return {
            "workflow_id": self.workflow_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_steps": len(self.steps),
            "step_counts": step_counts,
            "metadata": self.metadata
        }
    
    def get_step_status(self, step_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific step.
        
        Args:
            step_id: Step identifier
            
        Returns:
            Step status dictionary or None if not found
        """
        step = self.steps.get(step_id)
        if step:
            return step.to_dict()
        return None
    
    def pause(self) -> None:
        """Pause workflow execution (for manual intervention)."""
        self.state = WorkflowState.PAUSED
        self._save_state()
        logger.info(f"Workflow {self.workflow_id} paused")
    
    def resume(self) -> bool:
        """Resume paused workflow.
        
        Returns:
            True if resumed successfully
        """
        if self.state != WorkflowState.PAUSED:
            logger.warning(f"Cannot resume workflow {self.workflow_id}: not paused")
            return False
        
        return self.run(resume=True)
