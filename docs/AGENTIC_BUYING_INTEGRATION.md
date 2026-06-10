# Agentic Buying Intake Integration

## Overview

On June 10, 2026, Meta launched **Agentic Buying Intake** — a conversational AI experience that replaces the traditional multi-step form for New Goods & Services requests in buy@. This document describes how the Vendor Onboarding Automation integrates with the new agentic flow.

The Buy@ Assistant is built on Meta's Metamate platform using a sophisticated multi-agent architecture with 11+ specialized agents and 47+ MCP tools. Understanding this architecture is essential for effective integration.

## Buy@ Assistant Architecture

### Multi-Agent System Overview

The Buy@ Assistant uses an **orchestrator + specialist agent pattern** built on the Metamate platform:

**Top-Level Agents:**
1. **`MetamateEngineBuyAtAssistant`** (`BUY_ASSISTANT`) - Main entry point and user-facing assistant. Routes requests to specialized sub-agents via handoff tools. Does NOT answer questions directly.
2. **`MetamateEngineBuyAtOrchestrationAgent`** (`BUY_ORCHESTRATION_AGENT`) - Alternative orchestrator that delegates to purchasing, sourcing, and supplier sub-agents. Uses Claude Opus 4.6 with max reasoning effort.

### Specialist Agents (11 Total)

| Agent | Agent Name | Role |
|-------|------------|------|
| `MetamateEngineBuyAtPurchasingAgent` | `BUY_PURCHASING_AGENT` | AutoPR - generates draft Purchase Requests from cases, tasks, documents, URLs |
| `MetamateEngineBuyAtAutoPRCriticAgent` | - | Self-critique loop for PR quality |
| `MetamateEngineBuyAtSourcingAgent` | `BUY_SOURCING_AGENT` | Sourcing/procurement guidance, RFx management |
| `MetamateEngineBuyAtSupplierAgent` | `BUY_SUPPLIER_AGENT` | **Supplier lookup and management** (key for onboarding) |
| `MetamateEngineBuyAtAnalyticAgent` | `BUY_ANALYTIC_AGENT` | Data/reporting queries, dashboard composition |
| `MetamateEngineBuyAtAnalyticResearchAgent` | `BUY_ANALYTIC_RESEARCH_AGENT` | Deep analytical research, Python execution |
| `MetamateEngineBuyAtKnowledgeGraphAgent` | `BUY_KNOWLEDGE_GRAPH_AGENT` | Policy/knowledge lookups, entity search |
| `MetamateEngineBuyAtWorkflowAgent` | `BUY_WORKFLOW_AGENT` | Dynamic workflow orchestration |
| `MetamateEngineBuyAtGoodsOrServicesAgent` | - | Goods vs services classification |
| `MetamateEngineBuyAtSupportAssistant` | `BUY_HELPDESK_AGENT` | General buy@ support, PO actions, case management |
| `MetamateSmartinvoicingAssistantAgent` | `SMARTINVOICING_ASSISTANT` | Invoice handling |

### Key Agent for Supplier Onboarding: `BUY_SUPPLIER_AGENT`

The **`MetamateEngineBuyAtSupplierAgent`** (`BUY_SUPPLIER_AGENT`) is the primary integration point for supplier onboarding automation:

**Location:** `www/flib/intern/metamate/engine/domain_agents/agents/buy/supplier/MetamateEngineBuyAtSupplierAgent.php`

**LLM:** Claude Opus 4.6 (max reasoning effort)

**Tools:**
- `MetamateAgentBuyAtSupplierSearchTool` - Search for existing suppliers
- `MetamateAgentBuyAtSupplierOnboardingTool` - **Initiate supplier onboarding workflow**
- `MetamateAgentBuyAtSupplierOnboardingDashboardCaseSearchTool` - Track onboarding status via dashboard cases
- `MetamateAgentBuyAtSupplierRelationshipOwnerSearchTool` - Find supplier relationship owners
- `MetamateAgentKnowledgeLoadToolV3` - Load knowledge from URLs

