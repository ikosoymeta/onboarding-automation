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
    """
    
    CSC_URL = "https://www.internalfb.com/csc"
    LOGIN_TIMEOUT = 30000  # 30 seconds
    
    def __init__(self, headless: bool = True, screenshot_dir: str = "/tmp/csc_screenshots"):
        """Initialize CSC automation.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots
        """
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._browser = None
        self._page = None
        self._logged_in = False
    
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
            logger.warning(f"Failed to take screenshot: {e}")
            return None
    
    def login(self) -> bool:
        """Login to CSC via SSO."""
        logger.info("Logging in to CSC via SSO")
        
        try:
            with sync_playwright() as p:
                self._browser = p.chromium.launch(headless=self.headless)
                self._page = self._browser.new_page()
                
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
                
                except Exception as e:
                    self._take_screenshot(self._page, "login_error")
                    raise
                
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during CSC login: {e}")
            raise AuthenticationError(f"CSC login timeout: {e}")
        except Exception as e:
            logger.error(f"CSC login failed: {e}")
            raise AuthenticationError(f"CSC login failed: {e}")
    
    def onboard_worker(self, worker: WorkerInfo) -> str:
        """Onboard a single vendor worker via CSC UI.
        
        Args:
            worker: Worker information
            
        Returns:
            Worker ID assigned by CSC
            
        Raises:
            FormSubmissionError: If onboarding fails
        """
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
