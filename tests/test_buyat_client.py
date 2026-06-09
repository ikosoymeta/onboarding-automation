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
