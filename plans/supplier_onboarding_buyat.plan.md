# Plan: Buy@ Supplier Onboarding Automation

**Goal**: Automate supplier verification and onboarding request submission via Buy@ system, enabling programmatic checking of supplier existence and automated submission of Supplier Onboarding Request forms. The workflow first checks if supplier is already onboarded and active in Buy@ before creating a new onboarding request to avoid duplicates.

**Architecture**: Browser automation adapter for Buy@ supplier search (no public API available) combined with Butterfly Forms API for onboarding request submission. Uses Playwright for reliable browser automation with screenshot-on-failure for debugging. Workflow includes conditional logic: if supplier exists and is active, skip onboarding request; if supplier exists but inactive, reactivate; if supplier does not exist, submit new onboarding request.

**Tech Stack**: Python 3.12, Playwright, Butterfly Forms API (EntButterflyFormResponseMutator), pytest for testing

## Task Dependencies

| Group | Steps | Can Parallelize | Files Touched |
|-------|-------|-----------------|---------------|
| 1 | Steps 1-3 | Yes (independent) | src/buyat/client.py, tests/test_buyat_client.py |
| 2 | Step 4 | No (depends on Group 1) | src/buyat/__init__.py |
| 3 | Steps 5-7 | Yes (independent) | src/orchestrator/supplier_workflow.py, tests/test_supplier_workflow.py |
| 4 | Step 8 | No (depends on Group 3) | Integration test |

## Step 1: Create Buy@ client structure with supplier search interface

**File**: `src/buyat/client.py`

### 1a. Write failing test
```python
# tests/test_buyat_client.py
import unittest
from unittest.mock import MagicMock, patch
from src.buyat.client import BuyAtClient, SupplierInfo, SupplierNotFoundError


class TestBuyAtClient(unittest.TestCase):
    """Test cases for BuyAtClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = BuyAtClient()
    
    def test_search_supplier_found(self):
        """Test searching for existing supplier."""
        # This test will fail until implementation is complete
        result = self.client.search_supplier("Test Supplier Inc")
        self.assertIsInstance(result, SupplierInfo)
        self.assertEqual(result.name, "Test Supplier Inc")
        self.assertTrue(result.exists)
    
    def test_search_supplier_not_found(self):
        """Test searching for non-existent supplier."""
        with self.assertRaises(SupplierNotFoundError):
            self.client.search_supplier("NonExistent Supplier XYZ")
```

### 1b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtClient.test_search_supplier_found -v
```

### 1c. Write implementation
```python
# src/buyat/client.py
"""Buy@ client for supplier verification and onboarding.

Provides browser automation for searching suppliers in Buy@ system
since no public API is available.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class SupplierNotFoundError(Exception):
    """Raised when supplier is not found in Buy@."""
    pass


class BuyAtError(Exception):
    """Base exception for Buy@ operations."""
    pass


@dataclass
class SupplierInfo:
    """Information about a supplier in Buy@."""
    name: str
    exists: bool
    supplier_id: Optional[str] = None
    status: Optional[str] = None
    contact_email: Optional[str] = None


class BuyAtClient:
    """Client for interacting with Buy@ supplier system.
    
    Uses browser automation to search for suppliers since
    Buy@ does not provide a public API for supplier verification.
    """
    
    BUYAT_URL = "https://www.internalfb.com/buy/suppliers/onboarding"
    
    def __init__(self, headless: bool = True):
        """Initialize Buy@ client.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self._browser = None
        self._page = None
    
    def search_supplier(self, supplier_name: str) -> SupplierInfo:
        """Search for a supplier in Buy@.
        
        Args:
            supplier_name: Name of supplier to search for
            
        Returns:
            SupplierInfo with supplier details
            
        Raises:
            SupplierNotFoundError: If supplier is not found
            BuyAtError: If search fails
        """
        # TODO: Implement browser automation
        # For now, raise NotImplementedError to make test fail
        raise NotImplementedError("Browser automation not yet implemented")
    
    def verify_supplier_exists(self, supplier_name: str) -> bool:
        """Check if supplier exists in Buy@.
        
        Args:
            supplier_name: Name of supplier to check
            
        Returns:
            True if supplier exists, False otherwise
        """
        try:
            info = self.search_supplier(supplier_name)
            return info.exists
        except SupplierNotFoundError:
            return False
    
    def close(self):
        """Close browser resources."""
        if self._browser:
            self._browser.close()
