# PR Creation Feature Implementation Plan

## Overview

Extend the Vendor Onboarding Automation to support **Purchase Request (PR) creation** via the Buy@ Assistant, enabling end-to-end procurement workflows through continuous conversational interaction in Metamate.

**Goal**: Allow users to go from "I need to buy something" to "PR submitted" in a single continuous conversation, with the system handling supplier verification, TPA checks, document extraction, and PR draft creation.

## Background

The Buy@ Assistant (launched June 10, 2026) includes **AutoPR capabilities** via the `MetamateEngineBuyAtPurchasingAgent` (`BUY_PURCHASING_AGENT`). This agent can:
- Create PR drafts from Agent Workspace cases, tasks, attachments, and URLs
- Extract data from documents (quotes, SOWs, emails, Google Docs)
- Pre-fill PR fields with AI-driven extraction
- Provide field-level reasoning and citations

Currently, our implementation only supports supplier onboarding. This plan extends it to support the complete procurement flow.

## Architecture

### System Context

```
User (Metamate Chat)
    │
    ▼
Vendor Onboarding Skill (Metamate)
    │
    ├──> Supplier Onboarding (Existing)
    │     └─> BuyAtClient.invite_supplier()
    │           └─> AgenticBuyingClient.onboard_supplier()
    │                 └─> Buy@ Assistant → BUY_SUPPLIER_AGENT
    │
    └──> PR Creation (NEW)
          └─> BuyAtClient.create_pr_draft()
                └─> AgenticBuyingClient.create_pr_draft()
                      └─> Buy@ Assistant → BUY_PURCHASING_AGENT
                            └─> MetamateAgentBuyAtPurchaseRequestDraftCreateTool
```

### Component Design

#### 1. PRDraftInfo Data Class (New)

```python
@dataclass
class PRDraftInfo:
    """Information about a PR draft created via Buy@ Assistant."""
    pr_id: str
    pr_number: str  # e.g., "PR-2024-0789"
    pr_url: str
    supplier_name: str
    supplier_id: Optional[str]
    total_amount: float
    currency: str = "USD"
    status: str = "draft"
    created_at: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    requires_review: bool = True
```

#### 2. AgenticBuyingClient Extensions (New Methods)

**Location**: `src/buyat/client.py`

```python
class AgenticBuyingClient:
    # Existing methods...
    
    def create_pr_draft(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        delivery_date: Optional[str] = None,
        attachments: List[str] = None,
        reference_case_id: Optional[str] = None
    ) -> PRDraftInfo:
        """Create a PR draft via Buy@ Assistant AutoPR.
        
        Uses natural language to describe the purchase request to the
        Buy@ Assistant, which routes to BUY_PURCHASING_AGENT. The agent
        uses MetamateAgentBuyAtPurchaseRequestDraftCreateTool to create
        the draft.
        
        Args:
            supplier_name: Name of the supplier (must be onboarded)
            amount: Total purchase amount
            description: Description of goods/services
            justification: Business justification
            cost_center: Cost center for the purchase
            delivery_date: Required delivery date (YYYY-MM-DD)
            attachments: List of file paths to attach (quote, SOW, etc.)
            reference_case_id: Optional Agent Workspace case ID to reference
            
        Returns:
            PRDraftInfo with PR details and link
            
        Raises:
            AgenticFlowError: If PR creation fails
            SupplierNotFoundError: If supplier is not onboarded
        """
    
    def check_pr_status(self, pr_number: str) -> PRStatus:
        """Check status of a PR via Buy@ Assistant.
        
        Args:
            pr_number: PR number (e.g., "PR-2024-0789")
            
        Returns:
            PRStatus with current status, approvers, etc.
        """
    
    def upload_document(self, file_path: str) -> str:
        """Upload a document to the Buy@ Assistant conversation.
        
        Args:
            file_path: Path to document (PDF, DOCX, XLSX, etc.)
            
        Returns:
            Document ID or URL for reference in PR
        """
```

#### 3. BuyAtClient Extensions (New Methods)

**Location**: `src/buyat/client.py`

