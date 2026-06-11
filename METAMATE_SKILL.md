# Vendor Onboarding Automation Skill

## Overview

Automates the complete vendor onboarding workflow at Meta through conversational
interaction. Guides users through data collection, validates information,
orchestrates system interactions, and provides real-time status updates.

**NEW: Buy@ Assistant Integration** - As of June 2026, the skill now leverages
Meta's official Buy@ Assistant (Metamate multi-agent system) for supplier
onboarding. This provides AI-powered supplier verification and onboarding via
the Buy@ Assistant conversational UI, which routes to specialized Metamate agents
with access to 47+ MCP tools.

**NEW: Purchase Request Creation** - As of June 2026, the skill now supports
automated Purchase Request (PR) creation via Buy@ Assistant. Users can create PR
drafts for review or submit PRs directly to the approval workflow with async
status monitoring and notifications.

**Capabilities:**
- Conversational intake with progressive disclosure
- Real-time validation with helpful error messages
- Automated form submission across 7+ systems
- **Duplicate supplier detection via Buy@ Assistant** (NEW - uses Metamate agents)
- **Supplier onboarding via Buy@ Assistant** (NEW - AI-powered, replaces manual forms)
- **Purchase Request creation via Buy@ Assistant** (NEW - draft or direct submission with async monitoring)
- **PR status tracking with notifications** (NEW - real-time approval workflow monitoring)
- Bulk worker onboarding via CSC
- AMP group management for access control
- TPA security assessment initiation
- Proactive notifications via Workplace and Email

**Backend**: Python implementation at `/Users/ikosoy/Claude/project/Vendor_Onboarding/`
- GitHub: `https://github.com/ikosoymeta/onboarding-automation`

## Workflow

### Phase 1: Initiation and Supplier Verification
1. User initiates: "I need to onboard [Vendor Name]"
2. Skill checks Buy@ for existing supplier via **Buy@ Assistant** (NEW)
   - Uses `AgenticBuyingClient` to automate Buy@ Assistant UI
   - Routes to **BUY_SUPPLIER_AGENT** (Metamate) via `MetamateAgentBuyAtSupplierSearchTool`
   - Returns supplier info (exists, status, supplier ID)
3. If supplier exists and active → skip supplier onboarding (saves 1 week)
4. If supplier exists but inactive → proceed with reactivation via Buy@ Assistant
5. If supplier not found → proceed with new supplier onboarding via **Buy@ Assistant**
   - Uses `BuyAtClient.invite_supplier()` which calls `AgenticBuyingClient.onboard_supplier()`
   - Sends natural language prompt to Buy@ Assistant
   - Assistant routes to **BUY_SUPPLIER_AGENT** → `MetamateAgentBuyAtSupplierOnboardingTool`
   - Supplier receives email from suppliers@fb.com with 10-day enrollment deadline

### Phase 2: Conversational Intake
The skill guides the user through data collection:

**Supplier Information:**
- Business justification
- Estimated annual spend
- Contract dates and value
- Data access requirements

**Worker Information** (for each worker or via spreadsheet upload):
- Full name and email
- Job title and role
- Start/end dates
- Work location (Remote/Onsite/Hybrid)
- Manager email
- Phone number (optional)

**Access Requirements:**
- Systems requiring access (GitHub, AWS, etc.)
- AMP group configuration
- YubiKey needs and shipping addresses

The skill validates data in real-time and provides clear error messages with
fix instructions.

### Phase 3: Automated Execution
Once data is collected and validated, the skill orchestrates:

**Parallel Execution** (independent steps):
- Submit YubiKey requests (if needed)
- Submit Statement of Work via Butterfly API
- Initiate TPA Assessment
- Create AMP Group

**Sequential Execution** (dependent steps):
- Update CSC Profile (waits for AMP group)
- Onboard Workers via CSC bulk upload

Each step includes retry logic with exponential backoff for transient failures.

### Phase 4: Monitoring and Notifications
- Real-time status updates via chat
- Proactive Workplace notifications at milestones
- Email alerts for blockers requiring attention
- Estimated completion dates based on historical data
- Ability to check status anytime via "What's the status of [Vendor]?"

### Phase 5: Purchase Request Creation (NEW)
The skill now supports automated Purchase Request (PR) creation via Buy@ Assistant:

**PR Creation Modes:**
1. **Draft Mode** - Creates PR as draft for user review
   - User reviews draft in Buy@ UI
   - User manually submits when ready
   - Ideal for complex PRs requiring careful review

