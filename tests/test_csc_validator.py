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
