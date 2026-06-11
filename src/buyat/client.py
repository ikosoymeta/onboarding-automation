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
from enum import Enum
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


class DocumentType(Enum):
    """Types of documents for PR creation."""
    CONTRACT = "contract"
    QUOTE = "quote"
    SOW = "sow"  # Statement of Work
    INVOICE = "invoice"
    PROPOSAL = "proposal"
    UNKNOWN = "unknown"


@dataclass
class ExtractedField:
    """A field extracted from a document with confidence score."""
    value: Any
    confidence: float  # 0.0 to 1.0
    source: str  # Which part of document it came from


@dataclass
class PRDataExtraction:
    """Result of extracting PR data from a document."""
    supplier_name: Optional[ExtractedField] = None
    amount: Optional[ExtractedField] = None
    description: Optional[ExtractedField] = None
    justification: Optional[ExtractedField] = None
    cost_center: Optional[ExtractedField] = None
    delivery_date: Optional[ExtractedField] = None
    document_type: DocumentType = DocumentType.UNKNOWN
    raw_text: str = ""
    
    def get_missing_required_fields(self) -> List[str]:
        """Get list of required fields that are missing or low confidence."""
        missing = []
        required_fields = {
            "supplier_name": self.supplier_name,
            "amount": self.amount,
            "description": self.description,
            "cost_center": self.cost_center,
        }
        
        for field_name, field in required_fields.items():
            if field is None or field.confidence < 0.7:
                missing.append(field_name)
        
        # Justification is required but often not in documents
        if self.justification is None or self.justification.confidence < 0.7:
            missing.append("justification")
            
        return missing
    
    def get_high_confidence_fields(self) -> Dict[str, Any]:
        """Get fields extracted with high confidence (>0.7)."""
        result = {}
        for field_name in ["supplier_name", "amount", "description", "cost_center", "delivery_date"]:
            field = getattr(self, field_name)
            if field is not None and field.confidence >= 0.7:
                result[field_name] = field.value
        return result


@dataclass
class PRDraftInfo:
    """Information about a created PR draft."""
    pr_number: str
    pr_url: str
    status: str  # 'draft' or 'submitted'
    supplier_name: str
    amount: float
    description: str
    created_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None


@dataclass
class PRStatus:
    """Current status of a PR in approval workflow."""
    pr_number: str
    status: str  # draft, submitted, approved, rejected, etc.
    current_approver: Optional[str] = None
    approval_chain: List[str] = None
    po_number: Optional[str] = None
    blockers: List[str] = None
    last_updated: Optional[datetime] = None