**Sub-agents:**
- `MetamateAgentBuyAtKnowledgeGraphAgentTool` → KnowledgeGraph agent for policy/entity lookups

### AutoPR AI Agent

The **AutoPR AI Agent** (part of `MetamateEngineBuyAtPurchasingAgent`) is a key component:

**What it does:**
- Creates draft Purchase Requests from Agent Workspace cases, tasks, attachments, internal URLs (including Google Docs), and buy@ data
- Uses AI-driven extraction to pre-populate PR fields
- Provides field-level reasoning and citations for explainability
- Becomes the **default PR drafting experience starting March 2026**

**How to access:**
1. Via buy@ Assistant panel: "Create a purchase request draft from [case number]"
2. Via Agent Workspace: Case → Action dropdown → "Create purchase request using Buy@ Assistant"

**Key Limitations:**
- [IMPORTANT] Cannot create new suppliers, cost centers, purchasing categories, or FBPNs (must exist first)
- [IMPORTANT] Cannot modify PRs after submission
- [WARNING] Limited support for multi-turn PR updates after draft creation
- [IMPORTANT] No compliance/risk assessment (standard buy@ validations still apply)

### MCP Tools (47+ Tools)

The agents have access to 47+ tools registered via `MetamateAgentBuyAtToolFactory`:

**Purchase Request & PO Tools:**
- `BUY_PR_SEARCH` / `BUY_PR_NAVIGATOR` — Find and navigate PRs
- `BUY_PO_SEARCH` — Purchase order lookup
- `BUY_PR_LINE_SEARCH` — Line-item search
- `BUY_DOCUMENT_EXTRACTION` — Extract data from attachments

**Supplier Tools:**
- `MetamateAgentBuyAtSupplierSearchTool` — Search suppliers by name, ID, etc.
- `MetamateAgentBuyAtSupplierOnboardingTool` — Initiate onboarding workflow
- `MetamateAgentBuyAtSupplierOnboardingDashboardCaseSearchTool` — Find onboarding cases
- `MetamateAgentBuyAtSupplierRelationshipOwnerSearchTool` — Find supplier owners

## What Changed (User Perspective)

### Before (Traditional Form)
- Navigate to buy@ → Suppliers tab
- Search for supplier manually
- Click "Start Request" → Fill out multi-step form
- Enter supplier details in structured fields
- Submit for approval

### After (Agentic Flow)
- Navigate to buy@ → Suppliers page
- Click "buy@ assistant" button (top-right corner)
- Chat with AI assistant using natural language
- Describe your request: "I need to onboard supplier X for purpose Y"
- Assistant guides through the process conversationally
- Attach documents by describing them or uploading files
- Review and confirm the assistant's summary

## Key Features

### Conversational Interface
The buy@ assistant appears as a side panel on buy@ pages (e.g., spend.internalmeta.com/suppliers). Users interact via natural language instead of filling out forms.

### Natural Language Processing
The AI assistant understands requests like:
- "I need to onboard a new supplier: Acme Corp. Their email is contact@acme.com. Purpose: IT consulting services."
- "Can you check if supplier XYZ exists in the network?"
- "Please invite supplier ABC to the network for marketing services."

### Context Preservation
Information provided during the conversation carries forward into downstream forms without requiring re-entry. The assistant maintains context throughout the interaction.

### Downstream Unchanged
**Important**: The Agentic Buying Intake only replaces the intake form experience. All downstream operational workflows remain unchanged:
- Supplier onboarding process
- Approval workflows
- TPA (Third Party Assessment) initiation
- Contract routing
- Purchase Order generation

## Integration in Vendor Onboarding Automation

### Architecture: Browser Automation for Metamate Agents

The Vendor Onboarding Automation uses **browser automation** (Playwright) to interact with the Buy@ Assistant's conversational UI. This approach is necessary because:

1. **No Public API**: The Buy@ Assistant (Metamate agents) does not expose a public API for programmatic access
2. **UI-Based Interaction**: The assistant is designed for human interaction via the web interface
3. **Agent Orchestration**: The multi-agent system (router → specialist agents) is orchestrated internally by Metamate; we interact with the top-level `BUY_ASSISTANT` via its UI

