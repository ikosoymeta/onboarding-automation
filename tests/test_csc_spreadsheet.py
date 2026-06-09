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