```python
class BuyAtClient:
    # Existing methods...
    
    def create_pr_draft(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        **kwargs
    ) -> PRDraftInfo:
        """Create PR draft using Buy@ Assistant.
        
        High-level method that orchestrates PR creation via the
        Agentic Buying Intake flow.
        
        Args:
            supplier_name: Supplier name (must exist in Buy@)
            amount: Purchase amount
            description: Goods/services description
            justification: Business justification
            cost_center: Cost center code
            **kwargs: Additional options (delivery_date, attachments, etc.)
            
        Returns:
            PRDraftInfo with PR details
        """
    
    def verify_supplier_for_pr(self, supplier_name: str) -> SupplierPRReadiness:
        """Verify supplier is ready for PR creation.
        
        Checks:
        - Supplier exists in Buy@
        - Supplier is active
        - TPA is active (if required)
        - No blocking issues
        
        Args:
            supplier_name: Name of supplier to verify
            
        Returns:
            SupplierPRReadiness with status and any blockers
        """
```

#### 4. New Data Classes

```python
@dataclass
class SupplierPRReadiness:
    """Supplier readiness for PR creation."""
    supplier_name: str
    exists: bool
    is_active: bool
    supplier_id: Optional[str]
    tpa_required: bool
    tpa_active: bool
    tpa_expiry: Optional[str]
    blockers: List[str] = field(default_factory=list)
    can_proceed: bool = False

@dataclass
class PRStatus:
    """Status of a Purchase Request."""
    pr_number: str
    status: str  # draft, submitted, approved, rejected, etc.
    current_approver: Optional[str]
    approval_chain: List[str]
    submitted_at: Optional[str]
    approved_at: Optional[str]
    po_number: Optional[str]
```

## Implementation Phases

### Phase 1: Core PR Draft Creation (Week 1)

**Goal**: Basic PR draft creation via Buy@ Assistant

**Tasks:**
1. **Add PRDraftInfo dataclass** (`src/buyat/client.py`)
   - Define structure for PR draft information
   - Include PR ID, number, URL, amount, status

2. **Implement `AgenticBuyingClient.create_pr_draft()`**
   - Build natural language prompt for PR creation
   - Handle the conversational flow with Buy@ Assistant
   - Parse response to extract PR details
   - Handle errors and edge cases

3. **Implement `BuyAtClient.create_pr_draft()`**
   - High-level wrapper around agentic client
   - Validate supplier exists before creating PR
   - Handle fallback if agentic flow fails

4. **Add natural language prompt templates**
   - PR creation prompt with all required fields
   - Handle optional fields (delivery date, attachments)
   - Support reference to Agent Workspace cases

**Deliverable**: Can create PR drafts via Buy@ Assistant programmatically

**Test Criteria:**
- PR draft created successfully for valid supplier
- PR URL returned and accessible
- Amount and description correctly populated
- Error raised for non-existent supplier

### Phase 2: Supplier Verification & TPA Check (Week 1-2)

**Goal**: Comprehensive supplier readiness checking

**Tasks:**
1. **Implement `BuyAtClient.verify_supplier_for_pr()`**
   - Check supplier exists and is active
   - Check TPA status (if required for supplier/category)
   - Identify any blockers
   - Return structured readiness info

2. **Extend `AgenticBuyingClient` with TPA check**
   - Add `check_tpa_status()` method
   - Parse TPA status from assistant response
   - Handle TPA initiation if needed

3. **Add SupplierPRReadiness dataclass**
   - Structure for readiness information
   - Include blockers and remediation steps

**Deliverable**: Can verify supplier is ready for PR creation, including TPA status

**Test Criteria:**
- Correctly identifies active suppliers with valid TPA
- Detects inactive suppliers
- Detects expired TPA
- Lists specific blockers

### Phase 3: Document Handling (Week 2)

**Goal**: Support document attachments in PR creation

**Tasks:**
1. **Implement `AgenticBuyingClient.upload_document()`**
   - Handle file upload via Buy@ Assistant UI
   - Support PDF, DOCX, XLSX, images
   - Return document reference for PR

2. **Extend PR creation with attachments**
   - Modify `create_pr_draft()` to accept attachments
   - Upload documents before PR creation
   - Reference documents in PR prompt

3. **Add document extraction support**
   - Leverage Buy@ Assistant's document extraction capability
   - Parse extracted data from quotes/SOWs
   - Pre-fill PR fields from documents

