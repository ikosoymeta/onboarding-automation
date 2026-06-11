"""PR Polling Manager for async status monitoring with notifications.

Provides non-blocking PR status polling using threading. Integrates with
WorkflowOrchestrator for state persistence and supports notification
callbacks for status change events.
"""

import logging
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .client import AgenticBuyingClient, PRStatus

logger = logging.getLogger(__name__)


@dataclass
class PollingState:
    """State for an active PR polling session."""
    polling_id: str
    pr_number: str
    status: str  # 'active', 'stopped', 'completed', 'error'
    start_time: datetime
    last_check: Optional[datetime] = None
    last_status: Optional[str] = None
    check_count: int = 0
    error_count: int = 0
    thread_id: Optional[int] = None


class PRPollingManager:
    """Manages async PR status polling with notifications.
    
    Uses threading for non-blocking operation. Polling state is tracked
    in memory and can be persisted via WorkflowOrchestrator. Notification
    callbacks are invoked when PR status changes.
    
    Example:
        manager = PRPollingManager(
            pr_number="PR-12345",
            agentic_client=client,
            notification_callback=my_callback,
            poll_interval=300  # 5 minutes
        )
        polling_id = manager.start_polling()
        # ... later ...
        manager.stop_polling(polling_id)
    """
    
    def __init__(
        self,
        pr_number: str,
        agentic_client: AgenticBuyingClient,
        notification_callback: Optional[Callable[[PRStatus, str], None]] = None,
        poll_interval: int = 300,  # 5 minutes
        max_duration: int = 86400,  # 24 hours
        max_errors: int = 5
    ):
        """Initialize PR Polling Manager.
        
        Args:
            pr_number: The PR number to monitor
            agentic_client: AgenticBuyingClient for status checks
            notification_callback: Callback invoked on status changes.
                                 Signature: callback(pr_status: PRStatus, event_type: str)
                                 event_type: 'submitted', 'approved', 'rejected', 'status_update'
            poll_interval: Seconds between status checks (default: 300 = 5 min)
            max_duration: Maximum polling duration in seconds (default: 86400 = 24h)
            max_errors: Maximum consecutive errors before stopping (default: 5)
        """
        self.pr_number = pr_number
        self.agentic_client = agentic_client
        self.notification_callback = notification_callback
        self.poll_interval = poll_interval
        self.max_duration = max_duration
        self.max_errors = max_errors
        
        # Polling state management
        self._polling_states: Dict[str, PollingState] = {}
        self._polling_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        
        logger.info(
            f"PRPollingManager initialized for {pr_number}, "
            f"interval={poll_interval}s, max_duration={max_duration}s"
        )
    
    def start_polling(self) -> str:
        """Start async polling for PR status.
        
        Returns:
            polling_id: Unique ID for tracking this polling session
        """
        polling_id = f"poll_{self.pr_number}_{int(datetime.utcnow().timestamp())}"
        
        with self._lock:
            # Create polling state
            state = PollingState(
                polling_id=polling_id,
                pr_number=self.pr_number,
                status="active",
                start_time=datetime.utcnow()
            )
            self._polling_states[polling_id] = state
            
            # Create stop event for this polling session
            stop_event = threading.Event()
            self._stop_events[polling_id] = stop_event
            
            # Start polling thread
            thread = threading.Thread(
                target=self._polling_loop,
                args=(polling_id, stop_event),
                name=f"PRPoll-{self.pr_number}",
                daemon=True
            )
            thread.start()
            self._polling_threads[polling_id] = thread
            state.thread_id = thread.ident
            
            logger.info(
                f"Started polling for PR {self.pr_number}, "
                f"polling_id={polling_id}, thread_id={thread.ident}"
            )
        
        # Send initial 'submitted' notification
        if self.notification_callback:
            try:
                # Get initial status
                initial_status = self.agentic_client.check_pr_status(self.pr_number)
                self.notification_callback(initial_status, "submitted")
            except Exception as e:
                logger.warning(f"Failed to send initial notification: {e}")
        
        return polling_id
    
    def stop_polling(self, polling_id: str) -> None:
        """Stop polling for given PR.
        
        Args:
            polling_id: The polling ID returned by start_polling()
        """
        thread_to_join = None
        with self._lock:
            if polling_id not in self._polling_states:
                logger.warning(f"Polling ID not found: {polling_id}")
                return
            
            state = self._polling_states[polling_id]
            if state.status != "active":
                logger.info(f"Polling already stopped: {polling_id}")
                # Cleanup if not already done
                self._cleanup_polling_session(polling_id)
                return
            
            # Signal thread to stop
            stop_event = self._stop_events.get(polling_id)
            if stop_event:
                stop_event.set()
            
            state.status = "stopped"
            thread_to_join = self._polling_threads.get(polling_id)
            logger.info(f"Stopped polling: {polling_id}")
        
        # Wait for thread to finish outside the lock
        if thread_to_join and thread_to_join.is_alive():
            thread_to_join.join(timeout=5.0)
        
        # Cleanup the session
        with self._lock:
            self._cleanup_polling_session(polling_id)

    def _cleanup_polling_session(self, polling_id: str) -> None:
        """Remove polling session from internal dictionaries to prevent memory leaks.
        
        Must be called with self._lock held.
        
        Args:
            polling_id: The polling ID to clean up
        """
        self._polling_states.pop(polling_id, None)
        self._polling_threads.pop(polling_id, None)
        self._stop_events.pop(polling_id, None)
        logger.debug(f"Cleaned up polling session: {polling_id}")
    
    def get_polling_status(self, polling_id: str) -> Dict[str, Any]:
        """Get current polling status.
        
        Args:
            polling_id: The polling ID to check
            
        Returns:
            Dict with polling status information
        """
        with self._lock:
            if polling_id not in self._polling_states:
                return {"error": "Polling ID not found"}
            
            state = self._polling_states[polling_id]
            return {
                "polling_id": state.polling_id,
                "pr_number": state.pr_number,
                "status": state.status,
                "start_time": state.start_time.isoformat(),
                "last_check": state.last_check.isoformat() if state.last_check else None,
                "last_status": state.last_status,
                "check_count": state.check_count,
                "error_count": state.error_count,
                "thread_id": state.thread_id
            }
    
    def _polling_loop(self, polling_id: str, stop_event: threading.Event):
        """Main polling loop running in background thread.
        
        Args:
            polling_id: The polling ID for this session
            stop_event: Event to signal thread to stop
        """
        logger.info(f"Polling loop started for {polling_id}")
        
        # Get initial state and start time
        with self._lock:
            state = self._polling_states.get(polling_id)
            if not state:
                logger.error(f"Polling state not found: {polling_id}")
                return
            start_time = state.start_time
        
        last_status = None
        
        try:
            while not stop_event.is_set():
                # Re-acquire state under lock at start of each iteration
                # to ensure we have the latest state and it hasn't been cleaned up
                with self._lock:
                    state = self._polling_states.get(polling_id)
                    if not state:
                        logger.info(f"Polling state removed for {polling_id}, exiting loop")
                        break
                    if state.status != "active":
                        logger.info(f"Polling state not active for {polling_id}: {state.status}")
                        break
                
                # Check if max duration exceeded
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > self.max_duration:
                    logger.info(
                        f"Max duration exceeded for {polling_id}, "
                        f"elapsed={elapsed}s, max={self.max_duration}s"
                    )
                    with self._lock:
                        state = self._polling_states.get(polling_id)
                        if state:
                            state.status = "completed"
                    break
                
                try:
                    # Check PR status
                    pr_status = self.agentic_client.check_pr_status(self.pr_number)
                    
                    with self._lock:
                        state = self._polling_states.get(polling_id)
                        if not state:
                            break
                        state.last_check = datetime.utcnow()
                        state.check_count += 1
                        state.last_status = pr_status.status
                        state.error_count = 0  # Reset error count on success
                    
                    # Check if status changed
                    if last_status != pr_status.status:
                        logger.info(
                            f"PR {self.pr_number} status changed: "
                            f"{last_status} -> {pr_status.status}"
                        )
                        
                        # Determine event type
                        event_type = "status_update"
                        if pr_status.status == "approved":
                            event_type = "approved"
                        elif pr_status.status == "rejected":
                            event_type = "rejected"
                        elif pr_status.status == "submitted":
                            event_type = "submitted"
                        
                        # Invoke notification callback
                        if self.notification_callback:
                            try:
                                self.notification_callback(pr_status, event_type)
                            except Exception as e:
                                logger.error(f"Notification callback failed: {e}")
                        
                        last_status = pr_status.status
                        
                        # Stop polling if PR is in terminal state
                        if pr_status.status in ["approved", "rejected"]:
                            logger.info(
                                f"PR {self.pr_number} reached terminal state: "
                                f"{pr_status.status}, stopping polling"
                            )
                            with self._lock:
                                state = self._polling_states.get(polling_id)
                                if state:
                                    state.status = "completed"
                            break
                    
                except Exception as e:
                    logger.error(f"Error checking PR status for {polling_id}: {e}")
                    with self._lock:
                        state = self._polling_states.get(polling_id)
                        if not state:
                            break
                        state.error_count += 1
                        if state.error_count >= self.max_errors:
                            logger.error(
                                f"Max errors exceeded for {polling_id}, "
                                f"errors={state.error_count}, stopping"
                            )
                            state.status = "error"
                            break
                
                # Wait for next poll interval or stop signal
                stop_event.wait(timeout=self.poll_interval)
        
        finally:
            # Cleanup the polling session to prevent memory leaks
            with self._lock:
                self._cleanup_polling_session(polling_id)
            logger.info(f"Polling loop ended for {polling_id}")


