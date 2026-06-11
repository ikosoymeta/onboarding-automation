"""CSC browser automation for vendor worker onboarding.

Provides browser automation for CSC UI interactions since no public API
is available for vendor worker onboarding.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

logger = logging.getLogger(__name__)


class CSCError(Exception):
    """Base exception for CSC operations."""
    pass


class AuthenticationError(CSCError):
    """Raised when CSC authentication fails."""
    pass


class FormSubmissionError(CSCError):
    """Raised when form submission fails."""
    pass


@dataclass
class WorkerInfo:
    """Information about a vendor worker."""
    full_name: str
    email: str
    start_date: str
    end_date: str
    job_title: str
    manager_email: str
    work_location: str
    office_location: Optional[str] = None
    phone: Optional[str] = None


class CSCAutomation:
    """Browser automation for CSC vendor worker onboarding.
    
    Automates CSC UI interactions for onboarding individual vendor workers
    and bulk uploads via spreadsheet.
    
    Browser lifecycle is managed explicitly via start() and close() methods
    to ensure the browser stays alive across multiple operations.
    """
    
    CSC_URL = "https://www.internalfb.com/csc"
    LOGIN_TIMEOUT = 30000  # 30 seconds
    
    def __init__(self, headless: bool = True, screenshot_dir: str = None):
        """Initialize CSC automation.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots.
                          Defaults to ~/.vendor_onboarding/screenshots with 0700 permissions
        """
        self.headless = headless
        # Use secure default location with restricted permissions
        if screenshot_dir is None:
            screenshot_dir = Path.home() / ".vendor_onboarding" / "screenshots"
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._playwright = None
        self._browser = None
        self._page = None
        self._logged_in = False
    
    def _sanitize_email(self, email: str) -> str:
        """Sanitize email for logging (mask PII).
        
        Args:
            email: Email address to sanitize
            
        Returns:
            Sanitized email (e.g., 'john.doe@vendor.com' -> 'j***@vendor.com')
        """
        if not email or '@' not in email:
            return '***'
        local, domain = email.split('@', 1)
        if len(local) <= 1:
            return f'***@{domain}'
        return f'{local[0]}***@{domain}'
    
    def start(self):
        """Start the browser session.
        
        Must be called before login() and other operations.
        Browser will stay alive until close() is called.
        """
        if self._browser is not None:
            logger.warning("Browser already started")
            return
        
        logger.info("Starting browser session")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
    
    def close(self):
        """Close browser resources.
        
        Should be called when done with all operations.
        """
        if self._browser:
            logger.info("Closing browser session")
            self._browser.close()
            self._browser = None
            self._page = None
            self._logged_in = False
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def _take_screenshot(self, page, prefix: str = "error"):
        """Take screenshot for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"csc_{prefix}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            page.screenshot(path=str(filepath))
            logger.info(f"Screenshot saved to {filepath}")
            return str(filepath)
        except Exception as e:
            sanitized = self._sanitize_email(worker.email)
            self._take_screenshot(self._page, f"onboard_error_{sanitized}")
            logger.error(f"Failed to onboard worker {sanitized}: {e}")
            raise FormSubmissionError(f"Worker onboarding failed: {e}")
    def login(self) -> bool:
        """Login to CSC via SSO.
        
        Browser must be started via start() before calling login().
        Uses the requestor's existing SSO session.
        
        Returns:
            True if login successful
            
        Raises:
            AuthenticationError: If login fails
            CSCError: If browser not started
        """
        if self._page is None:
            raise CSCError("Browser not started. Call start() before login().")
        
        logger.info("Logging in to CSC via SSO")
        
        try:
            # Navigate to CSC
            self._page.goto(self.CSC_URL, wait_until="networkidle", timeout=self.LOGIN_TIMEOUT)
            
            # Check if already logged in (SSO session active)
            # Look for CSC dashboard elements
            try:
                self._page.wait_for_selector(
                    'text=/dashboard|welcome|home/i',
                    timeout=5000
                )
                logger.info("Already logged in via SSO")
                self._logged_in = True
                return True
            except PlaywrightTimeoutError:
                pass
            
            # If not logged in, look for login button
            login_button = self._page.query_selector('text=/log in|sign in/i')
            if login_button:
                logger.info("Clicking login button")
                login_button.click()
                self._page.wait_for_load_state("networkidle")
            
            # Wait for dashboard to confirm login
            self._page.wait_for_selector(
                'text=/dashboard|welcome|home/i',
                timeout=self.LOGIN_TIMEOUT
            )
            
            logger.info("Successfully logged in to CSC")
            self._logged_in = True
            return True
            
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during CSC login: {e}")
            self._take_screenshot(self._page, "login_error")
            raise AuthenticationError(f"CSC login timeout: {e}")
        except Exception as e:
            logger.error(f"CSC login failed: {e}")
            self._take_screenshot(self._page, "login_error")
            raise AuthenticationError(f"CSC login failed: {e}")
    
    def onboard_worker(self, worker: WorkerInfo) -> str:
        """Onboard a single vendor worker via CSC UI.
        
        Args:
            worker: Worker information (PII will be sanitized in logs)
            
        Returns:
            Worker ID assigned by CSC
            
        Raises:
            FormSubmissionError: If onboarding fails
            CSCError: If not logged in
        """
        if not self._logged_in:
            raise CSCError("Must login before onboarding workers. Call login() first.")
        
        # Sanitize PII for logging
        sanitized_email = self._sanitize_email(worker.email)
        logger.info(f"Onboarding worker: {worker.full_name} ({sanitized_email})")
        
        # TODO: Implement worker onboarding
        raise NotImplementedError("Worker onboarding not yet implemented")
    
    def bulk_upload_workers(self, workers: List[WorkerInfo], spreadsheet_path: str) -> Dict[str, Any]:
        """Upload multiple workers via CSC bulk upload.
        
        Args:
            workers: List of worker information
            spreadsheet_path: Path to generated spreadsheet
            
        Returns:
            Dictionary with upload results including uploaded_count, failed_count,
            and total_count for user-friendly progress reporting
            
        Raises:
            FormSubmissionError: If upload fails
        """
        if not self._logged_in:
            raise CSCError("Must login before bulk upload")
        
        logger.info(f"Bulk uploading {len(workers)} workers via spreadsheet")
        
        try:
            # Navigate to bulk upload page
            self._page.goto(f"{self.CSC_URL}/bulk-upload", wait_until="networkidle")
            
            # Wait for file upload input
            file_input = self._page.wait_for_selector(
                'input[type="file"]',
                timeout=10000
            )
            
            # Upload spreadsheet file
            file_input.set_input_files(spreadsheet_path)
            
            # Wait for file to be processed
            self._page.wait_for_selector('text=/processing|uploading/i', timeout=5000)
            self._page.wait_for_selector('text=/complete|ready/i', timeout=30000)
            
            # Click submit/upload button
            submit_button = self._page.wait_for_selector(
                'button:has-text("Submit"), button:has-text("Upload"), input[type="submit"]'
            )
            submit_button.click()
            
            # Wait for results
            self._page.wait_for_selector('text=/success|complete|results/i', timeout=60000)
            
            # Parse results
            # Look for success/failure counts
            result_text = self._page.content()
            
            import re
            uploaded_match = re.search(r'(\d+)\s+(?:workers?|records?)\s+(?:uploaded|processed|success)', result_text, re.I)
            failed_match = re.search(r'(\d+)\s+(?:workers?|records?)\s+(?:failed|error)', result_text, re.I)
            
            uploaded_count = int(uploaded_match.group(1)) if uploaded_match else len(workers)
            failed_count = int(failed_match.group(1)) if failed_match else 0
            
            logger.info(f"Bulk upload complete: {uploaded_count} uploaded, {failed_count} failed")
            
            return {
                "uploaded_count": uploaded_count,
                "failed_count": failed_count,
                "total_count": len(workers),
                "spreadsheet_path": spreadsheet_path
            }
            
        except Exception as e:
            self._take_screenshot(self._page, "bulk_upload_error")
            logger.error(f"Bulk upload failed: {e}")
            raise FormSubmissionError(f"Bulk upload failed: {e}")
    
    def close(self):
        """Close browser resources."""
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None
            self._logged_in = False
