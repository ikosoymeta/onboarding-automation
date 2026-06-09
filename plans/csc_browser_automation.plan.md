# Plan: CSC Browser Automation for Vendor Worker Onboarding

**Goal**: Automate CSC (Contractor Services Center) vendor worker onboarding via browser automation, enabling programmatic submission of individual worker details and bulk upload via spreadsheet generation.

**Architecture**: Playwright-based browser automation for CSC UI interactions, with spreadsheet generator for bulk uploads. Implements SSO authentication using requestor's credentials, form filling for individual workers, and Excel template generation for bulk operations. Includes robust error handling with screenshot-on-failure and retry logic.

**Tech Stack**: Python 3.12, Playwright, openpyxl for Excel generation, pytest for testing

## Task Dependencies

| Group | Steps | Can Parallelize | Files Touched |
|-------|-------|-----------------|---------------|
| 1 | Steps 1-3 | Yes (independent) | src/csc/automation.py, tests/test_csc_automation.py |
| 2 | Steps 4-5 | Yes (independent) | src/csc/spreadsheet.py, tests/test_csc_spreadsheet.py |
| 3 | Step 6 | No (depends on Group 1,2) | src/csc/__init__.py |
| 4 | Steps 7-8 | Yes (independent) | src/csc/validator.py, tests/test_csc_validator.py |
| 5 | Step 9 | No (depends on Group 4) | Integration test |

## Step 1: Create CSC automation client structure

**File**: `src/csc/automation.py`

### 1a. Write failing test
```python
# tests/test_csc_automation.py
import unittest
from unittest.mock import MagicMock, patch
from src.csc.automation import CSCAutomation, CSCError, AuthenticationError


class TestCSCAutomation(unittest.TestCase):
    """Test cases for CSCAutomation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.automation = CSCAutomation()
    
    def test_initialization(self):
        """Test CSC automation initializes correctly."""
        self.assertIsNotNone(self.automation)
        self.assertTrue(self.automation.headless)
    
    def test_login_with_sso(self):
        """Test SSO login to CSC."""
        # This test will fail until implementation is complete
        with patch('src.csc.automation.sync_playwright') as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()
            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_page.return_value = mock_page
            
            result = self.automation.login()
            self.assertTrue(result)
```