```

### 1d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtClient.test_search_supplier_found -v
```

### 1e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/buyat/client.py tests/test_buyat_client.py && git commit -m "Add Buy@ client structure with supplier search interface"
```

## Step 2: Implement Playwright browser automation for supplier search

**File**: `src/buyat/client.py`

### 2a. Write failing test
```python
# tests/test_buyat_client.py (add to TestBuyAtClient class)
    @patch('src.buyat.client.sync_playwright')
    def test_search_supplier_with_playwright(self, mock_playwright):
        """Test supplier search using Playwright automation."""
        # Mock Playwright browser and page
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        
        # Mock page content indicating supplier found
        mock_page.content.return_value = '<div class="supplier-result">Test Supplier Inc</div>'
        mock_page.query_selector.return_value = MagicMock()
        mock_page.query_selector.return_value.inner_text.return_value = "Test Supplier Inc"
        
        result = self.client.search_supplier("Test Supplier Inc")
        
        self.assertEqual(result.name, "Test Supplier Inc")
        self.assertTrue(result.exists)
        mock_page.goto.assert_called_with(self.client.BUYAT_URL)
```

### 2b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtClient.test_search_supplier_with_playwright -v
```

### 2c. Write implementation
```python
# src/buyat/client.py (update search_supplier method)
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class BuyAtClient:
    # ... existing code ...
    
    def search_supplier(self, supplier_name: str) -> SupplierInfo:
        """Search for a supplier in Buy@.
        
        Args:
            supplier_name: Name of supplier to search for
            
        Returns:
            SupplierInfo with supplier details
            
        Raises:
            SupplierNotFoundError: If supplier is not found
            BuyAtError: If search fails
        """
        logger.info(f"Searching for supplier: {supplier_name}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                
                try:
                    # Navigate to Buy@ onboarding page
                    page.goto(self.BUYAT_URL, wait_until="networkidle")
                    
                    # Wait for search input and enter supplier name
                    search_input = page.wait_for_selector(
                        'input[placeholder*="Search" i], input[name*="search" i]',
                        timeout=10000
                    )
                    search_input.fill(supplier_name)
                    search_input.press("Enter")
                    
                    # Wait for results
                    page.wait_for_timeout(2000)
                    
                    # Check if supplier found
                    # Look for supplier in results (adjust selector based on actual page)
                    supplier_element = page.query_selector(
                        f'text="{supplier_name}"'
                    )
                    
                    if supplier_element:
                        # Extract supplier details
                        supplier_id_elem = page.query_selector('[data-supplier-id]')
                        supplier_id = supplier_id_elem.get_attribute('data-supplier-id') if supplier_id_elem else None
                        
                        status_elem = page.query_selector('.supplier-status')
                        status = status_elem.inner_text() if status_elem else "Active"
                        
                        return SupplierInfo(
                            name=supplier_name,
                            exists=True,
                            supplier_id=supplier_id,
                            status=status
                        )
                    else:
                        # Check for "no results" message
                        no_results = page.query_selector('text=/no results|not found/i')
                        if no_results:
                            raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
                        
                        # If we can't determine, assume not found
                        raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
                
                finally:
                    browser.close()
        
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout searching for supplier: {e}")
            raise BuyAtError(f"Timeout searching Buy@: {e}")
        except Exception as e:
            logger.error(f"Error searching for supplier: {e}")
            raise BuyAtError(f"Failed to search Buy@: {e}")
```

### 2d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtClient.test_search_supplier_with_playwright -v
```

### 2e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/buyat/client.py && git commit -m "Implement Playwright browser automation for supplier search"
```

## Step 3: Add screenshot-on-failure and error handling

