# Vendor Onboarding Automation Agent

An autonomous agent that orchestrates the entire vendor onboarding workflow at Meta, from intake through provisioning.

## Overview

The current vendor onboarding process requires manual data entry across at least 7 different systems and 8+ Butterfly forms. This agent automates the entire workflow by collecting all required information upfront through a single intake interface, then orchestrating the process end-to-end without human intervention.

## Architecture

The solution is implemented as a multi-stage autonomous agent:

1. **Intake and Validation** - Single comprehensive intake form with real-time validation
2. **Orchestration Engine** - Workflow orchestrator with state management and parallel execution
3. **System Adapters** - API and browser automation adapters for Butterfly, CSC, AMP, TPA, and Buy@
4. **Monitoring and Notification** - Real-time dashboard and automated notifications

## Project Structure

```
Vendor_Onboarding/
├── src/
│   ├── butterfly/       # Butterfly Forms API client
│   ├── orchestrator/    # Workflow engine and state management
│   ├── intake/          # CLI and web intake tools
│   ├── csc/             # CSC browser automation
│   ├── amp/             # AMP browser automation
│   ├── tpa/             # TPA API client
│   ├── buyat/           # Buy@ supplier verification
│   └── notifications/   # Workplace and email notifications
├── config/
│   └── form_schemas.json # Form field mappings
├── web/
│   └── src/             # React web UI components
├── tests/               # Unit and integration tests
└── docs/                # Documentation
```

## Implementation Phases

### Phase 1: Foundation and Butterfly Automation (Weeks 1-3)
- Automate Butterfly form submissions via API
- Build workflow orchestrator
- Create CLI intake tool

### Phase 2: CSC Browser Automation (Weeks 4-6)
- Implement CSC browser automation via Playwright
- Build spreadsheet generator for bulk uploads
- Add CSC to workflow orchestrator

### Phase 3: AMP and TPA Integration (Weeks 7-9)
- Implement AMP browser automation
- Implement TPA API client
- Add Buy@ supplier verification

### Phase 4: Web UI and Monitoring (Weeks 10-12)
- Create web-based intake form
- Build monitoring dashboard
- Implement notification system

## Getting Started

See the implementation plan at `/Users/ikosoy/.llms/plans/vendor_onboarding_automation.plan.md` for detailed specifications.
