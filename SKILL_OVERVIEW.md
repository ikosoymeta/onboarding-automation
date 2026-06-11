# Vendor Onboarding Metamate Skill - Overview

**Version:** 2.0 (June 2026)  
**Status:** Implementation Complete, Testing Pending  
**Maintainer:** Igor Kosoy (ikosoy@meta.com)  
**Team:** BO&SS: Operations

## What the Skill Does

The Vendor Onboarding Automation Skill is a Metamate-powered conversational assistant that automates the complete vendor onboarding workflow at Meta. It guides users through data collection, validates information in real-time, orchestrates system interactions across 7+ Meta internal systems, and provides proactive status updates via Workplace and Email.

### Core Capabilities

**1. Vendor/Supplier Onboarding**
- Conversational intake with progressive disclosure
- Real-time validation with helpful error messages
- Automated form submission across 7+ systems (Buy@, Butterfly, CSC, AMP, TPA)
- Duplicate supplier detection via Buy@ Assistant (AI-powered)
- Supplier onboarding via Buy@ Assistant (replaces manual forms)
- Bulk worker onboarding via CSC spreadsheet upload
- AMP group management for access control
- TPA security assessment initiation

**2. Purchase Request (PR) Creation** (NEW - June 2026)
- Create PR drafts for user review
- Submit PRs directly to approval workflow
- Real-time PR status tracking
- Async monitoring with notifications (Workplace/Email)
- Document attachment support (quotes, SOWs)
- Supplier readiness verification (Buy@ status, TPA validation)

**3. Monitoring & Notifications**
- Real-time status updates via chat
- Proactive Workplace notifications at milestones
- Email alerts for blockers requiring attention
- Estimated completion dates based on historical data
- On-demand status queries

## Skill Location

### Code Repository
- **GitHub:** `https://github.com/ikosoymeta/onboarding-automation`
- **Local Path:** `/Users/ikosoy/Claude/project/Vendor_Onboarding/`
- **Devserver:** `~/Vendor_Onboarding/` (on devvm423.maz0 and other devservers)

### Key Files
- **Skill Definition:** `METAMATE_SKILL.md` - Complete skill documentation with workflows, examples, and integration details
- **Main Orchestrator:** `src/vendor_onboarding.py` - `VendorOnboardingSystem` class
- **Buy@ Integration:** `src/buyat/client.py` - `AgenticBuyingClient` and `BuyAtClient` (1,389 lines)
  - Supplier verification and onboarding
  - PR creation (draft and submission modes)
  - PR status checking
  - Document upload
- **PR Polling:** `src/buyat/pr_polling.py` - `PRPollingManager` for async monitoring (439 lines)
  - Thread-safe background polling
  - Notification callbacks
  - Memory leak protection
- **Workflow Engine:** `src/orchestrator/` - State management and parallel execution
- **System Clients:**
  - `src/butterfly/client.py` - Butterfly Forms API
  - `src/csc/automation.py` - CSC worker onboarding
  - `src/amp/automation.py` - AMP group management
  - `src/tpa/client.py` - TPA security assessment

### Documentation
- **Implementation Summary:** `PR_IMPLEMENTATION_SUMMARY.md` - Technical details of PR feature
- **Feature Status:** `PR_FEATURE_STATUS.md` - What's live vs remaining work
- **User Guide:** `docs/USER_GUIDE.md` - Comprehensive user documentation
- **Architecture:** `docs/architecture.md` - System design and integration patterns

## Commands Supported in Metamate

### Vendor Onboarding Commands

**Initiate Onboarding:**
- "I need to onboard [Vendor Name] as a vendor"
- "Onboard a vendor"
- "Onboard a supplier"
- "Start vendor onboarding for [Vendor Name]"
- "Help me onboard [Vendor Name]"

**Example:**
```
User: I need to onboard Acme Corp as a vendor

Metamate: I'll help you onboard Acme Corp! Let me check if they're 
          already in our systems...

          [Checks Buy@ via Buy@ Assistant]

          ✓ Good news! Acme Corp is already in Buy@ and active.
            This saves us about 1 week!

          How many workers are we onboarding?
```

**Check Status:**
- "What's the status of [Vendor Name] onboarding?"
- "Check status for [Vendor Name]"
- "Where are we with [Vendor Name]?"