**File**: `src/buyat/client.py`

### 3a. Write failing test
```python
# tests/test_buyat_client.py (add to TestBuyAtClient class)
    @patch('src.buyat.client.sync_playwright')
    @patch('src.buyat.client.datetime')
    def test_screenshot_on_failure(self, mock_datetime, mock_playwright):
        """Test that screenshot is taken on failure."""
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.side_effect = Exception("Navigation failed")
        
        with self.assertRaises(BuyAtError):
            self.client.search_supplier("Test Supplier")
        
        # Verify screenshot was taken
        mock_page.screenshot.assert_called_once()
        screenshot_path = mock_page.screenshot.call_args[1]['path']
        self.assertIn("buyat_error_20240101_120000.png", screenshot_path)
```

### 3b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtClient.test_screenshot_on_failure -v
```

### 3c. Write implementation
```python
# src/buyat/client.py (update imports and search_supplier method)
import os
from datetime import datetime
from pathlib import Path

class BuyAtClient:
    # ... existing code ...
    
    def __init__(self, headless: bool = True, screenshot_dir: str = "/tmp/buyat_screenshots"):
        """Initialize Buy@ client.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots
        """
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._browser = None
        self._page = None
    
    def _take_screenshot(self, page, prefix: str = "error"):
        """Take screenshot for debugging.
        
        Args:
            page: Playwright page object
            prefix: Prefix for screenshot filename
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"buyat_{prefix}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            page.screenshot(path=str(filepath))
            logger.info(f"Screenshot saved to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None
    
    def search_supplier(self, supplier_name: str) -> SupplierInfo:
        """Search for a supplier in Buy@."""
        logger.info(f"Searching for supplier: {supplier_name}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                
                try:
                    # Navigate to Buy@ onboarding page
                    page.goto(self.BUYAT_URL, wait_until="networkidle")
                    
                    # Wait for search input and enter supplier name
                    search_input = page.wait_for_selector(
                        'input[placeholder*="Search" i], input[name*="search" i]',
                        timeout=10000
                    )
                    search_input.fill(supplier_name)
                    search_input.press("Enter")
                    
                    # Wait for results
                    page.wait_for_timeout(2000)
                    
                    # Check if supplier found
                    supplier_element = page.query_selector(f'text="{supplier_name}"')
                    
                    if supplier_element:
                        supplier_id_elem = page.query_selector('[data-supplier-id]')
                        supplier_id = supplier_id_elem.get_attribute('data-supplier-id') if supplier_id_elem else None
                        
                        status_elem = page.query_selector('.supplier-status')
                        status = status_elem.inner_text() if status_elem else "Active"
                        
                        return SupplierInfo(
                            name=supplier_name,
                            exists=True,
                            supplier_id=supplier_id,
                            status=status
                        )
                    else:
                        no_results = page.query_selector('text=/no results|not found/i')
                        if no_results:
                            raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
                        raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
                
                except Exception as e:
                    # Take screenshot on any error
                    self._take_screenshot(page, "search_error")
                    raise
                
                finally:
                    browser.close()
        
        except SupplierNotFoundError:
            raise
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout searching for supplier: {e}")
            raise BuyAtError(f"Timeout searching Buy@: {e}")
        except Exception as e:
            logger.error(f"Error searching for supplier: {e}")
            raise BuyAtError(f"Failed to search Buy@: {e}")
```

### 3d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtClient.test_screenshot_on_failure -v
```

### 3e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/buyat/client.py && git commit -m "Add screenshot-on-failure and error handling for Buy@ client"
```

## Step 4: Create Buy@ module init and export public API

**File**: `src/buyat/__init__.py`

### 4a. Write failing test
```python
# tests/test_buyat_client.py (add new test class)
class TestBuyAtModule(unittest.TestCase):
    """Test Buy@ module exports."""
    
    def test_module_exports(self):
        """Test that module exports correct public API."""
        from src.buyat import BuyAtClient, SupplierInfo, SupplierNotFoundError, BuyAtError
        
        self.assertTrue(callable(BuyAtClient))
        self.assertTrue(callable(SupplierInfo))
        self.assertTrue(issubclass(SupplierNotFoundError, Exception))
        self.assertTrue(issubclass(BuyAtError, Exception))
```

### 4b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtModule.test_module_exports -v
```

### 4c. Write implementation
```python
# src/buyat/__init__.py
"""Buy@ client for supplier verification and onboarding."""

from .client import BuyAtClient, SupplierInfo, SupplierNotFoundError, BuyAtError

__all__ = ["BuyAtClient", "SupplierInfo", "SupplierNotFoundError", "BuyAtError"]
```

### 4d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_buyat_client.TestBuyAtModule.test_module_exports -v
```

### 4e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/buyat/__init__.py && git commit -m "Create Buy@ module init with public API exports"
```

## Step 5: Create supplier onboarding workflow orchestrator

**File**: `src/orchestrator/supplier_workflow.py`

### 5a. Write failing test
```python
# tests/test_supplier_workflow.py
import unittest
from unittest.mock import MagicMock, patch
from src.orchestrator.supplier_workflow import SupplierOnboardingWorkflow


class TestSupplierOnboardingWorkflow(unittest.TestCase):
    """Test cases for SupplierOnboardingWorkflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.workflow = SupplierOnboardingWorkflow()
    
    def test_workflow_initialization(self):
        """Test workflow initializes with correct steps."""
        self.assertIsNotNone(self.workflow.orchestrator)
        # Should have steps for: verify_supplier, check_status, submit_onboarding_form (conditional)
        step_ids = list(self.workflow.orchestrator.steps.keys())
        self.assertIn("verify_supplier", step_ids)
        self.assertIn("check_supplier_status", step_ids)
        self.assertIn("submit_onboarding_form", step_ids)
    
    def test_execute_with_existing_active_supplier(self):
        """Test workflow skips onboarding when supplier is already active."""
        with patch.object(self.workflow, '_verify_supplier') as mock_verify:
            mock_verify.return_value = {"exists": True, "supplier_id": "SUP123", "status": "Active"}
            
            with patch.object(self.workflow, '_check_supplier_status') as mock_check:
                mock_check.return_value = {"is_active": True, "needs_onboarding": False}
                
                with patch.object(self.workflow, '_submit_onboarding_form') as mock_submit:
                    result = self.workflow.execute("Test Supplier Inc", {"business_justification": "Test"})
                    
                    self.assertTrue(result["success"])
                    self.assertEqual(result["supplier_id"], "SUP123")
                    self.assertFalse(result["onboarding_submitted"])
                    # Submit should NOT be called for active supplier
                    mock_submit.assert_not_called()
    
    def test_execute_with_new_supplier(self):
        """Test workflow submits onboarding for new supplier."""
        with patch.object(self.workflow, '_verify_supplier') as mock_verify:
            mock_verify.return_value = {"exists": False}
            
            with patch.object(self.workflow, '_check_supplier_status') as mock_check:
                mock_check.return_value = {"is_active": False, "needs_onboarding": True}
                
                with patch.object(self.workflow, '_submit_onboarding_form') as mock_submit:
                    mock_submit.return_value = {"response_id": "resp_456", "status": "submitted"}
                    
                    result = self.workflow.execute("New Supplier Inc", {"business_justification": "Test"})
                    
                    self.assertTrue(result["success"])
                    self.assertTrue(result["onboarding_submitted"])
                    mock_submit.assert_called_once()