**Deliverable**: Can create PRs with attached quotes, SOWs, and other documents

**Test Criteria:**
- PDF quote uploaded successfully
- Document referenced in PR
- Extracted data populates PR fields

### Phase 4: PR Status Tracking (Week 2-3)

**Goal**: Monitor PR status and provide updates

**Tasks:**
1. **Implement `AgenticBuyingClient.check_pr_status()`**
   - Query PR status via Buy@ Assistant
   - Parse approval chain and current status
   - Handle various PR states (draft, submitted, approved, etc.)

2. **Add PRStatus dataclass**
   - Structure for PR status information
   - Include approval chain, dates, PO number

3. **Implement status polling**
   - Add method to wait for PR approval
   - Configurable polling interval and timeout
   - Callback for status updates

**Deliverable**: Can check PR status and wait for approval

**Test Criteria:**
- Correctly reports PR status
- Tracks approval chain
- Detects when PR is approved and PO generated

### Phase 5: Metamate Skill Integration (Week 3)

**Goal**: Integrate PR creation into the Metamate skill

**Tasks:**
1. **Update `~/.llms/skills/vendor-onboarding/SKILL.md`**
   - Add PR creation workflow documentation
   - Add trigger phrases for PR creation
   - Add usage examples

2. **Extend skill with PR workflow**
   - Add conversational flow for PR creation
   - Integrate with existing vendor onboarding flow
   - Handle continuous conversation (supplier check → PR creation)

3. **Add status checking commands**
   - "What's the status of PR-2024-0789?"
   - "Check my PR status"
   - Proactive notifications on approval

**Deliverable**: Complete end-to-end PR creation via Metamate conversation

**Test Criteria:**
- Skill responds to "Create a PR for Acme Corp"
- Guides through data collection
- Creates PR draft successfully
- Provides status updates

### Phase 6: Advanced Features (Week 4)

**Goal**: Enhanced capabilities for power users

**Tasks:**
1. **Reference existing artifacts**
   - Link PR to Agent Workspace case
   - Reference previous PRs from same supplier
   - Use conversation history for context

2. **Smart defaults**
   - Suggest cost centers based on history
   - Auto-fill from supplier profile
   - Remember user preferences

3. **Bulk operations**
   - Create multiple PRs from spreadsheet
   - Batch status checking

4. **Integration with onboarding**
   - If supplier not onboarded, offer to onboard first
   - Seamless transition from onboarding to PR creation

**Deliverable**: Advanced PR creation features for complex scenarios

## API Design

### AgenticBuyingClient

```python
class AgenticBuyingClient:
    def create_pr_draft(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        delivery_date: Optional[str] = None,
        attachments: List[str] = None,
        reference_case_id: Optional[str] = None
    ) -> PRDraftInfo:
        """Create PR draft via Buy@ Assistant.
        
        Example:
            client = AgenticBuyingClient()
            client.start()
            client.navigate_to_suppliers()
            client.open_assistant()
            
            pr = client.create_pr_draft(
                supplier_name="Acme Corp",
                amount=50000.0,
                description="10x Software License (Annual)",
                justification="Q3 team expansion",
                cost_center="12345",
                delivery_date="2024-07-01",
                attachments=["/path/to/quote.pdf"]
            )
            
            print(f"PR created: {pr.pr_number}")
            print(f"URL: {pr.pr_url}")
        """
    
    def check_pr_status(self, pr_number: str) -> PRStatus:
        """Check PR status.
        
        Example:
            status = client.check_pr_status("PR-2024-0789")
            print(f"Status: {status.status}")
            print(f"Approver: {status.current_approver}")
        """
```

### BuyAtClient

```python
class BuyAtClient:
    def create_pr_draft(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        **kwargs
    ) -> PRDraftInfo:
        """Create PR draft (high-level API).
        
        Automatically verifies supplier and handles the agentic flow.
        """
    
    def verify_supplier_for_pr(
        self,
        supplier_name: str
    ) -> SupplierPRReadiness:
        """Verify supplier is ready for PR creation."""
```

## Natural Language Prompts

### PR Creation Prompt Template