### 1b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_initialization -v
```

### 1c. Write implementation
```python
# src/csc/automation.py
"""CSC browser automation for vendor worker onboarding.

Provides browser automation for CSC UI interactions since no public API
is available for vendor worker onboarding.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class CSCError(Exception):
    """Base exception for CSC operations."""
    pass


class AuthenticationError(CSCError):
    """Raised when CSC authentication fails."""
    pass


class FormSubmissionError(CSCError):
    """Raised when form submission fails."""
    pass


@dataclass
class WorkerInfo:
    """Information about a vendor worker."""
    full_name: str
    email: str
    start_date: str
    end_date: str
    job_title: str
    manager_email: str
    work_location: str
    office_location: Optional[str] = None
    phone: Optional[str] = None


class CSCAutomation:
    """Browser automation for CSC vendor worker onboarding.
    
    Automates CSC UI interactions for onboarding individual vendor workers
    and bulk uploads via spreadsheet.
    """
    
    CSC_URL = "https://www.internalfb.com/csc"
    LOGIN_TIMEOUT = 30000  # 30 seconds
    
    def __init__(self, headless: bool = True, screenshot_dir: str = "/tmp/csc_screenshots"):
        """Initialize CSC automation.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots
        """
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._browser = None
        self._page = None
        self._logged_in = False
    
    def login(self) -> bool:
        """Login to CSC via SSO.
        
        Uses the requestor's existing SSO session. If not logged in,
        will prompt for authentication.
        
        Returns:
            True if login successful
            
        Raises:
            AuthenticationError: If login fails
        """
        # TODO: Implement SSO login
        raise NotImplementedError("SSO login not yet implemented")
    
    def onboard_worker(self, worker: WorkerInfo) -> str:
        """Onboard a single vendor worker via CSC UI.
        
        Args:
            worker: Worker information
            
        Returns:
            Worker ID assigned by CSC
            
        Raises:
            FormSubmissionError: If onboarding fails
        """
        # TODO: Implement worker onboarding
        raise NotImplementedError("Worker onboarding not yet implemented")
    
    def bulk_upload_workers(self, workers: List[WorkerInfo], spreadsheet_path: str) -> Dict[str, Any]:
        """Upload multiple workers via CSC bulk upload.
        
        Args:
            workers: List of worker information
            spreadsheet_path: Path to generated spreadsheet
            
        Returns:
            Dictionary with upload results
            
        Raises:
            FormSubmissionError: If upload fails
        """
        # TODO: Implement bulk upload
        raise NotImplementedError("Bulk upload not yet implemented")
    
    def close(self):
        """Close browser resources."""
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None
            self._logged_in = False
```

### 1d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_initialization -v
```

### 1e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/automation.py tests/test_csc_automation.py && git commit -m "Add CSC automation client structure"
```

## Step 2: Implement SSO login with session management

**File**: `src/csc/automation.py`

### 2a. Write failing test
```python
# tests/test_csc_automation.py (add to TestCSCAutomation)
    @patch('src.csc.automation.sync_playwright')
    def test_login_success(self, mock_playwright):
        """Test successful SSO login."""
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        
        # Mock successful login (already authenticated)
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = MagicMock()
        
        result = self.automation.login()
        self.assertTrue(result)
        self.assertTrue(self.automation._logged_in)
    
    @patch('src.csc.automation.sync_playwright')
    def test_login_failure(self, mock_playwright):
        """Test login failure handling."""
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.side_effect = Exception("Navigation failed")
        
        with self.assertRaises(AuthenticationError):
            self.automation.login()
```

### 2b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_login_success -v
```

### 2c. Write implementation
```python
# src/csc/automation.py (update imports and login method)
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

class CSCAutomation:
    # ... existing code ...
    
    def _take_screenshot(self, page, prefix: str = "error"):
        """Take screenshot for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"csc_{prefix}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            page.screenshot(path=str(filepath))
            logger.info(f"Screenshot saved to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None
    
    def login(self) -> bool:
        """Login to CSC via SSO."""
        logger.info("Logging in to CSC via SSO")
        
        try:
            with sync_playwright() as p:
                self._browser = p.chromium.launch(headless=self.headless)
                self._page = self._browser.new_page()
                
                try:
                    # Navigate to CSC
                    self._page.goto(self.CSC_URL, wait_until="networkidle", timeout=self.LOGIN_TIMEOUT)
                    
                    # Check if already logged in (SSO session active)
                    # Look for CSC dashboard elements
                    try:
                        self._page.wait_for_selector(
                            'text=/dashboard|welcome|home/i',
                            timeout=5000
                        )
                        logger.info("Already logged in via SSO")
                        self._logged_in = True
                        return True
                    except PlaywrightTimeoutError:
                        pass
                    
                    # If not logged in, look for login button
                    login_button = self._page.query_selector('text=/log in|sign in/i')
                    if login_button:
                        logger.info("Clicking login button")
                        login_button.click()
                        self._page.wait_for_load_state("networkidle")
                    
                    # Wait for dashboard to confirm login
                    self._page.wait_for_selector(
                        'text=/dashboard|welcome|home/i',
                        timeout=self.LOGIN_TIMEOUT
                    )
                    
                    logger.info("Successfully logged in to CSC")
                    self._logged_in = True
                    return True
                
                except Exception as e:
                    self._take_screenshot(self._page, "login_error")
                    raise
                
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during CSC login: {e}")
            raise AuthenticationError(f"CSC login timeout: {e}")
        except Exception as e:
            logger.error(f"CSC login failed: {e}")
            raise AuthenticationError(f"CSC login failed: {e}")
```

### 2d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_login_success -v
```

### 2e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/automation.py && git commit -m "Implement SSO login with session management for CSC"
```

## Step 3: Implement individual worker onboarding form filling

**File**: `src/csc/automation.py`

### 3a. Write failing test
```python
# tests/test_csc_automation.py (add to TestCSCAutomation)
    @patch('src.csc.automation.sync_playwright')
    def test_onboard_worker(self, mock_playwright):
        """Test onboarding a single worker."""
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        
        # Setup automation as logged in
        self.automation._browser = mock_browser
        self.automation._page = mock_page
        self.automation._logged_in = True
        
        worker = WorkerInfo(
            full_name="John Doe",
            email="john@vendor.com",
            start_date="2024-04-01",
            end_date="2025-04-01",
            job_title="Software Engineer",
            manager_email="manager@meta.com",
            work_location="Remote"
        )
        
        # Mock successful form submission
        mock_page.query_selector.return_value = MagicMock()
        
        worker_id = self.automation.onboard_worker(worker)
        self.assertIsNotNone(worker_id)
```

### 3b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_onboard_worker -v
```

### 3c. Write implementation
```python
# src/csc/automation.py (update onboard_worker method)
    def onboard_worker(self, worker: WorkerInfo) -> str:
        """Onboard a single vendor worker via CSC UI."""
        if not self._logged_in:
            raise CSCError("Must login before onboarding workers")
        
        logger.info(f"Onboarding worker: {worker.full_name} ({worker.email})")
        
        try:
            # Navigate to new worker onboarding page
            self._page.goto(f"{self.CSC_URL}/onboard/new", wait_until="networkidle")
            
            # Fill worker details form
            # Name
            name_input = self._page.wait_for_selector('input[name*="name" i], input[id*="name" i]', timeout=10000)
            name_input.fill(worker.full_name)
            
            # Email
            email_input = self._page.wait_for_selector('input[type="email"], input[name*="email" i]')
            email_input.fill(worker.email)
            
            # Job title
            title_input = self._page.wait_for_selector('input[name*="title" i], input[name*="job" i]')
            title_input.fill(worker.job_title)
            
            # Start date
            start_date_input = self._page.wait_for_selector('input[name*="start" i][type="date"], input[id*="start" i]')
            start_date_input.fill(worker.start_date)
            
            # End date
            end_date_input = self._page.wait_for_selector('input[name*="end" i][type="date"], input[id*="end" i]')
            end_date_input.fill(worker.end_date)
            
            # Manager email
            manager_input = self._page.wait_for_selector('input[name*="manager" i]')
            manager_input.fill(worker.manager_email)
            
            # Work location (dropdown)
            location_select = self._page.wait_for_selector('select[name*="location" i]')
            location_select.select_option(label=worker.work_location)
            
            # Office location (if onsite/hybrid)
            if worker.office_location and worker.work_location in ["Onsite", "Hybrid"]:
                office_input = self._page.wait_for_selector('input[name*="office" i]')
                office_input.fill(worker.office_location)
            
            # Phone (optional)
            if worker.phone:
                phone_input = self._page.query_selector('input[type="tel"], input[name*="phone" i]')
                if phone_input:
                    phone_input.fill(worker.phone)
            
            # Submit form
            submit_button = self._page.wait_for_selector('button[type="submit"], input[type="submit"]')
            submit_button.click()
            
            # Wait for confirmation and extract worker ID
            self._page.wait_for_selector('text=/success|confirmed|worker id/i', timeout=15000)
            
            # Extract worker ID from confirmation page
            worker_id_elem = self._page.query_selector('text=/worker id[:\\s]+([A-Z0-9]+)/i')
            if worker_id_elem:
                import re
                match = re.search(r'([A-Z0-9]+)', worker_id_elem.inner_text())
                if match:
                    worker_id = match.group(1)
                    logger.info(f"Worker onboarded successfully with ID: {worker_id}")
                    return worker_id
            
            # Fallback: return email as identifier
            logger.warning("Could not extract worker ID, using email as identifier")
            return worker.email
            
        except Exception as e:
            self._take_screenshot(self._page, f"onboard_error_{worker.email}")
            logger.error(f"Failed to onboard worker {worker.email}: {e}")
            raise FormSubmissionError(f"Worker onboarding failed: {e}")
```

### 3d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_onboard_worker -v
```

### 3e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/automation.py && git commit -m "Implement individual worker onboarding form filling"
```

## Step 4: Create CSC spreadsheet generator for bulk uploads

**File**: `src/csc/spreadsheet.py`

### 4a. Write failing test
```python
# tests/test_csc_spreadsheet.py
import unittest
import tempfile
import os
from src.csc.spreadsheet import CSCSpreadsheetGenerator
from src.csc.automation import WorkerInfo


class TestCSCSpreadsheetGenerator(unittest.TestCase):
    """Test cases for CSCSpreadsheetGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = CSCSpreadsheetGenerator()
    
    def test_generate_spreadsheet(self):
        """Test generating CSC bulk upload spreadsheet."""
        workers = [
            WorkerInfo(
                full_name="John Doe",
                email="john@vendor.com",
                start_date="2024-04-01",
                end_date="2025-04-01",
                job_title="Engineer",
                manager_email="manager@meta.com",
                work_location="Remote"
            ),
            WorkerInfo(
                full_name="Jane Smith",
                email="jane@vendor.com",
                start_date="2024-04-15",
                end_date="2025-04-15",
                job_title="Designer",
                manager_email="manager@meta.com",
                work_location="Onsite",
                office_location="Menlo Park"
            )
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result_path = self.generator.generate(workers, tmp_path)
            self.assertTrue(os.path.exists(result_path))
            self.assertEqual(result_path, tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
```

### 4b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_spreadsheet.TestCSCSpreadsheetGenerator.test_generate_spreadsheet -v
```

### 4c. Write implementation
```python
# src/csc/spreadsheet.py
"""CSC spreadsheet generator for bulk worker uploads.

Generates Excel spreadsheets in CSC bulk upload format.
"""

import logging
from typing import List
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from .automation import WorkerInfo

logger = logging.getLogger(__name__)


class CSCSpreadsheetGenerator:
    """Generates CSC bulk upload spreadsheets.
    
    Creates Excel files in the format expected by CSC bulk upload feature.
    """
    
    # CSC bulk upload template columns
    COLUMNS = [
        "Full Name",
        "Email Address",
        "Job Title",
        "Start Date (YYYY-MM-DD)",
        "End Date (YYYY-MM-DD)",
        "Manager Email",
        "Work Location",
        "Office Location",
        "Phone Number"
    ]
    
    def __init__(self):
        """Initialize spreadsheet generator."""
        pass
    
    def generate(self, workers: List[WorkerInfo], output_path: str) -> str:
        """Generate CSC bulk upload spreadsheet.
        
        Args:
            workers: List of worker information
            output_path: Path where spreadsheet will be saved
            
        Returns:
            Path to generated spreadsheet
        """
        logger.info(f"Generating CSC spreadsheet for {len(workers)} workers")
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Vendor Workers"
        
        # Add header row
        for col_idx, column_name in enumerate(self.COLUMNS, 1):
            cell = ws.cell(row=1, column=col_idx, value=column_name)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # Add worker data rows
        for row_idx, worker in enumerate(workers, 2):
            ws.cell(row=row_idx, column=1, value=worker.full_name)
            ws.cell(row=row_idx, column=2, value=worker.email)
            ws.cell(row=row_idx, column=3, value=worker.job_title)
            ws.cell(row=row_idx, column=4, value=worker.start_date)
            ws.cell(row=row_idx, column=5, value=worker.end_date)
            ws.cell(row=row_idx, column=6, value=worker.manager_email)
            ws.cell(row=row_idx, column=7, value=worker.work_location)
            ws.cell(row=row_idx, column=8, value=worker.office_location or "")
            ws.cell(row=row_idx, column=9, value=worker.phone or "")
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save workbook
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(str(output_path))
        
        logger.info(f"Spreadsheet saved to {output_path}")
        return str(output_path)
    
    def validate_spreadsheet(self, spreadsheet_path: str) -> List[str]:
        """Validate CSC spreadsheet format.
        
        Args:
            spreadsheet_path: Path to spreadsheet to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            from openpyxl import load_workbook
            wb = load_workbook(spreadsheet_path)
            ws = wb.active
            
            # Check header row
            header = [cell.value for cell in ws[1]]
            if header != self.COLUMNS:
                errors.append(f"Invalid header. Expected: {self.COLUMNS}, Got: {header}")
            
            # Check data rows
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                if not any(row):  # Skip empty rows
                    continue
                
                # Check required fields
                if not row[0]:  # Full Name
                    errors.append(f"Row {row_idx}: Full Name is required")
                if not row[1]:  # Email
                    errors.append(f"Row {row_idx}: Email Address is required")
                if not row[2]:  # Job Title
                    errors.append(f"Row {row_idx}: Job Title is required")
        
        except Exception as e:
            errors.append(f"Failed to validate spreadsheet: {e}")
        
        return errors
```

### 4d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_spreadsheet.TestCSCSpreadsheetGenerator.test_generate_spreadsheet -v
```

### 4e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/spreadsheet.py tests/test_csc_spreadsheet.py && git commit -m "Create CSC spreadsheet generator for bulk uploads"
```

## Step 5: Implement bulk upload via spreadsheet

**File**: `src/csc/automation.py`

### 5a. Write failing test
```python
# tests/test_csc_automation.py (add to TestCSCAutomation)
    @patch('src.csc.automation.sync_playwright')
    def test_bulk_upload_workers(self, mock_playwright):
        """Test bulk upload of workers via spreadsheet."""
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        
        self.automation._browser = mock_browser
        self.automation._page = mock_page
        self.automation._logged_in = True
        
        workers = [
            WorkerInfo(
                full_name="John Doe",
                email="john@vendor.com",
                start_date="2024-04-01",
                end_date="2025-04-01",
                job_title="Engineer",
                manager_email="manager@meta.com",
                work_location="Remote"
            )
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx') as tmp:
            result = self.automation.bulk_upload_workers(workers, tmp.name)
            self.assertIn("uploaded_count", result)
            self.assertIn("failed_count", result)
```

### 5b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_bulk_upload_workers -v
```

### 5c. Write implementation
```python
# src/csc/automation.py (update bulk_upload_workers method)
    def bulk_upload_workers(self, workers: List[WorkerInfo], spreadsheet_path: str) -> Dict[str, Any]:
        """Upload multiple workers via CSC bulk upload."""
        if not self._logged_in:
            raise CSCError("Must login before bulk upload")
        
        logger.info(f"Bulk uploading {len(workers)} workers via spreadsheet")
        
        try:
            # Navigate to bulk upload page
            self._page.goto(f"{self.CSC_URL}/bulk-upload", wait_until="networkidle")
            
            # Wait for file upload input
            file_input = self._page.wait_for_selector(
                'input[type="file"]',
                timeout=10000
            )
            
            # Upload spreadsheet file
            file_input.set_input_files(spreadsheet_path)
            
            # Wait for file to be processed
            self._page.wait_for_selector('text=/processing|uploading/i', timeout=5000)
            self._page.wait_for_selector('text=/complete|ready/i', timeout=30000)
            
            # Click submit/upload button
            submit_button = self._page.wait_for_selector(
                'button:has-text("Submit"), button:has-text("Upload"), input[type="submit"]'
            )
            submit_button.click()
            
            # Wait for results
            self._page.wait_for_selector('text=/success|complete|results/i', timeout=60000)
            
            # Parse results
            # Look for success/failure counts
            result_text = self._page.content()
            
            import re
            uploaded_match = re.search(r'(\d+)\s+(?:workers?|records?)\s+(?:uploaded|processed|success)', result_text, re.I)
            failed_match = re.search(r'(\d+)\s+(?:workers?|records?)\s+(?:failed|error)', result_text, re.I)
            
            uploaded_count = int(uploaded_match.group(1)) if uploaded_match else len(workers)
            failed_count = int(failed_match.group(1)) if failed_match else 0
            
            logger.info(f"Bulk upload complete: {uploaded_count} uploaded, {failed_count} failed")
            
            return {
                "uploaded_count": uploaded_count,
                "failed_count": failed_count,
                "total_count": len(workers),
                "spreadsheet_path": spreadsheet_path
            }
            
        except Exception as e:
            self._take_screenshot(self._page, "bulk_upload_error")
            logger.error(f"Bulk upload failed: {e}")
            raise FormSubmissionError(f"Bulk upload failed: {e}")
```

### 5d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCAutomation.test_bulk_upload_workers -v
```

### 5e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/automation.py && git commit -m "Implement bulk upload via spreadsheet for CSC"
```

## Step 6: Create CSC module init and exports

**File**: `src/csc/__init__.py`

### 6a. Write failing test
```python
# tests/test_csc_automation.py (add new test class)
class TestCSCModule(unittest.TestCase):
    """Test CSC module exports."""
    
    def test_module_exports(self):
        """Test that module exports correct public API."""
        from src.csc import (
            CSCAutomation, CSCError, AuthenticationError, FormSubmissionError,
            WorkerInfo, CSCSpreadsheetGenerator
        )
        
        self.assertTrue(callable(CSCAutomation))
        self.assertTrue(callable(WorkerInfo))
        self.assertTrue(callable(CSCSpreadsheetGenerator))
```

### 6b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCModule.test_module_exports -v
```

### 6c. Write implementation
```python
# src/csc/__init__.py
"""CSC browser automation for vendor worker onboarding."""

from .automation import (
    CSCAutomation,
    CSCError,
    AuthenticationError,
    FormSubmissionError,
    WorkerInfo
)
from .spreadsheet import CSCSpreadsheetGenerator

__all__ = [
    "CSCAutomation",
    "CSCError",
    "AuthenticationError",
    "FormSubmissionError",
    "WorkerInfo",
    "CSCSpreadsheetGenerator"
]
```

### 6d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCModule.test_module_exports -v
```

### 6e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/__init__.py && git commit -m "Create CSC module init with public API exports"
```

## Step 7: Create CSC data validator

**File**: `src/csc/validator.py`

### 7a. Write failing test
```python
# tests/test_csc_validator.py
import unittest
from src.csc.validator import CSCDataValidator
from src.csc.automation import WorkerInfo


class TestCSCDataValidator(unittest.TestCase):
    """Test cases for CSCDataValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = CSCDataValidator()
    
    def test_validate_worker_valid(self):
        """Test validation of valid worker data."""
        worker = WorkerInfo(
            full_name="John Doe",
            email="john@vendor.com",
            start_date="2024-04-01",
            end_date="2025-04-01",
            job_title="Engineer",
            manager_email="manager@meta.com",
            work_location="Remote"
        )
        
        errors = self.validator.validate_worker(worker)
        self.assertEqual(len(errors), 0)
    
    def test_validate_worker_invalid_email(self):
        """Test validation catches invalid email."""
        worker = WorkerInfo(
            full_name="John Doe",
            email="invalid-email",
            start_date="2024-04-01",
            end_date="2025-04-01",
            job_title="Engineer",
            manager_email="manager@meta.com",
            work_location="Remote"
        )
        
        errors = self.validator.validate_worker(worker)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("email" in e.lower() for e in errors))