### New Components

#### AgenticBuyingClient
A new class (`src/buyat/client.py`) that automates the conversational UI via browser automation:

```python
from src.buyat import AgenticBuyingClient

client = AgenticBuyingClient(headless=True)
client.start()
client.navigate_to_suppliers()
client.open_assistant()

# Onboard a supplier via conversation
# This sends a message to the BUY_ASSISTANT, which routes to BUY_SUPPLIER_AGENT
response = client.onboard_supplier(
    supplier_name="Acme Corp",
    supplier_email="contact@acme.com",
    purpose="IT consulting services",
    subscribers=["manager@meta.com"]
)
```

**Key Methods:**
- `start()`: Initialize browser session (Playwright)
- `navigate_to_suppliers()`: Go to Suppliers page (spend.internalmeta.com/suppliers)
- `open_assistant()`: Open the buy@ assistant side panel (triggers `BUY_ASSISTANT`)
- `send_message(message)`: Send natural language message to assistant
- `onboard_supplier(...)`: High-level workflow for supplier onboarding (routes to `BUY_SUPPLIER_AGENT`)
- `check_supplier_status(name)`: Check if supplier exists via conversation
- `close()`: Clean up browser resources

**How it works:**
1. Browser navigates to buy@ Suppliers page
2. Clicks "buy@ assistant" button to open chat panel
3. Sends natural language message via the chat input
4. The `BUY_ASSISTANT` (MetamateEngineBuyAtAssistant) receives the message
5. Assistant routes to appropriate specialist agent (e.g., `BUY_SUPPLIER_AGENT` for supplier tasks)
6. Specialist agent uses its tools (e.g., `MetamateAgentBuyAtSupplierOnboardingTool`) to execute the request
7. Response is displayed in the chat panel
8. Automation parses the response and returns it

#### Enhanced BuyAtClient
The existing `BuyAtClient` now supports agentic flow:

```python
from src.buyat import BuyAtClient

# Enable agentic flow (default)
client = BuyAtClient(use_agentic=True)

# Invite a new supplier via agentic conversation
# This uses the BUY_SUPPLIER_AGENT via the assistant UI
supplier = client.invite_supplier(
    supplier_name="Acme Corp",
    supplier_email="contact@acme.com",
    purpose="IT consulting services",
    subscribers=["manager@meta.com"]
)

# Search for supplier (uses agentic flow if enabled)
# Routes to BUY_SUPPLIER_AGENT via MetamateAgentBuyAtSupplierSearchTool
info = client.search_supplier("Acme Corp")
```

**New Parameters:**
- `use_agentic` (bool, default=True): Enable Agentic Buying Intake flow

**New Methods:**
- `invite_supplier(...)`: Invite new supplier via conversational AI (uses `BUY_SUPPLIER_AGENT`)
- `start_agentic_session()`: Initialize agentic flow session
- `_search_supplier_via_agentic()`: Internal method for agentic search (uses supplier search tool)

### Integration with Metamate Agents

When the automation sends a message like:
```
"I need to onboard a new supplier: Acme Corp. 
Their email is contact@acme.com. 
Purpose: IT consulting services."
```

The following happens internally in the Buy@ Assistant:

1. **`BUY_ASSISTANT`** (MetamateEngineBuyAtAssistant) receives the message
2. Router analyzes intent and determines this is a supplier onboarding request
3. **Handoff** to `BUY_SUPPLIER_AGENT` (MetamateEngineBuyAtSupplierAgent) via `MetamateExperimentalHandoffTool`
4. **`BUY_SUPPLIER_AGENT`** processes the request using:
   - `MetamateAgentBuyAtSupplierSearchTool` - Check if supplier already exists
   - `MetamateAgentBuyAtSupplierOnboardingTool` - Initiate onboarding workflow
   - `MetamateAgentKnowledgeLoadToolV3` - Load any relevant documentation