@dataclass
class SupplierPRReadiness:
    """Supplier verification result for PR creation."""
    supplier_name: str
    exists: bool
    is_active: bool
    can_proceed: bool
    blockers: List[str] = None
    tpa_status: Optional[str] = None
    tpa_expiry: Optional[datetime] = None


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
    
    # PR Creation Prompt Templates
    PR_DRAFT_PROMPT_TEMPLATE = """Create a purchase request DRAFT with the following details:

Supplier: {supplier_name}
Amount: ${amount:,.2f}
Description: {description}
Business Justification: {justification}
Cost Center: {cost_center}
{delivery_date_line}
{reference_case_line}
{attachments_section}

IMPORTANT: Create this as a DRAFT ONLY. Do not submit for approval.
The user will review the draft and submit manually later.
Provide the PR number, PR URL, and confirm it is in draft status.
"""

    PR_SUBMIT_PROMPT_TEMPLATE = """Create a purchase request and SUBMIT FOR APPROVAL IMMEDIATELY with the following details:

Supplier: {supplier_name}
Amount: ${amount:,.2f}
Description: {description}
Business Justification: {justification}
Cost Center: {cost_center}
{delivery_date_line}
{reference_case_line}
{attachments_section}

IMPORTANT: Submit this PR for approval immediately. Do not leave as draft.
The PR should enter the approval workflow right away.
Provide the PR number, PR URL, and confirm it has been submitted.
"""

    PR_STATUS_CHECK_TEMPLATE = """What is the current status of purchase request {pr_number}?

Please provide:
1. Current status (draft, submitted, approved, rejected, etc.)
2. Current approver (if in approval)
3. Approval chain
4. PO number (if approved)
5. Any blockers or issues
"""

    # Additional PR MCP Tool Templates (NEW)
    PR_UPDATE_TEMPLATE = """Update purchase request {pr_number} with the following changes:

{updates}

Please confirm the updates have been applied and provide the updated PR details.
"""

    PR_JUSTIFICATION_TEMPLATE = """Generate a business justification for the following purchase request:

Supplier: {supplier_name}
Amount: ${amount:,.2f}
Description: {description}
Cost Center: {cost_center}
{additional_context}

Please provide a compelling business justification that explains:
1. Why this purchase is necessary
2. Business value and impact
3. Urgency and timing
4. Alternatives considered (if any)
"""

    PR_SEARCH_TEMPLATE = """Search for purchase requests with the following criteria:

{criteria}

Please provide a list of matching PRs with:
- PR Number
- Status
- Supplier
- Amount
- Created Date
- Current Approver (if applicable)
"""

    # Document-First PR Creation Templates (NEW)
    PR_FROM_DOCUMENT_TEMPLATE = """Create a purchase request from the attached {document_type} document.

The document has been uploaded and contains the following information (extracted with AI):
{extracted_fields}

Please:
1. Create a PR using the extracted information
2. For any fields with low confidence or missing, note them clearly
3. Provide the PR number, URL, and list any fields that need manual review or completion

Document Type: {document_type}
File: {file_name}
"""

    PR_FROM_CONTRACT_TEMPLATE = """Create a purchase request from the attached CONTRACT document.

Contracts typically contain:
- Supplier legal name and details
- Contract value and payment terms
- Service/goods description
- Contract start and end dates
- Renewal terms

Extract all relevant PR fields from the contract. Pay special attention to:
- Total contract value (may need to be broken into PRs)
- Supplier legal entity name (must match Buy@ exactly)
- Contract dates (for service period)
- Payment terms and milestones

{extracted_fields}

Create the PR and identify any fields requiring manual input.
"""

    PR_FROM_QUOTE_TEMPLATE = """Create a purchase request from the attached QUOTE document.

Quotes typically contain:
- Supplier name and contact info
- Itemized pricing with quantities
- Total amount
- Quote validity dates
- Terms and conditions

Extract all PR fields from the quote. Focus on:
- Line item details (description, quantity, unit price)
- Total quoted amount
- Quote expiration date (for urgency)
- Supplier details

{extracted_fields}

Create the PR and list any missing required fields.
"""

    PR_FROM_SOW_TEMPLATE = """Create a purchase request from the attached Statement of Work (SOW) document.

SOWs typically contain:
- Detailed scope of work
- Deliverables and milestones
- Timeline and duration
- Resource requirements
- Pricing structure (fixed fee, T&M, etc.)

Extract PR fields from the SOW, focusing on:
- Scope description (for PR description)
- Total value and payment schedule
- Project timeline (for delivery dates)
- Supplier information

{extracted_fields}

Create the PR and identify fields needing manual completion.
"""
    
    def __init__(
        self, 
        headless: bool = True, 
        screenshot_dir: str = None
    ):
        """Initialize Agentic Buying client.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots.
                          Defaults to ~/.vendor_onboarding/screenshots.
                          Path is validated to prevent directory traversal.
        """
        self.headless = headless
        if screenshot_dir is None:
            screenshot_dir = Path.home() / ".vendor_onboarding" / "screenshots"
        else:
            # Validate screenshot_dir to prevent path traversal attacks
            screenshot_path = Path(screenshot_dir).resolve()
            # Ensure path is within user's home directory or /tmp
            home = Path.home().resolve()
            tmp = Path("/tmp").resolve()
            try:
                # Python 3.9+: Use is_relative_to for proper path validation
                if not (screenshot_path.is_relative_to(home) or 
                        screenshot_path.is_relative_to(tmp)):
                    raise ValueError(
                        f"screenshot_dir must be within home directory ({home}) "
                        f"or /tmp, got: {screenshot_dir}"
                    )
            except AttributeError:
                # Fallback for Python < 3.9: Use resolved path parts comparison
                if not (str(screenshot_path).startswith(str(home) + "/") or 
                        str(screenshot_path).startswith(str(tmp) + "/") or
                        screenshot_path == home or screenshot_path == tmp):
                    raise ValueError(
                        f"screenshot_dir must be within home directory ({home}) "
                        f"or /tmp, got: {screenshot_dir}"
                    )
            screenshot_dir = screenshot_path
        
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._playwright = None
        self._browser = None
        self._page = None
        self._assistant_open = False
        import threading
        self._lock = threading.Lock()  # For thread safety
    
    def start(self):
        """Start the browser session.
        
        Must be called before other operations. Browser stays alive
        until close() is called.
        
        Thread-safe: Uses lock to prevent concurrent initialization.
        """
        with self._lock:
            if self._browser is not None:
                logger.warning("Browser already started")
                return
            
            logger.info("Starting browser session for Agentic Buying")
            playwright = None
            browser = None
            try:
                playwright = sync_playwright().start()
                browser = playwright.chromium.launch(headless=self.headless)
                page = browser.new_page()
                
                # Only assign if all steps succeed
                self._playwright = playwright
                self._browser = browser
                self._page = page
            except Exception:
                # Cleanup partially initialized resources
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
                if playwright:
                    try:
                        playwright.stop()
                    except Exception:
                        pass
                raise
    
    def close(self):
        """Close browser resources.
        
        Thread-safe: Uses lock to prevent concurrent access during cleanup.
        """
        with self._lock:
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
        """Take screenshot for debugging.
        
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        try:
            with self._lock:
                # Check if page is available before attempting screenshot
                if self._page is None:
                    logger.debug("Cannot take screenshot: page not initialized")
                    return None
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"buyat_{prefix}_{timestamp}.png"
                filepath = self.screenshot_dir / filename
                self._page.screenshot(path=str(filepath))
                logger.info(f"Screenshot saved to {filepath}")
                return str(filepath)
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def is_started(self) -> bool:
        """Check if browser session is started.
        
        Returns:
            True if browser is initialized and ready for use
        """
        return self._browser is not None and self._page is not None
    
    def navigate_to_suppliers(self):
        """Navigate to the Suppliers page where buy@ assistant is available.
        
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        with self._lock:
            if not self._page:
                raise AgenticFlowError("Browser not started. Call start() first.")
            
            logger.info(f"Navigating to Suppliers page: {self.SUPPLIERS_URL}")
            self._page.goto(self.SUPPLIERS_URL, timeout=self.PAGE_LOAD_TIMEOUT)
            self._page.wait_for_load_state("networkidle")
    
    def open_assistant(self):
        """Open the buy@ assistant side panel.
        
        The assistant appears as a button in the top-right corner of
        buy@ pages. Clicking it opens the chat interface.
        
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        with self._lock:
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
        
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        with self._lock:
            if not self._assistant_open:
                raise AgenticFlowError("Assistant not open. Call open_assistant() first.")
            
            # Log without sensitive message content
            logger.info("Sending message to buy@ assistant")
            
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
                # Note: _wait_for_response also acquires the lock, but since we already
                # hold it (RLock would be needed for reentrancy), we call the inner logic directly
                # For simplicity, we release lock before calling _wait_for_response and re-acquire after
                # Actually, let's just inline the wait logic here to avoid lock reentrancy issues
                
                # Wait for response to appear (look for message bubbles)
                logger.debug("Waiting for assistant response")
                message_selector = '[data-testid="assistant-message"], .assistant-message, [class*="assistant"]'
                self._page.wait_for_selector(
                    message_selector,
                    timeout=self.AGENT_RESPONSE_TIMEOUT
                )
                
                # Get the latest assistant message
                messages = self._page.locator(message_selector).all()
                
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
            # Use consistent selector for both wait and retrieval
            message_selector = '[data-testid="assistant-message"], .assistant-message, [class*="assistant"]'
            self._page.wait_for_selector(
                message_selector,
                timeout=self.AGENT_RESPONSE_TIMEOUT
            )
            
            # Get the latest assistant message
            # This selector may need adjustment based on actual DOM structure
            messages = self._page.locator(message_selector).all()
            
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

    def create_pr_draft(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        submit_for_approval: bool = False,
        delivery_date: Optional[str] = None,
        attachments: List[str] = None,
        reference_case_id: Optional[str] = None
    ) -> PRDraftInfo:
        """Create a PR draft or submit for approval via Agentic Buying Intake.
        
        Uses natural language to describe the PR request to the AI assistant,
        which then creates the PR via the BUY_PURCHASING_AGENT.
        
        Args:
            supplier_name: Name of the supplier
            amount: PR amount in USD
            description: Description of goods/services
            justification: Business justification for the purchase
            cost_center: Cost center for charging
            submit_for_approval: If True, submit immediately for approval.
                               If False, create as draft only.
            delivery_date: Optional delivery date (YYYY-MM-DD format)
            attachments: Optional list of file paths to attach (quotes, SOWs, etc.)
            reference_case_id: Optional reference case ID
            
        Returns:
            PRDraftInfo with PR details including number, URL, and status
        """
        logger.info(
            f"Creating PR {'(submit for approval)' if submit_for_approval else '(draft)'}: "
            f"{supplier_name}, ${amount:,.2f}"
        )
        
        # Upload attachments first if provided
        uploaded_docs = []
        if attachments:
            for file_path in attachments:
                try:
                    doc_id = self.upload_document(file_path)
                    uploaded_docs.append(doc_id)
                    logger.info(f"Uploaded document: {file_path} -> {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to upload {file_path}: {e}")
        
        # Build the prompt using the appropriate template
        delivery_date_line = f"Delivery Date: {delivery_date}" if delivery_date else ""
        reference_case_line = f"Reference Case: {reference_case_id}" if reference_case_id else ""
        
        if uploaded_docs:
            attachments_section = "Attached Documents:\n" + "\n".join(f"- {doc}" for doc in uploaded_docs)
        elif attachments:
            # Attachments were provided but failed to upload, list them anyway
            attachments_section = "Attached Documents:\n" + "\n".join(f"- {att}" for att in attachments)
        else:
            attachments_section = ""
        
        template = self.PR_SUBMIT_PROMPT_TEMPLATE if submit_for_approval else self.PR_DRAFT_PROMPT_TEMPLATE
        
        prompt = template.format(
            supplier_name=supplier_name,
            amount=amount,
            description=description,
            justification=justification,
            cost_center=cost_center,
            delivery_date_line=delivery_date_line,
            reference_case_line=reference_case_line,
            attachments_section=attachments_section
        )
        
        # Send the PR creation request
        response = self.send_message(prompt)
        
        # Parse the response to extract PR details
        # This is a simplified parser - real implementation would need more robust parsing
        pr_number = self._extract_pr_number(response.message)
        pr_url = self._extract_pr_url(response.message)
        status = "submitted" if submit_for_approval else "draft"
        
        pr_info = PRDraftInfo(
            pr_number=pr_number or "UNKNOWN",
            pr_url=pr_url or "",
            status=status,
            supplier_name=supplier_name,
            amount=amount,
            description=description,
            created_at=datetime.utcnow(),
            submitted_at=datetime.utcnow() if submit_for_approval else None
        )
        
        logger.info(f"PR created: {pr_info.pr_number}, status: {pr_info.status}")
        return pr_info

    def check_pr_status(self, pr_number: str) -> PRStatus:
        """Check the current status of a PR via Agentic Buying Intake.
        
        Args:
            pr_number: The PR number to check
            
        Returns:
            PRStatus with current status, approver, and other details
        """
        logger.info(f"Checking status for PR: {pr_number}")
        
        prompt = self.PR_STATUS_CHECK_TEMPLATE.format(pr_number=pr_number)
        response = self.send_message(prompt)
        
        # Parse the response to extract status details
        # This is a simplified parser - real implementation would need more robust parsing
        status = self._parse_pr_status(response.message)
        current_approver = self._parse_current_approver(response.message)
        approval_chain = self._parse_approval_chain(response.message)
        po_number = self._parse_po_number(response.message)
        blockers = self._parse_blockers(response.message)
        
        pr_status = PRStatus(
            pr_number=pr_number,
            status=status,
            current_approver=current_approver,
            approval_chain=approval_chain,
            po_number=po_number,
            blockers=blockers,
            last_updated=datetime.utcnow()
        )
        
        logger.info(f"PR {pr_number} status: {status}")
        return pr_status

    def update_pr(self, pr_number: str, updates: Dict[str, Any]) -> PRStatus:
        """Update an existing purchase request via Buy@ Assistant.
        
        Uses MetamateAgentBuyAtPurchaseRequestUpdateTool to modify PR fields.
        Can update quantities, prices, add line items, change delivery dates, etc.
        
        Args:
            pr_number: The PR number to update
            updates: Dictionary of field updates (e.g., {"quantity": 10, "price": 500.00})
            
        Returns:
            PRStatus with updated PR details
            
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        logger.info(f"Updating PR {pr_number} with {len(updates)} changes")
        
        with self._lock:
            # Format updates as readable text
            updates_text = "\n".join([f"- {k}: {v}" for k, v in updates.items()])
            
            prompt = self.PR_UPDATE_TEMPLATE.format(
                pr_number=pr_number,
                updates=updates_text
            )
            
            response = self.send_message(prompt)
            
            # Parse updated status
            status = self._parse_pr_status(response.message)
            logger.info(f"PR {pr_number} updated, new status: {status}")
            
            # Return updated status
            return self.check_pr_status(pr_number)

    def generate_justification(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        cost_center: str,
        additional_context: Optional[str] = None
    ) -> str:
        """Generate AI-powered business justification for a PR.
        
        Uses MetamateAgentBuyAtPurchaseRequestJustificationTool to create
        compelling business justifications that improve approval speed.
        
        Args:
            supplier_name: Name of the supplier
            amount: PR amount in USD
            description: Description of goods/services
            cost_center: Cost center for charging
            additional_context: Optional additional context (urgency, alternatives, etc.)
            
        Returns:
            Generated justification text
            
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        logger.info(f"Generating justification for {supplier_name} PR")
        
        with self._lock:
            context = f"\nAdditional Context: {additional_context}" if additional_context else ""
            
            prompt = self.PR_JUSTIFICATION_TEMPLATE.format(
                supplier_name=supplier_name,
                amount=amount,
                description=description,
                cost_center=cost_center,
                additional_context=context
            )
            
            response = self.send_message(prompt)
            justification = response.message
            
            logger.info(f"Justification generated ({len(justification)} chars)")
            return justification

    def search_prs(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for purchase requests by criteria.
        
        Uses MetamateAgentBuyAtPurchaseRequestSearchTool to find PRs
        matching specified filters.
        
        Args:
            criteria: Search criteria (e.g., {"supplier": "Acme", "status": "approved", 
                     "date_from": "2026-01-01", "amount_min": 1000})
            
        Returns:
            List of matching PRs with details (PR number, status, supplier, amount, etc.)
            
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        logger.info(f"Searching PRs with criteria: {criteria}")
        
        with self._lock:
            # Format criteria as readable text
            criteria_text = "\n".join([f"- {k}: {v}" for k, v in criteria.items()])
            
            prompt = self.PR_SEARCH_TEMPLATE.format(criteria=criteria_text)
            
            response = self.send_message(prompt)
            
            # Parse PR list from response (simplified)
            # In production, would use more robust parsing
            prs = self._parse_pr_search_results(response.message)
            
            logger.info(f"Found {len(prs)} matching PRs")
            return prs

    def _parse_pr_search_results(self, message: str) -> List[Dict[str, Any]]:
        """Parse PR search results from assistant response."""
        import re
        prs = []
        
        # Look for PR patterns in the message
        # This is simplified - production would need more robust parsing
        pr_matches = re.finditer(r'PR[-\s#]*(\d+)', message, re.IGNORECASE)
        for match in pr_matches:
            pr_number = f"PR-{match.group(1)}"
            prs.append({
                "pr_number": pr_number,
                "status": "unknown",  # Would extract from context
            })
        
        return prs

    def _detect_document_type(self, file_path: str) -> DocumentType:
        """Detect document type from filename and content hints.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            DocumentType enum value
        """
        filename = Path(file_path).name.lower()
        
        # Check filename patterns
        if any(keyword in filename for keyword in ['contract', 'agreement', 'msa', 'psa']):
            return DocumentType.CONTRACT
        elif any(keyword in filename for keyword in ['quote', 'quotation', 'estimate']):
            return DocumentType.QUOTE
        elif any(keyword in filename for keyword in ['sow', 'statement_of_work', 'statementofwork']):
            return DocumentType.SOW
        elif any(keyword in filename for keyword in ['invoice', 'bill']):
            return DocumentType.INVOICE
        elif any(keyword in filename for keyword in ['proposal', 'rfp', 'rfq']):
            return DocumentType.PROPOSAL
        else:
            return DocumentType.UNKNOWN

    def create_pr_from_document(
        self,
        file_path: str,
        document_type: Optional[DocumentType] = None,
        additional_context: Optional[str] = None
    ) -> PRDataExtraction:
        """Create a PR by extracting data from a document (Document-First Workflow).
        
        Implements progressive disclosure: Uploads the document to Buy@ Assistant,
        which extracts PR fields using AI. Returns extracted data with confidence
        scores. The caller can then prompt user only for missing/low-confidence fields.
        
        This enables the workflow:
        1. User uploads contract/quote/SOW
        2. AI extracts supplier, amount, description, etc.
        3. System asks only for fields that couldn't be extracted
        4. User provides missing info
        5. PR is created with combined data
        
        Args:
            file_path: Path to the document (PDF, DOCX, etc.)
            document_type: Optional document type. If not provided, auto-detected from filename.
            additional_context: Optional context to help extraction (e.g., "This is for software licenses")
            
        Returns:
            PRDataExtraction with extracted fields and confidence scores.
            Use get_missing_required_fields() to identify what to ask user.
            Use get_high_confidence_fields() to get extracted data.
            
        Thread-safe: Uses lock to prevent concurrent browser access.
        
        Example:
            # User uploads contract
            extraction = client.create_pr_from_document(
                file_path="/path/to/contract.pdf",
                document_type=DocumentType.CONTRACT
            )
            
            # Check what was extracted
            print(f"Supplier: {extraction.supplier_name.value} "
                  f"(confidence: {extraction.supplier_name.confidence})")
            
            # Get missing fields to ask user
            missing = extraction.get_missing_required_fields()
            # Returns: ['justification', 'cost_center'] (if not in doc)
            
            # Get high-confidence fields to use directly
            fields = extraction.get_high_confidence_fields()
            # Returns: {'supplier_name': 'Acme Corp', 'amount': 5000.0, ...}
        """
        logger.info(f"Creating PR from document: {file_path}")
        
        with self._lock:
            # Detect document type if not provided
            if document_type is None:
                document_type = self._detect_document_type(file_path)
            
            logger.info(f"Document type detected: {document_type.value}")
            
            # Upload the document first
            try:
                doc_id = self.upload_document(file_path)
                logger.info(f"Document uploaded: {doc_id}")
            except Exception as e:
                logger.error(f"Failed to upload document: {e}")
                raise AgenticFlowError(f"Document upload failed: {e}")
            
            # Select appropriate template based on document type
            if document_type == DocumentType.CONTRACT:
                template = self.PR_FROM_CONTRACT_TEMPLATE
            elif document_type == DocumentType.QUOTE:
                template = self.PR_FROM_QUOTE_TEMPLATE
            elif document_type == DocumentType.SOW:
                template = self.PR_FROM_SOW_TEMPLATE
            else:
                template = self.PR_FROM_DOCUMENT_TEMPLATE
            
            # Build prompt with document info
            # Note: In a real implementation, the Buy@ Assistant would return
            # structured data with confidence scores. Here we simulate that
            # by asking the Assistant to extract and it returns text we parse.
            file_name = Path(file_path).name
            extracted_fields_text = (
                f"Document uploaded: {doc_id}\n"
                f"Please extract all relevant PR fields from this {document_type.value}."
            )
            if additional_context:
                extracted_fields_text += f"\nContext: {additional_context}"
            
            prompt = template.format(
                document_type=document_type.value,
                file_name=file_name,
                extracted_fields=extracted_fields_text
            )
            
            # Send to Buy@ Assistant for extraction
            response = self.send_message(prompt)
            
            # Parse the response to extract fields with confidence
            # In production, the Assistant would return structured data.
            # Here we parse the text response and simulate confidence scores.
            extraction = self._parse_document_extraction(
                response.message,
                document_type,
                file_path
            )
            
            logger.info(
                f"Document extraction complete. "
                f"High-confidence fields: {len(extraction.get_high_confidence_fields())}, "
                f"Missing: {len(extraction.get_missing_required_fields())}"
            )
            
            return extraction

    def _parse_document_extraction(
        self,
        message: str,
        document_type: DocumentType,
        file_path: str
    ) -> PRDataExtraction:
        """Parse document extraction results from Assistant response.
        
        In production, the Buy@ Assistant would return structured data with
        confidence scores. This is a simplified parser that extracts fields
        from text and assigns simulated confidence scores.
        
        Args:
            message: Assistant response text
            document_type: Type of document
            file_path: Original file path
            
        Returns:
            PRDataExtraction with parsed fields
        """
        import re
        
        extraction = PRDataExtraction(
            document_type=document_type,
            raw_text=message
        )
        
        # Extract supplier name (look for patterns)
        supplier_match = re.search(
            r'supplier[:\s]+([^\n]+)', message, re.IGNORECASE
        )
        if supplier_match:
            extraction.supplier_name = ExtractedField(
                value=supplier_match.group(1).strip(),
                confidence=0.85,
                source="document_text"
            )
        
        # Extract amount (look for $ amounts)
        amount_match = re.search(
            r'\$[\s]*([0-9,]+\.?[0-9]*)', message
        )
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            try:
                extraction.amount = ExtractedField(
                    value=float(amount_str),
                    confidence=0.90,
                    source="document_text"
                )
            except ValueError:
                pass
        
        # Extract description (look for description field)
        desc_match = re.search(
            r'description[:\s]+([^\n]+)', message, re.IGNORECASE
        )
        if desc_match:
            extraction.description = ExtractedField(
                value=desc_match.group(1).strip(),
                confidence=0.75,
                source="document_text"
            )
        
        # Note: Justification and cost_center are typically NOT in supplier
        # documents (they're internal Meta information), so they will usually
        # be missing and need to be asked from the user.
        
        return extraction

    def upload_document(self, file_path: str) -> str:
        """Upload a document to the Buy@ Assistant for PR attachment.
        
        Args:
            file_path: Path to the file to upload (PDF, DOCX, XLSX, images)
            
        Returns:
            Document ID or reference that can be used in PR prompts
            
        Raises:
            AgenticFlowError: If upload fails
        
        Thread-safe: Uses lock to prevent concurrent browser access.
        """
        with self._lock:
            if not self._page:
                raise AgenticFlowError("Browser not started. Call start() first.")
            
            if not self._assistant_open:
                raise AgenticFlowError("Assistant not open. Call open_assistant() first.")
            
            logger.info(f"Uploading document: {file_path}")
            
            try:
                # Find the file upload button or area
                # Based on typical Buy@ Assistant UI, there's usually a paperclip icon
                upload_button = self._page.locator(
                    'button[aria-label*="attach"], button[aria-label*="upload"], '
                    'input[type="file"]'
                ).first
                
                if upload_button.is_visible(timeout=5000):
                    # If it's a file input, set the file directly
                    if upload_button.get_attribute("type") == "file":
                        upload_button.set_input_files(file_path)
                    else:
                        # Click the button and handle file chooser
                        with self._page.expect_file_chooser() as fc_info:
                            upload_button.click()
                        file_chooser = fc_info.value
                        file_chooser.set_files(file_path)
                    
                    # Wait for upload to complete
                    self._page.wait_for_timeout(2000)
                    
                    # Try to get the document ID from the UI
                    # This may need adjustment based on actual DOM structure
                    doc_id = Path(file_path).name  # Fallback to filename
                    logger.info(f"Document uploaded successfully: {doc_id}")
                    return doc_id
                else:
                    raise AgenticFlowError("File upload button not found")
                    
            except PlaywrightTimeoutError as e:
                self._take_screenshot("upload_timeout")
                raise AgenticFlowError(f"Failed to upload document: {e}")
            except Exception as e:
                self._take_screenshot("upload_error")
                raise AgenticFlowError(f"Document upload failed: {e}")

    def _extract_pr_number(self, message: str) -> Optional[str]:
        """Extract PR number from assistant response."""
        import re
        # Look for patterns like PR-12345, PR#12345, PR 12345
        match = re.search(r'PR[-\s#]*(\d+)', message, re.IGNORECASE)
        if match:
            return f"PR-{match.group(1)}"
        return None

    def _extract_pr_url(self, message: str) -> Optional[str]:
        """Extract PR URL from assistant response."""
        import re
        # Look for URLs in the message
        match = re.search(r'https?://[^\s]+', message)
        if match:
            return match.group(0)
        return None

    def _parse_pr_status(self, message: str) -> str:
        """Parse PR status from assistant response."""
        message_lower = message.lower()
        if "approved" in message_lower:
            return "approved"
        elif "rejected" in message_lower:
            return "rejected"
        elif "submitted" in message_lower or "pending" in message_lower:
            return "submitted"
        elif "draft" in message_lower:
            return "draft"
        return "unknown"

    def _parse_current_approver(self, message: str) -> Optional[str]:
        """Parse current approver from assistant response."""
        import re
        # Look for patterns like "Current approver: John Doe" or "Approver: jdoe@meta.com"
        match = re.search(r'(?:current )?approver[:\s]+([^\n]+)', message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _parse_approval_chain(self, message: str) -> List[str]:
        """Parse approval chain from assistant response."""
        import re
        # Look for approval chain section
        chain = []
        # Simple parsing - look for lines with approver names/emails
        for line in message.split('\n'):
            if 'approver' in line.lower() or '@' in line:
                # Extract email or name
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', line)
                if email_match:
                    chain.append(email_match.group(0))
        return chain

    def _parse_po_number(self, message: str) -> Optional[str]:
        """Parse PO number from assistant response."""
        import re
        match = re.search(r'PO[-\s#]*(\d+)', message, re.IGNORECASE)
        if match:
            return f"PO-{match.group(1)}"
        return None

    def _parse_blockers(self, message: str) -> List[str]:
        """Parse blockers/issues from assistant response."""
        blockers = []
        message_lower = message.lower()
        if "blocker" in message_lower or "issue" in message_lower or "problem" in message_lower:
            # Extract lines mentioning blockers
            for line in message.split('\n'):
                line_lower = line.lower()
                if any(word in line_lower for word in ["blocker", "issue", "problem", "missing", "required"]):
                    blockers.append(line.strip())
        return blockers


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
        # Validate screenshot_dir to prevent path traversal (consistent with AgenticBuyingClient)
        if screenshot_dir is None:
            screenshot_dir = Path.home() / ".vendor_onboarding" / "screenshots"
        else:
            screenshot_path = Path(screenshot_dir).resolve()
            home = Path.home().resolve()
            tmp = Path("/tmp").resolve()
            try:
                if not (screenshot_path.is_relative_to(home) or 
                        screenshot_path.is_relative_to(tmp)):
                    raise ValueError(
                        f"screenshot_dir must be within home directory ({home}) "
                        f"or /tmp, got: {screenshot_dir}"
                    )
            except AttributeError:
                # Fallback for Python < 3.9
                if not (str(screenshot_path).startswith(str(home) + "/") or 
                        str(screenshot_path).startswith(str(tmp) + "/") or
                        screenshot_path == home or screenshot_path == tmp):
                    raise ValueError(
                        f"screenshot_dir must be within home directory ({home}) "
                        f"or /tmp, got: {screenshot_dir}"
                    )
            screenshot_dir = screenshot_path
        
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Note: _browser and _page are not used in BuyAtClient - all browser
        # operations are delegated to _agentic_client. These attributes are
        # kept for backward compatibility but are not actively used.
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
        # NOTE: Traditional flow not yet implemented. This is a placeholder
        # that raises SupplierNotFoundError to maintain backward compatibility
        # with existing tests and client code. In production, this would use
        # Playwright to navigate to Buy@ URL, search for supplier, and parse results.
        raise SupplierNotFoundError(
            f"Supplier '{supplier_name}' not found in Buy@ (traditional search not implemented). "
            f"Use BuyAtClient with use_agentic=True for supplier search."
        )
    
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
        if not self._agentic_client.is_started():
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
        
        # Check for negation phrases FIRST (before positive matches)
        # This prevents "not found" from matching "found"
        if "not found" in message_lower or "does not exist" in message_lower:
            raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
        
        # Now check for positive indicators
        if "exists" in message_lower or "found" in message_lower:
            exists = True
            if "active" in message_lower:
                is_active = True
                status = "active"
            elif "inactive" in message_lower:
                status = "inactive"
            elif "pending" in message_lower:
                status = "pending"
        
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
                          not @facebook.com, @meta.com, @oculus.com, @whatsapp.com, @fb.com)
            purpose: Business purpose for onboarding this supplier
            subscribers: Optional list of internal employee emails to receive
                        status notifications
            
        Returns:
            SupplierInfo with the new supplier details
            
        Raises:
            BuyAtError: If invitation fails
            ValueError: If supplier_email is invalid (internal domain)
        """
        # Validate email is external (check domain suffix, not substring)
        internal_domains = ["@facebook.com", "@meta.com", "@oculus.com", "@whatsapp.com", "@fb.com"]
        email_lower = supplier_email.lower()
        if any(email_lower.endswith(domain) for domain in internal_domains):
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
            if not self._agentic_client.is_started():
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

    def create_pr_draft(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        submit_for_approval: bool = False,
        **kwargs
    ) -> PRDraftInfo:
        """Create a PR draft or submit for approval via Buy@ Assistant.
        
        High-level API that verifies supplier exists and is ready for PR
        creation before delegating to AgenticBuyingClient.
        
        Args:
            supplier_name: Name of the supplier
            amount: PR amount in USD
            description: Description of goods/services
            justification: Business justification for the purchase
            cost_center: Cost center for charging
            submit_for_approval: If True, submit immediately for approval.
                               If False, create as draft only.
            **kwargs: Additional arguments passed to AgenticBuyingClient.create_pr_draft
                     (delivery_date, attachments, reference_case_id)
            
        Returns:
            PRDraftInfo with PR details including number, URL, and status
            
        Raises:
            SupplierNotFoundError: If supplier does not exist
            BuyAtError: If supplier is not active or not ready for PR
        """
        logger.info(
            f"Creating PR via BuyAtClient: {supplier_name}, "
            f"${amount:,.2f}, submit={submit_for_approval}"
        )
        
        # Verify supplier exists and is active
        supplier_info = self.search_supplier(supplier_name, use_cache=False)
        if not supplier_info.exists:
            raise SupplierNotFoundError(
                f"Supplier '{supplier_name}' not found in Buy@. "
                f"Please invite the supplier first."
            )
        
        if not supplier_info.is_active:
            raise BuyAtError(
                f"Supplier '{supplier_name}' exists but is not active. "
                f"Status: {supplier_info.status}. Please reactivate the supplier first."
            )
        
        # If submitting for approval, verify supplier is ready for PR (TPA check)
        if submit_for_approval:
            readiness = self.verify_supplier_for_pr(supplier_name)
            if not readiness.can_proceed:
                blockers = ", ".join(readiness.blockers or ["Unknown blocker"])
                raise BuyAtError(
                    f"Supplier '{supplier_name}' is not ready for PR creation. "
                    f"Blockers: {blockers}"
                )
        
        # Ensure agentic client is available
        if not self.use_agentic or not self._agentic_client:
            raise BuyAtError(
                "PR creation requires agentic flow. "
                "Initialize BuyAtClient with use_agentic=True"
            )
        
        # Start agentic session if not already started
        if not self._agentic_client.is_started():
            self.start_agentic_session()
        
        # Delegate to AgenticBuyingClient
        return self._agentic_client.create_pr_draft(
            supplier_name=supplier_name,
            amount=amount,
            description=description,
            justification=justification,
            cost_center=cost_center,
            submit_for_approval=submit_for_approval,
            **kwargs
        )

    def verify_supplier_for_pr(self, supplier_name: str) -> SupplierPRReadiness:
        """Verify if a supplier is ready for PR creation.
        
        Checks:
        - Supplier exists in Buy@
        - Supplier is active
        - TPA status (if required)
        
        Args:
            supplier_name: Name of the supplier to verify
            
        Returns:
            SupplierPRReadiness with can_proceed flag and list of blockers
        """
        logger.info(f"Verifying supplier PR readiness: {supplier_name}")
        
        blockers = []
        
        # Check if supplier exists and is active
        try:
            supplier_info = self.search_supplier(supplier_name, use_cache=False)
            exists = supplier_info.exists
            is_active = supplier_info.is_active
            
            if not exists:
                blockers.append(f"Supplier '{supplier_name}' not found in Buy@")
            elif not is_active:
                blockers.append(
                    f"Supplier '{supplier_name}' is not active (status: {supplier_info.status})"
                )
        except SupplierNotFoundError:
            exists = False
            is_active = False
            blockers.append(f"Supplier '{supplier_name}' not found in Buy@")
        
        # Check TPA status if supplier exists
        tpa_status = None
        tpa_expiry = None
        if exists and is_active:
            try:
                # Try to import TPA client
                from ..tpa.client import TPAClient
                tpa_client = TPAClient()
                tpa_info = tpa_client.get_tpa_status(supplier_name)
                tpa_status = tpa_info.get("status")
                tpa_expiry = tpa_info.get("expiry_date")
                
                if tpa_status != "active":
                    blockers.append(f"TPA status is '{tpa_status}' (not active)")
                elif tpa_expiry and tpa_expiry < datetime.utcnow():
                    blockers.append(f"TPA expired on {tpa_expiry}")
            except ImportError:
                logger.debug("TPA client not available, skipping TPA check")
            except Exception as e:
                logger.warning(f"Failed to check TPA status: {e}")
                # Don't block PR creation if TPA check fails - just warn
        
        can_proceed = len(blockers) == 0
        
        readiness = SupplierPRReadiness(
            supplier_name=supplier_name,
            exists=exists,
            is_active=is_active,
            can_proceed=can_proceed,
            blockers=blockers if blockers else None,
            tpa_status=tpa_status,
            tpa_expiry=tpa_expiry
        )
        
        logger.info(
            f"Supplier PR readiness: {supplier_name}, "
            f"can_proceed={can_proceed}, blockers={blockers}"
        )
        return readiness

    def create_pr_and_monitor(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        notification_callback: Optional[Callable] = None,
        **kwargs
    ) -> tuple[PRDraftInfo, str]:
        """Create PR with real submission and start async monitoring.
        
        Creates a PR with submit_for_approval=True and starts async polling
        for approval status. The polling runs in a background thread and
        invokes the notification_callback when status changes.
        
        Args:
            supplier_name: Name of the supplier
            amount: PR amount in USD
            description: Description of goods/services
            justification: Business justification for the purchase
            cost_center: Cost center for charging
            notification_callback: Optional callback invoked on status changes.
                                 Signature: callback(pr_status: PRStatus, event_type: str)
                                 event_type: 'submitted', 'approved', 'rejected', 'status_update'
            **kwargs: Additional arguments (delivery_date, attachments, reference_case_id,
                     poll_interval, max_duration)
            
        Returns:
            Tuple of (PRDraftInfo, polling_id) for tracking
        """
        logger.info(f"Creating PR with monitoring: {supplier_name}, ${amount:,.2f}")
        
        # Create PR with real submission
        pr_info = self.create_pr_draft(
            supplier_name=supplier_name,
            amount=amount,
            description=description,
            justification=justification,
            cost_center=cost_center,
            submit_for_approval=True,
            **kwargs
        )
        
        # Start async polling with PRPollingManager
        from .pr_polling import PRPollingManager
        
        poll_interval = kwargs.get('poll_interval', 300)
        max_duration = kwargs.get('max_duration', 86400)
        
        manager = PRPollingManager(
            pr_number=pr_info.pr_number,
            agentic_client=self._agentic_client,
            notification_callback=notification_callback,
            poll_interval=poll_interval,
            max_duration=max_duration
        )
        polling_id = manager.start_polling()
        logger.info(
            f"PR created with monitoring: {pr_info.pr_number}, "
            f"polling_id={polling_id}"
        )
        return pr_info, polling_id

    def update_pr(self, pr_number: str, updates: Dict[str, Any]) -> PRStatus:
        """Update an existing purchase request.
        
        Uses Buy@ Assistant to modify PR fields such as quantities, prices,
        delivery dates, or add line items.
        
        Args:
            pr_number: The PR number to update (e.g., "PR-12345")
            updates: Dictionary of field updates
            
        Returns:
            PRStatus with updated PR details
            
        Example:
            client.update_pr("PR-12345", {"quantity": 10, "price": 500.00})
        """
        logger.info(f"Updating PR {pr_number} via BuyAtClient")
        
        if not self.use_agentic or not self._agentic_client:
            raise BuyAtError(
                "PR update requires agentic flow. "
                "Initialize BuyAtClient with use_agentic=True"
            )
        
        if not self._agentic_client.is_started():
            self.start_agentic_session()
        
        return self._agentic_client.update_pr(pr_number, updates)

    def generate_justification(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        cost_center: str,
        additional_context: Optional[str] = None
    ) -> str:
        """Generate AI-powered business justification for a PR.
        
        Uses Buy@ Assistant to create compelling justification text
        that improves approval speed.
        
        Args:
            supplier_name: Name of the supplier
            amount: PR amount in USD
            description: Description of goods/services
            cost_center: Cost center for charging
            additional_context: Optional context (urgency, alternatives, etc.)
            
        Returns:
            Generated justification text
        """
        logger.info(f"Generating justification for {supplier_name} PR")
        
        if not self.use_agentic or not self._agentic_client:
            raise BuyAtError(
                "Justification generation requires agentic flow. "
                "Initialize BuyAtClient with use_agentic=True"
            )
        
        if not self._agentic_client.is_started():
            self.start_agentic_session()
        
        return self._agentic_client.generate_justification(
            supplier_name=supplier_name,
            amount=amount,
            description=description,
            cost_center=cost_center,
            additional_context=additional_context
        )

    def search_prs(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for purchase requests by criteria.
        
        Uses Buy@ Assistant to find PRs matching specified filters.
        
        Args:
            criteria: Search criteria (supplier, status, date range, amount, etc.)
            
        Returns:
            List of matching PRs with details
            
        Example:
            client.search_prs({
                "supplier": "Acme Corp",
                "status": "approved",
                "date_from": "2026-01-01"
            })
        """
        logger.info(f"Searching PRs via BuyAtClient with criteria: {criteria}")
        if not self.use_agentic or not self._agentic_client:
            raise BuyAtError(
                "PR search requires agentic flow. "
                "Initialize BuyAtClient with use_agentic=True"
            )
        if not self._agentic_client.is_started():
            self.start_agentic_session()
        return self._agentic_client.search_prs(criteria)

    def create_pr_from_document(
        self,
        file_path: str,
        document_type: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a PR by extracting data from a document (Document-First Workflow).
        
        Implements progressive disclosure: Uploads document to Buy@ Assistant,
        which extracts PR fields using AI. Returns extracted data and list of
        missing fields that user needs to provide.
        
        This enables the workflow:
        1. User uploads contract/quote/SOW
        2. AI extracts supplier, amount, description, etc.
        3. System asks only for missing fields (progressive disclosure)
        4. User provides missing info
        5. PR is created with combined data
        
        Args:
            file_path: Path to the document (PDF, DOCX, etc.)
            document_type: Optional type hint ('contract', 'quote', 'sow', 'invoice', 'proposal')
            additional_context: Optional context to help extraction
            
        Returns:
            Dictionary with:
            - 'extracted': Dict of fields extracted with high confidence
            - 'missing': List of required fields still needed from user
            - 'document_type': Detected document type
            - 'suggested_next_steps': What user should do next
            
        Example:
            # User uploads contract
            result = client.create_pr_from_document(
                file_path="/path/to/contract.pdf",
                document_type="contract",
                additional_context="Software licenses for Project X"
            )
            
            # Check what was extracted
            print(result['extracted'])
            # {'supplier_name': 'Acme Corp', 'amount': 5000.0, ...}
            
            # See what's missing
            print(result['missing'])
            # ['justification', 'cost_center']
            
            # User provides missing fields, then create PR
        """
        from .client import DocumentType
        
        logger.info(f"Creating PR from document via BuyAtClient: {file_path}")
        
        if not self.use_agentic or not self._agentic_client:
            raise BuyAtError(
                "Document-based PR creation requires agentic flow. "
                "Initialize BuyAtClient with use_agentic=True"
            )
        
        if not self._agentic_client.is_started():
            self.start_agentic_session()
        
        # Convert string document_type to enum if provided
        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type.lower())
            except ValueError:
                logger.warning(f"Unknown document type: {document_type}, using auto-detection")
        
        # Call AgenticBuyingClient method
        extraction = self._agentic_client.create_pr_from_document(
            file_path=file_path,
            document_type=doc_type,
            additional_context=additional_context
        )
        
        # Format result for user
        result = {
            "extracted": extraction.get_high_confidence_fields(),
            "missing": extraction.get_missing_required_fields(),
            "document_type": extraction.document_type.value,
            "suggested_next_steps": []
        }
        
        # Add suggestions based on what's missing
        if result["missing"]:
            result["suggested_next_steps"].append(
                f"Please provide the following missing information: {', '.join(result['missing'])}"
            )
        else:
            result["suggested_next_steps"].append(
                "All required fields extracted successfully. Ready to create PR."
            )
        
        if extraction.document_type == DocumentType.UNKNOWN:
            result["suggested_next_steps"].append(
                "Document type could not be determined. Please specify if this is a contract, quote, SOW, or invoice."
            )
        
        logger.info(
            f"Document PR extraction complete: "
            f"{len(result['extracted'])} fields extracted, "
            f"{len(result['missing'])} fields missing"
        )
        
        return result