# Notification Callback Implementations

def logging_notification_callback(pr_status: PRStatus, event_type: str) -> None:
    """Simple logging notification callback.
    
    Args:
        pr_status: Current PR status
        event_type: Type of event ('submitted', 'approved', 'rejected', 'status_update')
    """
    logger.info(
        f"PR Notification [{event_type}]: "
        f"PR {pr_status.pr_number} is {pr_status.status}. "
        f"Approver: {pr_status.current_approver}, "
        f"PO: {pr_status.po_number}"
    )


def email_notification_callback(
    pr_status: PRStatus,
    event_type: str,
    recipients: List[str],
    smtp_config: Optional[Dict[str, Any]] = None
) -> None:
    """Email notification callback.
    
    Args:
        pr_status: Current PR status
        event_type: Type of event
        recipients: List of email addresses to notify
        smtp_config: Optional SMTP configuration
    """
    try:
        # Import email utilities (if available in the project)
        # This is a placeholder - actual implementation would use project's email utils
        subject = f"PR {pr_status.pr_number} - {event_type.upper()}"
        body = f"""
PR Status Update

PR Number: {pr_status.pr_number}
Status: {pr_status.status}
Event: {event_type}

Current Approver: {pr_status.current_approver or 'N/A'}
PO Number: {pr_status.po_number or 'N/A'}

Approval Chain: {', '.join(pr_status.approval_chain or [])}
Blockers: {', '.join(pr_status.blockers or ['None'])}

Last Updated: {pr_status.last_updated}
"""
        logger.info(f"Email notification would be sent to {recipients}: {subject}")
        # Actual email sending would go here
        # send_email(recipients, subject, body, smtp_config)
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")