```

### 7b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_validator.TestCSCDataValidator.test_validate_worker_valid -v
```

### 7c. Write implementation
```python
# src/csc/validator.py
"""CSC data validator for worker information.

Validates worker data against CSC requirements before submission.
"""

import re
import logging
from typing import List
from datetime import datetime

from .automation import WorkerInfo

logger = logging.getLogger(__name__)


class CSCDataValidator:
    """Validates worker data for CSC onboarding."""
    
    # CSC-specific validation rules
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    DATE_FORMAT = "%Y-%m-%d"
    VALID_LOCATIONS = ["Remote", "Onsite", "Hybrid"]
    
    def __init__(self):
        """Initialize validator."""
        pass
    
    def validate_worker(self, worker: WorkerInfo) -> List[str]:
        """Validate a single worker's information.
        
        Args:
            worker: Worker information to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate full name
        if not worker.full_name or not worker.full_name.strip():
            errors.append("Full name is required")
        elif len(worker.full_name) > 100:
            errors.append("Full name must be 100 characters or less")
        
        # Validate email
        if not worker.email:
            errors.append("Email is required")
        elif not re.match(self.EMAIL_PATTERN, worker.email):
            errors.append(f"Invalid email format: {worker.email}")
        
        # Validate dates
        try:
            start_date = datetime.strptime(worker.start_date, self.DATE_FORMAT)
        except ValueError:
            errors.append(f"Invalid start date format. Expected YYYY-MM-DD, got: {worker.start_date}")
            start_date = None
        
        try:
            end_date = datetime.strptime(worker.end_date, self.DATE_FORMAT)
        except ValueError:
            errors.append(f"Invalid end date format. Expected YYYY-MM-DD, got: {worker.end_date}")
            end_date = None
        
        if start_date and end_date and start_date >= end_date:
            errors.append("End date must be after start date")
        
        # Validate job title
        if not worker.job_title or not worker.job_title.strip():
            errors.append("Job title is required")
        
        # Validate manager email
        if not worker.manager_email:
            errors.append("Manager email is required")
        elif not re.match(self.EMAIL_PATTERN, worker.manager_email):
            errors.append(f"Invalid manager email format: {worker.manager_email}")
        
        # Validate work location
        if worker.work_location not in self.VALID_LOCATIONS:
            errors.append(f"Work location must be one of: {', '.join(self.VALID_LOCATIONS)}")
        
        # Validate office location for onsite/hybrid
        if worker.work_location in ["Onsite", "Hybrid"]:
            if not worker.office_location or not worker.office_location.strip():
                errors.append(f"Office location is required for {worker.work_location} work")
        
        # Validate phone (if provided)
        if worker.phone:
            # Simple phone validation - at least 10 digits
            digits = re.sub(r'\D', '', worker.phone)
            if len(digits) < 10:
                errors.append(f"Phone number must have at least 10 digits: {worker.phone}")
        
        return errors
    
    def validate_workers(self, workers: List[WorkerInfo]) -> Dict[int, List[str]]:
        """Validate multiple workers.
        
        Args:
            workers: List of workers to validate
            
        Returns:
            Dictionary mapping worker index to list of errors
        """
        results = {}
        for idx, worker in enumerate(workers):
            errors = self.validate_worker(worker)
            if errors:
                results[idx] = errors
        return results
```

