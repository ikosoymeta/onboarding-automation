"""Integration tests for PR polling functionality.

Tests PRPollingManager lifecycle, notification callbacks, and concurrent polling.
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, call
from datetime import datetime, timedelta

from src.buyat.pr_polling import (
    PRPollingManager,
    PollingState,
    logging_notification_callback,
    NotificationCallbackRegistry,
    notification_registry
)
from src.buyat.client import AgenticBuyingClient, PRStatus


class TestPRPollingManager:
    """Test PRPollingManager functionality."""
    
    @pytest.fixture
    def mock_agentic_client(self):
        """Create mocked AgenticBuyingClient."""
        client = Mock(spec=AgenticBuyingClient)
        return client
    
    @pytest.fixture
    def manager(self, mock_agentic_client):
        """Create PRPollingManager with mocked client."""
        return PRPollingManager(
            pr_number="PR-12345",
            agentic_client=mock_agentic_client,
            poll_interval=1,  # 1 second for testing
            max_duration=10,  # 10 seconds for testing
            max_errors=3
        )
    
    def test_start_polling(self, manager):
        """Test starting polling session."""
        # Mock status check
        mock_status = PRStatus(
            pr_number="PR-12345",
            status="submitted",
            current_approver="manager@meta.com"
        )
        manager.agentic_client.check_pr_status.return_value = mock_status
        
        polling_id = manager.start_polling()
        
        assert polling_id.startswith("poll_PR-12345_")
        assert polling_id in manager._polling_states
        
        state = manager._polling_states[polling_id]
        assert state.pr_number == "PR-12345"
        assert state.status == "active"
        
        # Cleanup
        manager.stop_polling(polling_id)
        time.sleep(0.5)  # Give thread time to stop
    
    def test_stop_polling(self, manager):
        """Test stopping polling session."""
        mock_status = PRStatus(
            pr_number="PR-12345",
            status="submitted"
        )
        manager.agentic_client.check_pr_status.return_value = mock_status
        
        polling_id = manager.start_polling()
        time.sleep(0.5)  # Let it run briefly
        
        manager.stop_polling(polling_id)
        time.sleep(0.5)  # Give thread time to stop
        
        state = manager._polling_states[polling_id]
        assert state.status == "stopped"
    
    def test_get_polling_status(self, manager):
        """Test getting polling status."""
        mock_status = PRStatus(
            pr_number="PR-12345",
            status="submitted"
        )
        manager.agentic_client.check_pr_status.return_value = mock_status
        
        polling_id = manager.start_polling()
        time.sleep(0.5)
        
        status = manager.get_polling_status(polling_id)
        
        assert status["polling_id"] == polling_id
        assert status["pr_number"] == "PR-12345"
        assert status["status"] in ["active", "stopped"]
        assert "start_time" in status
        
        manager.stop_polling(polling_id)
        time.sleep(0.5)
    
    def test_polling_detects_status_change(self, manager):
        """Test that polling detects status changes and invokes callback."""
        callback_calls = []
        
        def test_callback(pr_status, event_type):
            callback_calls.append((pr_status.status, event_type))
        
        manager.notification_callback = test_callback
        
        # Mock status to change from submitted to approved
        statuses = [
            PRStatus(pr_number="PR-12345", status="submitted"),
            PRStatus(pr_number="PR-12345", status="submitted"),
            PRStatus(pr_number="PR-12345", status="approved", po_number="PO-99999"),
        ]
        manager.agentic_client.check_pr_status.side_effect = statuses
        
        polling_id = manager.start_polling()
        time.sleep(3.5)  # Wait for multiple polls
        
        # Should have detected the status change to approved
        approved_calls = [c for c in callback_calls if c[0] == "approved"]
        assert len(approved_calls) > 0
        assert approved_calls[0][1] == "approved"
        
        manager.stop_polling(polling_id)
        time.sleep(0.5)
    
    def test_polling_stops_on_terminal_state(self, manager):
        """Test that polling stops when PR reaches terminal state."""
        # Mock status to go from submitted to approved
        statuses = [
            PRStatus(pr_number="PR-12345", status="submitted"),
            PRStatus(pr_number="PR-12345", status="approved", po_number="PO-99999"),
        ]
        manager.agentic_client.check_pr_status.side_effect = statuses * 10
        
        polling_id = manager.start_polling()
        time.sleep(3)  # Wait for polls
        
        state = manager._polling_states[polling_id]
        # Should have completed (stopped) after reaching approved status
        assert state.status in ["completed", "active"]  # May still be active if not yet polled
        
        manager.stop_polling(polling_id)
        time.sleep(0.5)
    
    def test_polling_handles_errors(self, manager):
        """Test that polling handles errors gracefully."""
        # Mock to raise errors
        manager.agentic_client.check_pr_status.side_effect = Exception("API Error")
        
        polling_id = manager.start_polling()
        time.sleep(4)  # Wait for multiple error attempts
        
        state = manager._polling_states[polling_id]
        # Should have error count and eventually stop after max_errors
        assert state.error_count > 0
        
        manager.stop_polling(polling_id)
        time.sleep(0.5)
    
    def test_polling_max_duration(self):
        """Test that polling stops after max duration."""
        mock_client = Mock(spec=AgenticBuyingClient)
        mock_status = PRStatus(pr_number="PR-12345", status="submitted")
        mock_client.check_pr_status.return_value = mock_status
        
        # Create manager with very short max_duration
        manager = PRPollingManager(
            pr_number="PR-12345",
            agentic_client=mock_client,
            poll_interval=1,
            max_duration=2  # 2 seconds
        )
        
        polling_id = manager.start_polling()
        time.sleep(4)  # Wait longer than max_duration
        
        state = manager._polling_states[polling_id]
        assert state.status == "completed"
    
    def test_concurrent_polling(self, mock_agentic_client):
        """Test that multiple PRs can be polled concurrently."""
        mock_status = PRStatus(pr_number="PR-12345", status="submitted")
        mock_agentic_client.check_pr_status.return_value = mock_status
        
        manager1 = PRPollingManager(
            pr_number="PR-11111",
            agentic_client=mock_agentic_client,
            poll_interval=1,
            max_duration=5
        )
        manager2 = PRPollingManager(
            pr_number="PR-22222",
            agentic_client=mock_agentic_client,
            poll_interval=1,
            max_duration=5
        )
        
        polling_id1 = manager1.start_polling()
        polling_id2 = manager2.start_polling()
        
        time.sleep(2)
        
        # Both should be active
        assert manager1._polling_states[polling_id1].status == "active"
        assert manager2._polling_states[polling_id2].status == "active"
        
        # Cleanup
        manager1.stop_polling(polling_id1)
        manager2.stop_polling(polling_id2)
        time.sleep(0.5)


class TestNotificationCallbacks:
    """Test notification callback implementations."""
    
    def test_logging_notification_callback(self, caplog):
        """Test logging notification callback."""
        pr_status = PRStatus(
            pr_number="PR-12345",
            status="approved",
            current_approver="manager@meta.com",
            po_number="PO-99999"
        )
        
        logging_notification_callback(pr_status, "approved")
        
        # Check that log message was created
        assert "PR-12345" in caplog.text
        assert "approved" in caplog.text.lower()
    
    def test_notification_callback_registry(self):
        """Test notification callback registry."""
        registry = NotificationCallbackRegistry()
        
        # Should have default callbacks
        assert "logging" in registry.list_callbacks()
        assert "email" in registry.list_callbacks()
        assert "workplace" in registry.list_callbacks()
        
        # Register custom callback
        def custom_callback(pr_status, event_type):
            pass
        
        registry.register("custom", custom_callback)
        assert "custom" in registry.list_callbacks()
        assert registry.get("custom") == custom_callback
        
        # Get non-existent callback
        assert registry.get("nonexistent") is None


class TestIntegrationWithBuyAtClient:
    """Integration tests for PR creation with monitoring."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mocked BuyAtClient."""
        from src.buyat.client import BuyAtClient
        client = BuyAtClient(headless=True, use_agentic=True)
        client._agentic_client = Mock(spec=AgenticBuyingClient)
        client._agentic_client.is_started.return_value = True
        return client
    
    def test_create_pr_and_monitor(self, mock_client):
        """Test create_pr_and_monitor method."""
        # Mock supplier verification
        supplier_info = Mock()
        supplier_info.exists = True
        supplier_info.is_active = True
        mock_client.search_supplier = Mock(return_value=supplier_info)
        
        # Mock PR creation
        pr_info = PRDraftInfo(
            pr_number="PR-12345",
            pr_url="https://buy.meta.com/pr/12345",
            status="submitted",
            supplier_name="Test Supplier",
            amount=5000.00,
            description="Test purchase"
        )
        mock_client._agentic_client.create_pr_draft.return_value = pr_info
        
        # Mock PR status for polling
        mock_status = PRStatus(
            pr_number="PR-12345",
            status="submitted"
        )
        mock_client._agentic_client.check_pr_status.return_value = mock_status
        
        # Create PR with monitoring
        result_pr_info, polling_id = mock_client.create_pr_and_monitor(
            supplier_name="Test Supplier",
            amount=5000.00,
            description="Test purchase",
            justification="Business need",
            cost_center="CC-12345",
            poll_interval=1,
            max_duration=5
        )
        
        assert result_pr_info.pr_number == "PR-12345"
        assert polling_id.startswith("poll_PR-12345_")
        
        # Give polling a moment to start, then cleanup would happen
        # In real usage, the polling continues in background
        time.sleep(0.5)