5. **Response** is generated and displayed in the chat panel
6. **Automation** parses the response and returns structured data

### Usage Examples

#### Example 1: Onboard New Supplier via Agentic Flow

```python
from src.buyat import BuyAtClient

client = BuyAtClient(use_agentic=True, headless=False)

try:
    # Invite a new supplier
    supplier = client.invite_supplier(
        supplier_name="HCL America Solutions",
        supplier_email="procurement@hcl.com",
        purpose="Professional services for IT infrastructure project",
        subscribers=["igor@meta.com", "procurement@meta.com"]
    )
    
    print(f"Supplier invitation sent: {supplier.name}")
    print(f"Status: {supplier.status}")
    print(f"Supplier has 10 business days to complete enrollment")
    
finally:
    client.close()
```

#### Example 2: Check Supplier Status via Conversation

```python
from src.buyat import AgenticBuyingClient

client = AgenticBuyingClient(headless=True)

try:
    client.start()
    client.navigate_to_suppliers()
    client.open_assistant()
    
    # Ask about supplier status
    response = client.check_supplier_status("Accenture International")
    print(f"Assistant response: {response.message}")
    
finally:
    client.close()
```

#### Example 3: Custom Conversational Flow

```python
from src.buyat import AgenticBuyingClient

client = AgenticBuyingClient(headless=False)

try:
    client.start()
    client.navigate_to_suppliers()
    client.open_assistant()
    
    # Start conversation
    response = client.send_message(
        "I need to onboard a new supplier for marketing services"
    )
    
    # Handle follow-up questions
    if response.has_followup:
        response = client.send_message(
            "The supplier is WPP Group. Email: vendor@wpp.com. "
            "We need them for Q3 campaign creative work."
        )
    
    # Confirm if required
    if response.requires_confirmation:
        response = client.send_message("Yes, please proceed with the invitation")
    
    print(f"Final response: {response.message}")
    
finally:
    client.close()
```

## Migration Guide

### For Existing Code

**Before:**
```python
client = BuyAtClient()
try:
    info = client.search_supplier("Acme Corp")
except SupplierNotFoundError:
    # Supplier doesn't exist, need to invite manually
    pass
```

**After (with agentic flow):**
```python
client = BuyAtClient(use_agentic=True)
try:
    info = client.search_supplier("Acme Corp")
except SupplierNotFoundError:
    # Automatically invite via agentic conversation
    info = client.invite_supplier(
        supplier_name="Acme Corp",
        supplier_email="contact@acme.com",
        purpose="IT services"
    )
```

### Disabling Agentic Flow

If you need to use the traditional form-based workflow:

```python
client = BuyAtClient(use_agentic=False)
# Uses traditional browser automation (when implemented)
```

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  Vendor Onboarding                       │
│                    Orchestrator                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   BuyAtClient                            │
│  ┌──────────────────┐      ┌──────────────────────────┐ │
│  │ Traditional Flow │      │   Agentic Flow (New)     │ │
│  │  (Form-based)    │      │ (Conversational AI)      │ │
│  └──────────────────┘      └──────────────────────────┘ │
│           │                          │                   │
│           ▼                          ▼                   │
│  ┌─────────────────┐      ┌──────────────────────────┐  │
│  │ Browser         │      │ AgenticBuyingClient      │  │
│  │ Automation      │      │ - Chat interface         │  │
│  │ (TODO)          │      │ - Natural language       │  │
│  └─────────────────┘      │ - Context preservation   │  │
│                           └──────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User initiates onboarding** → Orchestrator collects supplier info
2. **BuyAtClient.search_supplier()** → Checks if supplier exists (via agentic or traditional)
3. **If not found** → BuyAtClient.invite_supplier() → Uses AgenticBuyingClient
4. **AgenticBuyingClient** → Opens buy@ assistant, sends natural language prompt
5. **Assistant processes** → Asks follow-up questions, guides through flow
6. **Confirmation** → Assistant presents summary, user confirms
7. **Supplier notified** → Receives email from suppliers@fb.com with 10-day deadline
8. **Status tracking** → BuyAtClient can check status via agentic conversation

