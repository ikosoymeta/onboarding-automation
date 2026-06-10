# Buy@ Assistant Workflow Integration

## Overview

The Vendor Onboarding Automation now integrates with the **Buy@ Assistant** (Metamate multi-agent system) as the primary method for supplier onboarding. This replaces the custom browser automation flow with the official Buy@ Assistant, which uses Meta's Metamate platform with 11 specialized agents and 47+ MCP tools.

## Why Use Buy@ Assistant?

### Benefits Over Custom Automation

| Aspect | Custom Automation | Buy@ Assistant (Metamate) |
|--------|------------------|---------------------------|
| **Maintenance** | We maintain browser selectors, handle UI changes | Meta maintains the agents and tools |
| **Reliability** | Brittle - breaks on UI changes | Robust - uses official APIs and tools |
| **Capabilities** | Limited to what we can automate via UI | Full access to 47+ MCP tools, agent reasoning |
| **Support** | We debug and fix issues | Meta's Buy@ team supports the agents |
| **Features** | Basic form filling | AI-powered extraction, reasoning, citations |
| **Future-proof** | Need to update for every UI change | Agents evolve with the platform |

### Architecture

```
Vendor Onboarding Workflow
    │
    ▼
┌─────────────────────────────────┐
│  VendorOnboardingSystem         │
│  (use_buyat_assistant=True)     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  BuyAtClient                    │
│  (use_agentic=True)             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  AgenticBuyingClient            │
│  (Browser Automation)           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Buy@ Assistant UI              │
│  (spend.internalmeta.com)       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Metamate Platform              │
│  ┌───────────────────────────┐  │
│  │ BUY_ASSISTANT (Router)    │  │
│  └────────┬──────────────────┘  │
│           │                     │
│           ▼                     │
│  ┌───────────────────────────┐  │
│  │ BUY_SUPPLIER_AGENT        │  │
│  │ (Claude Opus 4.6)         │  │
│  └────────┬──────────────────┘  │
│           │                     │
│           ▼                     │
│  ┌───────────────────────────┐  │
│  │ MCP Tools:                │  │
│  │ - SupplierSearchTool      │  │
│  │ - SupplierOnboardingTool  │  │
│  │ - ... (47+ tools)         │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

## Integration Points

### 1. VendorOnboardingSystem

The main `VendorOnboardingSystem` class now accepts a `use_buyat_assistant` parameter:

```python
from src.vendor_onboarding import VendorOnboardingSystem

# Use Buy@ Assistant (recommended - default)
system = VendorOnboardingSystem(use_buyat_assistant=True)

# Use traditional Butterfly forms (fallback)
system = VendorOnboardingSystem(use_buyat_assistant=False)
```

**When `use_buyat_assistant=True`:**
- Supplier onboarding uses the Buy@ Assistant conversational UI
- Routes to `BUY_SUPPLIER_AGENT` via Metamate
- Uses `MetamateAgentBuyAtSupplierOnboardingTool` internally
- Supplier receives email from suppliers@fb.com with 10-day deadline
- If Buy@ Assistant fails, automatically falls back to Butterfly forms

**When `use_buyat_assistant=False`:**
- Uses traditional Butterfly Supplier Onboarding Form
- Custom browser automation (when implemented)
- Direct form submission via Butterfly API

### 2. Workflow Steps

**Step 1: Supplier Verification and Onboarding**

```python
# In VendorOnboardingSystem.onboard_vendor()

# 1. Verify if supplier exists
supplier_info = self.buyat.search_supplier(supplier_name)

if not supplier_info.exists or not supplier_info.is_active:
    if self.use_buyat_assistant:
        # Use Buy@ Assistant (Metamate agents)
        self.buyat.invite_supplier(
            supplier_name=supplier_name,
            supplier_email=supplier_email,
            purpose=purpose,
            subscribers=subscribers
        )
        # Agent handles: search → invite → track status
    else:
        # Use traditional Butterfly form
        self.butterfly.submit_supplier_onboarding(data=supplier_data)
```

## Usage Examples

### Example 1: Default (Buy@ Assistant)

```python
from src.vendor_onboarding import VendorOnboardingSystem
from src.csc import WorkerInfo

# Initialize with Buy@ Assistant (default)
system = VendorOnboardingSystem(use_buyat_assistant=True)