**Example:**
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

### Purchase Request (PR) Creation Commands (NEW)

**Create PR Draft:**
- "Create a purchase request for [Supplier]"
- "Create a PR for [Supplier]"
- "Create a PR draft for [Supplier]"
- "I need to create a purchase request"
- "Create a PR for [Supplier] for $[Amount]"

**Example:**
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

**Submit PR Directly:**
- "Submit a PR for [Supplier]"
- "Submit a PR for [Supplier] for $[Amount]"
- "Create and submit a PR for [Supplier]"

**Example:**
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

**Check PR Status:**
- "Check status of PR [PR Number]"
- "What's the status of my purchase request?"
- "Check PR status for [PR Number]"

**Example:**
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

**PR with Blockers:**
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

### Buy@ Assistant (Metamate Multi-Agent System)
- **Purpose:** Supplier verification, onboarding, and PR creation via conversational AI
- **Agents:**
  - **BUY_ASSISTANT** - Top-level router
  - **BUY_SUPPLIER_AGENT** - Supplier operations (Claude Opus 4.6)
  - **BUY_PURCHASING_AGENT** - PR creation (NEW)
- **MCP Tools:** 47+ tools including supplier search, onboarding, and PR creation
- **Operations:**
  - Search supplier, check status, invite new supplier
  - Create PR draft, submit PR, check PR status, upload attachments (NEW)

### Other Integrations
- **Butterfly Forms API** - YubiKey, SOW, CSC Setup, TPA forms
- **CSC (Contractor Services Center)** - Worker onboarding via browser automation
- **AMP (Access Management Platform)** - Group management for access control
- **TPA (Third Party Assessment)** - Security assessment via API
- **Notifications** - Workplace posts, Email alerts, Task creation

## Backend API Usage

```python
from src.vendor_onboarding import VendorOnboardingSystem
from src.buyat.client import BuyAtClient
from src.buyat.pr_polling import PRPollingManager

# Initialize with Buy@ Assistant
system = VendorOnboardingSystem(use_buyat_assistant=True)

# Onboard vendor
result = system.onboard_vendor(
    supplier_name="Acme Corp",
    supplier_data={
        "supplier_email": "contact@acme.com",
        "business_purpose": "IT services",
        "subscribers": ["manager@meta.com"]
    },
    workers=[...]
)

# Create PR (NEW)
buyat_client = BuyAtClient(use_agentic=True)

# Draft mode
pr_draft = buyat_client.create_pr_draft(
    supplier_name="Acme Corp",
    amount=5000.00,
    description="Software licenses",
    justification="Needed for project X",
    cost_center="CC-12345",
    submit_for_approval=False
)

# Direct submission with monitoring (NEW)
pr_info, polling_id = buyat_client.create_pr_and_monitor(
    supplier_name="Acme Corp",
    amount=10000.00,
    description="Hardware purchase",
    justification="Server upgrade",
    cost_center="CC-67890",
    notification_callback=my_callback
)
```

## Current Status

**Implementation:** ✅ Complete  
- PR creation with draft and submission modes
- Async monitoring with thread-safe polling
- Comprehensive test suite (750+ lines)
- Bug fixes for memory leaks and thread safety

**Testing:** 🟡 Pending
- Unit tests written (require pytest)
- End-to-end testing with real Buy@ Assistant needed
- Integration testing with WorkflowOrchestrator pending (Phase 4)

**Deployment:** 🟡 Pending
- Metamate skill definition updated (METAMATE_SKILL.md)
- Awaiting skill registry deployment
- User documentation and training materials needed

## Getting Started

**For Users:** Trigger the skill in Metamate with any of the commands listed above.

**For Developers:**
```bash
# Clone repository
git clone https://github.com/ikosoymeta/onboarding-automation.git
cd onboarding-automation

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run tests
python -m pytest tests/test_buyat/test_pr_creation.py -v
python -m pytest tests/test_buyat/test_pr_polling.py -v
```

**Documentation:**
- Skill Definition: `METAMATE_SKILL.md`
- Implementation Details: `PR_IMPLEMENTATION_SUMMARY.md`
- Feature Status: `PR_FEATURE_STATUS.md`
- User Guide: `docs/USER_GUIDE.md`
