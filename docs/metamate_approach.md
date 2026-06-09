# Vendor Onboarding Automation - Metamate-Based Approach

## Executive Summary

**Pivot**: Instead of building a standalone automation system with browser automation, leverage **Metamate's agentic capabilities** to orchestrate the vendor onboarding workflow directly through conversational chat.

**Key Insight**: With Buy@ transitioning to an agentic interface tomorrow, and Metamate's existing access to Meta's internal tools, we can build a **conversational workflow assistant** that guides users through onboarding while Metamate handles all system interactions behind the scenes.

## Why Metamate-Based Approach?

### Advantages Over Standalone System

| Aspect | Standalone System | Metamate-Based | Benefit |
|--------|------------------|----------------|---------|
| **User Interface** | Build CLI + Web UI from scratch | Natural chat interface | ✅ Zero UI development, familiar interaction |
| **System Access** | Browser automation (fragile) | Native tool access | ✅ More reliable, no UI breakage |
| **Buy@ Integration** | Screen scraping | Agentic API (new) | ✅ Official support, stable |
| **Maintenance** | Update selectors when UI changes | API-based, stable | ✅ Lower maintenance burden |
| **Deployment** | Install Python, dependencies, browsers | Already available in Metamate | ✅ Zero installation |
| **Discoverability** | Users must find and install tool | Available in Metamate | ✅ Higher adoption |
| **Context** | Stateless, needs config files | Conversational memory | ✅ Natural multi-turn interaction |

### Metamate Capabilities We Can Leverage

1. **Tool Access**: Metamate has built-in access to:
   - Butterfly Forms API (via existing tools)
   - Buy@ (new agentic interface)
   - CSC, AMP, TPA (via browser automation or APIs)
   - Workplace (notifications)
   - Email (notifications)
   - Task system (tracking)

2. **Conversational Intelligence**:
   - Natural language understanding
   - Context retention across turns
   - Clarifying questions when data is ambiguous
   - Progress updates and status reporting

