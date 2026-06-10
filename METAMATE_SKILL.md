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

**Capabilities:**
- Conversational intake with progressive disclosure
- Real-time validation with helpful error messages
- Automated form submission across 7+ systems
- **Duplicate supplier detection via Buy@ Assistant** (NEW - uses Metamate agents)
- **Supplier onboarding via Buy@ Assistant** (NEW - AI-powered, replaces manual forms)
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

## Usage

### Trigger Phrases

The skill can be triggered by any of the following phrases:
- "I need to onboard [Vendor Name] as a vendor"
- "Onboard a vendor"
- "Onboard a supplier"
- "Start vendor onboarding for [Vendor Name]"
- "Help me onboard [Vendor Name]"

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

## System Integrations

### Buy@ Assistant (Metamate Multi-Agent System) - NEW
- **Purpose**: Supplier verification, duplicate prevention, and supplier onboarding via conversational AI
- **Method**: Browser automation of Buy@ Assistant UI (spend.internalmeta.com) which routes to Metamate agents
- **Architecture**: 
  - **BUY_ASSISTANT** (MetamateEngineBuyAtAssistant) - Top-level router
  - **BUY_SUPPLIER_AGENT** (MetamateEngineBuyAtSupplierAgent) - Handles supplier operations via Claude Opus 4.6
  - **MCP Tools**: 47+ tools including `MetamateAgentBuyAtSupplierSearchTool`, `MetamateAgentBuyAtSupplierOnboardingTool`
- **Operations**: 
  - Search supplier (via `BUY_SUPPLIER_AGENT` → `SupplierSearchTool`)
  - Check supplier status (active/inactive/pending)
  - Invite new supplier (via `SupplierOnboardingTool` - supplier receives email from suppliers@fb.com with 10-day deadline)
  - Get supplier ID and relationship owner
- **Implementation**: `src/buyat/client.py` - `AgenticBuyingClient` and `BuyAtClient` with `use_agentic=True`
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
- `src/orchestrator/` - Workflow engine with state management and parallel execution

**Usage in Metamate Skill:**
```python
from src.vendor_onboarding import VendorOnboardingSystem

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