# Define workers
workers = [
    WorkerInfo(
        full_name="John Doe",
        email="john@acme.com",
        start_date="2024-04-01",
        end_date="2025-04-01",
        job_title="Software Engineer",
        manager_email="manager@meta.com",
        work_location="Remote"
    )
]

# Supplier data (must include email for Buy@ Assistant)
supplier_data = {
    "supplier_name": "Acme Corp",
    "supplier_email": "procurement@acme.com",  # Required for Buy@ Assistant
    "business_purpose": "IT consulting services for Q2 project",
    "contact_name": "Jane Smith",
    "contact_phone": "555-0123",
    "subscribers": ["manager@meta.com", "procurement@meta.com"]
}

# Execute onboarding
result = system.onboard_vendor(
    supplier_name="Acme Corp",
    supplier_data=supplier_data,
    workers=workers,
    enable_yubikey=True,
    enable_tpa=True
)

print(f"Success: {result.success}")
print(f"Supplier ID: {result.supplier_id}")
print(f"Workers onboarded: {result.workers_onboarded}")
```

### Example 2: Fallback to Traditional Forms

```python
# Force traditional Butterfly forms (no Buy@ Assistant)
system = VendorOnboardingSystem(use_buyat_assistant=False)

result = system.onboard_vendor(
    supplier_name="Acme Corp",
    supplier_data=supplier_data,  # No email required
    workers=workers
)
```

### Example 3: Hybrid Approach (Automatic Fallback)

```python
# Try Buy@ Assistant first, fall back to Butterfly if it fails
system = VendorOnboardingSystem(use_buyat_assistant=True)

try:
    result = system.onboard_vendor(...)
    # If Buy@ Assistant succeeds, supplier is onboarded via Metamate
    # If it fails, system automatically falls back to Butterfly forms
except Exception as e:
    # Only reaches here if BOTH methods fail
    print(f"Onboarding failed: {e}")
```

## Data Requirements

### For Buy@ Assistant (use_buyat_assistant=True)

**Required fields in `supplier_data`:**
- `supplier_email` or `contact_email` - External email (not @meta.com, @facebook.com, etc.)
- `business_purpose` or `justification` - Why you need this supplier

**Optional fields:**
- `subscribers` - List of emails to receive status notifications
- `supplier_name` - Should match the `supplier_name` parameter
- `contact_name` - Supplier contact person
- `contact_phone` - Supplier phone number

**Example:**
```python
supplier_data = {
    "supplier_email": "vendor@external.com",  # REQUIRED - must be external
    "business_purpose": "Marketing services for Q3 campaign",  # REQUIRED
    "subscribers": ["manager@meta.com"],  # Optional
    "contact_name": "John Vendor",  # Optional
}
```

### For Traditional Forms (use_buyat_assistant=False)

**Required fields:** Standard Butterfly Supplier Onboarding Form fields (no email requirement)

## Migration Guide

### From Custom Automation to Buy@ Assistant

**Before (Custom Browser Automation):**
```python
# Old approach - custom automation for each system
system = VendorOnboardingSystem()
# Internally uses:
# - BuyAtClient with custom browser automation (TODO)
# - ButterflyClient for forms
# - CSCAutomation for workers
# - etc.
```

**After (Buy@ Assistant Integration):**
```python
# New approach - leverage official Buy@ Assistant
system = VendorOnboardingSystem(use_buyat_assistant=True)
# Internally uses:
# - BuyAtClient with AgenticBuyingClient (browser automation for Assistant UI)
# - Assistant routes to BUY_SUPPLIER_AGENT (Metamate)
# - Agent uses official MCP tools (SupplierOnboardingTool, etc.)
# - Falls back to Butterfly forms if needed
```

### Benefits of Migration

1. **Reduced Maintenance**: No need to maintain custom browser selectors for Buy@ UI
2. **Official Support**: Buy@ Assistant is supported by Meta's Buy@ team
3. **Better Reliability**: Uses official MCP tools instead of UI scraping
4. **Future-Proof**: Agents evolve with the platform, not brittle UI automation
5. **AI Capabilities**: Leverages Claude Opus 4.6 reasoning for complex supplier scenarios

## Error Handling and Fallback

The system implements a **graceful degradation** strategy:

```python
if self.use_buyat_assistant:
    try:
        # Try Buy@ Assistant first
        self.buyat.invite_supplier(...)
        logger.info("Buy@ Assistant onboarding succeeded")
    except Exception as e:
        logger.error(f"Buy@ Assistant failed: {e}")
        # Fall back to traditional Butterfly form
        logger.info("Falling back to Butterfly form")
        self.use_buyat_assistant = False
        self.butterfly.submit_supplier_onboarding(...)
