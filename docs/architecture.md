# Vendor Onboarding Automation - Architecture & Solution Design

## Executive Summary

The Vendor Onboarding Automation system transforms Meta's manual, multi-system vendor onboarding process into a streamlined, automated workflow. By collecting all required information upfront through a single intake interface, the system orchestrates the entire onboarding process across 7+ systems without human intervention, reducing onboarding time from weeks to days while ensuring compliance and auditability.

## Current State Challenges

### Pain Points
- **Manual Process**: 7+ disconnected systems requiring repeated data entry
- **Long Lead Times**: 
  - YubiKeys: 3+ weeks
  - Contracts: 6+ weeks  
  - APAC/EMEA equipment: 34-36 days
- **No Visibility**: No unified tracking across systems
- **Error-Prone**: Repeated manual data entry leads to mistakes
- **Complex Knowledge**: Requires expertise in which forms to fill in which order
- **8+ Butterfly Forms**: Supplier Onboarding, YubiKey, SoW, CSC, TPA, etc.

### Systems Involved
1. **Buy@** - Supplier verification and onboarding
2. **Butterfly** - Forms and approvals (5+ forms)
3. **CSC** - Contractor Services Center (worker onboarding)
4. **AMP** - Access Management Platform (group setup)
5. **TPA** - Third Party Assessment (security review)
6. **Okta** - Identity and access routing
7. **Beeline** - Vendor management (future)

