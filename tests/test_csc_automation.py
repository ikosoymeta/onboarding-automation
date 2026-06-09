import unittest
from unittest.mock import MagicMock, patch
import tempfile
from src.csc.automation import CSCAutomation, CSCError, AuthenticationError, WorkerInfo


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