2. **Direct Submission Mode** - Submits PR immediately to approval workflow
   - PR enters approval workflow right away
   - Async status monitoring with notifications
   - Ideal for straightforward PRs

**PR Creation Workflow:**
1. User initiates: "Create a PR for [Supplier]" or "Create a purchase request"
2. Skill collects PR details:
   - Supplier name (must exist in Buy@ and be active)
   - Amount (USD)
   - Description of goods/services
   - Business justification
   - Cost center
   - Optional: Delivery date, reference case ID, attachments (quotes, SOWs)
3. Skill verifies supplier readiness:
   - Checks supplier exists in Buy@
   - Verifies supplier is active
   - Checks TPA status (if applicable)
   - Identifies any blockers
4. If `submit_for_approval=True`:
   - Creates PR and submits immediately to approval workflow
   - Starts async monitoring in background thread
   - Returns PR number, URL, and polling ID for tracking
   - Sends notifications on status changes (submitted → approved/rejected)
5. If `submit_for_approval=False` (draft mode):
   - Creates PR as draft only
   - Returns PR number and URL for manual review
   - User submits via Buy@ UI when ready

**PR Status Monitoring:**
- Real-time status checks via Buy@ Assistant
- Tracks: draft, submitted, approved, rejected statuses
- Identifies current approver and approval chain
- Extracts PO number when approved
- Lists blockers/issues if any
- Async polling with configurable intervals (default: 5 minutes)
- Notifications via Workplace/Email on status changes

## Usage

### Trigger Phrases

**Vendor Onboarding:**
The skill can be triggered by any of the following phrases:
- "I need to onboard [Vendor Name] as a vendor"
- "Onboard a vendor"
- "Onboard a supplier"
- "Start vendor onboarding for [Vendor Name]"
- "Help me onboard [Vendor Name]"

**Purchase Request Creation (NEW):**
- "Create a purchase request for [Supplier]"
- "Create a PR for [Supplier]"
- "Create a PR draft for [Supplier]"
- "Submit a PR for [Supplier]"
- "I need to create a purchase request"
- "Create a PR for [Supplier] for $[Amount]"
- "Check status of PR [PR Number]"
- "What's the status of my purchase request?"

### Starting a New Onboarding

**Example 1: Simple trigger**
```
User: Onboard a vendor

Metamate: I'll help you onboard a vendor! Which supplier would you like to onboard?
```

**Example 2: With vendor name**
```
User: I need to onboard Acme Corp as a vendor

Metamate: I'll help you onboard Acme Corp! Let me check if they're 
          already in our systems...

          [Checks Buy@ via Buy@ Assistant]

          ✓ Good news! Acme Corp is already in Buy@ and active.
            This saves us about 1 week!

          How many workers are we onboarding?
```

**Example 3: Supplier onboarding**
```
User: Onboard a supplier

Metamate: I'll help you onboard a supplier! Which supplier would you 
          like to onboard? Please provide:
          - Supplier legal name
          - Supplier contact email (for onboarding invitation)
          - Business purpose
```

### Creating a Purchase Request (NEW)

**Example 1: Create PR Draft**
```
User: Create a PR draft for Acme Corp

Metamate: I'll help you create a purchase request draft for Acme Corp!
          Let me first verify the supplier...

          [Checks Buy@ via Buy@ Assistant]

          ✓ Acme Corp is active in Buy@ and ready for PR creation.

          Please provide the following details:
          1. Amount (USD)
          2. Description of goods/services
          3. Business justification
          4. Cost center

User: $5000 for software licenses, needed for project X, cost center CC-12345

Metamate: Creating PR draft for Acme Corp...

          ✓ PR Draft Created Successfully!
          
          PR Number: PR-12345
          PR URL: https://buy.meta.com/pr/12345
          Status: Draft
          
          The PR has been created as a draft. You can review it at the URL above
          and submit it manually when ready.
```

