# Vendor Onboarding Automation - User Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Usage Guide](#usage-guide)
5. [Examples](#examples)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

## Overview

The Vendor Onboarding Automation system streamlines Meta's vendor onboarding process by automating form submissions, worker onboarding, and access management across multiple systems.

### What Works Today ✅

**Fully Implemented and Tested:**
- ✅ **Butterfly Forms API**: Submit Supplier Onboarding, YubiKey, Statement of Work, CSC Setup, and TPA forms via API
- ✅ **Workflow Orchestrator**: State management, dependency handling, retry logic, checkpoint/resume
- ✅ **CLI Intake Tool**: Interactive prompts with validation, config file support, dry-run mode
- ✅ **Data Validation**: Email, date, phone, and field validation with clear error messages
- ✅ **TPA API Integration**: Submit assessments, poll status, get results
- ✅ **Spreadsheet Generator**: Create CSC bulk upload files with formatting and instructions

**Partially Implemented (Requires Browser Setup):**
- ⚠️ **CSC Browser Automation**: Structure complete, needs Playwright browser setup
- ⚠️ **AMP Browser Automation**: Structure complete, needs Playwright browser setup  
- ⚠️ **Buy@ Integration**: Structure complete, needs Playwright browser setup

### What This Means

**You CAN use the system today for:**
- Validating vendor data before submission
- Generating CSC bulk upload spreadsheets
- Submitting Butterfly forms via API (if you have API access)
- Initiating TPA assessments via API
- Tracking workflow progress with the orchestrator

**You CANNOT yet (without additional setup):**
- Fully automated end-to-end onboarding (requires browser automation setup)
- Automatic CSC worker onboarding (needs Playwright browser)
- Automatic AMP group creation (needs Playwright browser)
- Automatic Buy@ supplier verification (needs Playwright browser)

## Quick Start

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone https://github.com/ikosoymeta/onboarding-automation.git
cd onboarding-automation

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers (for browser automation)
playwright install chromium

# 4. Verify installation
python3 -m pytest tests/test_butterfly_client.py -v
```

### Your First Vendor Onboarding

**Option 1: Interactive CLI (Recommended for first time)**

```bash
# Start interactive onboarding
python3 -m src.intake.cli --interactive

# Follow the prompts to enter:
# - Supplier information
# - Worker details (or upload spreadsheet)
# - Access requirements
# - YubiKey needs
```

**Option 2: Config File (Recommended for repeatability)**

```bash
# 1. Create a config file (see examples/vendor_config.json)
# 2. Validate the config
python3 -m src.intake.cli --config examples/vendor_config.json --dry-run

# 3. Run the onboarding
python3 -m src.intake.cli --config examples/vendor_config.json
```

## Installation

### Prerequisites

- **Python 3.12+** (required)
- **Git** (for version control)
- **Internet access** (for API calls to Meta systems)

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/ikosoymeta/onboarding-automation.git
cd onboarding-automation
```

#### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Your prompt should now show (venv)
```

#### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `playwright` - Browser automation for CSC, AMP, Buy@
- `openpyxl` - Excel spreadsheet generation
- `requests` - HTTP client for APIs
- `pytest` - Testing framework

#### 4. Install Playwright Browsers

```bash
# Install Chromium browser for automation
playwright install chromium

# This downloads ~100MB browser binary
# Required for: CSC, AMP, and Buy@ automation
```

#### 5. Verify Installation

```bash
# Run the test suite
python3 -m pytest tests/test_butterfly_client.py -v
python3 -m pytest tests/test_workflow.py -v
python3 -m pytest tests/test_intake_cli.py -v

# Expected: All tests pass (may see warnings about missing modules,
# but core functionality tests should pass)
```

#### 6. Configure Environment (Optional)

Create a `.env` file for configuration:

```bash
# .env file
BUTTERFLY_API_URL=https://www.internalfb.com/butterfly/api
TPA_API_URL=https://www.internalfb.com/tpa/api
CSC_URL=https://www.internalfb.com/csc
AMP_URL=https://www.internalfb.com/amp
BUYAT_URL=https://www.internalfb.com/buy/suppliers/onboarding

# Optional: Custom screenshot directory (for debugging)
SCREENSHOT_DIR=~/.vendor_onboarding/screenshots

# Optional: Log level
LOG_LEVEL=INFO
```

## Usage Guide

### Command Line Interface

The CLI tool is the primary interface for vendor onboarding.

#### Basic Usage

```bash
# Interactive mode - prompts for all information
python3 -m src.intake.cli --interactive

# Config file mode - load from JSON file
python3 -m src.intake.cli --config path/to/config.json

# Dry run - validate without submitting
python3 -m src.intake.cli --config config.json --dry-run

# Save output to file
python3 -m src.intake.cli --interactive --output onboarding_data.json
```

#### CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--interactive` | Run interactive prompts | `--interactive` |
| `--config, -c` | Load from JSON config file | `-c vendor.json` |
| `--output, -o` | Save collected data to file | `-o output.json` |
| `--dry-run` | Validate only, don't submit | `--dry-run` |
| `--schema` | Custom form schema file | `--schema custom.json` |

### Interactive Mode Walkthrough

When you run `python3 -m src.intake.cli --interactive`, the system guides you through:

#### Step 1: Supplier Information
```
============================================================
SUPPLIER INFORMATION
============================================================

Supplier legal name: Acme Corporation
Supplier contact email: contact@acme.com
Supplier contact phone (optional): +1-555-0123
Business justification: Need vendor for Q2 project development
Estimated annual spend (e.g., $100000): $150000
Contract start date (YYYY-MM-DD): 2024-04-15
Contract end date (YYYY-MM-DD): 2025-04-15
Requestor manager (unixname): jsmith
```

**Tips:**
- Use the legal name as it appears in contracts
- Email must be valid format (user@domain.com)
- Dates must be YYYY-MM-DD format
- Manager unixname is required for approvals

#### Step 2: YubiKey Request (Optional)
```
============================================================
YUBIKEY REQUEST
============================================================

Do vendor workers need YubiKeys? [Y/n]: Y

Enter vendor worker information (leave name empty to finish):

Worker full name: John Doe
  Email for John Doe: john.doe@acme.com
  Shipping address for John Doe:
    Street address: 1 Hacker Way
    City: Menlo Park
    State/Province: CA
    ZIP/Postal code: 94025
    Country: USA

Worker full name: [Press Enter to finish]

Urgency level:
  1. Standard (3+ weeks)
  2. Expedited (1-2 weeks)
  3. Emergency (< 1 week)
Enter choice number [1]: 1

Business justification for YubiKeys: Workers need MFA for system access
```

#### Step 3: Statement of Work
```
============================================================
STATEMENT OF WORK
============================================================

Vendor name: Acme Corporation
SOW title: Q2 2024 Development Services
Scope description (detailed): Provide software development services for...
```

#### Step 4: CSC Program Setup
```
============================================================
CSC PROGRAM SETUP
============================================================

Program name: Acme Corp Vendors Q2 2024
Vendor name: Acme Corporation
Meta program manager (unixname): jsmith

Vendor manager information:
  Name: Jane Smith
  Email: jane.smith@acme.com
  Phone (optional): +1-555-0124

Number of vendor workers: 3
Work location:
  1. Onsite
  2. Remote
  3. Hybrid
Enter choice number [1]: 2

Program start date (YYYY-MM-DD): 2024-04-15

Enter systems/tools vendor needs access to (leave empty to finish):
System/tool name: GitHub
System/tool name: AWS
System/tool name: [Press Enter to finish]

AMP group name for access management: acme-corp-vendors
```

### Config File Mode

For repeatable onboardings or automation, use a JSON config file.

#### Example Config File

```json
{
  "supplier": {
    "supplier_name": "Acme Corporation",
    "supplier_contact_email": "contact@acme.com",
    "supplier_contact_phone": "+1-555-0123",
    "business_justification": "Need vendor for Q2 project development",
    "estimated_spend": "$150000",
    "contract_start_date": "2024-04-15",
    "contract_end_date": "2025-04-15",
    "requestor_manager": "jsmith"
  },
  "yubikey": {
    "vendor_workers": [
      {
        "full_name": "John Doe",
        "email": "john.doe@acme.com",
        "shipping_address": {
          "street": "1 Hacker Way",
          "city": "Menlo Park",
          "state": "CA",
          "zip": "94025",
          "country": "USA"
        }
      }
    ],
    "urgency": "Standard (3+ weeks)",
    "business_justification": "Workers need MFA for system access"
  },
  "sow": {
    "vendor_name": "Acme Corporation",
    "sow_title": "Q2 2024 Development Services",
    "scope_description": "Provide software development services...",
    "deliverables": [
      {
        "name": "API Development",
        "description": "Build REST API endpoints",
        "due_date": "2024-06-01"
      }
    ],
    "start_date": "2024-04-15",
    "end_date": "2025-04-15",
    "total_value": "$150000",
    "payment_terms": "Net 30"
  },
  "csc": {
    "program_name": "Acme Corp Vendors Q2 2024",
    "vendor_name": "Acme Corporation",
    "program_manager": "jsmith",
    "vendor_manager": {
      "name": "Jane Smith",
      "email": "jane.smith@acme.com",
      "phone": "+1-555-0124"
    },
    "worker_count": 3,
    "work_location": "Remote",
    "start_date": "2024-04-15",
    "access_requirements": ["GitHub", "AWS", "Asana"],
    "amp_group_name": "acme-corp-vendors"
  }
}
```

#### Using Config Files

```bash
# Validate config without submitting
python3 -m src.intake.cli --config acme_corp.json --dry-run

# If validation passes, run the onboarding
python3 -m src.intake.cli --config acme_corp.json

# Save collected data to a new config file
python3 -m src.intake.cli --interactive --output my_vendor.json
```

### Python API Usage

For programmatic access, use the Python API directly.

#### Basic Example

```python
from src.vendor_onboarding import VendorOnboardingSystem
from src.csc import WorkerInfo

# Initialize the system
system = VendorOnboardingSystem()

# Define workers
workers = [
    WorkerInfo(
        full_name="John Doe",
        email="john.doe@acme.com",
        start_date="2024-04-01",
        end_date="2025-04-01",
        job_title="Software Engineer",
        manager_email="manager@meta.com",
        work_location="Remote",
        phone="+1-555-0123"
    ),
    WorkerInfo(
        full_name="Jane Smith",
        email="jane.smith@acme.com",
        start_date="2024-04-01",
        end_date="2025-04-01",
        job_title="Product Designer",
        manager_email="manager@meta.com",
        work_location="Onsite",
        office_location="Menlo Park"
    )
]

# Supplier data
supplier_data = {
    "supplier_name": "Acme Corporation",
    "supplier_contact_email": "contact@acme.com",
    "business_justification": "Q2 project development",
    "estimated_spend": "$150000",
    "contract_start_date": "2024-04-15",
    "contract_end_date": "2025-04-15",
    "requestor_manager": "jsmith",
    "data_access_level": "Internal",
    "systems": ["GitHub", "AWS"],
    "handles_pii": False,
    "handles_financial_data": False
}

# Execute onboarding
result = system.onboard_vendor(
    supplier_name="Acme Corporation",
    supplier_data=supplier_data,
    workers=workers,
    amp_group_name="acme-corp-vendors",
    enable_yubikey=True,
    enable_tpa=True
)

# Check results
if result.success:
    print(f"✓ Onboarding successful!")
    print(f"  Workers onboarded: {result.workers_onboarded}")
    print(f"  AMP Group: {result.amp_group_id}")
    print(f"  TPA Assessment: {result.tpa_assessment_id}")
else:
    print(f"✗ Onboarding completed with errors:")
    for error in result.errors:
        print(f"  - {error}")
```

#### Checking Workflow Status

```python
# Get status of an ongoing workflow
status = system.get_status("workflow-id-123")

print(f"Status: {status['status']}")
print(f"Progress: {status['progress_percent']}%")
print(f"Completed: {status['completed_steps']}/{status['total_steps']}")
```

## Examples

### Example 1: Simple Vendor with One Worker

**Scenario**: Onboard a single consultant for a short-term project.

```bash
python3 -m src.intake.cli --interactive
```

**Inputs:**
- Supplier: "Consulting Firm LLC"
- Workers: 1 (John Doe, john@consulting.com)
- Duration: 3 months
- Access: GitHub only
- YubiKey: No (uses existing)

**Expected Result:**
- Supplier verification via Buy@
- Statement of Work submitted
- CSC worker onboarding completed
- No AMP group needed (single worker)
- **Time**: ~15 minutes active, 2-3 days total

### Example 2: Large Vendor with Bulk Workers

**Scenario**: Onboard a vendor with 10 workers across multiple locations.

**Step 1: Prepare spreadsheet**
```bash
# Generate template
python3 -c "
from src.csc import CSCSpreadsheetGenerator, WorkerInfo
import tempfile

workers = []  # Empty list for template
generator = CSCSpreadsheetGenerator()
generator.generate(workers, 'template.xlsx')
print('Template created: template.xlsx')
"
```

**Step 2: Fill spreadsheet** with 10 workers

**Step 3: Run onboarding**
```bash
python3 -m src.intake.cli --config large_vendor.json
```

**Expected Result:**
- All 10 workers onboarded via CSC bulk upload
- AMP group created with all members
- YubiKeys ordered for all workers
- **Time**: ~20 minutes active, 3-4 days total

### Example 3: Existing Vendor, Add Workers

**Scenario**: Acme Corp is already onboarded, need to add 3 more workers.

```python
from src.vendor_onboarding import VendorOnboardingSystem
from src.csc import WorkerInfo

system = VendorOnboardingSystem()

# Only need worker info - supplier already exists!
workers = [...]
result = system.onboard_vendor(
    supplier_name="Acme Corp",  # Already in Buy@
    supplier_data={},  # Minimal data needed
    workers=workers,
    enable_yubikey=True,
    enable_tpa=False  # Already assessed
)

# Supplier onboarding form is automatically skipped!
```

**Expected Result:**
- Buy@ check finds existing supplier (skips supplier form, saves 1 week!)
- Only worker onboarding and YubiKeys processed
- **Time**: ~10 minutes active, 1-2 days total

## Troubleshooting

### Common Issues

#### Issue: "ModuleNotFoundError: No module named 'playwright'"

**Cause**: Playwright not installed or browser not downloaded.

**Solution**:
```bash
pip install playwright
playwright install chromium
```

#### Issue: "Supplier not found in Buy@" but supplier exists

**Cause**: Buy@ search may require exact name match or the supplier might be under a different legal name.

**Solution**:
1. Verify the exact legal name in Buy@
2. Try variations (e.g., "Acme Corp" vs "Acme Corporation")
3. Check if supplier is under parent company name
4. Contact procurement team to verify supplier ID

#### Issue: Butterfly form submission fails with validation error

**Cause**: Required field missing or invalid format.

**Solution**:
1. Run with `--dry-run` flag to validate before submitting
2. Check error message for specific field issues
3. Verify date formats are YYYY-MM-DD
4. Verify email addresses are valid format
5. Check that all required fields are provided

#### Issue: CSC bulk upload fails

**Cause**: Spreadsheet format incorrect or CSC session timeout.

**Solution**:
1. Use the spreadsheet generator to create a valid template
2. Do not modify the header row
3. Ensure all required columns are filled
4. Check that dates are in YYYY-MM-DD format
5. Verify work location is exactly "Remote", "Onsite", or "Hybrid" (case-sensitive)

#### Issue: AMP group creation fails (group already exists)

**Cause**: AMP group name already in use.

**Solution**:
1. Choose a different group name
2. Or, use the existing group and add members to it
3. Check AMP for existing groups before creating

### Getting Help

**Check logs**: The system logs detailed information to help diagnose issues.

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 -m src.intake.cli --interactive
```

**Log locations**:
- Console output: Real-time progress and errors
- File logs: `~/.vendor_onboarding/logs/` (if configured)
- Screenshots: `~/.vendor_onboarding/screenshots/` (on browser automation failures)

**Common log messages**:
- `INFO`: Normal progress updates
- `WARNING`: Non-critical issues (e.g., supplier not found, will create new)
- `ERROR`: Failures that prevented step completion
- `DEBUG`: Detailed debugging information (enable with LOG_LEVEL=DEBUG)

## FAQ

### General Questions

**Q: How long does vendor onboarding take?**
A: Active time is ~20 minutes for data collection. Total calendar time is 3-4 days, mostly waiting for:
- TPA assessment review (2-3 days)
- YubiKey delivery (3+ weeks, but doesn't block worker access)

**Q: Can I save my progress and resume later?**
A: Yes! The CLI tool supports saving to a JSON file with `--output`, and you can resume with `--config`. The workflow engine also supports resuming interrupted workflows.

**Q: What if a step fails?**
A: The system automatically retries transient failures (network issues) up to 5 times with exponential backoff. For persistent failures, the workflow pauses and notifies you. You can fix the issue and resume from where it left off.

**Q: Do I need admin access to any systems?**
A: No! The system uses YOUR existing permissions via SSO. You can only do what you're already authorized to do in each system.

### Technical Questions

**Q: Can I run this in CI/CD or automation?**
A: Yes! Use the config file mode (`--config`) for automation. However, browser-based steps (CSC, AMP, Buy@) require an interactive session with SSO authentication.

**Q: How do I handle multiple vendors at once?**
A: Each vendor onboarding is a separate workflow. You can run multiple CLI instances in parallel, or use the Python API to orchestrate multiple onboardings programmatically.

**Q: Can I customize the forms or workflow?**
A: Yes! Form schemas are defined in `config/form_schemas.json`. You can modify field requirements, validation rules, and add custom fields. The workflow engine supports custom step definitions.

**Q: Is my data secure?**
A: Yes! 
- Credentials are never stored (uses your SSO session)
- PII is sanitized in logs
- Screenshots are stored with restricted permissions (0700)
- All data stays within Meta's network
- Complete audit trail for compliance

### Troubleshooting Questions

**Q: The system says a supplier exists but I can't find it in Buy@.**
A: The supplier might be inactive or under a different name. Check:
1. Exact legal name spelling
2. Parent company name
3. DBA (doing business as) name
4. Contact procurement team for supplier ID

**Q: Worker onboarding fails with "Invalid email format".**
A: Ensure emails follow the format `user@domain.com`. The system validates email format before submission to prevent CSC errors.

**Q: Can I onboard workers without YubiKeys?**
A: Yes! Set `enable_yubikey=False` when calling the API, or answer "No" to the YubiKey prompt in interactive mode.

## Support

For issues, questions, or feature requests:

1. **Check this guide** - Most common issues are covered in Troubleshooting and FAQ
2. **Check logs** - Enable DEBUG logging for detailed information
3. **Review architecture docs** - See `docs/architecture.md` for technical details
4. **Contact team** - Reach out to the Vendor Onboarding Automation team

**Project Repository**: https://github.com/ikosoymeta/onboarding-automation
**Documentation**: `/Users/ikosoy/Claude/project/Vendor_Onboarding/docs/`
**Issues**: Report via GitHub Issues or contact the team directly
