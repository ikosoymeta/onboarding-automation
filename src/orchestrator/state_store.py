"""State persistence for workflow orchestration.

Provides checkpoint/resume capability using SQLite for durable state storage.
"""

import json
import sqlite3
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StateStore(ABC):
    """Abstract base class for workflow state storage."""
    
    @abstractmethod
    def save_workflow(self, workflow_id: str, state: Dict[str, Any]) -> None:
        """Save workflow state."""
        pass
    
    @abstractmethod
    def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow state."""
        pass
    
    @abstractmethod
    def list_workflows(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workflows, optionally filtered by status."""
        pass
    
    @abstractmethod
    def delete_workflow(self, workflow_id: str) -> None:
        """Delete workflow state."""
        pass


class SQLiteStateStore(StateStore):
    """SQLite-based state store for workflow persistence."""
    
    def __init__(self, db_path: str = "workflow_state.db"):
        """Initialize SQLite state store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON workflows(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated ON workflows(updated_at)
            """)
            conn.commit()
    
    def save_workflow(self, workflow_id: str, state: Dict[str, Any]) -> None:
        """Save workflow state to database.
        
        Args:
            workflow_id: Unique workflow identifier
            state: Workflow state dictionary
        """
        status = state.get("status", "unknown")
        now = datetime.utcnow().isoformat()
        state_json = json.dumps(state)
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if workflow exists
            cursor = conn.execute(
                "SELECT workflow_id FROM workflows WHERE workflow_id = ?",
                (workflow_id,)
            )
            exists = cursor.fetchone() is not None
            
            if exists:
                conn.execute("""
                    UPDATE workflows
                    SET status = ?, updated_at = ?, state_json = ?
                    WHERE workflow_id = ?
                """, (status, now, state_json, workflow_id))
            else:
                conn.execute("""
                    INSERT INTO workflows (workflow_id, status, created_at, updated_at, state_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (workflow_id, status, now, now, state_json))
            
            conn.commit()
        
        logger.debug(f"Saved workflow {workflow_id} with status {status}")
    
    def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow state from database.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            Workflow state dictionary or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT state_json FROM workflows WHERE workflow_id = ?",
                (workflow_id,)
            )
            row = cursor.fetchone()
            
            if row:
                state = json.loads(row[0])
                logger.debug(f"Loaded workflow {workflow_id}")
                return state
            
            logger.debug(f"Workflow {workflow_id} not found")
            return None
    
    def list_workflows(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workflows, optionally filtered by status.
        
        Args:
            status: Filter by workflow status (optional)
            
        Returns:
            List of workflow state dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            if status:
                cursor = conn.execute(
                    "SELECT state_json FROM workflows WHERE status = ? ORDER BY updated_at DESC",
                    (status,)
                )
            else:
                cursor = conn.execute(
                    "SELECT state_json FROM workflows ORDER BY updated_at DESC"
                )
            
            workflows = []
            for row in cursor.fetchall():
                state = json.loads(row[0])
                workflows.append(state)
            
            logger.debug(f"Listed {len(workflows)} workflows (status={status})")
            return workflows
    
    def delete_workflow(self, workflow_id: str) -> None:
        """Delete workflow state from database.
        
        Args:
            workflow_id: Unique workflow identifier
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM workflows WHERE workflow_id = ?",
                (workflow_id,)
            )
            conn.commit()
        
        logger.debug(f"Deleted workflow {workflow_id}")
    
    def get_workflow_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information for a workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            Summary dictionary with metadata (no full state)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT workflow_id, status, created_at, updated_at
                FROM workflows WHERE workflow_id = ?
            """, (workflow_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "workflow_id": row[0],
                    "status": row[1],
                    "created_at": row[2],
                    "updated_at": row[3]
                }
            
            return None
