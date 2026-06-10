import unittest
from unittest.mock import MagicMock, patch, call
from src.buyat.client import (
    AgenticBuyingClient, 
    AgenticResponse,
    BuyAtClient, 
    SupplierInfo, 
    SupplierNotFoundError,
    AgenticFlowError
)


class TestAgenticBuyingClient(unittest.TestCase):
    """Test cases for AgenticBuyingClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = AgenticBuyingClient(headless=True)
    
    def test_init(self):
        """Test client initialization."""
        self.assertTrue(self.client.headless)
        self.assertIsNotNone(self.client.screenshot_dir)
        self.assertFalse(self.client._assistant_open)
    
    @patch('src.buyat.client.sync_playwright')
    def test_start_browser(self, mock_playwright):
        """Test starting browser session."""
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.start.return_value = mock_pw
        
        self.client.start()
        
        self.assertIsNotNone(self.client._browser)
        self.assertIsNotNone(self.client._page)
        mock_playwright.return_value.start.assert_called_once()
    
    def test_close_browser(self):
        """Test closing browser resources."""
        mock_browser = MagicMock()
        mock_playwright = MagicMock()
        self.client._browser = mock_browser
        self.client._playwright = mock_playwright
        self.client._assistant_open = True
        
        self.client.close()
        
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        self.assertIsNone(self.client._browser)
        self.assertFalse(self.client._assistant_open)
    
    @patch('src.buyat.client.AgenticBuyingClient._wait_for_response')
    def test_send_message(self, mock_wait):
        """Test sending a message to the assistant."""
        mock_page = MagicMock()
        mock_input = MagicMock()
        mock_button = MagicMock()
        
        # Configure locator to return different mocks for different calls
        # First call (input field) returns mock_input, second call (button) returns mock_button
        mock_page.locator.side_effect = [
            MagicMock(first=MagicMock(return_value=mock_input)),
            MagicMock(first=MagicMock(return_value=mock_button))
        ]
        mock_input.is_visible.return_value = True
        mock_button.is_visible.return_value = True
        
        self.client._page = mock_page
        self.client._assistant_open = True
        mock_wait.return_value = AgenticResponse(
            message="I can help you with that. What supplier do you need?",
            has_followup=True
        )
        
        response = self.client.send_message("I need to onboard a supplier")
        
        mock_input.fill.assert_called_once_with("I need to onboard a supplier")
        mock_button.click.assert_called_once()
        self.assertTrue(response.has_followup)
    
    def test_onboard_supplier_prompt(self):
        """Test that onboard_supplier generates correct prompt."""
        with patch.object(self.client, 'send_message') as mock_send:
            mock_send.return_value = AgenticResponse(
                message="Supplier invitation initiated",
                requires_confirmation=True
            )
            
            self.client._assistant_open = True
            response = self.client.onboard_supplier(
                supplier_name="Acme Corp",
                supplier_email="contact@acme.com",
                purpose="IT consulting services",
                subscribers=["manager@meta.com"]
            )
            
            # Verify the prompt was constructed correctly
            call_args = mock_send.call_args[0][0]
            self.assertIn("Acme Corp", call_args)
            self.assertIn("contact@acme.com", call_args)
            self.assertIn("IT consulting services", call_args)
            self.assertIn("manager@meta.com", call_args)
            self.assertIn("10 business days", call_args)


class TestBuyAtClientAgentic(unittest.TestCase):
    """Test cases for BuyAtClient with agentic flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = BuyAtClient(use_agentic=True)
    
    def test_init_with_agentic(self):
        """Test initialization with agentic flow enabled."""
        self.assertTrue(self.client.use_agentic)
        self.assertIsNotNone(self.client._agentic_client)
    
    def test_init_without_agentic(self):
        """Test initialization with agentic flow disabled."""
        client = BuyAtClient(use_agentic=False)
        self.assertFalse(client.use_agentic)
        self.assertIsNone(client._agentic_client)
    
    def test_invite_supplier_validates_email(self):
        """Test that invite_supplier validates external email."""
        with self.assertRaises(ValueError) as ctx:
            self.client.invite_supplier(
                supplier_name="Test Supplier",
                supplier_email="user@meta.com",  # Internal email
                purpose="Testing"
            )
        self.assertIn("must be external", str(ctx.exception))
    
    def test_invite_supplier_validates_facebook_email(self):
        """Test that invite_supplier rejects @facebook.com emails."""
        with self.assertRaises(ValueError):
            self.client.invite_supplier(
                supplier_name="Test Supplier",
                supplier_email="user@facebook.com",
                purpose="Testing"
            )
    
    @patch('src.buyat.client.AgenticBuyingClient.onboard_supplier')
    def test_invite_supplier_success(self, mock_onboard):
        """Test successful supplier invitation."""
        mock_onboard.return_value = AgenticResponse(
            message="Supplier invitation sent successfully",
            requires_confirmation=False
        )
        
        # Mock the agentic client as already started
        self.client._agentic_client._browser = MagicMock()
        self.client._agentic_client._page = MagicMock()
        
        result = self.client.invite_supplier(
            supplier_name="Acme Corp",
            supplier_email="contact@acme.com",
            purpose="IT services",
            subscribers=["manager@meta.com"]
        )
        
        self.assertIsInstance(result, SupplierInfo)
        self.assertEqual(result.name, "Acme Corp")
        self.assertEqual(result.contact_email, "contact@acme.com")
        self.assertEqual(result.status, "pending_invitation")
        self.assertFalse(result.is_active)
        mock_onboard.assert_called_once()
    
    def test_invite_supplier_requires_agentic(self):
        """Test that invite_supplier requires agentic flow."""
        client = BuyAtClient(use_agentic=False)
        
        with self.assertRaises(BuyAtError) as ctx:
            client.invite_supplier(
                supplier_name="Test",
                supplier_email="test@external.com",
                purpose="Testing"
            )
        self.assertIn("requires agentic flow", str(ctx.exception))
    
    @patch('src.buyat.client.AgenticBuyingClient.check_supplier_status')
    def test_search_via_agentic(self, mock_check):
        """Test supplier search via agentic flow."""
        mock_check.return_value = AgenticResponse(
            message="Supplier Acme Corp exists and is active",
            has_followup=False
        )
        
        # Mock the agentic client as already started
        self.client._agentic_client._browser = MagicMock()
        self.client._agentic_client._page = MagicMock()
        
        result = self.client._search_supplier_via_agentic("Acme Corp")
        
        self.assertIsInstance(result, SupplierInfo)
        self.assertEqual(result.name, "Acme Corp")
        self.assertTrue(result.exists)
        self.assertTrue(result.is_active)
        self.assertEqual(result.status, "active")
    
    @patch('src.buyat.client.AgenticBuyingClient.check_supplier_status')
    def test_search_via_agentic_not_found(self, mock_check):
        """Test supplier search when not found via agentic flow."""
        mock_check.return_value = AgenticResponse(
            message="Supplier XYZ Corp was not found in the system",
            has_followup=False
        )
        
        self.client._agentic_client._browser = MagicMock()
        self.client._agentic_client._page = MagicMock()
        
        with self.assertRaises(SupplierNotFoundError):
            self.client._search_supplier_via_agentic("XYZ Corp")


if __name__ == '__main__':
    unittest.main()
