import unittest
from unittest.mock import MagicMock, patch
from src.tpa.client import TPAClient, TPAError, AssessmentStatus


class TestTPAClient(unittest.TestCase):
    """Test cases for TPAClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = TPAClient()
    
    def test_initialization(self):
        """Test TPA client initializes correctly."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.base_url, "https://www.internalfb.com/tpa/api")
    
    def test_submit_assessment(self):
        """Test submitting TPA assessment."""
        assessment_data = {
            "vendor_name": "Acme Corp",
            "data_access_level": "Internal",
            "systems": ["System A", "System B"],
            "handles_pii": False
        }
        
        with patch.object(self.client, '_make_request') as mock_request:
            mock_request.return_value = {
                "assessment_id": "TPA-2024-001",
                "status": "submitted"
            }
            
            result = self.client.submit_assessment(assessment_data)
            self.assertEqual(result["assessment_id"], "TPA-2024-001")
            self.assertEqual(result["status"], AssessmentStatus.SUBMITTED)