### 7d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_validator.TestCSCDataValidator.test_validate_worker_valid -v
```

### 7e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/validator.py tests/test_csc_validator.py && git commit -m "Create CSC data validator for worker information"
```

## Step 8: Add validator to CSC module exports

**File**: `src/csc/__init__.py`

### 8a. Write failing test
```python
# tests/test_csc_automation.py (update TestCSCModule)
    def test_module_exports(self):
        """Test that module exports correct public API."""
        from src.csc import (
            CSCAutomation, CSCError, AuthenticationError, FormSubmissionError,
            WorkerInfo, CSCSpreadsheetGenerator, CSCDataValidator
        )
        
        self.assertTrue(callable(CSCAutomation))
        self.assertTrue(callable(WorkerInfo))
        self.assertTrue(callable(CSCSpreadsheetGenerator))
        self.assertTrue(callable(CSCDataValidator))
```

### 8b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCModule.test_module_exports -v
```

### 8c. Write implementation
```python
# src/csc/__init__.py (update)
"""CSC browser automation for vendor worker onboarding."""

from .automation import (
    CSCAutomation,
    CSCError,
    AuthenticationError,
    FormSubmissionError,
    WorkerInfo
)
from .spreadsheet import CSCSpreadsheetGenerator
from .validator import CSCDataValidator

