# Agentic Buying Intake Integration Design

## Overview

On June 10, 2026, Meta launched Agentic Buying Intake — a conversational AI experience that replaces the traditional multi-step form for New Goods & Services requests in buy@. This design document outlines how to adapt the Vendor Onboarding Automation to work with the new agentic flow.

The Agentic Buying Intake uses a chat-based interface where users describe their requests in natural language and attach supporting documents. The AI agent handles the intake process, carrying context forward into downstream forms without requiring re-entry of information. Critically, the downstream operational workflow (supplier onboarding, approvals, TPA, etc.) remains unchanged.

## Buy@ Assistant Architecture

The Buy@ Assistant is built on Meta's Metamate platform using a multi-agent orchestration pattern. Understanding this architecture is crucial for effective integration.

### Core Architecture: Orchestrator + Specialist Agents

The system uses a hierarchical multi-agent architecture:

**Top-Level Router:**
- **`MetamateEngineBuyAtAssistant`** (`BUY_ASSISTANT`) - Main entry point and user-facing assistant. Routes requests to specialized sub-agents via handoff tools. Does not answer questions directly.

**Alternative Orchestrator:**
- **`MetamateEngineBuyAtOrchestrationAgent`** (`BUY_ORCHESTRATION_AGENT`) - Routes to purchasing, sourcing, and supplier sub-agents. Uses Claude Opus 4.6 with max reasoning effort.

### Specialist Agents

| Agent | Role | Key Capabilities |
|-------|------|------------------|
| `MetamateEngineBuyAtPurchasingAgent` | AutoPR - Purchase Request generation | Creates draft PRs from cases, tasks, documents, URLs |
| `MetamateEngineBuyAtAutoPRCriticAgent` | Self-critique loop | Reviews PR quality, provides feedback |
| `MetamateEngineBuyAtSourcingAgent` | Sourcing/procurement guidance | Creates/updates sourcing events, manages RFx |
| `MetamateEngineBuyAtSupplierAgent` | Supplier lookup and management | Searches suppliers, manages onboarding, finds relationship owners |
| `MetamateEngineBuyAtAnalyticAgent` | Data/reporting queries | Dashboard composition, SQL queries, data retrieval |
| `MetamateEngineBuyAtAnalyticResearchAgent` | Deep analytical research | Complex data analysis, Python code execution |
| `MetamateEngineBuyAtKnowledgeGraphAgent` | Policy/knowledge lookups | Searches policies, entities, PRs, POs, suppliers |
| `MetamateEngineBuyAtWorkflowAgent` | Workflow orchestration | Dynamically loads tools based on workflow |
| `MetamateEngineBuyAtGoodsOrServicesAgent` | Classification | Determines if request is for goods or services |
| `MetamateEngineBuyAtSupportAssistant` | General buy@ support | Helpdesk, PO actions, case management |
| `MetamateSmartinvoicingAssistantAgent` | Invoice handling | Invoice search, DTP assistance |

### MCP Tools (47+ Tools)

The agents have access to 47+ tools registered via `MetamateAgentBuyAtToolFactory`, organized into categories:

**Purchase Request & PO Tools:**
- `BUY_PR_SEARCH` / `BUY_PR_NAVIGATOR` — Find and navigate PRs
- `BUY_PO_SEARCH` — Purchase order lookup
- `BUY_PR_LINE_SEARCH` — Line-item search
- `BUY_DOCUMENT_EXTRACTION` — Extract data from attachments

**Supplier Tools:**
- `MetamateAgentBuyAtSupplierSearchTool` — Search suppliers
- `MetamateAgentBuyAtSupplierOnboardingTool` — Initiate onboarding
- `MetamateAgentBuyAtSupplierOnboardingDashboardCaseSearchTool` — Find onboarding cases
- `MetamateAgentBuyAtSupplierRelationshipOwnerSearchTool` — Find supplier owners

**AutoPR Tools:**
- `MetamateAgentBuyAtPurchaseRequestDraftCreateTool` — Create PR drafts
- `MetamateAgentBuyAtPurchaseRequestUpdateTool` — Update PRs
- `MetamateAgentTaskDetailsTool` — Get task details
- `MetamateAgentProcurementCaseDetailsTool` — Get case details

### Helper Traits

Shared functionality across agents:
- `MetamateEngineBuyAtLLMPipelineTrait` — Shared LLM pipeline utilities
- `MetamateEngineBuyAtSuggestFollowupPromptTrait` — Follow-up suggestions
- `MetamateEngineBuyAtThreadContextTrait` — Conversation context management
- `MetamateEngineBuyAtAssistantPOandPRCheckTrait` — PO/PR validation

### Integration Points for Vendor Onboarding

The `MetamateEngineBuyAtSupplierAgent` (`BUY_SUPPLIER_AGENT`) is the key integration point for supplier onboarding automation. It provides:

1. **Supplier Search**: `MetamateAgentBuyAtSupplierSearchTool` - Search for existing suppliers
2. **Supplier Onboarding**: `MetamateAgentBuyAtSupplierOnboardingTool` - Initiate onboarding workflow
3. **Onboarding Case Search**: `MetamateAgentBuyAtSupplierOnboardingDashboardCaseSearchTool` - Track onboarding status
4. **Relationship Owner Search**: `MetamateAgentBuyAtSupplierRelationshipOwnerSearchTool` - Find supplier contacts

The agent uses Claude Opus 4.6 with max reasoning effort, indicating complex reasoning capabilities for supplier management tasks.

### AutoPR AI Agent

The **AutoPR AI Agent** (part of `MetamateEngineBuyAtPurchasingAgent`) is particularly relevant:
- Creates draft Purchase Requests from Agent Workspace cases, tasks, attachments, and URLs
- Extracts details using AI-driven extraction
- Provides field-level reasoning and citations for explainability
- Becomes the default PR drafting experience starting March 2026
- Accessible via buy@ Assistant panel or directly from Agent Workspace cases

**Key Limitations:**
- Cannot create new suppliers, cost centers, purchasing categories, or FBPNs (must exist first)
- Cannot update PRs after submission
- Limited support for multi-turn PR updates after draft creation
- No compliance/risk assessment (standard buy@ validations still apply)

## Current State

The existing `BuyAtClient` (`src/buyat/client.py`) provides:
- Supplier search and verification via browser automation (TODO implementation)
- Caching to avoid repeated searches
- Methods: `search_supplier()`, `verify_supplier_exists()`, `is_supplier_active()`

The client currently has a TODO for implementing actual browser automation using Playwright.

## New Requirements

With the Agentic Buying Intake launch, we need to:

1. **Interact with conversational UI**: Instead of filling form fields, send natural language messages to the AI agent
2. **Handle chat-based flow**: The agent asks follow-up questions; we must respond appropriately
3. **Support vendor onboarding**: Describe supplier onboarding requests in natural language
4. **Maintain backward compatibility**: The off-ramp to traditional forms exists (though not advertised)
5. **Preserve existing functionality**: Supplier search/verification remains valuable

## Architecture

### Approach: Hybrid Conversational Automation

We will extend `BuyAtClient` with new methods for agentic flow automation while preserving existing supplier verification capabilities. The approach uses browser automation (Playwright) to interact with the chat interface.

### Components

#### 1. AgenticBuyingClient (New Class)

A new class that handles the conversational UI automation:

```python
class AgenticBuyingClient:
    """Client for Agentic Buying Intake conversational UI.
    
    Automates the chat-based interface for New Goods & Services requests,
    including vendor onboarding workflows.
    """
    
    AGENTIC_URL = "https://www.internalfb.com/buy/new-request"
    
    def __init__(self, headless: bool = True, screenshot_dir: str = None):
        # Initialize browser, same as BuyAtClient
```

**Key Methods:**
- `start_new_request()`: Navigate to buy@, select New Goods & Services tile
- `send_message(message: str)`: Send a message to the AI agent
- `wait_for_agent_response()`: Wait for and parse agent's reply
- `attach_document(file_path: str)`: Upload supporting documents
- `onboard_supplier(supplier_name: str, email: str, purpose: str)`: High-level workflow for supplier onboarding
- `review_and_confirm()`: Review agent's summary and confirm submission

#### 2. Enhanced BuyAtClient

Extend the existing `BuyAtClient` to integrate with agentic flow:

```python
class BuyAtClient:
    # Existing methods preserved
    
    def __init__(self, ..., use_agentic: bool = True):
        # Add agentic flow support
        self.use_agentic = use_agentic
        self.agentic_client = AgenticBuyingClient(...) if use_agentic else None
    
    def invite_supplier_via_agentic(
        self, 
        supplier_name: str, 
        supplier_email: str,
        purpose: str,
        subscribers: List[str] = None
    ) -> SupplierInfo:
        """Invite a new supplier using the Agentic Buying Intake flow.
        
        Uses conversational AI to describe the onboarding request
        and handles the chat-based interaction.
        """
```

### Data Flow

#### Vendor Onboarding via Agentic Flow

1. **Initialize**: Create `AgenticBuyingClient`, launch browser
2. **Navigate**: Go to buy@ New Request page, select "New Goods & Services"
3. **Start Conversation**: Agent greets user, asks what they need
4. **Describe Request**: Send natural language prompt:
   ```
   "I need to onboard a new supplier: {supplier_name}. 
   Their email is {supplier_email}. 
   Purpose: {purpose}. 
   Please invite them to the supplier network."
   ```
5. **Handle Follow-ups**: Agent may ask for:
   - Additional supplier details
   - Supporting documents (quote, SOW, contract)
   - Budget/cost center information
   - Subscribers for notifications