**Example 2: Submit PR Directly**
```
User: Submit a PR for Acme Corp for $10000

Metamate: I'll help you submit a purchase request for Acme Corp!
          Let me verify the supplier and collect details...

          [Checks Buy@ and TPA status via Buy@ Assistant]

          ✓ Acme Corp is active and TPA is valid.
          
          Please provide:
          1. Description of goods/services
          2. Business justification  
          3. Cost center
          4. Any attachments? (quotes, SOWs)

User: Hardware purchase for server upgrade, infrastructure team, CC-67890, 
      attaching quote.pdf

Metamate: Creating and submitting PR for Acme Corp...

          ✓ PR Submitted Successfully!
          
          PR Number: PR-67890
          PR URL: https://buy.meta.com/pr/67890
          Status: Submitted to Approval Workflow
          
          I've started monitoring this PR. You'll receive notifications when:
          - PR is approved (PO will be generated)
          - PR is rejected (with reason)
          - Status changes
          
          Current Approver: manager@meta.com
          Approval Chain: manager@meta.com → director@meta.com
```

**Example 3: Check PR Status**
```
User: Check status of PR-67890

Metamate: Checking status for PR-67890...

          [Queries Buy@ Assistant]

          PR-67890 Status: Approved ✓
          
          PO Number: PO-99999
          Approved by: director@meta.com
          Approval Date: 2026-06-11
          
          The PR has been fully approved and a PO has been generated.
```

**Example 4: PR with Blockers**
```
User: Create a PR for New Supplier Inc for $2500

Metamate: I'll help you create a PR for New Supplier Inc.
          Let me verify the supplier...

          [Checks Buy@ via Buy@ Assistant]

          ⚠️  Supplier Not Ready for PR Creation
          
          Issues found:
          - Supplier 'New Supplier Inc' not found in Buy@
          
          Would you like me to:
          1. Invite New Supplier Inc to Buy@ first (takes ~1 week)
          2. Choose a different supplier that already exists
```

## System Integrations

### Buy@ Assistant (Metamate Multi-Agent System) - NEW
- **Purpose**: Supplier verification, duplicate prevention, supplier onboarding, and **Purchase Request creation** via conversational AI
- **Method**: Browser automation of Buy@ Assistant UI (spend.internalmeta.com) which routes to Metamate agents
- **Architecture**: 
  - **BUY_ASSISTANT** (MetamateEngineBuyAtAssistant) - Top-level router
  - **BUY_SUPPLIER_AGENT** (MetamateEngineBuyAtSupplierAgent) - Handles supplier operations via Claude Opus 4.6
  - **BUY_PURCHASING_AGENT** (NEW) - Handles PR creation via `MetamateAgentBuyAtPurchaseRequestDraftCreateTool`
  - **MCP Tools**: 47+ tools including `MetamateAgentBuyAtSupplierSearchTool`, `MetamateAgentBuyAtSupplierOnboardingTool`, `MetamateAgentBuyAtPurchaseRequestDraftCreateTool` (NEW)
- **Operations**: 
  - Search supplier (via `BUY_SUPPLIER_AGENT` → `SupplierSearchTool`)
  - Check supplier status (active/inactive/pending)
  - Invite new supplier (via `SupplierOnboardingTool` - supplier receives email from suppliers@fb.com with 10-day deadline)
  - Get supplier ID and relationship owner
  - **Create PR draft** (NEW - via `BUY_PURCHASING_AGENT` → `PurchaseRequestDraftCreateTool`)
  - **Submit PR for approval** (NEW - immediate submission to workflow)
  - **Check PR status** (NEW - real-time approval tracking)
  - **Upload PR attachments** (NEW - quotes, SOWs, supporting docs)
- **Implementation**: `src/buyat/client.py` - `AgenticBuyingClient` and `BuyAtClient` with `use_agentic=True`
  - **NEW:** `src/buyat/pr_polling.py` - `PRPollingManager` for async status monitoring with thread-safe operation
- **Benefits**: Official Meta-supported, uses 47+ MCP tools, AI-powered reasoning, no UI maintenance

### Butterfly Forms API
- **Purpose**: Submit forms for approvals and requests
- **Method**: Direct API via `EntButterflyFormResponseMutator`
- **Forms**: YubiKey, Statement of Work, CSC Setup, TPA (Supplier Onboarding now via Buy@ Assistant)
- **Implementation**: `src/butterfly/client.py`

### CSC (Contractor Services Center)
- **Purpose**: Worker onboarding and provisioning
- **Method**: Browser automation via Playwright
- **Operations**: Individual worker onboarding, bulk upload via spreadsheet
- **Implementation**: `src/csc/automation.py`

### AMP (Access Management Platform)
- **Purpose**: Group management for access control
- **Method**: Browser automation via Playwright
- **Operations**: Create groups, add/remove members, configure permissions
- **Implementation**: `src/amp/automation.py`