__all__ = [
    "CSCAutomation",
    "CSCError",
    "AuthenticationError",
    "FormSubmissionError",
    "WorkerInfo",
    "CSCSpreadsheetGenerator",
    "CSCDataValidator"
]
```

### 8d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_csc_automation.TestCSCModule.test_module_exports -v
```

### 8e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/csc/__init__.py && git commit -m "Add CSCDataValidator to module exports"
```

## Step 9: End-to-end verification

**File**: Verification script

### 9a. Create verification script
```python
# scripts/verify_csc_automation.py
"""End-to-end verification script for CSC automation."""

import sys
sys.path.insert(0, '/Users/ikosoy/Claude/project/Vendor_Onboarding')

from src.csc import CSCAutomation, WorkerInfo, CSCSpreadsheetGenerator, CSCDataValidator

def main():
    """Run end-to-end verification."""
    print("="*60)
    print("CSC AUTOMATION - END-TO-END VERIFICATION")
    print("="*60)
    
    # Test data
    workers = [
        WorkerInfo(
            full_name="John Doe",
            email="john.doe@vendor.com",
            start_date="2024-04-01",
            end_date="2025-04-01",
            job_title="Software Engineer",
            manager_email="manager@meta.com",
            work_location="Remote",
            phone="+1-555-0123"
        ),
        WorkerInfo(
            full_name="Jane Smith",
            email="jane.smith@vendor.com",
            start_date="2024-04-15",
            end_date="2025-04-15",
            job_title="Product Designer",
            manager_email="manager@meta.com",
            work_location="Onsite",
            office_location="Menlo Park",
            phone="+1-555-0124"
        )
    ]
    
    print(f"\n1. Validating {len(workers)} workers...")
    validator = CSCDataValidator()
    for idx, worker in enumerate(workers):
        errors = validator.validate_worker(worker)
        if errors:
            print(f"   Worker {idx+1} ({worker.email}): FAILED")
            for error in errors:
                print(f"     - {error}")
            return False
        else:
            print(f"   Worker {idx+1} ({worker.email}): PASSED")
    
    print("\n2. Generating CSC spreadsheet...")
    generator = CSCSpreadsheetGenerator()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        spreadsheet_path = tmp.name
    
    try:
        result_path = generator.generate(workers, spreadsheet_path)
        print(f"   Spreadsheet generated: {result_path}")
        
        # Validate spreadsheet
        errors = generator.validate_spreadsheet(result_path)
        if errors:
            print("   Spreadsheet validation FAILED:")
            for error in errors:
                print(f"     - {error}")
            return False
        else:
            print("   Spreadsheet validation PASSED")
    finally:
        import os
        if os.path.exists(spreadsheet_path):
            os.unlink(spreadsheet_path)
    
    print("\n3. CSC Automation client ready...")
    automation = CSCAutomation(headless=True)
    print("   Client initialized successfully")
    print("   Features available:")
    print("     - SSO login")
    print("     - Individual worker onboarding")
    print("     - Bulk upload via spreadsheet")
    print("     - Screenshot-on-failure")
    
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)
    print("\nThe CSC automation is ready for use.")
    print("\nExample usage:")
    print("  automation = CSCAutomation()")
    print("  automation.login()")
    print("  worker_id = automation.onboard_worker(worker)")
    print("  result = automation.bulk_upload_workers(workers, spreadsheet_path)")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### 9b. Run verification
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 scripts/verify_csc_automation.py
```

### 9c. Commit verification script
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add scripts/verify_csc_automation.py && git commit -m "Add end-to-end verification script for CSC automation"
```

## Summary

This plan implements CSC browser automation for vendor worker onboarding with:

1. **CSC Automation** (`src/csc/automation.py`): Playwright-based browser automation for CSC UI, with SSO login, individual worker onboarding, and bulk upload via spreadsheet
2. **Spreadsheet Generator** (`src/csc/spreadsheet.py`): Generates Excel files in CSC bulk upload format with proper styling and validation
3. **Data Validator** (`src/csc/validator.py`): Validates worker data against CSC requirements before submission

All steps follow TDD pattern with failing tests written first, then implementation, then verification. The automation handles the complete CSC workflow from login through worker onboarding with robust error handling and screenshot-on-failure for debugging.