## Natural Language Prompts

### Supplier Onboarding Prompt Template

```
I need to onboard a new supplier for our vendor network.

Supplier Name: {supplier_name}
Supplier Email: {supplier_email}
Business Purpose: {purpose}
Subscribers for notifications: {subscribers}

Please initiate the supplier invitation process. The supplier should 
receive enrollment instructions at their email address. They will have 
10 business days to complete the enrollment.
```

### Supplier Status Check Prompt

```
Can you check if supplier "{supplier_name}" already exists in the 
supplier network? If they exist, please provide their status (active, 
inactive, pending). If not, I need to invite them as a new supplier.
```

## Error Handling

### Common Issues

1. **Assistant not responding**
   - Timeout after 30 seconds
   - Take screenshot for debugging
   - Raise `AgenticFlowError`

2. **Unexpected response format**
   - Log the response for analysis
   - Attempt to parse with fallback logic
   - Raise error if critical information missing

3. **Browser automation failures**
   - Element not found → Screenshot + retry
   - Navigation timeout → Increase timeout, retry
   - Authentication issues → Verify SSO session

### Fallback Strategy

If agentic flow fails, the system can fall back to traditional form-based workflow (when implemented):

```python
try:
    # Try agentic flow first
    result = client.invite_supplier(...)
except AgenticFlowError:
    # Fall back to traditional form
    client.use_agentic = False
    result = client.invite_supplier_traditional(...)
```

## Testing

### Unit Tests
Location: `tests/test_agentic_buying.py`

```bash
# Run agentic buying tests
python3 -m unittest tests.test_agentic_buying -v
```

**Test Coverage:**
- AgenticBuyingClient initialization
- Browser session management
- Message sending and response parsing
- Supplier onboarding prompt generation
- Email validation (external domains only)
- Error handling

### Integration Tests
Requires access to buy@ staging environment and valid SSO session.

## Security Considerations

1. **Screenshot Storage**: All screenshots saved to `~/.vendor_onboarding/screenshots/` with 0o700 permissions
2. **PII Handling**: Supplier emails are business contacts; logged with sanitization
3. **Session Management**: Relies on user's existing buy@ SSO session; no credentials stored
4. **Audit Trail**: All actions logged for compliance and debugging

## Limitations

1. **No Public API**: The Agentic Buying Intake does not provide a programmatic API; browser automation is required
2. **UI Dependency**: Automation depends on DOM structure; may break if UI changes
3. **Response Parsing**: Natural language responses require parsing; may need updates as assistant evolves
4. **Rate Limits**: Unknown if conversational interface has rate limits

## Future Enhancements

1. **Structured Responses**: If Meta adds structured data to assistant responses, update parsing logic
2. **API Release**: If Meta releases a public API for Agentic Buying, migrate from browser automation
3. **Multi-turn Conversations**: Enhance to handle complex multi-turn onboarding scenarios
4. **Document Attachment**: Add support for uploading files (quotes, SOWs, contracts) via the chat interface
5. **Skills Integration**: Leverage Agentic Buying "Skills" feature for recurring supplier onboarding patterns

## References

- **Agentic Buying Intake Wiki**: https://www.internalfb.com/wiki/Finance/Source_to_Pay/Agentic_Buying_Intake/
- **FYI Workplace Group**: https://fb.workplace.com/groups/26147349944907174
- **Feedback Group**: https://fb.workplace.com/groups/1498478181887863
- **Design Document**: `docs/plans/2026-06-10-agentic-buying-intake-design.md`
- **Implementation**: `src/buyat/client.py`
- **Tests**: `tests/test_agentic_buying.py`

## Support

For issues with the Agentic Buying Intake itself (not the automation):
- File a task using the bugnub icon in the Agentic Buying case
- Post in the Feedback Workplace group

For issues with the automation code:
- Check logs in `~/.vendor_onboarding/logs/`
- Review screenshots in `~/.vendor_onboarding/screenshots/`
- Open an issue in the Vendor_Onboarding repository
