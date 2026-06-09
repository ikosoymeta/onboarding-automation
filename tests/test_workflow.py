"""Unit tests for workflow orchestrator."""

import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch

from src.orchestrator.workflow import (
    WorkflowOrchestrator,
    WorkflowState,
    StepStatus,
    WorkflowStep
)
from src.orchestrator.state_store import SQLiteStateStore


class TestWorkflowOrchestrator(unittest.TestCase):
    """Test cases for WorkflowOrchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.state_store = SQLiteStateStore(self.temp_db.name)
        self.orchestrator = WorkflowOrchestrator(
            workflow_id="test-workflow",
            state_store=self.state_store,
            max_workers=2
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)
    
    def test_add_step(self):
        """Test adding steps to workflow."""
        def dummy_action():
            return "result"
        
        self.orchestrator.add_step("step1", "Step 1", dummy_action)
        self.assertIn("step1", self.orchestrator.steps)
        self.assertEqual(self.orchestrator.steps["step1"].name, "Step 1")
    
    def test_add_step_duplicate(self):
        """Test adding duplicate step raises error."""
        def dummy_action():
            return "result"
        
        self.orchestrator.add_step("step1", "Step 1", dummy_action)
        with self.assertRaises(ValueError):
            self.orchestrator.add_step("step1", "Step 1 Duplicate", dummy_action)
    
    def test_get_ready_steps(self):
        """Test getting steps ready for execution."""
        def action1():
            return "result1"
        
        def action2():
            return "result2"
        
        # Step 1 has no dependencies
        self.orchestrator.add_step("step1", "Step 1", action1)
        # Step 2 depends on step 1
        self.orchestrator.add_step("step2", "Step 2", action2, dependencies=["step1"])
        
        ready = self.orchestrator._get_ready_steps()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].step_id, "step1")
    
    def test_workflow_execution_success(self):
        """Test successful workflow execution."""
        results = []
        
        def action1():
            results.append("step1")
            return "result1"
        
        def action2():
            results.append("step2")
            return "result2"
        
        self.orchestrator.add_step("step1", "Step 1", action1)
        self.orchestrator.add_step("step2", "Step 2", action2)
        
        success = self.orchestrator.run()
        
        self.assertTrue(success)
        self.assertEqual(self.orchestrator.state, WorkflowState.COMPLETED)
        self.assertEqual(len(results), 2)
        self.assertIn("step1", results)
        self.assertIn("step2", results)
    
    def test_workflow_with_dependencies(self):
        """Test workflow execution with dependencies."""
        execution_order = []
        
        def action1():
            execution_order.append("step1")
            return "result1"
        
        def action2():
            execution_order.append("step2")
            return "result2"
        
        def action3():
            execution_order.append("step3")
            return "result3"
        
        # step3 depends on step1 and step2
        self.orchestrator.add_step("step1", "Step 1", action1)
        self.orchestrator.add_step("step2", "Step 2", action2)
        self.orchestrator.add_step("step3", "Step 3", action3, dependencies=["step1", "step2"])
        
        success = self.orchestrator.run()
        
        self.assertTrue(success)
        # step3 should execute after step1 and step2
        self.assertEqual(execution_order[2], "step3")
    
    def test_workflow_failure(self):
        """Test workflow execution with failing step."""
        def action1():
            return "result1"
        
        def action2():
            raise Exception("Step failed")
        
        self.orchestrator.add_step("step1", "Step 1", action1)
        self.orchestrator.add_step("step2", "Step 2", action2)
        
        success = self.orchestrator.run()
        
        self.assertFalse(success)
        self.assertEqual(self.orchestrator.state, WorkflowState.FAILED)
        self.assertEqual(self.orchestrator.steps["step2"].status, StepStatus.FAILED)
    
    def test_workflow_retry_logic(self):
        """Test step retry logic."""
        attempt_count = [0]
        
        def flaky_action():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Flaky failure")
            return "success"
        
        self.orchestrator.add_step("step1", "Step 1", flaky_action, max_retries=3)
        success = self.orchestrator.run()
        
        self.assertTrue(success)
        self.assertEqual(attempt_count[0], 3)
        self.assertEqual(self.orchestrator.steps["step1"].retry_count, 2)
    
    def test_workflow_blocked_steps(self):
        """Test that steps with failed dependencies are blocked."""
        def action1():
            raise Exception("Failed")
        
        def action2():
            return "result2"
        
        self.orchestrator.add_step("step1", "Step 1", action1)
        self.orchestrator.add_step("step2", "Step 2", action2, dependencies=["step1"])
        
        success = self.orchestrator.run()
        
        self.assertFalse(success)
        self.assertEqual(self.orchestrator.steps["step2"].status, StepStatus.BLOCKED)
    
    def test_get_status(self):
        """Test getting workflow status."""
        def action1():
            return "result1"
        
        self.orchestrator.add_step("step1", "Step 1", action1)
        self.orchestrator.add_step("step2", "Step 2", action1)
        
        status = self.orchestrator.get_status()
        
        self.assertEqual(status["workflow_id"], "test-workflow")
        self.assertEqual(status["total_steps"], 2)
        self.assertEqual(status["step_counts"]["pending"], 2)
    
    def test_state_persistence(self):
        """Test workflow state persistence."""
        def action1():
            return "result1"
        
        self.orchestrator.add_step("step1", "Step 1", action1)
        self.orchestrator.metadata["test_key"] = "test_value"
        self.orchestrator.run()
        
        # Create new orchestrator with same workflow_id and load state
        orchestrator2 = WorkflowOrchestrator(
            workflow_id="test-workflow",
            state_store=self.state_store
        )
        
        loaded = orchestrator2._load_state()
        self.assertTrue(loaded)
        self.assertEqual(orchestrator2.state, WorkflowState.COMPLETED)
        self.assertEqual(orchestrator2.metadata["test_key"], "test_value")


class TestSQLiteStateStore(unittest.TestCase):
    """Test cases for SQLiteStateStore."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.store = SQLiteStateStore(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)
    
    def test_save_and_load_workflow(self):
        """Test saving and loading workflow state."""
        state = {
            "workflow_id": "test-123",
            "status": "running",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:01:00",
            "steps": {}
        }
        
        self.store.save_workflow("test-123", state)
        loaded = self.store.load_workflow("test-123")
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["workflow_id"], "test-123")
        self.assertEqual(loaded["status"], "running")
    
    def test_list_workflows(self):
        """Test listing workflows."""
        state1 = {"workflow_id": "wf1", "status": "completed", "steps": {}}
        state2 = {"workflow_id": "wf2", "status": "running", "steps": {}}
        state3 = {"workflow_id": "wf3", "status": "completed", "steps": {}}
        
        self.store.save_workflow("wf1", state1)
        self.store.save_workflow("wf2", state2)
        self.store.save_workflow("wf3", state3)
        
        all_workflows = self.store.list_workflows()
        self.assertEqual(len(all_workflows), 3)
        
        completed = self.store.list_workflows(status="completed")
        self.assertEqual(len(completed), 2)
    
    def test_delete_workflow(self):
        """Test deleting workflow state."""
        state = {"workflow_id": "test-123", "status": "running", "steps": {}}
        self.store.save_workflow("test-123", state)
        
        self.store.delete_workflow("test-123")
        loaded = self.store.load_workflow("test-123")
        
        self.assertIsNone(loaded)


if __name__ == '__main__':
    unittest.main()