def workplace_notification_callback(
    pr_status: PRStatus,
    event_type: str,
    group_id: Optional[str] = None,
    user_ids: Optional[List[str]] = None
) -> None:
    """Workplace notification callback.
    
    Args:
        pr_status: Current PR status
        event_type: Type of event
        group_id: Optional Workplace group ID to post to
        user_ids: Optional list of user IDs to tag
    """
    try:
        # Import Workplace utilities (if available in the project)
        # This is a placeholder - actual implementation would use project's Workplace utils
        message = f"""
🔔 PR Status Update: {pr_status.pr_number}

Status: {pr_status.status.upper()}
Event: {event_type}

Current Approver: {pr_status.current_approver or 'N/A'}
PO Number: {pr_status.po_number or 'N/A'}
"""
        logger.info(f"Workplace notification would be posted: {message}")
        # Actual Workplace posting would go here
        # post_to_workplace(group_id, message, user_ids)
        
    except Exception as e:
        logger.error(f"Failed to send Workplace notification: {e}")


class NotificationCallbackRegistry:
    """Registry for managing notification callbacks."""
    
    def __init__(self):
        self._callbacks: Dict[str, Callable] = {
            "logging": logging_notification_callback,
            "email": email_notification_callback,
            "workplace": workplace_notification_callback,
        }
    
    def register(self, name: str, callback: Callable):
        """Register a custom notification callback.
        
        Args:
            name: Name for the callback
            callback: Callable with signature (pr_status: PRStatus, event_type: str)
        """
        self._callbacks[name] = callback
        logger.info(f"Registered notification callback: {name}")
    
    def get(self, name: str) -> Optional[Callable]:
        """Get a registered callback by name.
        
        Args:
            name: Name of the callback
            
        Returns:
            The callback function or None if not found
        """
        return self._callbacks.get(name)
    
    def list_callbacks(self) -> List[str]:
        """List all registered callback names."""
        return list(self._callbacks.keys())


# Global registry instance
notification_registry = NotificationCallbackRegistry()