### TPA (Third Party Assessment)
- **Purpose**: Security assessment and compliance
- **Method**: Direct API via TPAClient
- **Operations**: Submit assessment, poll status, get results
- **Implementation**: `src/tpa/client.py`

### Notifications
- **Workplace**: Post updates to onboarding group, tag stakeholders
- **Email**: Send critical alerts and completion summaries
- **Task System**: Create tracking tasks for visibility

## Backend Implementation

The skill uses the Vendor Onboarding Automation backend located at:
- **GitHub**: `https://github.com/ikosoymeta/onboarding-automation`
- **Local**: `/Users/ikosoy/Claude/project/Vendor_Onboarding/`

**Key Components:**
- `src/vendor_onboarding.py` - Main `VendorOnboardingSystem` class that orchestrates the workflow
- `src/buyat/client.py` - **NEW** Buy@ Assistant integration via `AgenticBuyingClient`
  - **NEW:** PR creation methods: `create_pr_draft()`, `check_pr_status()`, `upload_document()`
  - **NEW:** Supplier verification: `verify_supplier_for_pr()`, `create_pr_and_monitor()`
  - **NEW:** Data classes: `PRDraftInfo`, `PRStatus`, `SupplierPRReadiness`
- `src/buyat/pr_polling.py` - **NEW** Async PR status monitoring via `PRPollingManager`
  - Thread-safe polling with configurable intervals
  - Notification callbacks for status changes
  - Memory leak protection and proper cleanup
- `src/orchestrator/` - Workflow engine with state management and parallel execution

**Usage in Metamate Skill:**
```python
from src.vendor_onboarding import VendorOnboardingSystem
from src.buyat.client import BuyAtClient
from src.buyat.pr_polling import PRPollingManager

# Initialize with Buy@ Assistant (recommended)
system = VendorOnboardingSystem(use_buyat_assistant=True)

# Execute onboarding
result = system.onboard_vendor(
    supplier_name="Acme Corp",
    supplier_data={
        "supplier_email": "contact@acme.com",  # Required for Buy@ Assistant
        "business_purpose": "IT services",
        "subscribers": ["manager@meta.com"]
    },
    workers=[...]
)

# NEW: Create Purchase Request
buyat_client = BuyAtClient(use_agentic=True)

# Create PR draft (for review)
pr_draft = buyat_client.create_pr_draft(
    supplier_name="Acme Corp",
    amount=5000.00,
    description="Software licenses",
    justification="Needed for project X",
    cost_center="CC-12345",
    submit_for_approval=False  # Draft mode
)

# Or submit PR directly with monitoring
pr_info, polling_id = buyat_client.create_pr_and_monitor(
    supplier_name="Acme Corp",
    amount=10000.00,
    description="Hardware purchase",
    justification="Server upgrade",
    cost_center="CC-67890",
    notification_callback=my_callback
)
```
User: I need to onboard Acme Corp as a vendor

Metamate: I'll help you onboard Acme Corp! Let me check if they're 
          already in our systems...
          
          [Checks Buy@]
          
          ✓ Good news! Acme Corp is already in Buy@ and active.
            This saves us about 1 week!
          
          How many workers are we onboarding?
```

### Providing Worker Information

Users can provide worker details in multiple ways:

**Option 1: Conversational (one by one)**
```
Metamate: For each worker, I'll need:
          1. Full name
          2. Email address
          3. Job title
          4. Work location
          
          Let's start with the first worker. What's their full name?
```

**Option 2: Spreadsheet Upload**
```
Metamate: You can upload a spreadsheet with these columns:
          - Full Name
          - Email Address
          - Job Title
          - Start Date (YYYY-MM-DD)
          - End Date (YYYY-MM-DD)
          - Manager Email
          - Work Location
          - Office Location (if Onsite/Hybrid)
          
          [User uploads file]
          
          ✓ Validated 3 workers successfully!
```

### Checking Status

```
User: What's the status of Acme Corp onboarding?

Metamate: Here's the current status for Acme Corp:

          Overall Progress: 67% Complete (6 of 9 steps)
          Estimated Completion: April 12, 2024
          
          ✓ Supplier verified (Active in Buy@)
          ✓ YubiKey request submitted (Tracking: 1Z999AA1)
          ✓ Statement of Work approved
          ⏳ TPA Assessment in progress (Est. 2 days)
          ⏳ AMP group creation pending
          ⏳ CSC worker onboarding pending
          
          I'll notify you when TPA is complete!
```