3. **Existing Infrastructure**:
   - No deployment needed
   - Already authenticated (uses user's credentials)
   - Built-in error handling and retry logic
   - Audit trail via conversation history

## Revised Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    User (via Chat)                           │
│  "I need to onboard Acme Corp as a vendor with 5 workers"    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Metamate (Conversational Agent)                 │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Vendor Onboarding Skill                               │ │
│  │                                                        │ │
│  │  • Intake Orchestrator (conversational prompts)        │ │
│  │  • Workflow Engine (state management)                  │ │
│  │  • System Adapters (tool integrations)                 │ │
│  │  • Progress Tracker (status updates)                   │ │
│  │  • Notification Manager (Workplace/Email)              │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────┬──────────────────┬──────────────┬──────────────┘
             │                  │              │
    ┌────────▼────────┐  ┌─────▼──────┐  ┌───▼──────────┐
    │   Buy@ Agent    │  │ Butterfly  │  │     CSC      │
    │  (New - Agentic)│  │  API Tool  │  │  Browser/API │
    └────────┬────────┘  └─────┬──────┘  └────┬─────────┘
             │                 │              │
    ┌────────▼────────┐  ┌─────▼──────┐  ┌───▼──────────┐
    │   AMP Tool      │  │  TPA API   │  │ Workplace    │
    │                 │  │            │  │  Bot         │
    └─────────────────┘  └────────────┘  └──────────────┘
```

### Component Design

#### 1. Vendor Onboarding Skill (Metamate Skill)

**Location**: `~/.llms/skills/vendor-onboarding/SKILL.md`

**Purpose**: Metamate skill that orchestrates the complete vendor onboarding workflow through conversational interaction.

**Key Features**:
- **Conversational Intake**: Guides user through data collection via natural chat
- **Progressive Disclosure**: Asks only relevant questions based on previous answers
- **Smart Defaults**: Infers values from context (e.g., manager from user profile)
- **Validation**: Real-time validation with helpful error messages
- **Status Updates**: Proactive notifications at key milestones

**Example Interaction**:

```
User: I need to onboard Acme Corp as a vendor

Metamate: I'll help you onboard Acme Corp! Let me gather the required information.

First, let me check if Acme Corp is already in our systems...
[Checks Buy@ via agentic interface]

✓ Good news! Acme Corp is already in Buy@ (ID: SUP12345) and active.
  This means we can skip the supplier onboarding form.

Now, tell me about the vendor workers:
- How many workers need to be onboarded?
- What are their roles?
- When do they need to start?

User: 3 workers - 2 engineers and 1 designer. They start April 15th.

Metamate: Great! I'll need details for each worker:
1. Full name
2. Email address  
3. Job title
4. Work location (Remote/Onsite/Hybrid)

You can provide them one by one, or upload a spreadsheet. Which would you prefer?

User: Let me upload a spreadsheet

Metamate: Perfect! Please upload an Excel file with these columns:
- Full Name
- Email Address
- Job Title
- Start Date (YYYY-MM-DD)
- End Date (YYYY-MM-DD)
- Manager Email
- Work Location
- Office Location (if Onsite/Hybrid)
- Phone Number (optional)

[User uploads file]

✓ Validated 3 workers successfully!
  - John Doe (john@acme.com) - Software Engineer
  - Jane Smith (jane@acme.com) - Product Designer  
  - Bob Johnson (bob@acme.com) - Software Engineer

Next, I need to know about access requirements. Which systems will they need access to?

[Continues conversational intake...]

Once I have all information, I'll:
1. Create AMP group for access management
2. Submit YubiKey requests (if needed)
3. Onboard workers via CSC
4. Initiate TPA assessment
5. Keep you updated on progress!

Shall I proceed?
```

#### 2. Workflow Engine (State Management)

**Purpose**: Track onboarding progress across multiple systems and sessions

**Implementation**:
- Uses Metamate's conversation state to track progress
- Persists to SQLite for long-running workflows (weeks)
- Enables resume if conversation is interrupted
- Provides status via `vendor_onboarding_status` command

**State Structure**:
```python
{
    "workflow_id": "vo-2024-0456",
    "supplier_name": "Acme Corp",
    "supplier_id": "SUP12345",
    "status": "in_progress",
    "current_step": "tpa_assessment",
    "completed_steps": ["buyat_verification", "yubikey_request", "amp_group"],
    "pending_steps": ["csc_onboarding", "tpa_completion"],
    "workers": [...],
    "amp_group_id": "acme-corp-vendors",
    "tpa_assessment_id": "TPA-2024-0456",
    "created_at": "2024-04-01T10:00:00Z",
    "updated_at": "2024-04-01T10:30:00Z"
}
```

#### 3. System Adapters (Tool Wrappers)

**Buy@ Adapter** (NEW - Agentic Interface):
```python
# Uses Metamate's Buy@ agentic capability (available tomorrow)
def verify_supplier(supplier_name: str) -> SupplierInfo:
    """Check if supplier exists in Buy@ via agentic interface."""
    # Metamate will have native Buy@ tool
    result = metmate.tools.buyat.search(supplier_name)
    return SupplierInfo(
        exists=result.found,
        supplier_id=result.id,
        status=result.status
    )
```

**Butterfly Adapter** (Existing):
```python
# Reuse existing ButterflyClient from Phase 1
from src.butterfly import ButterflyClient

def submit_forms(forms_data: Dict) -> Dict[str, str]:
    """Submit Butterfly forms via API."""
    client = ButterflyClient()
    results = {}
    
    if forms_data.get("yubikey"):
        resp = client.submit_yubikey_request(forms_data["yubikey"])
        results["yubikey"] = resp.response_id
    
    # ... other forms
    return results
```

**CSC Adapter** (Browser Automation via Metamate):
```python
# Metamate has browser automation capabilities
def onboard_workers(workers: List[WorkerInfo]) -> Dict:
    """Onboard workers via CSC using Metamate browser."""
    # Metamate can launch browser and automate CSC
    # Or use CSC API if available
    pass
```

**AMP Adapter**:
```python
# Similar to CSC - browser automation or API
def create_amp_group(name: str, members: List[str]) -> str:
    """Create AMP group for vendor access."""
    pass
```

**TPA Adapter** (Existing):
```python
# Reuse existing TPAClient from Phase 3
from src.tpa import TPAClient

def initiate_tpa(vendor_data: Dict) -> str:
    """Initiate TPA assessment."""
    client = TPAClient()
    result = client.submit_assessment(vendor_data)
    return result["assessment_id"]
```

#### 4. Notification Manager

**Purpose**: Keep requestor and stakeholders informed via Workplace and Email

**Implementation**:
```python
def notify_progress(workflow_id: str, message: str, subscribers: List[str]):
    """Send progress update to requestor and subscribers."""
    
    # Workplace notification
    workplace_post = f"""
    🔄 Vendor Onboarding Update: {supplier_name}
    
    {message}
    
    View details: [Dashboard Link]
    """
    metmate.tools.workplace.create_post(
        group_id=ONBOARDING_GROUP,
        message=workplace_post,
        tag_people=subscribers
    )
    
    # Email notification (for critical updates)
    if is_critical(message):
        metmate.tools.email.send(
            to=subscribers,
            subject=f"Vendor Onboarding: {supplier_name}",
            body=message
        )
```

## User Experience Flow

### Complete Conversational Workflow

```
User: @Metamate I need to onboard Acme Corp as a vendor

Metamate: I'll help you onboard Acme Corp! 🎉

Let me start by checking if they're already in our systems...

[2 seconds later]

✓ Good news! Acme Corp is already in Buy@ and active.
  This means we can skip the supplier onboarding form and save ~1 week!

Now I need some information. I'll guide you through it step by step.

First, about the contract:
• What's the business justification for this vendor?
• What's the estimated annual spend?
• What are the contract start and end dates?

User: We're hiring them for Q2 project development. Budget is $150K. 
      April 15, 2024 to April 15, 2025.

Metamate: Perfect! Got it:
✓ Business justification: Q2 project development
✓ Budget: $150,000
✓ Duration: April 15, 2024 → April 15, 2025 (12 months)

Next, tell me about the workers. How many people are we onboarding?

User: 3 workers

Metamate: Great! For each worker, I'll need:
1. Full name
2. Email address
3. Job title
4. Work location (Remote, Onsite, or Hybrid)
5. Manager's email

You can:
• Type them one by one (I'll prompt you)
• Upload a spreadsheet
• Paste from a list

What works best for you?

User: Let me upload a spreadsheet

Metamate: Perfect! I've created a template for you with the required columns.
          [Provides download link for template]
          
          Once you fill it out, just upload it here and I'll validate the data.

[User uploads spreadsheet]

✓ Validated 3 workers successfully!
  ✓ John Doe (john.doe@acme.com) - Software Engineer, Remote
  ✓ Jane Smith (jane.smith@acme.com) - Product Designer, Onsite (Menlo Park)
  ✓ Bob Johnson (bob.johnson@acme.com) - Data Analyst, Hybrid (New York)

Next, access requirements. Which systems do they need access to?
(Common options: GitHub, Asana, Figma, AWS, GCP)

User: They need GitHub and AWS access.

Metamate: Got it! I'll create an AMP group called 'acme-corp-vendors' with these 3 members.
          This group will be used to manage their access to GitHub and AWS.

Do the workers need YubiKeys for MFA?

User: Yes, all three need YubiKeys.

Metamate: I'll need shipping addresses for the YubiKeys. I can:
• Use the same address for all three
• Collect individual addresses
• Skip for now and handle separately

What would you prefer?

User: Same address for all - ship to our Menlo Park office.

Metamate: Perfect! I'll use:
  Meta HQ, 1 Hacker Way, Menlo Park, CA 94025

Let me summarize what I'll do:

📋 **Vendor Onboarding Plan for Acme Corp**

**Supplier**: Acme Corp (already active in Buy@ ✓ - skipping supplier form)
**Workers**: 3 people to onboard
**Access**: GitHub, AWS (via AMP group: acme-corp-vendors)
**Security**: YubiKeys for all 3 workers (shipped to Menlo Park)
**Compliance**: TPA assessment will be initiated

**Estimated Timeline**:
• AMP group creation: 5 minutes
• YubiKey request: 3 minutes (delivery: 3+ weeks)
• CSC worker onboarding: 10 minutes
• TPA assessment: 3 minutes to initiate (review: 2-3 days)

**Total active time**: ~20 minutes
**Total calendar time**: 3-4 days (mostly waiting for TPA)

Shall I proceed? (yes/no)

User: Yes, proceed!

Metamate: 🚀 Starting vendor onboarding workflow...

[5 minutes later]

✅ **Progress Update: Acme Corp**

Completed:
✓ AMP group 'acme-corp-vendors' created with 3 members
✓ YubiKey request submitted (Tracking: 1Z999AA1234567890)
✓ CSC worker onboarding completed (3 workers processed)
✓ TPA assessment initiated (ID: TPA-2024-0456)

Next Steps:
• TPA assessment is under review (estimated 2-3 days)
• YubiKeys will ship within 3 weeks
• I'll notify you when TPA is complete

You can check status anytime by asking: "What's the status of Acme Corp onboarding?"

[2 days later - proactive notification]

📬 **Vendor Onboarding Update: Acme Corp**

Great news! The TPA assessment has been approved! ✅

**Summary**:
• Risk Level: Medium
• Findings: 2 minor (addressed)
• Status: APPROVED

**Next Steps**:
• Workers can now access approved systems
• YubiKeys are in transit (tracking: 1Z999AA1234567890)
• Onboarding complete!

Is there anything else you need help with?
```

## Benefits of Metamate Approach

### For Users
✅ **Zero Installation**: Already available in Metamate, no setup required
✅ **Natural Interface**: Chat is familiar, no learning curve
✅ **Context Aware**: Metamate remembers conversation history
✅ **Flexible Input**: Type, upload files, or paste data - whatever is easiest
✅ **Proactive Updates**: Metamate notifies you, no need to check status
✅ **Always Available**: Access from anywhere Metamate is available

### For Implementation Team
✅ **Faster Development**: No need to build UI, auth, or deployment infrastructure
✅ **Leverage Existing Tools**: Use Metamate's built-in capabilities
✅ **Easier Maintenance**: No browser automation to break when UIs change
✅ **Built-in Features**: Notifications, file handling, user management already available
✅ **Focus on Logic**: Spend time on workflow logic, not infrastructure

### For Meta
✅ **Higher Adoption**: Users already in Metamate, lower barrier to entry
✅ **Consistent Experience**: Follows Metamate interaction patterns
✅ **Centralized**: All automations in one place, easier to discover
✅ **Secure**: Uses Metamate's existing security model and audit logging

## Implementation Plan

### Phase 1: Metamate Skill Foundation (Week 1-2)
**Goal**: Create basic Metamate skill with conversational intake

**Tasks**:
1. Create skill structure (`~/.llms/skills/vendor-onboarding/SKILL.md`)
2. Implement conversational intake orchestrator
3. Integrate Buy@ agentic interface (available tomorrow)
4. Integrate existing Butterfly API client
5. Add progress tracking and status updates

**Deliverable**: Users can start onboarding via chat, system collects data and submits Butterfly forms

### Phase 2: Worker Onboarding (Week 3-4)
**Goal**: Complete CSC and AMP integration

**Tasks**:
1. Integrate CSC worker onboarding (reuse existing automation or Metamate browser)
2. Integrate AMP group management
3. Add spreadsheet upload support via chat
4. Implement bulk worker processing
5. Add validation with user-friendly error messages

**Deliverable**: End-to-end onboarding including workers and access groups

### Phase 3: Compliance & Notifications (Week 5-6)
**Goal**: Add TPA and notification capabilities

**Tasks**:
1. Integrate TPA API client (already built)
2. Implement Workplace notifications
3. Add Email notifications for critical updates
4. Create status checking commands
5. Add subscriber management

**Deliverable**: Complete workflow with compliance and notifications

### Phase 4: Polish & Documentation (Week 7-8)
**Goal**: Production-ready with documentation

**Tasks**:
1. Create user guide (how to use via Metamate)
2. Add example conversations and common scenarios
3. Implement advanced features (resume, cancel, modify)
4. Performance optimization
5. Pilot with 5-10 real onboardings
6. Gather feedback and iterate

**Deliverable**: Production-ready system with documentation

## Migration Strategy

### From Standalone to Metamate

The work completed in Phases 1-2 (standalone system) is **not wasted** - it provides:

1. **API Clients**: Butterfly, TPA clients can be reused directly in Metamate skill
2. **Business Logic**: Validation rules, form schemas, workflow logic all apply
3. **Testing**: Unit tests validate core logic that Metamate will use
4. **Documentation**: Architecture docs and user guides inform Metamate skill design

**What changes**:
- ❌ **Remove**: CLI tool, browser automation (replaced by Metamate tools)
- ✅ **Reuse**: API clients, validation logic, workflow engine, data models
- ✅ **Adapt**: Convert to Metamate skill format with conversational interface

## Success Metrics

### Adoption Metrics
- **Conversations Started**: Number of vendor onboardings initiated via Metamate
- **Completion Rate**: % of started onboardings that complete successfully
- **User Satisfaction**: Rating of conversational experience (target: >4.5/5)

### Efficiency Metrics
- **Time to Complete**: Target < 20 minutes active time (vs. 40 hours manual)
- **Forms Automated**: 100% of forms submitted via API (no manual entry)
- **Error Rate**: < 5% (vs. 30% manual)

### Quality Metrics
- **First-Time Success**: % of onboardings that complete without rework
- **User Feedback**: Qualitative feedback on ease of use
- **Support Tickets**: Number of issues requiring human intervention

## Conclusion

The Metamate-based approach represents a **fundamental shift** from building standalone automation to leveraging conversational AI as the orchestration layer. With Buy@ becoming agentic tomorrow, this is the perfect time to pivot.

**Key Advantages**:
1. **Faster to Market**: 6-8 weeks instead of 12+ weeks (no UI to build)
2. **Better UX**: Natural conversation vs. forms and dashboards
3. **Lower Maintenance**: API-based vs. fragile browser automation
4. **Higher Adoption**: Users already in Metamate daily

**Recommendation**: Pivot to Metamate-based approach immediately. The foundation work (API clients, validation logic, workflow engine) is reusable. Focus on building the conversational skill that orchestrates everything through Metamate's native capabilities.
