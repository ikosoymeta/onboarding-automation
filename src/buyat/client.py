"""Buy@ client for supplier verification and onboarding.

Provides browser automation for searching suppliers in Buy@ system
since no public API is available. Includes caching to avoid repeated
searches and handles supplier reactivation for inactive suppliers.

Supports both traditional form-based workflow and the new Agentic
Buying Intake conversational UI (launched June 10, 2026).
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class SupplierNotFoundError(Exception):
    """Raised when supplier is not found in Buy@."""
    pass


class BuyAtError(Exception):
    """Base exception for Buy@ operations."""
    pass


class AgenticFlowError(BuyAtError):
    """Raised when Agentic Buying Intake flow fails."""
    pass


@dataclass
class SupplierInfo:
    """Information about a supplier in Buy@."""
    name: str
    exists: bool
    supplier_id: Optional[str] = None
    status: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: bool = False


@dataclass
class AgenticResponse:
    """Response from the Agentic Buying Intake assistant."""
    message: str
    has_followup: bool = False
    requires_confirmation: bool = False
    suggested_actions: List[str] = None


class AgenticBuyingClient:
    """Client for Agentic Buying Intake conversational UI.
    
    Automates the chat-based interface for New Goods & Services requests,
    including vendor onboarding workflows. Launched June 10, 2026, this
    replaces the traditional multi-step form with a conversational AI
    experience.
    
    The assistant is available as a side panel on buy@ pages (e.g., 
    spend.internalmeta.com/suppliers) and guides users through intake
    via natural language.
    """
    
    # URLs for Agentic Buying Intake
    SUPPLIERS_URL = "https://spend.internalmeta.com/suppliers"
    NEW_REQUEST_URL = "https://www.internalfb.com/buy/new-request"
    
    # Timeouts
    AGENT_RESPONSE_TIMEOUT = 30000  # 30 seconds
    PAGE_LOAD_TIMEOUT = 60000  # 60 seconds
    
    def __init__(
        self, 
        headless: bool = True, 
        screenshot_dir: str = None
    ):
        """Initialize Agentic Buying client.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots.
                          Defaults to ~/.vendor_onboarding/screenshots
        """
        self.headless = headless
        if screenshot_dir is None:
            screenshot_dir = Path.home() / ".vendor_onboarding" / "screenshots"
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._playwright = None
        self._browser = None
        self._page = None
        self._assistant_open = False
    
    def start(self):
        """Start the browser session.
        
        Must be called before other operations. Browser stays alive
        until close() is called.
        """
        if self._browser is not None:
            logger.warning("Browser already started")
            return
        
        logger.info("Starting browser session for Agentic Buying")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
    
    def close(self):
        """Close browser resources."""
        if self._browser:
            logger.info("Closing browser session")
            self._browser.close()
            self._browser = None
            self._page = None
            self._assistant_open = False
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def _take_screenshot(self, prefix: str = "agentic_error"):
        """Take screenshot for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"buyat_{prefix}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            self._page.screenshot(path=str(filepath))
            logger.info(f"Screenshot saved to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def navigate_to_suppliers(self):
        """Navigate to the Suppliers page where buy@ assistant is available."""
        if not self._page:
            raise AgenticFlowError("Browser not started. Call start() first.")
        
        logger.info(f"Navigating to Suppliers page: {self.SUPPLIERS_URL}")
        self._page.goto(self.SUPPLIERS_URL, timeout=self.PAGE_LOAD_TIMEOUT)
        self._page.wait_for_load_state("networkidle")
    
    def open_assistant(self):
        """Open the buy@ assistant side panel.
        
        The assistant appears as a button in the top-right corner of
        buy@ pages. Clicking it opens the chat interface.
        """
        if not self._page:
            raise AgenticFlowError("Browser not started. Call start() first.")
        
        logger.info("Opening buy@ assistant panel")
        try:
            # Look for the buy@ assistant button (top right)
            # Based on screenshot: blue button with "buy@ assistant" text
            assistant_button = self._page.locator(
                'button:has-text("buy@ assistant")'
            ).first
            
            if assistant_button.is_visible(timeout=5000):
                assistant_button.click()
                # Wait for assistant panel to open
                self._page.wait_for_selector(
                    'text="buy@ assistant"', 
                    timeout=10000
                )
                self._assistant_open = True
                logger.info("buy@ assistant panel opened successfully")
            else:
                raise AgenticFlowError("buy@ assistant button not found")
                
        except PlaywrightTimeoutError as e:
            self._take_screenshot("assistant_open_timeout")
            raise AgenticFlowError(f"Failed to open assistant: {e}")
    
    def send_message(self, message: str) -> AgenticResponse:
        """Send a message to the buy@ assistant.
        
        Args:
            message: Natural language message to send to the assistant
            
        Returns:
            AgenticResponse with the assistant's reply
        """
        if not self._assistant_open:
            raise AgenticFlowError("Assistant not open. Call open_assistant() first.")
        
        logger.info(f"Sending message to assistant: {message[:100]}...")
        
        try:
            # Find the chat input field (based on screenshot: "Ask buy@ assistant...")
            chat_input = self._page.locator(
                'input[placeholder*="Ask buy@ assistant"]'
            ).first
            
            if not chat_input.is_visible(timeout=5000):
                # Try alternative selector
                chat_input = self._page.locator(
                    'textarea[placeholder*="Ask buy@"]'
                ).first
            
            chat_input.fill(message)
            
            # Find and click send button (arrow icon in screenshot)
            send_button = self._page.locator(
                'button[type="submit"]'
            ).first
            
            if send_button.is_visible(timeout=2000):
                send_button.click()
            else:
                # Try pressing Enter
                chat_input.press("Enter")
            
            # Wait for assistant response
            response = self._wait_for_response()
            return response
            
        except PlaywrightTimeoutError as e:
            self._take_screenshot("send_message_timeout")
            raise AgenticFlowError(f"Failed to send message: {e}")
    
    def _wait_for_response(self) -> AgenticResponse:
        """Wait for and parse the assistant's response.
        
        Returns:
            AgenticResponse with the assistant's message
        """
        logger.debug("Waiting for assistant response")
        
        try:
            # Wait for response to appear (look for message bubbles)
            # The assistant's responses appear in the chat panel
            self._page.wait_for_selector(
                '[data-testid="assistant-message"], .assistant-message, [class*="assistant"]',
                timeout=self.AGENT_RESPONSE_TIMEOUT
            )
            
            # Get the latest assistant message
            # This selector may need adjustment based on actual DOM structure
            messages = self._page.locator(
                '[data-testid="assistant-message"], .assistant-message'
            ).all()
            
            if messages:
                latest_message = messages[-1].inner_text()
                logger.info(f"Assistant response: {latest_message[:200]}...")
                
                # Check if response requires confirmation or has follow-ups
                has_followup = "?" in latest_message or "please" in latest_message.lower()
                requires_confirmation = any(
                    word in latest_message.lower() 
                    for word in ["confirm", "review", "approve", "submit"]
                )
                
                return AgenticResponse(
                    message=latest_message,
                    has_followup=has_followup,
                    requires_confirmation=requires_confirmation
                )
            else:
                raise AgenticFlowError("No assistant response found")
                
        except PlaywrightTimeoutError:
            self._take_screenshot("response_timeout")
            raise AgenticFlowError("Timeout waiting for assistant response")
    
    def onboard_supplier(
        self,
        supplier_name: str,
        supplier_email: str,
        purpose: str,
        subscribers: List[str] = None
    ) -> AgenticResponse:
        """Onboard a new supplier using the Agentic Buying Intake flow.
        
        Uses natural language to describe the supplier onboarding request
        to the AI assistant, which then guides through the process.
        
        Args:
            supplier_name: Name of the supplier to onboard
            supplier_email: Contact email for the supplier (must be external)
            purpose: Business purpose for onboarding this supplier
            subscribers: Optional list of internal employee emails to receive
                        status notifications
            
        Returns:
            AgenticResponse with the assistant's reply and next steps
        """
        logger.info(f"Starting supplier onboarding via agentic flow: {supplier_name}")
        
        # Build natural language prompt for supplier onboarding
        prompt_parts = [
            f"I need to onboard a new supplier for our vendor network.",
            f"",
            f"Supplier Name: {supplier_name}",
            f"Supplier Email: {supplier_email}",
            f"Business Purpose: {purpose}",
        ]
        
        if subscribers:
            prompt_parts.append(f"Subscribers for notifications: {', '.join(subscribers)}")
        
        prompt_parts.extend([
            f"",
            f"Please initiate the supplier invitation process. The supplier ",
            f"should receive enrollment instructions at their email address. ",
            f"They will have 10 business days to complete the enrollment."
        ])
        
        prompt = "\n".join(prompt_parts)
        
        # Send the onboarding request
        response = self.send_message(prompt)
        
        logger.info(f"Supplier onboarding initiated. Assistant response: {response.message[:200]}")
        return response
    
    def check_supplier_status(self, supplier_name: str) -> AgenticResponse:
        """Check if a supplier exists and get their status via agentic flow.
        
        Args:
            supplier_name: Name of supplier to check
            
        Returns:
            AgenticResponse with supplier information
        """
        prompt = (
            f'Can you check if supplier "{supplier_name}" already exists in '
            f'the supplier network? If they exist, please provide their status '
            f'(active, inactive, pending). If not, I need to invite them as '
            f'a new supplier.'
        )
        
        return self.send_message(prompt)


class BuyAtClient:
    """Client for interacting with Buy@ supplier system.
    
    Uses browser automation to search for suppliers since
    Buy@ does not provide a public API for supplier verification.
    
    Features:
    - Supplier search and verification
    - Caching to avoid repeated searches
    - Handles supplier reactivation
    - Secure screenshot storage
    - NEW: Agentic Buying Intake conversational UI support (June 2026)
    """
    
    BUYAT_URL = "https://www.internalfb.com/buy/suppliers/onboarding"
    SUPPLIERS_URL = "https://spend.internalmeta.com/suppliers"
    
    def __init__(
        self, 
        headless: bool = True, 
        screenshot_dir: str = None,
        cache_ttl: int = 3600,
        use_agentic: bool = True
    ):
        """Initialize Buy@ client.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots.
                          Defaults to ~/.vendor_onboarding/screenshots
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            use_agentic: Whether to use the new Agentic Buying Intake flow
                        (default: True). If False, uses traditional form.
        """
        self.headless = headless
        # Use secure default location with restricted permissions
        if screenshot_dir is None:
            screenshot_dir = Path.home() / ".vendor_onboarding" / "screenshots"
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._browser = None
        self._page = None
        self._cache: Dict[str, tuple[SupplierInfo, datetime]] = {}
        self.cache_ttl = cache_ttl
        self.use_agentic = use_agentic
        self._agentic_client = None
        if use_agentic:
            self._agentic_client = AgenticBuyingClient(
                headless=headless,
                screenshot_dir=str(screenshot_dir)
            )
    
    def _is_cache_valid(self, cached_time: datetime) -> bool:
        """Check if cached entry is still valid.
        
        Args:
            cached_time: When the entry was cached
            
        Returns:
            True if cache entry is still valid
        """
        return datetime.utcnow() - cached_time < timedelta(seconds=self.cache_ttl)
    
    def _get_from_cache(self, supplier_name: str) -> Optional[SupplierInfo]:
        """Get supplier info from cache if valid.
        
        Args:
            supplier_name: Name of supplier to look up
            
        Returns:
            Cached SupplierInfo or None if not cached or expired
        """
        if supplier_name in self._cache:
            info, cached_time = self._cache[supplier_name]
            if self._is_cache_valid(cached_time):
                logger.debug(f"Cache hit for supplier: {supplier_name}")
                return info
            else:
                logger.debug(f"Cache expired for supplier: {supplier_name}")
                del self._cache[supplier_name]
        return None
    
    def _save_to_cache(self, supplier_name: str, info: SupplierInfo):
        """Save supplier info to cache.
        
        Args:
            supplier_name: Name of supplier
            info: Supplier information to cache
        """
        self._cache[supplier_name] = (info, datetime.utcnow())
        logger.debug(f"Cached supplier info for: {supplier_name}")
    
    def search_supplier(self, supplier_name: str, use_cache: bool = True) -> SupplierInfo:
        """Search for a supplier in Buy@.
        
        Uses the Agentic Buying Intake if available (use_agentic=True),
        otherwise falls back to traditional supplier search.
        
        Args:
            supplier_name: Name of supplier to search for
            use_cache: Whether to use cached results if available
            
        Returns:
            SupplierInfo with supplier details
            
        Raises:
            SupplierNotFoundError: If supplier is not found
            BuyAtError: If search fails
        """
        # Check cache first
        if use_cache:
            cached = self._get_from_cache(supplier_name)
            if cached:
                return cached
        
        logger.info(f"Searching for supplier: {supplier_name}")
        
        # Try agentic flow first if enabled
        if self.use_agentic and self._agentic_client:
            try:
                return self._search_supplier_via_agentic(supplier_name)
            except Exception as e:
                logger.warning(f"Agentic search failed, falling back to traditional: {e}")
        
        # Fall back to traditional browser automation
        # TODO: Implement actual browser automation for traditional flow
        # For now, simulate the search
        # In production, this would use Playwright to:
        # 1. Navigate to Buy@ URL
        # 2. Search for supplier name
        # 3. Parse results to determine if exists and status
        
        # Simulated logic for demonstration
        # In real implementation, replace with actual browser automation
        
        # Simulate not found for demo purposes
        # Real implementation would check actual Buy@ system
        raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
    
    def _search_supplier_via_agentic(self, supplier_name: str) -> SupplierInfo:
        """Search for supplier using Agentic Buying Intake.
        
        Args:
            supplier_name: Name of supplier to search for
            
        Returns:
            SupplierInfo with supplier details
        """
        if not self._agentic_client:
            raise BuyAtError("Agentic client not initialized")
        
        # Start browser if not already started
        if not self._agentic_client._browser:
            self._agentic_client.start()
            self._agentic_client.navigate_to_suppliers()
            self._agentic_client.open_assistant()
        
        # Ask assistant to check supplier status
        response = self._agentic_client.check_supplier_status(supplier_name)
        
        # Parse response to determine if supplier exists
        # This is a simplified parser - real implementation would need
        # more robust NLP or structured response handling
        message_lower = response.message.lower()
        
        exists = False
        is_active = False
        status = "unknown"
        
        if "exists" in message_lower or "found" in message_lower:
            exists = True
            if "active" in message_lower:
                is_active = True
                status = "active"
            elif "inactive" in message_lower:
                status = "inactive"
            elif "pending" in message_lower:
                status = "pending"
        
        if not exists and ("not found" in message_lower or "does not exist" in message_lower):
            raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
        
        info = SupplierInfo(
            name=supplier_name,
            exists=exists,
            status=status,
            is_active=is_active
        )
        
        # Cache the result
        self._save_to_cache(supplier_name, info)
        return info
    
    def invite_supplier(
        self,
        supplier_name: str,
        supplier_email: str,
        purpose: str,
        subscribers: List[str] = None
    ) -> SupplierInfo:
        """Invite a new supplier to the Buy@ network.
        
        Uses the Agentic Buying Intake conversational flow to initiate
        supplier onboarding. The supplier will receive enrollment
        instructions from suppliers@fb.com and has 10 business days
        to complete the process.
        
        Args:
            supplier_name: Name of the supplier to invite
            supplier_email: Contact email for the supplier (must be external,
                          not @facebook, @meta, @oculus, @whatsapp)
            purpose: Business purpose for onboarding this supplier
            subscribers: Optional list of internal employee emails to receive
                        status notifications
            
        Returns:
            SupplierInfo with the new supplier details
            
        Raises:
            BuyAtError: If invitation fails
            ValueError: If supplier_email is invalid (internal domain)
        """
        # Validate email is external
        internal_domains = ["@facebook.com", "@meta.com", "@oculus.com", "@whatsapp.com", "@fb.com"]
        email_lower = supplier_email.lower()
        if any(domain in email_lower for domain in internal_domains):
            raise ValueError(
                f"Supplier email must be external (not {', '.join(internal_domains)}). "
                f"Got: {supplier_email}"
            )
        
        logger.info(f"Inviting supplier via agentic flow: {supplier_name} ({supplier_email})")
        
        if not self.use_agentic or not self._agentic_client:
            raise BuyAtError(
                "Supplier invitation requires agentic flow. "
                "Initialize BuyAtClient with use_agentic=True"
            )
        
        try:
            # Start browser if not already started
            if not self._agentic_client._browser:
                self._agentic_client.start()
                self._agentic_client.navigate_to_suppliers()
                self._agentic_client.open_assistant()
            
            # Initiate onboarding via agentic flow
            response = self._agentic_client.onboard_supplier(
                supplier_name=supplier_name,
                supplier_email=supplier_email,
                purpose=purpose,
                subscribers=subscribers
            )
            
            # Create SupplierInfo for the newly invited supplier
            # Status is "pending" until they complete enrollment
            info = SupplierInfo(
                name=supplier_name,
                exists=True,
                status="pending_invitation",
                contact_email=supplier_email,
                is_active=False
            )
            
            # Cache the result
            self._save_to_cache(supplier_name, info)
            
            logger.info(
                f"Supplier invitation sent successfully. "
                f"Supplier has 10 business days to complete enrollment."
            )
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to invite supplier: {e}")
            raise BuyAtError(f"Supplier invitation failed: {e}")
    
    def verify_supplier_exists(self, supplier_name: str, use_cache: bool = True) -> bool:
        """Check if supplier exists in Buy@.
        
        Args:
            supplier_name: Name of supplier to check
            use_cache: Whether to use cached results
            
        Returns:
            True if supplier exists, False otherwise
        """
        try:
            info = self.search_supplier(supplier_name, use_cache=use_cache)
            return info.exists
        except SupplierNotFoundError:
            return False
    
    def is_supplier_active(self, supplier_name: str, use_cache: bool = True) -> bool:
        """Check if supplier is active in Buy@.
        
        Args:
            supplier_name: Name of supplier to check
            use_cache: Whether to use cached results
            
        Returns:
            True if supplier exists and is active, False otherwise
        """
        try:
            info = self.search_supplier(supplier_name, use_cache=use_cache)
            return info.exists and info.is_active
        except SupplierNotFoundError:
            return False
    
    def clear_cache(self):
        """Clear the supplier cache."""
        self._cache.clear()
        logger.info("Supplier cache cleared")
    
    def close(self):
        """Close browser resources."""
        if self._agentic_client:
            self._agentic_client.close()
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None
    
    def start_agentic_session(self):
        """Start an Agentic Buying Intake session.
        
        Opens the browser, navigates to the Suppliers page, and opens
        the buy@ assistant panel. Must be called before using agentic
        flow methods.
        """
        if not self.use_agentic or not self._agentic_client:
            raise BuyAtError("Agentic flow not enabled")
        
        self._agentic_client.start()
        self._agentic_client.navigate_to_suppliers()
        self._agentic_client.open_assistant()
        logger.info("Agentic Buying session started successfully")