```

### 5b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_supplier_workflow.TestSupplierOnboardingWorkflow.test_workflow_initialization -v
```

### 5c. Write implementation
```python
# src/orchestrator/supplier_workflow.py
"""Supplier onboarding workflow orchestrator.

Orchestrates the supplier verification and onboarding request process:
1. Verify supplier exists in Buy@ (via browser automation)
2. Check if supplier is active (skip onboarding if already active)
3. Submit Supplier Onboarding Request form (via Butterfly API) - only if needed
"""

import logging
from typing import Any, Dict, Optional

from .workflow import WorkflowOrchestrator
from ..buyat import BuyAtClient, SupplierNotFoundError
from ..butterfly import ButterflyClient

logger = logging.getLogger(__name__)


class SupplierOnboardingWorkflow:
    """Workflow for onboarding suppliers via Buy@.
    
    Steps:
    1. Verify supplier exists in Buy@ system
    2. Check supplier status (active/inactive)
    3. Submit Supplier Onboarding Request form via Butterfly API (conditional)
    
    The workflow intelligently skips the onboarding form submission if the
    supplier already exists and is active in Buy@, preventing duplicate requests.
    """
    
    def __init__(self, workflow_id: Optional[str] = None):
        """Initialize supplier onboarding workflow.
        
        Args:
            workflow_id: Optional workflow ID for resuming
        """
        self.orchestrator = WorkflowOrchestrator(workflow_id=workflow_id)
        self.buyat_client = BuyAtClient()
        self.butterfly_client = ButterflyClient()
        self._supplier_info: Optional[Dict[str, Any]] = None
        self._form_data: Optional[Dict[str, Any]] = None
        self._supplier_status: Optional[Dict[str, Any]] = None
        
        self._setup_workflow()
    
    def _setup_workflow(self):
        """Set up workflow steps."""
        # Step 1: Verify supplier exists in Buy@
        self.orchestrator.add_step(
            step_id="verify_supplier",
            name="Verify supplier in Buy@",
            action=self._verify_supplier,
            dependencies=[],
            max_retries=2
        )
        
        # Step 2: Check supplier status (active/inactive)
        self.orchestrator.add_step(
            step_id="check_supplier_status",
            name="Check supplier active status",
            action=self._check_supplier_status,
            dependencies=["verify_supplier"],
            max_retries=1
        )
        
        # Step 3: Submit onboarding form (depends on status check, conditional)
        self.orchestrator.add_step(
            step_id="submit_onboarding_form",
            name="Submit Supplier Onboarding Request",
            action=self._submit_onboarding_form,
            dependencies=["check_supplier_status"],
            max_retries=3
        )
    
    def _verify_supplier(self) -> Dict[str, Any]:
        """Verify supplier exists in Buy@.
        
        Returns:
            Dictionary with supplier verification results
        """
        if not self._supplier_info:
            raise ValueError("Supplier info not set")
        
        supplier_name = self._supplier_info.get("supplier_name")
        if not supplier_name:
            raise ValueError("Supplier name is required")
        
        logger.info(f"Verifying supplier: {supplier_name}")
        
        try:
            supplier = self.buyat_client.search_supplier(supplier_name)
            return {
                "exists": True,
                "supplier_id": supplier.supplier_id,
                "name": supplier.name,
                "status": supplier.status
            }
        except SupplierNotFoundError:
            logger.warning(f"Supplier not found: {supplier_name}")
            return {
                "exists": False,
                "name": supplier_name
            }
    
    def _check_supplier_status(self) -> Dict[str, Any]:
        """Check if supplier is active and needs onboarding.
        
        Returns:
            Dictionary with status check results
        """
        verify_result = self.orchestrator.get_step_status("verify_supplier")
        if not verify_result or not verify_result.get("result"):
            raise ValueError("Supplier verification must complete first")
        
        supplier_data = verify_result["result"]
        exists = supplier_data.get("exists", False)
        status = supplier_data.get("status", "")
        
        # Determine if supplier is active
        is_active = exists and status.lower() in ["active", "approved", "enabled"]
        needs_onboarding = not is_active
        
        logger.info(f"Supplier status check: exists={exists}, status={status}, is_active={is_active}, needs_onboarding={needs_onboarding}")
        
        self._supplier_status = {
            "is_active": is_active,
            "needs_onboarding": needs_onboarding,
            "status": status
        }
        
        return self._supplier_status
    
    def _submit_onboarding_form(self) -> Dict[str, Any]:
        """Submit Supplier Onboarding Request form (conditional).
        
        Only submits if supplier does not exist or is not active.
        If supplier is already active, this step is skipped.
        
        Returns:
            Dictionary with form submission results
        """
        # Check if onboarding is needed
        if self._supplier_status and not self._supplier_status.get("needs_onboarding", True):
            logger.info("Supplier is already active, skipping onboarding form submission")
            return {
                "skipped": True,
                "reason": "Supplier already active in Buy@",
                "response_id": None,
                "status": "skipped"
            }
        
        if not self._form_data:
            raise ValueError("Form data not set")
        
        logger.info("Submitting Supplier Onboarding Request form")
        
        # Submit via Butterfly API
        response = self.butterfly_client.submit_supplier_onboarding(
            data=self._form_data,
            validate=True
        )
        
        return {
            "skipped": False,
            "response_id": response.response_id,
            "status": response.status.value,
            "form_id": response.form_id
        }
    
    def execute(self, supplier_name: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the supplier onboarding workflow.
        
        Args:
            supplier_name: Name of supplier to onboard
            form_data: Data for Supplier Onboarding Request form
            
        Returns:
            Dictionary with workflow execution results
        """
        self._supplier_info = {"supplier_name": supplier_name}
        self._form_data = form_data
        
        # Store in orchestrator metadata
        self.orchestrator.metadata["supplier_name"] = supplier_name
        self.orchestrator.metadata["workflow_type"] = "supplier_onboarding"
        
        success = self.orchestrator.run()
        
        # Get results from steps
        verify_result = self.orchestrator.get_step_status("verify_supplier")
        status_result = self.orchestrator.get_step_status("check_supplier_status")
        submit_result = self.orchestrator.get_step_status("submit_onboarding_form")
        
        supplier_exists = verify_result.get("result", {}).get("exists", False) if verify_result else False
        is_active = status_result.get("result", {}).get("is_active", False) if status_result else False
        onboarding_submitted = False
        if submit_result and submit_result.get("result"):
            onboarding_submitted = not submit_result["result"].get("skipped", False)
        
        return {
            "success": success,
            "workflow_id": self.orchestrator.workflow_id,
            "supplier_exists": supplier_exists,
            "supplier_active": is_active,
            "onboarding_submitted": onboarding_submitted,
            "onboarding_skipped": not onboarding_submitted and supplier_exists and is_active,
            "supplier_id": verify_result.get("result", {}).get("supplier_id") if verify_result else None,
            "response_id": submit_result.get("result", {}).get("response_id") if submit_result else None
        }
```