6. **Attach Documents**: If available, upload relevant files
7. **Review Summary**: Agent presents summary of request
8. **Confirm**: Approve and submit
9. **Track Status**: Supplier receives invitation from suppliers@fb.com

#### Natural Language Prompt Templates

**Supplier Onboarding:**
```
I need to onboard a new supplier for our vendor network.

Supplier Name: {supplier_name}
Supplier Email: {supplier_email}
Business Purpose: {purpose}
{f"Subscribers: {', '.join(subscribers)}" if subscribers else ""}

Please initiate the supplier invitation process. The supplier should 
receive enrollment instructions at their email address.
```

**Supplier Search (if needed):**
```
Can you check if supplier "{supplier_name}" already exists in the 
supplier network? If they exist, please provide their status. If not, 
I need to invite them as a new supplier.
```

### Error Handling

1. **Agent Unavailable**: Fall back to traditional form via off-ramp
2. **Unclear Response**: Ask agent to clarify or rephrase
3. **Missing Information**: Agent will prompt for required details; collect and provide
4. **Timeout**: Implement retry logic with exponential backoff
5. **Unexpected Flow**: Take screenshot, log state, raise exception

### Browser Automation Details

**Technology**: Playwright (already used in other parts of the codebase - see `src/csc/automation.py`)

**Key Selectors** (to be determined via inspection):
- Chat input field
- Send message button
- Agent response container
- File upload button
- Confirmation/Submit button
- Off-ramp link (to traditional form)

**Wait Strategies**:
- Wait for agent response (detect typing indicator disappearance)
- Wait for specific text in agent reply
- Wait for UI elements to become interactive

## Integration Points

### With Existing BuyAtClient

The existing `BuyAtClient.search_supplier()` method can be used to:
1. Check if supplier exists before attempting onboarding
2. Verify supplier status after onboarding initiation
3. Cache results to avoid redundant checks

### With Workflow Orchestrator

The `src/orchestrator/workflow.py` can invoke the agentic flow as part of the vendor onboarding pipeline:
1. Collect supplier information via intake form
2. Use `AgenticBuyingClient` to initiate onboarding
3. Monitor status via `BuyAtClient` supplier verification
4. Proceed to next steps (CSC, AMP, TPA) once supplier is active

## Testing Strategy

### Unit Tests
- Mock browser interactions
- Test prompt generation
- Test response parsing
- Test error handling

### Integration Tests
- Test against staging buy@ environment
- Verify end-to-end supplier onboarding flow
- Test fallback to traditional form
- Test with various supplier scenarios (new, existing, inactive)

### Test Data
- Mock supplier names and emails
- Sample documents (PDF, DOCX) for attachment testing
- Various business purposes

## Security Considerations

1. **Screenshot Storage**: Continue using secure directory with 0o700 permissions
2. **Credential Handling**: No credentials stored; relies on user's existing buy@ session
3. **PII Protection**: Supplier emails are business contacts; handle per Meta data policies
4. **Audit Trail**: Log all actions for compliance and debugging

## Rollout Plan

### Phase 1: Foundation (Week 1)
- Implement `AgenticBuyingClient` with basic chat interaction
- Add methods for sending messages and waiting for responses
- Implement navigation to Agentic Buying Intake

### Phase 2: Supplier Onboarding Flow (Week 2)
- Implement `onboard_supplier()` high-level workflow
- Add natural language prompt templates
- Handle follow-up questions and document attachment
- Implement review and confirmation

### Phase 3: Integration & Testing (Week 3)
- Integrate with existing `BuyAtClient`
- Add fallback to traditional form
- Comprehensive testing (unit, integration)
- Documentation and examples

### Phase 4: Production Readiness (Week 4)
- Error handling and retry logic
- Monitoring and alerting
- Performance optimization
- Security review

## Success Criteria

1. **Functional**: Successfully onboard a new supplier via agentic flow
2. **Reliable**: 95% success rate for standard onboarding scenarios
3. **Maintainable**: Clear code structure, comprehensive documentation
4. **Compatible**: Works alongside existing BuyAtClient functionality
5. **Observable**: Logging and screenshots for debugging failures

## Open Questions

1. What are the exact CSS selectors for the chat interface elements?
2. How does the agent handle supplier invitation specifically? Does it use the same backend as the traditional form?
3. What is the expected response time for the AI agent?
4. Are there rate limits on the conversational interface?
5. How do we detect when the agent has finished processing and is waiting for user input?

## References

- Agentic Buying Intake Wiki: https://www.internalfb.com/wiki/Finance/Source_to_Pay/Agentic_Buying_Intake/
- Agentic Buying Intake FYI Group: https://fb.workplace.com/groups/26147349944907174
- Agentic Buying Intake Feedback Group: https://fb.workplace.com/groups/1498478181887863
- Existing BuyAtClient: `src/buyat/client.py`
- CSC Automation (Playwright example): `src/csc/automation.py`