## Solution Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   CLI Tool  │  │   Web UI     │  │  Monitoring Dashboard  │  │
│  │ (Interactive│  │ (React +     │  │  (Real-time Progress)  │  │
│  │  Prompts)   │  │  Progressive │  │                        │  │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
┌─────────▼────────────────▼─────────────────────▼────────────────┐
│                    Orchestration Engine                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Workflow Orchestrator                                    │  │
│  │  • State Machine (SQLite persistence)                    │  │
│  │  • Dependency Graph (validates all dependencies exist)   │  │
│  │  • Retry Logic (exponential backoff)                     │  │
│  │  • Checkpoint/Resume (reconstructs actions on resume)    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────┬────────────────┬──────────────────┬───────────────────┘
          │                │                  │
┌─────────▼──────┐  ┌──────▼───────┐  ┌──────▼────────┐
│   Butterfly    │  │     CSC      │  │     AMP       │
│   API Adapter  │  │   Browser    │  │   Browser     │
│                │  │  Automation  │  │  Automation   │
│ • Form Submit  │  │              │  │               │
│ • Validation   │  │ • SSO Login  │  │ • Group Mgmt  │
│ • Status Check │  │ • Worker     │  │ • Membership  │
└────────┬───────┘  │   Onboarding │  └──────┬────────┘
         │          │ • Bulk Upload│         │
         │          └──────┬───────┘         │
         │                 │                 │
┌────────▼──────┐  ┌───────▼────────┐  ┌────▼──────────┐
│     TPA       │  │     Buy@       │  │  Notifications│
│  API Adapter  │  │    Browser     │  │               │
│               │  │   Automation   │  │ • Workplace   │
│ • Assessment  │  │                │  │ • Email       │
│ • Status Poll │  │ • Supplier     │  │ • Task System │
└───────────────┘  │   Search       │  └───────────────┘
                   │ • Verification │
                   │ • Caching      │
                   └────────────────┘
```

### Architecture Improvements (Risk Mitigation)

Based on code review findings, the following architectural improvements have been implemented:

#### 1. Browser Lifecycle Management (Critical Fix)
**Risk**: Browser context manager closes prematurely, making browser unusable for subsequent operations.

**Solution**: 
- Browser lifecycle now managed at the orchestrator level, not per-method
- Playwright context stored as instance variable with explicit `close()` method
- Context manager pattern replaced with manual lifecycle control
- Ensures browser stays alive across multiple operations in a workflow

#### 2. Dependency Validation (Critical Fix)
**Risk**: Workflow steps could run prematurely if dependencies not yet registered, causing race conditions.

**Solution**:
- `_get_ready_steps()` now validates that all dependencies exist in the steps dictionary
- Raises `ValueError` with clear message if dependency is missing
- Prevents silent failures and ensures correct execution order
- Added validation at workflow setup time to catch configuration errors early

#### 3. Resume Functionality (Critical Fix)
**Risk**: Workflow resume did not reconstruct step actions, making resume non-functional.

**Solution**:
- Implemented action registry pattern: actions registered by name, reconstructed on resume
- Workflow state now includes action references (not just metadata)
- On resume, orchestrator re-binds actions from registry before execution
- Documented requirement: steps must be re-registered with same IDs before resume

#### 4. Robust Upload Detection (Warning Fix)
**Risk**: Bulk upload detection relied on transient text that might not appear, causing false failures.

**Solution**:
- Implemented multi-strategy detection: 
  1. Wait for processing text (with short timeout, non-blocking)
  2. Wait for file input to clear (indicates upload complete)
  3. Wait for success indicator (final confirmation)
- Fallback to success if file input cleared but no text appeared
- More resilient to UI timing variations

#### 5. PII Protection (Security)
**Risk**: Worker PII (name, email, phone) logged at INFO level, exposing sensitive data in logs.

**Solution**:
- Implemented log sanitization: PII fields masked in log messages
- Example: `john.doe@vendor.com` → `j***@vendor.com`
- Sensitive operations logged at DEBUG level instead of INFO
- Audit trail still captures complete data in secure workflow state (not logs)
- Documented PII handling in security guidelines

#### 6. Secure Defaults (Security)
**Risk**: Screenshot directory defaults to world-readable `/tmp`, exposing sensitive screenshots.

**Solution**:
- Changed default to `~/.vendor_onboarding/screenshots` with 0700 permissions
- Directory created with restricted access (owner-only)
- Documented security implications in configuration guide
- Users can still configure custom path if needed

#### 7. Flexible Validation (UX Improvement)
**Risk**: Spreadsheet header validation too strict, failing on whitespace/case differences.

**Solution**:
- Implemented normalized header comparison:
  - Strip leading/trailing whitespace
  - Case-insensitive comparison
  - Allow additional columns (validate required columns exist)
- Provides better user experience when users modify templates
- Clear error messages indicate which required columns are missing

### Component Details

#### 1. Intake Layer
**Purpose**: Collect all required information upfront through a single interface

**CLI Tool** (`src/intake/cli.py`):
- Interactive prompts with real-time validation
- Progressive disclosure (only asks relevant questions)
- Support for config file input (JSON)
- Dry-run mode for validation without submission
- Save/resume capability

**Web UI** (Future - Phase 4):
- React-based interface
- Real-time supplier lookup
- Draft save functionality
- Visual progress indicators

**Key Features**:
- Single intake collects data for ALL downstream systems
- Smart defaults based on vendor type
- Validation against form schemas before submission
- Estimated completion time based on selected options

#### 2. Orchestration Engine
**Purpose**: Coordinate workflow execution across systems with dependency management

**Workflow Orchestrator** (`src/orchestrator/workflow.py`):
- **State Machine**: Tracks status of each step (pending, running, completed, failed, blocked)
- **Dependency Graph**: Ensures steps execute in correct order
  - Parallel: Supplier onboarding, YubiKey, SoW, TPA, AMP (independent)
  - Sequential: CSC profile update (waits for AMP group)
- **Retry Logic**: Exponential backoff for transient failures (network issues, rate limits)
- **Persistence**: SQLite-based state store enables resume after failures/restarts
- **Audit Logging**: Complete trail of all actions for compliance

**Example Workflow**:
```
1. Verify Supplier in Buy@ (2 min)
   ↓
2. Check Supplier Status (1 min)
   ↓ (if not active)
3. Submit Supplier Onboarding Form (5 min) ←─┐
   ↓                                        │
4. Submit YubiKey Request (3 min) ──────────┤
   ↓                                        ├── Parallel
5. Submit Statement of Work (5 min) ────────┤   Execution
   ↓                                        │
6. Initiate TPA Assessment (3 min) ─────────┤
   ↓                                        │
7. Create AMP Group (5 min) ←───────────────┘
   ↓
8. Update CSC Profile (5 min) [waits for AMP]
   ↓
9. Onboard Workers via CSC (10 min) [bulk upload]
```

#### 3. System Adapters

**Butterfly API Adapter** (`src/butterfly/client.py`):
- Wraps `EntButterflyFormResponseMutator` for form submission
- Implements two-step pattern: create response → run rules
- Supports 5 forms:
  - Supplier Onboarding Request (983940998852772)
  - YubiKey Request (1556853164947065)
  - Statement of Work (362229256183108)
  - CSC Program Setup (3295502980761487)
  - Combined Onboarding + TPA (1125599821621684)
- Field validation against schemas
- Retry logic with exponential backoff

**CSC Browser Automation** (`src/csc/automation.py`):
- Playwright-based automation (no public API available)
- SSO login using requestor's credentials
- Individual worker onboarding via form filling
- Bulk upload via spreadsheet generation
- Screenshot-on-failure for debugging

**CSC Spreadsheet Generator** (`src/csc/spreadsheet.py`):
- Generates Excel files in CSC bulk upload format
- User-friendly features:
  - Instructions worksheet with step-by-step guidance
  - Formatted headers with clear column names
  - Data validation to prevent errors
  - Auto-adjusted column widths

**AMP Browser Automation** (`src/amp/automation.py` - Phase 3):
- Playwright automation for group creation
- Dynamic membership configuration
- Integration with AMP2GW for Google Workspace sync

**TPA API Adapter** (`src/tpa/client.py` - Phase 3):
- TPA intake API integration
- Risk assessment questionnaire automation
- Status polling for completion

**Buy@ Browser Automation** (`src/buyat/client.py`):
- Supplier search and verification
- Determines if supplier exists and is active
- Prevents duplicate onboarding requests

#### 4. Monitoring & Notifications
**Dashboard** (Phase 4):
- Real-time progress tracking for all onboardings
- Visual status indicators (forms submitted, pending, blocked)
- Estimated completion dates based on historical data
- Drill-down into individual workflow details

**Notifications**:
- Workplace bot for status updates
- Email notifications for blockers requiring attention
- Integration with Meta's task system
- Subscriber model: requestor + additional stakeholders stay informed

## Data Flow

### User Journey

```
1. USER INITIATES ONBOARDING
   ↓
   User runs: vendor-onboard --interactive
   or uploads config file: vendor-onboard --config vendor.json
   
2. INTAKE COLLECTION (10 minutes)
   ↓
   • Supplier information (name, contact, business justification)
   • Contract details (dates, value, scope)
   • Worker information (names, emails, roles, locations)
   • Access requirements (systems, AMP groups)
   • YubiKey needs (shipping addresses, urgency)
   
3. VALIDATION (1 minute)
   ↓
   • Validates all data against form schemas
   • Checks supplier existence in Buy@
   • Verifies email formats, date ranges, required fields
   • Returns clear error messages with fix instructions
   
4. WORKFLOW EXECUTION (Automated - hours to days)
   ↓
   Orchestrator executes steps in optimal order:
   
   PARALLEL (independent, run simultaneously):
   ├─► Verify Supplier in Buy@ → Check if active
   ├─► Submit YubiKey Request (if needed)
   ├─► Submit Statement of Work
   ├─► Initiate TPA Assessment
   └─► Create AMP Group
   
   SEQUENTIAL (dependent):
   └─► Update CSC Profile (waits for AMP group)
       └─► Onboard Workers (bulk upload via CSC)
   
5. MONITORING & NOTIFICATIONS
   ↓
   • Real-time dashboard updates
   • Workplace notifications on milestones
   • Email alerts for blockers
   • Estimated completion date updates
   
6. COMPLETION
   ↓
   • All workers provisioned with access
   • YubiKeys shipped (tracking provided)
   • AMP groups configured
   • Audit trail generated
   • Summary report sent to requestor
```

## Benefits for Users

### Time Savings

| Activity | Manual Process | Automated | Time Saved |
|----------|---------------|-----------|------------|
| **Initial Data Collection** | 2 hours (multiple forms) | 10 minutes (single intake) | **1h 50m (92%)** |
| **Form Submission** | 4 hours (8 forms × 30 min) | 0 minutes (automated) | **4 hours (100%)** |
| **Status Checking** | 1 hour/day (checking systems) | 0 minutes (dashboard) | **1 hour/day** |
| **Error Correction** | 2 hours (rework) | 10 minutes (validation) | **1h 50m (92%)** |
| **Total per Onboarding** | **~40 hours** (spread over weeks) | **~2 hours** (active time) | **38 hours (95%)** |

**Annual Impact** (assuming 50 vendor onboardings/year):
- **Time Saved**: 1,900 hours (95% reduction)
- **Equivalent**: ~1 FTE saved
- **Cost Savings**: ~$200,000/year (at $100/hour loaded cost)

### Improved User Experience

**Before (Manual Process)**:
1. ❌ Learn which of 8+ forms to fill out
2. ❌ Fill out same information repeatedly across systems
3. ❌ Wait days/weeks with no visibility into status
4. ❌ Discover errors late in process, requiring rework
5. ❌ Manually check multiple systems for updates
6. ❌ Coordinate across teams via email/Slack

**After (Automated)**:
1. ✅ Single intake form with smart prompts
2. ✅ Data entered once, used everywhere
3. ✅ Real-time dashboard shows exact status
4. ✅ Validation catches errors upfront
5. ✅ Automated notifications keep you informed
6. ✅ System orchestrates cross-team dependencies

### Audit and Compliance Benefits

**Complete Audit Trail**:
- Every action logged with timestamp, actor, and system
- Immutable workflow state stored in SQLite
- Form submission IDs tracked for all Butterfly forms
- Screenshot capture on errors for troubleshooting
- Requestor attribution maintained throughout (no service account)

**Compliance Features**:
- **Data Validation**: Ensures all required fields meet format requirements before submission
- **Approval Workflows**: Respects existing Butterfly approval chains
- **Access Control**: Uses requestor's SSO credentials (principle of least privilege)
- **Retention**: Workflow state preserved for compliance audits
- **Reporting**: Summary reports include all actions taken and systems touched

**Example Audit Log**:
```
2024-04-01 10:00:00 - Workflow started by ikosoy
2024-04-01 10:00:15 - Supplier 'Acme Corp' verified in Buy@ (ID: SUP12345)
2024-04-01 10:00:15 - Supplier status: Active (onboarding skipped)
2024-04-01 10:00:20 - YubiKey request submitted (Form ID: 1556853164947065, Response: resp_789)
2024-04-01 10:00:25 - Statement of Work submitted (Form ID: 362229256183108, Response: resp_790)
2024-04-01 10:00:30 - TPA assessment initiated (TPA-2024-0456)
2024-04-01 10:00:35 - AMP group 'acme-corp-vendors' created
2024-04-01 10:00:40 - CSC profile updated (Profile ID: CSC-7890)
2024-04-01 10:00:45 - Bulk upload: 5 workers submitted via CSC
2024-04-01 10:00:50 - Workflow completed successfully
```

### Risk Reduction

**Eliminates Common Errors**:
- ❌ **Duplicate Suppliers**: System checks Buy@ first, skips onboarding if supplier already active
- ❌ **Invalid Data**: Schema validation catches format errors before submission
- ❌ **Missing Dependencies**: Orchestrator ensures AMP group exists before CSC update
- ❌ **Lost Track**: Dashboard provides single pane of glass for all onboardings
- ❌ **Stalled Workflows**: Automated notifications alert on blockers

**Improves Reliability**:
- **Retry Logic**: Transient failures (network, rate limits) automatically retried with backoff
- **Checkpoint/Resume**: Workflows survive restarts, can resume from last successful step
- **Idempotent Operations**: Safe to retry without creating duplicates
- **Error Isolation**: Failure in one step doesn't affect independent parallel steps

## Implementation Roadmap

### Phase 1: Foundation (Completed ✓)
- ✅ Project structure and Git setup
- ✅ Butterfly Forms API client (5 forms)
- ✅ Workflow orchestrator with state management
- ✅ CLI intake tool with validation
- ✅ Form schemas configuration

### Phase 2: CSC Automation (Completed ✓)
- ✅ CSC browser automation (Playwright)
- ✅ Individual worker onboarding
- ✅ Spreadsheet generator with user-friendly formatting
- ✅ Bulk upload via spreadsheet
- ✅ Data validator with clear error messages
- ✅ End-to-end verification script

### Phase 3: AMP & TPA Integration (Weeks 7-9)
- 🔄 AMP browser automation for group management
- 🔄 TPA API integration for security assessments
- 🔄 Buy@ supplier verification enhancements
- 🔄 Integration testing across all adapters

### Phase 4: Web UI & Monitoring (Weeks 10-12)
- 📋 React-based web intake form
- 📋 Real-time monitoring dashboard
- 📋 Workplace bot notifications
- 📋 Email integration
- 📋 User documentation and training materials

## Success Metrics

### Efficiency Metrics
- **Time to Complete Intake**: Target < 15 minutes (vs. 2+ hours manual)
- **Forms Submitted Automatically**: Target 100% (vs. 0% manual)
- **Error Rate**: Target < 5% (vs. 30% manual due to rework)
- **User Satisfaction**: Target > 4.5/5.0

### Operational Metrics
- **Workflow Success Rate**: Target > 95%
- **Average Completion Time**: Target < 5 business days (vs. 3-6 weeks)
- **System Uptime**: Target > 99.5%
- **Support Tickets**: Target < 2 per 10 onboardings

### Adoption Metrics
- **User Adoption**: Target 80% of vendor onboardings within 6 months
- **Repeat Usage**: Target > 90% of users return for subsequent onboardings
- **Time Saved**: Track cumulative hours saved

## Technical Requirements

### Dependencies
- Python 3.12+
- Playwright (browser automation) - browser lifecycle managed at orchestrator level
- openpyxl (Excel generation)
- SQLite (state persistence with action registry for resume)
- Meta internal libraries:
  - EntButterflyFormResponseMutator
  - GraphQLButterflyFormSubmitHandler

### Security Considerations (Enhanced)

**Credentials Management**:
- **Never stored**: Uses requestor's existing SSO session
- **No service accounts**: Runs with user's own permissions (principle of least privilege)
- **Session handling**: Browser contexts isolated per workflow
- **Token lifecycle**: SSO tokens never persisted to disk

**Data Protection**:
- **PII Sanitization**: Worker names, emails, phones masked in logs (e.g., `j***@vendor.com`)
- **Memory clearing**: Sensitive data explicitly cleared after use (`del` + `gc.collect()`)
- **Screenshot security**: Default directory `~/.vendor_onboarding/screenshots` with 0700 permissions (owner-only)
- **State encryption**: Workflow state containing PII encrypted at rest (SQLite SEE or application-level)

**Audit Trail**:
- **Complete logging**: All actions logged with timestamp, actor, system, and outcome
- **Requestor attribution**: Every action attributed to actual user (not service account)
- **Immutable records**: Workflow state append-only, prevents tampering
- **Compliance ready**: Logs formatted for SIEM ingestion and compliance audits

**Access Control**:
- **Respects system permissions**: Cannot exceed user's existing access levels
- **No privilege escalation**: Browser automation uses user's SSO session
- **Network isolation**: Runs on user's machine or approved Meta infrastructure
- **Data residency**: All data stays within Meta network boundaries

### Scalability & Reliability

**Concurrent Workflows**:
- Supports 50+ simultaneous onboardings
- Each workflow isolated with separate browser context
- Resource pooling prevents system overload

**State Management**:
- SQLite handles 1000+ workflows efficiently with proper indexing
- Action registry enables workflow resume after restart
- State snapshots enable point-in-time recovery

**Browser Resources**:
- Playwright browsers managed via context pool (max 5 concurrent)
- Automatic cleanup on workflow completion or failure
- Screenshot capture on error (stored securely, auto-purged after 30 days)

**Rate Limiting & Resilience**:
- Respects Butterfly API limits (100 req/min) with token bucket algorithm
- Exponential backoff for transient failures (max 5 retries)
- Circuit breaker pattern for downstream system outages
- Graceful degradation: independent steps continue if one fails

### Risk Mitigation Summary

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| Browser lifecycle closes prematurely | Critical | Manage at orchestrator level, manual lifecycle control | ✅ Fixed |
| Dependency race conditions | Critical | Validate dependencies exist before execution | ✅ Fixed |
| Resume functionality broken | Critical | Action registry pattern for reconstruction | ✅ Fixed |
| False upload failures | Warning | Multi-strategy detection with fallbacks | ✅ Fixed |
| PII exposure in logs | Warning | Sanitize logs, mask sensitive fields | ✅ Fixed |
| Insecure screenshot storage | Warning | Secure default path with 0700 permissions | ✅ Fixed |
| Strict header validation | Info | Normalize headers, allow extra columns | ✅ Fixed |
| Untracked documentation | Warning | All docs/plans committed to Git | ✅ Fixed |

## Conclusion

The Vendor Onboarding Automation system transforms a fragmented, manual process into a streamlined, automated workflow. By investing in this automation, Meta will:

1. **Save 95% of time** spent on vendor onboarding (38 hours per onboarding)
2. **Improve user experience** with single intake, real-time visibility, and proactive notifications
3. **Ensure compliance** with complete audit trails and data validation
4. **Reduce errors** by 90% through upfront validation and duplicate prevention
5. **Enable scale** to handle increased vendor onboarding demand without additional headcount

The modular architecture allows for incremental delivery, with Phase 1 and 2 already complete, providing immediate value while Phases 3 and 4 add enhanced capabilities.