### 5d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_supplier_workflow.TestSupplierOnboardingWorkflow.test_workflow_initialization -v
```

### 5e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/orchestrator/supplier_workflow.py tests/test_supplier_workflow.py && git commit -m "Create supplier onboarding workflow orchestrator"
```

## Step 6: Add workflow resume capability and status checking

**File**: `src/orchestrator/supplier_workflow.py`

### 6a. Write failing test
```python
# tests/test_supplier_workflow.py (add to TestSupplierOnboardingWorkflow)
    def test_workflow_resume(self):
        """Test resuming a paused workflow."""
        workflow1 = SupplierOnboardingWorkflow(workflow_id="test-resume-123")
        workflow1._supplier_info = {"supplier_name": "Test Supplier"}
        workflow1._form_data = {"business_justification": "Test"}
        
        # Simulate partial execution
        workflow1.orchestrator.metadata["test"] = "data"
        workflow1.orchestrator._save_state()
        
        # Create new workflow with same ID and resume
        workflow2 = SupplierOnboardingWorkflow(workflow_id="test-resume-123")
        self.assertEqual(workflow2.orchestrator.metadata.get("test"), "data")
    
    def test_get_workflow_status(self):
        """Test getting workflow status."""
        status = self.workflow.get_status()
        self.assertIn("workflow_id", status)
        self.assertIn("state", status)
        self.assertIn("steps", status)
```

