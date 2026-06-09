VERDICT: NEEDS_REVISION

## Summary Assessment
The plan attempts to implement a Metamate-based vendor onboarding system but contains critical structural flaws: file paths do not exist in the codebase, test commands are incorrect, tasks are massively oversized (not 2-5 minutes), the TDD cycle is incomplete, and dependency grouping is wrong. The plan requires significant revision before execution.

## Critical Issues (must fix)

### 1. File Paths Do Not Exist
The plan references `src/metamate/` directory which does NOT exist in the codebase. The actual structure has:
- `src/intake/` (not `src/metamate/intake.py`)
- `src/orchestrator/workflow.py` (not `src/metamate/workflow.py`)
- No `src/metamate/` directory exists at all

**Impact**: All implementation steps will fail because the target directories do not exist. The import paths in adapters.py (`from ..butterfly import ButterflyClient`) are also incorrect for the proposed structure.

**Fix**: Either create the `src/metamate/` directory structure OR update all file paths to use existing directories (`src/intake/`, `src/orchestrator/`).

### 2. Test Commands Are Incorrect and Unrunnable
- The plan uses `python3 -m unittest` but `requirements.txt` specifies `pytest>=7.4.0` as the test framework
- The plan references test files that do NOT exist: `tests/test_skill.py`, `tests/test_intake.py`, `tests/test_metamate_workflow.py`, `tests/test_adapters.py`, `tests/test_metamate_integration.py`
- Existing tests use pytest conventions (e.g., `tests/test_workflow.py`, `tests/test_intake_cli.py`)

**Impact**: None of the test commands in the plan will work. Developers will be unable to verify their work.

**Fix**: Update all test commands to use `pytest` and reference existing test file naming conventions. Create the test files before referencing them.

### 3. Tasks Are Not Bite-Sized (Violate 2-5 Minute Requirement)
Each implementation step contains massive code blocks that would take 30+ minutes, not 2-5 minutes:
- **Step 1c**: 296 lines of SKILL.md markdown documentation
- **Step 2c**: 160+ lines of intake.py implementation
- **Step 3c**: 100+ lines of workflow.py implementation  
- **Step 4c**: 130+ lines of adapters.py implementation

**Impact**: The plan cannot be executed as written. Developers will get stuck on oversized tasks.

**Fix**: Break each implementation into smaller, focused tasks:
- Step 1: Create skill file structure (5 min), Add Overview section (5 min), Add Workflow section (5 min), Add Usage section (5 min), Add System Integrations section (5 min)
- Step 2: Create IntakeState enum (5 min), Create IntakeData dataclass (5 min), Implement start_intake method (5 min), Implement handle_supplier_check_result (5 min), etc.

### 4. Incomplete TDD Cycle in Step 5
Step 5 (Integration test) violates TDD principles:
- The plan states "The implementation is complete from previous steps" 
- Skips "write failing test" and "run test to verify it fails"
- Jumps directly to "implementation is complete"

**Impact**: No verification that the integration actually works. The TDD cycle is broken.

**Fix**: Step 5 must follow the full TDD cycle: write failing integration test → run to verify failure → implement (if needed) → run to verify pass.

### 5. Incorrect Dependency Grouping
- **Group 2** (Steps 4-5) claims "Yes (independent)" but Step 5 (integration test) depends on Group 4 (adapters, Steps 7-8). The integration test imports `MetamateAdapters` from `src.metamate.adapters`.
- The dependency table is wrong and would cause parallel execution failures.

**Impact**: If executed in parallel as suggested, Step 5 would fail because adapters.py does not exist yet.

**Fix**: Move Step 5 to depend on Group 4, or remove the adapter dependency from the integration test. Update the dependency table to reflect actual dependencies.

### 6. Missing Edge Cases and Error Handling Tasks
The plan lacks tasks for critical edge cases:
- Supplier name variations and fuzzy matching ("Acme Corp" vs "Acme Corporation")
- Duplicate worker detection (same email submitted twice)
- Partial failures in bulk worker upload (some succeed, some fail)
- Buy@ API rate limiting, timeouts, and transient failures
- Spreadsheet format validation (missing columns, invalid dates, malformed emails)
- CSC session timeouts during long bulk uploads
- AMP group naming conflicts (group already exists)
- Handling inactive suppliers that need reactivation (mentioned but not implemented)

**Impact**: The implementation will fail in production when encountering real-world data variations and system failures.

**Fix**: Add explicit tasks for each edge case with corresponding tests.

### 7. Missing Validation Logic Tasks
The SKILL.md mentions "real-time validation with helpful error messages" but the plan has no tasks to implement:
- Email format validation
- Date format validation (YYYY-MM-DD)
- Required field validation
- Business justification length validation
- Phone number format validation
- Manager email existence verification

**Impact**: Users will be able to submit invalid data, causing downstream failures.

**Fix**: Add tasks to implement validation logic in intake.py with corresponding unit tests.

## Suggestions (nice to have)

### 1. Add State Persistence Tasks
The architecture mentions "SQLite persistence" but the plan has no tasks for:
- Creating the SQLite schema
- Implementing save/load workflow state
- Handling concurrent access
- Migration strategy for schema changes

### 2. Add Notification System Tasks
The SKILL.md describes "Proactive Workplace notifications" and "Email alerts" but the plan has no implementation tasks for the notification system.

### 3. Add Configuration Management
No tasks for managing configuration (API endpoints, retry counts, timeout values) across environments.

### 4. Add Monitoring and Observability
No tasks for logging, metrics, or tracing the workflow execution.

## Verified Claims (things you confirmed are correct)

1. **Butterfly client exists**: `src/butterfly/client.py` exists and contains the `ButterflyClient` class with methods for form submission as referenced in the plan.

2. **TPA client exists**: `src/tpa/client.py` exists and contains the `TPAClient` class with assessment submission capabilities.

3. **Python 3.12**: The `requirements.txt` specifies Python 3.12 compatible dependencies (playwright>=1.40.0, openpyxl>=3.1.0).

4. **Metamate skill location**: The plan correctly identifies that Metamate skills are stored in `~/.llms/skills/` directory.

5. **Test framework**: The `requirements.txt` includes `pytest`, `pytest-mock`, and `pytest-cov`, confirming pytest is the intended test framework (not unittest).