```

**Fallback triggers:**
- Buy@ Assistant UI not accessible
- Browser automation fails (element not found, timeout)
- Metamate agent returns error
- Network issues

**Result:** The workflow continues with traditional forms, ensuring onboarding is not blocked.

## Monitoring and Observability

### Logging

The system logs key events:
```
INFO: Vendor Onboarding System initialized (use_buyat_assistant=True)
INFO: Step 1: Verifying supplier in Buy@
INFO: Supplier Acme Corp needs onboarding
INFO: Using Buy@ Assistant (Metamate) for supplier onboarding
INFO: Supplier onboarding initiated via Buy@ Assistant. Supplier has 10 business days to complete enrollment.
```

### Screenshots

For debugging Buy@ Assistant interactions, screenshots are saved to:
```
~/.vendor_onboarding/screenshots/
  - buyat_agentic_error_20260610_143022.png
  - buyat_assistant_open_timeout_20260610_143105.png
```

### Metrics to Track

- **Buy@ Assistant Success Rate**: % of onboardings completed via Assistant vs fallback
- **Time to Onboard**: Compare Assistant vs traditional form duration
- **Error Types**: Categorize failures (UI changes, agent errors, network issues)

## Testing

### Unit Tests

```python
# Test Buy@ Assistant integration
def test_buyat_assistant_onboarding():
    system = VendorOnboardingSystem(use_buyat_assistant=True)
    # Mock the BuyAtClient.invite_supplier method
    # Verify it is called with correct parameters
    # Verify fallback to Butterfly on failure
```

### Integration Tests

Requires:
- Access to buy@ staging environment
- Valid SSO session
- Test supplier data (with external email)

```python
# Integration test with real Buy@ Assistant
def test_real_buyat_assistant():
    system = VendorOnboardingSystem(use_buyat_assistant=True)
    result = system.onboard_vendor(
        supplier_name="Test Supplier " + uuid.uuid4().hex[:8],
        supplier_data={
            "supplier_email": "test@external.com",
            "business_purpose": "Integration test"
        },
        workers=[]
    )
    assert result.success
```

## Future Enhancements

### 1. Direct MCP Tool Access

If Meta exposes MCP tools via API (instead of UI-only), we could call them directly:
```python
# Future: Direct MCP tool invocation (no browser automation)
from metamate import MCPClient

mcp = MCPClient()
result = mcp.call_tool(
    "MetamateAgentBuyAtSupplierOnboardingTool",
    supplier_name="Acme Corp",
    supplier_email="contact@acme.com",
    purpose="IT services"
)
```

### 2. Async Status Tracking

Poll the Buy@ Assistant for onboarding status:
```python
# Check if supplier completed onboarding
status = system.buyat.check_supplier_onboarding_status(supplier_name)
if status.is_complete:
    # Proceed with dependent steps (CSC, AMP, etc.)
```

### 3. Agent Workspace Integration

Trigger onboarding directly from Agent Workspace cases:
```python
# From an Agent Workspace case
system.onboard_from_case(case_id="12345")
# Agent extracts supplier info from case and initiates onboarding
```

## References

- **Buy@ Assistant Architecture**: `docs/AGENTIC_BUYING_INTEGRATION.md`
- **Design Document**: `docs/plans/2026-06-10-agentic-buying-intake-design.md`
- **Implementation**: `src/buyat/client.py` (AgenticBuyingClient, BuyAtClient)
- **Workflow Integration**: `src/vendor_onboarding.py` (VendorOnboardingSystem)
- **Official Docs**:
  - Buy@ Assistant Design: https://docs.google.com/document/d/1jazCbd129d0H7stOiMhAXBy7E8GijnGAT6vW7vwqLlk
  - AutoPR User Guide: https://www.internalfb.com/wiki/Enterprise_Products_User_Docs/Spend_Tools/Agent_Workspace/Guided_Buying/Agent_Tutorials_-_Agent_Workspace/AutoPR_AI_Agent/
  - Architecture: https://www.internalfb.com/code/fbsource/www/flib/intern/metamate/engine/domain_agents/agents/buy/.claude/CLAUDE.md