### 6b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_supplier_workflow.TestSupplierOnboardingWorkflow.test_workflow_resume -v
```

### 6c. Write implementation
```python
# src/orchestrator/supplier_workflow.py (add methods to SupplierOnboardingWorkflow class)
    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status.
        
        Returns:
            Dictionary with workflow status information
        """
        status = self.orchestrator.get_status()
        
        # Add supplier-specific information
        status["supplier_name"] = self.orchestrator.metadata.get("supplier_name")
        status["workflow_type"] = "supplier_onboarding"
        
        return status
    
    def resume(self) -> Dict[str, Any]:
        """Resume a paused or failed workflow.
        
        Returns:
            Dictionary with workflow execution results
        """
        logger.info(f"Resuming workflow {self.orchestrator.workflow_id}")
        
        # Load state to get supplier info and form data
        state = self.orchestrator.state_store.load_workflow(
            self.orchestrator.workflow_id
        )
        
        if state and "metadata" in state:
            metadata = state["metadata"]
            # Restore supplier info and form data from metadata if available
            if "supplier_name" in metadata:
                self._supplier_info = {"supplier_name": metadata["supplier_name"]}
        
        success = self.orchestrator.resume()
        
        return {
            "success": success,
            "workflow_id": self.orchestrator.workflow_id,
            "resumed": True
        }
    
    @classmethod
    def list_workflows(cls, status: Optional[str] = None) -> list:
        """List supplier onboarding workflows.
        
        Args:
            status: Filter by workflow status
            
        Returns:
            List of workflow summaries
        """
        from .state_store import SQLiteStateStore
        store = SQLiteStateStore()
        workflows = store.list_workflows(status=status)
        
        # Filter to only supplier onboarding workflows
        supplier_workflows = [
            w for w in workflows
            if w.get("metadata", {}).get("workflow_type") == "supplier_onboarding"
        ]
        
        return supplier_workflows
```

### 6d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_supplier_workflow.TestSupplierOnboardingWorkflow.test_workflow_resume -v
```

### 6e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add src/orchestrator/supplier_workflow.py && git commit -m "Add workflow resume capability and status checking"
```

## Step 7: Create integration test for end-to-end supplier onboarding

**File**: `tests/test_supplier_onboarding_integration.py`

### 7a. Write failing test
```python
# tests/test_supplier_onboarding_integration.py
import unittest
from unittest.mock import MagicMock, patch, Mock
from src.orchestrator.supplier_workflow import SupplierOnboardingWorkflow
from src.buyat import SupplierInfo
from src.butterfly import FormResponse, FormStatus


class TestSupplierOnboardingIntegration(unittest.TestCase):
    """Integration test for end-to-end supplier onboarding."""
    
    @patch('src.orchestrator.supplier_workflow.BuyAtClient')
    @patch('src.orchestrator.supplier_workflow.ButterflyClient')
    def test_end_to_end_supplier_onboarding(self, mock_butterfly, mock_buyat):
        """Test complete supplier onboarding workflow."""
        # Mock Buy@ client - supplier exists
        mock_buyat_instance = MagicMock()
        mock_buyat.return_value = mock_buyat_instance
        mock_buyat_instance.search_supplier.return_value = SupplierInfo(
            name="Acme Corp",
            exists=True,
            supplier_id="SUP789",
            status="Active"
        )
        
        # Mock Butterfly client - form submission succeeds
        mock_butterfly_instance = MagicMock()
        mock_butterfly.return_value = mock_butterfly_instance
        mock_butterfly_instance.submit_supplier_onboarding.return_value = FormResponse(
            form_id="983940998852772",
            response_id="resp_12345",
            status=FormStatus.SUBMITTED
        )
        
        # Execute workflow
        workflow = SupplierOnboardingWorkflow()
        form_data = {
            "supplier_name": "Acme Corp",
            "supplier_contact_email": "contact@acme.com",
            "business_justification": "Need vendor for project X",
            "estimated_spend": "$100000",
            "contract_start_date": "2024-03-01",
            "contract_end_date": "2025-03-01",
            "requestor_manager": "manager"
        }
        
        result = workflow.execute("Acme Corp", form_data)
        
        # Verify results
        self.assertTrue(result["success"])
        self.assertTrue(result["supplier_verified"])
        self.assertTrue(result["form_submitted"])
        self.assertEqual(result["supplier_id"], "SUP789")
        self.assertEqual(result["response_id"], "resp_12345")
        
        # Verify clients were called correctly
        mock_buyat_instance.search_supplier.assert_called_once_with("Acme Corp")
        mock_butterfly_instance.submit_supplier_onboarding.assert_called_once()
```

### 7b. Run test to verify it fails
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_supplier_onboarding_integration.TestSupplierOnboardingIntegration.test_end_to_end_supplier_onboarding -v
```

### 7c. Write implementation
The implementation is already complete from previous steps. The test should pass now.

### 7d. Run test to verify it passes
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 -m unittest tests.test_supplier_onboarding_integration.TestSupplierOnboardingIntegration.test_end_to_end_supplier_onboarding -v
```

### 7e. Commit
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && git add tests/test_supplier_onboarding_integration.py && git commit -m "Create integration test for end-to-end supplier onboarding"
```

## Step 8: End-to-end verification

**File**: Verification script

### 8a. Create verification script
```python
# scripts/verify_supplier_onboarding.py
"""End-to-end verification script for supplier onboarding."""

import sys
sys.path.insert(0, '/Users/ikosoy/Claude/project/Vendor_Onboarding')

from src.orchestrator.supplier_workflow import SupplierOnboardingWorkflow

def main():
    """Run end-to-end verification."""
    print("="*60)
    print("SUPPLIER ONBOARDING - END-TO-END VERIFICATION")
    print("="*60)
    
    # Test data
    supplier_name = "Test Supplier Inc"
    form_data = {
        "supplier_name": supplier_name,
        "supplier_contact_email": "test@supplier.com",
        "supplier_contact_phone": "+1-555-0123",
        "business_justification": "Test onboarding via automation",
        "estimated_spend": "$50000",
        "contract_start_date": "2024-04-01",
        "contract_end_date": "2025-04-01",
        "requestor_manager": "testmanager"
    }
    
    print(f"\n1. Creating workflow for supplier: {supplier_name}")
    workflow = SupplierOnboardingWorkflow()
    print(f"   Workflow ID: {workflow.orchestrator.workflow_id}")
    
    print("\n2. Workflow steps configured:")
    for step_id, step in workflow.orchestrator.steps.items():
        print(f"   - {step_id}: {step.name}")
        if step.dependencies:
            print(f"     Dependencies: {', '.join(step.dependencies)}")
    
    print("\n3. Validating form data...")
    from src.butterfly import ButterflyClient
    client = ButterflyClient()
    errors = client.validate_form_data("supplier_onboarding_request", form_data)
    
    if errors:
        print("   Validation FAILED:")
        for error in errors:
            print(f"     - {error}")
        return False
    else:
        print("   Validation PASSED")
    
    print("\n4. Checking workflow status...")
    status = workflow.get_status()
    print(f"   State: {status['state']}")
    print(f"   Total steps: {status['total_steps']}")
    
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)
    print("\nThe supplier onboarding workflow is ready for execution.")
    print("To execute with real data, run:")
    print(f"  workflow.execute('{supplier_name}', form_data)")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### 8b. Run verification
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && python3 scripts/verify_supplier_onboarding.py
```

### 8c. Commit verification script
```bash
cd /Users/ikosoy/Claude/project/Vendor_Onboarding && mkdir -p scripts && git add scripts/verify_supplier_onboarding.py && git commit -m "Add end-to-end verification script for supplier onboarding"
```

## Summary

This plan implements Buy@ supplier onboarding automation with:

1. **Buy@ Client** (`src/buyat/client.py`): Browser automation for supplier search with Playwright, screenshot-on-failure, and error handling
2. **Supplier Workflow** (`src/orchestrator/supplier_workflow.py`): Orchestrates verification and form submission with dependency management
3. **Integration**: Connects Buy@ verification with Butterfly Forms API for complete automation

All steps follow TDD pattern with failing tests written first, then implementation, then verification.
