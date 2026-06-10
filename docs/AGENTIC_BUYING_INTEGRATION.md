# Agentic Buying Intake Integration

## Overview

On June 10, 2026, Meta launched **Agentic Buying Intake** — a conversational AI experience that replaces the traditional multi-step form for New Goods & Services requests in buy@. This document describes how the Vendor Onboarding Automation integrates with the new agentic flow.

## What Changed

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

### New Components

#### AgenticBuyingClient
A new class (`src/buyat/client.py`) that automates the conversational UI:

```python
from src.buyat import AgenticBuyingClient

client = AgenticBuyingClient(headless=True)
client.start()
client.navigate_to_suppliers()
client.open_assistant()

# Onboard a supplier via conversation
response = client.onboard_supplier(
    supplier_name="Acme Corp",
    supplier_email="contact@acme.com",
    purpose="IT consulting services",
    subscribers=["manager@meta.com"]
)
```

**Key Methods:**
- `start()`: Initialize browser session
- `navigate_to_suppliers()`: Go to Suppliers page
- `open_assistant()`: Open the buy@ assistant side panel
- `send_message(message)`: Send natural language message to assistant
- `onboard_supplier(...)`: High-level workflow for supplier onboarding
- `check_supplier_status(name)`: Check if supplier exists via conversation
- `close()`: Clean up browser resources

#### Enhanced BuyAtClient
The existing `BuyAtClient` now supports agentic flow:

```python
from src.buyat import BuyAtClient

# Enable agentic flow (default)
client = BuyAtClient(use_agentic=True)

# Invite a new supplier via agentic conversation
supplier = client.invite_supplier(
    supplier_name="Acme Corp",
    supplier_email="contact@acme.com",
    purpose="IT consulting services",
    subscribers=["manager@meta.com"]
)

# Search for supplier (uses agentic flow if enabled)
info = client.search_supplier("Acme Corp")
```

**New Parameters:**
- `use_agentic` (bool, default=True): Enable Agentic Buying Intake flow

**New Methods:**
- `invite_supplier(...)`: Invite new supplier via conversational AI
- `start_agentic_session()`: Initialize agentic flow session
- `_search_supplier_via_agentic()`: Internal method for agentic search

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
