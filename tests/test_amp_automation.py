import unittest
from unittest.mock import MagicMock, patch
from src.amp.automation import AMPAutomation, AMPError, AuthenticationError


class TestAMPAutomation(unittest.TestCase):
    """Test cases for AMPAutomation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.automation = AMPAutomation()
    
    def test_initialization(self):
        """Test AMP automation initializes correctly."""
        self.assertIsNotNone(self.automation)
        self.assertTrue(self.automation.headless)
    
    def test_login_with_sso(self):
        """Test SSO login to AMP."""
        with patch('src.amp.automation.sync_playwright') as mock_pw:
            mock_browser = MagicMock()
            mock_page = MagicMock()
            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_page.return_value = mock_page
            
            result = self.automation.login()
            self.assertTrue(result)
