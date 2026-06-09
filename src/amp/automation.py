"""AMP browser automation for group management.

Provides browser automation for AMP (Access Management Platform) UI interactions
since no public API is available for group management operations.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

logger = logging.getLogger(__name__)


class AMPError(Exception):
    """Base exception for AMP operations."""
    pass


class AuthenticationError(AMPError):
    """Raised when AMP authentication fails."""
    pass


class GroupManagementError(AMPError):
    """Raised when group management operations fail."""
    pass


@dataclass
class AMPGroup:
    """Information about an AMP group."""
    name: str
    description: str
    members: List[str]
    group_id: Optional[str] = None
    created: bool = False


class AMPAutomation:
    """Browser automation for AMP group management.
    
    Automates AMP UI interactions for creating and managing groups,
    including dynamic membership configuration.
    
    Browser lifecycle is managed explicitly via start() and close() methods
    to ensure the browser stays alive across multiple operations.
    """
    
    AMP_URL = "https://www.internalfb.com/amp"
    LOGIN_TIMEOUT = 30000  # 30 seconds
    
    def __init__(self, headless: bool = True, screenshot_dir: str = None):
        """Initialize AMP automation.
        
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
    
    def _take_screenshot(self, page, prefix: str = "error"):
        """Take screenshot for debugging.
        
        Args:
            page: Playwright page object
            prefix: Prefix for screenshot filename
            
        Returns:
            Path to screenshot file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"amp_{prefix}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            page.screenshot(path=str(filepath))
            logger.info(f"Screenshot saved to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None
    
    def start(self):
        """Start the browser session.
        
        Must be called before login() and other operations.
        Browser will stay alive until close() is called.
        """
        if self._browser is not None:
            logger.warning("Browser already started")
            return
        
        logger.info("Starting AMP browser session")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
    
    def close(self):
        """Close browser resources.
        
        Should be called when done with all operations.
        """
        if self._browser:
            logger.info("Closing AMP browser session")
            self._browser.close()
            self._browser = None
            self._page = None
            self._logged_in = False
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def login(self) -> bool:
        """Login to AMP via SSO.
        
        Browser must be started via start() before calling login().
        Uses the requestor's existing SSO session. Handles YubiKey
        authentication if required.
        
        Returns:
            True if login successful
            
        Raises:
            AuthenticationError: If login fails
            AMPError: If browser not started
        """
        if self._page is None:
            raise AMPError("Browser not started. Call start() before login().")
        
        logger.info("Logging in to AMP via SSO")
        
        try:
            # Navigate to AMP
            self._page.goto(self.AMP_URL, wait_until="networkidle", timeout=self.LOGIN_TIMEOUT)
            
            # Check if already logged in (SSO session active)
            try:
                self._page.wait_for_selector(
                    'text=/dashboard|groups|welcome/i',
                    timeout=5000
                )
                logger.info("Already logged in to AMP via SSO")
                self._logged_in = True
                return True
            except PlaywrightTimeoutError:
                pass
            
            # If not logged in, look for login button
            login_button = self._page.query_selector('text=/log in|sign in/i')
            if login_button:
                logger.info("Clicking AMP login button")
                login_button.click()
                self._page.wait_for_load_state("networkidle")
            
            # Handle YubiKey authentication if prompted
            try:
                yubikey_prompt = self._page.wait_for_selector(
                    'text=/yubikey|security key|touch/i',
                    timeout=5000
                )
                if yubikey_prompt:
                    logger.info("YubiKey authentication required - waiting for user interaction")
                    # Wait for YubiKey touch (up to 30 seconds)
                    self._page.wait_for_selector(
                        'text=/dashboard|groups|welcome/i',
                        timeout=30000
                    )
            except PlaywrightTimeoutError:
                pass  # No YubiKey prompt, continue
            
            # Wait for dashboard to confirm login
            self._page.wait_for_selector(
                'text=/dashboard|groups|welcome/i',
                timeout=self.LOGIN_TIMEOUT
            )
            
            logger.info("Successfully logged in to AMP")
            self._logged_in = True
            return True
            
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during AMP login: {e}")
            self._take_screenshot(self._page, "login_error")
            raise AuthenticationError(f"AMP login timeout: {e}")
        except Exception as e:
            logger.error(f"AMP login failed: {e}")
            self._take_screenshot(self._page, "login_error")
            raise AuthenticationError(f"AMP login failed: {e}")
    
    def create_group(self, group: AMPGroup) -> str:
        """Create a new AMP group.
        
        Args:
            group: AMPGroup with name, description, and initial members
            
        Returns:
            Group ID assigned by AMP
            
        Raises:
            GroupManagementError: If group creation fails
            AMPError: If not logged in
        """
        if not self._logged_in:
            raise AMPError("Must login before creating groups. Call login() first.")
        
        logger.info(f"Creating AMP group: {group.name}")
        
        try:
            # Navigate to group creation page
            self._page.goto(f"{self.AMP_URL}/groups/new", wait_until="networkidle")
            
            # Fill group name
            name_input = self._page.wait_for_selector(
                'input[name*="name" i], input[id*="name" i]',
                timeout=10000
            )
            name_input.fill(group.name)
            
            # Fill description
            desc_input = self._page.wait_for_selector(
                'textarea[name*="description" i], textarea[id*="description" i]'
            )
            desc_input.fill(group.description)
            
            # Add initial members
            for member in group.members:
                member_input = self._page.wait_for_selector(
                    'input[placeholder*="member" i], input[name*="member" i]'
                )
                member_input.fill(member)
                member_input.press("Enter")
                # Wait for member to be added
                self._page.wait_for_timeout(500)
            
            # Submit form
            submit_button = self._page.wait_for_selector(
                'button[type="submit"], button:has-text("Create"), button:has-text("Save")'
            )
            submit_button.click()
            
            # Wait for confirmation
            self._page.wait_for_selector(
                'text=/success|created|group id/i',
                timeout=15000
            )
            
            # Extract group ID
            import re
            content = self._page.content()
            match = re.search(r'group[_\s]+id[:\s]+([a-zA-Z0-9_-]+)', content, re.I)
            if match:
                group_id = match.group(1)
                logger.info(f"AMP group created successfully with ID: {group_id}")
                return group_id
            
            # Fallback: use group name as ID
            logger.warning("Could not extract group ID, using name as identifier")
            return group.name
            
        except Exception as e:
            self._take_screenshot(self._page, f"create_group_error_{group.name}")
            logger.error(f"Failed to create AMP group {group.name}: {e}")
            raise GroupManagementError(f"Group creation failed: {e}")
    
    def add_members(self, group_id: str, members: List[str]) -> bool:
        """Add members to an existing AMP group.
        
        Args:
            group_id: ID of the group to modify
            members: List of member emails to add
            
        Returns:
            True if members added successfully
            
        Raises:
            GroupManagementError: If operation fails
        """
        if not self._logged_in:
            raise AMPError("Must login before managing groups")
        
        logger.info(f"Adding {len(members)} members to AMP group {group_id}")
        
        try:
            # Navigate to group page
            self._page.goto(f"{self.AMP_URL}/groups/{group_id}", wait_until="networkidle")
            
            # Find and click "Add Members" button
            add_button = self._page.wait_for_selector(
                'button:has-text("Add"), button:has-text("Add Members")',
                timeout=10000
            )
            add_button.click()
            
            # Add each member
            for member in members:
                member_input = self._page.wait_for_selector(
                    'input[placeholder*="email" i], input[placeholder*="member" i]'
                )
                member_input.fill(member)
                member_input.press("Enter")
                self._page.wait_for_timeout(500)
            
            # Save changes
            save_button = self._page.wait_for_selector(
                'button:has-text("Save"), button:has-text("Confirm")'
            )
            save_button.click()
            
            # Wait for confirmation
            self._page.wait_for_selector(
                'text=/success|updated|saved/i',
                timeout=10000
            )
            
            logger.info(f"Successfully added {len(members)} members to group {group_id}")
            return True
            
        except Exception as e:
            self._take_screenshot(self._page, f"add_members_error_{group_id}")
            logger.error(f"Failed to add members to group {group_id}: {e}")
            raise GroupManagementError(f"Add members failed: {e}")