```
Create a purchase request draft with the following details:

Supplier: {supplier_name}
Amount: ${amount:,.2f}
Description: {description}
Business Justification: {justification}
Cost Center: {cost_center}
{f"Delivery Date: {delivery_date}" if delivery_date else ""}
{f"Reference Case: {reference_case_id}" if reference_case_id else ""}

{f"Attached Documents:" if attachments else ""}
{fchr(10).join(f"- {att}" for att in attachments) if attachments else ""}

Please create the PR draft and provide the PR number and link.
Ensure all required fields are populated based on the information provided.
```

### Supplier Verification Prompt

```
Can you verify if supplier "{supplier_name}" is ready for a purchase request?

Please check:
1. Does the supplier exist in Buy@?
2. Is the supplier active?
3. Is TPA active (if required)?
4. Are there any blockers preventing PR creation?

Provide the supplier ID and status.
```

### PR Status Check Prompt

```
What is the current status of purchase request {pr_number}?

Please provide:
1. Current status (draft, submitted, approved, etc.)
2. Current approver (if in approval)
3. Approval chain
4. PO number (if approved)
5. Any blockers or issues
```

## Error Handling

### Common Errors

1. **SupplierNotFoundError**
   - Supplier does not exist in Buy@
   - **Remediation**: Offer to onboard supplier first

2. **SupplierInactiveError**
   - Supplier exists but is inactive
   - **Remediation**: Guide through reactivation process

3. **TPANotActiveError**
   - Supplier requires TPA but it's not active
   - **Remediation**: Initiate TPA assessment

4. **InsufficientDataError**
   - Missing required PR fields
   - **Remediation**: Ask user for missing information

5. **AgenticFlowError**
   - Buy@ Assistant unavailable or error
   - **Remediation**: Retry or fall back to manual process

## Testing Strategy

### Unit Tests

```python
class TestPRCreation(unittest.TestCase):
    def test_create_pr_draft_success(self):
        """Test successful PR draft creation."""
        # Mock Buy@ Assistant response
        # Verify PRDraftInfo returned correctly
    
    def test_create_pr_draft_supplier_not_found(self):
        """Test PR creation fails for non-existent supplier."""
        # Verify SupplierNotFoundError raised
    
    def test_verify_supplier_ready(self):
        """Test supplier verification for PR readiness."""
        # Verify all checks performed (exists, active, TPA)
    
    def test_check_pr_status(self):
        """Test PR status checking."""
        # Verify status parsed correctly
```

### Integration Tests

- Test with real Buy@ Assistant (staging environment)
- Verify end-to-end PR creation flow
- Test document upload and extraction
- Test status polling

## Documentation Updates

### Update SKILL.md

Add new section for PR creation:

```markdown
## PR Creation Workflow

### Trigger Phrases
- "Create a PR for [Supplier]"
- "I need to buy [item] from [Supplier]"
- "Create purchase request"

### Workflow
1. Verify supplier is onboarded and active
2. Check TPA status
3. Collect PR details (amount, description, justification, cost center)
4. Upload supporting documents (quote, SOW)
5. Create PR draft via Buy@ Assistant
6. Provide PR link for review and submission
7. Monitor status and notify on approval
```

### Update README.md

Add PR creation to feature list and usage examples.

## Success Criteria

1. **Functional**: Can create PR drafts via Buy@ Assistant for valid suppliers
2. **Reliable**: 90% success rate for PR creation
3. **User-Friendly**: Clear error messages and guidance for missing data
4. **Integrated**: Works seamlessly with existing vendor onboarding flow
5. **Documented**: Complete documentation with examples

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Buy@ Assistant UI changes | High | Use stable selectors, add monitoring, maintain fallback |
| Supplier not onboarded | Medium | Detect and offer to onboard first, then continue to PR |
| TPA not active | Medium | Check TPA status, initiate if needed, inform user of delay |
| Document extraction fails | Low | Allow manual entry of PR details, attach document anyway |
| PR approval takes long time | Low | Provide status checking, proactive notifications |

## Timeline

- **Week 1**: Phase 1 (Core PR creation) + Phase 2 (Supplier verification)
- **Week 2**: Phase 3 (Document handling) + Phase 4 (Status tracking)
- **Week 3**: Phase 5 (Metamate skill integration)
- **Week 4**: Phase 6 (Advanced features) + Testing + Documentation

**Total**: 4 weeks for complete implementation
