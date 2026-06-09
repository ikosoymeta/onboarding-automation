"""Unit tests for intake CLI."""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.intake.cli import IntakeCLI


class TestIntakeCLI(unittest.TestCase):
    """Test cases for IntakeCLI."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary schema file
        self.schema_data = {
            "forms": {
                "supplier_onboarding_request": {
                    "form_id": "123",
                    "fields": {
                        "supplier_name": {"type": "string", "required": True},
                        "supplier_contact_email": {"type": "email", "required": True}
                    }
                }
            }
        }
        
        self.temp_schema = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(self.schema_data, self.temp_schema)
        self.temp_schema.close()
        
        self.cli = IntakeCLI(schema_path=self.temp_schema.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_schema.name)
    
    def test_load_from_file(self):
        """Test loading data from JSON file."""
        test_data = {
            "supplier": {
                "supplier_name": "Test Vendor",
                "supplier_contact_email": "test@example.com"
            }
        }
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(test_data, temp_file)
        temp_file.close()
        
        try:
            data = self.cli.load_from_file(temp_file.name)
            self.assertEqual(data["supplier"]["supplier_name"], "Test Vendor")
        finally:
            os.unlink(temp_file.name)
    
    def test_save_to_file(self):
        """Test saving data to JSON file."""
        self.cli.data = {
            "supplier": {
                "supplier_name": "Test Vendor"
            }
        }
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.close()
        
        try:
            self.cli.save_to_file(temp_file.name)
            
            with open(temp_file.name, 'r') as f:
                data = json.load(f)
            
            self.assertEqual(data["supplier"]["supplier_name"], "Test Vendor")
        finally:
            os.unlink(temp_file.name)
    
    def test_validate_valid_data(self):
        """Test validation with valid data."""
        self.cli.data = {
            "supplier": {
                "supplier_name": "Test Vendor",
                "supplier_contact_email": "test@example.com"
            }
        }
        
        errors = self.cli.validate()
        self.assertEqual(len(errors), 0)
    
    def test_validate_invalid_data(self):
        """Test validation with invalid data."""
        self.cli.data = {
            "supplier": {
                "supplier_name": "",  # Required but empty
                "supplier_contact_email": "invalid-email"  # Invalid format
            }
        }
        
        errors = self.cli.validate()
        self.assertGreater(len(errors), 0)
    
    @patch('builtins.input')
    def test_prompt(self, mock_input):
        """Test prompt for user input."""
        mock_input.return_value = "Test Value"
        result = self.cli._prompt("Enter value")
        self.assertEqual(result, "Test Value")
    
    @patch('builtins.input')
    def test_prompt_with_default(self, mock_input):
        """Test prompt with default value."""
        mock_input.return_value = ""
        result = self.cli._prompt("Enter value", default="Default")
        self.assertEqual(result, "Default")
    
    @patch('builtins.input')
    def test_prompt_required(self, mock_input):
        """Test prompt for required field."""
        # First empty, then valid
        mock_input.side_effect = ["", "Valid Value"]
        result = self.cli._prompt("Enter value", required=True)
        self.assertEqual(result, "Valid Value")
    
    @patch('builtins.input')
    def test_prompt_choice(self, mock_input):
        """Test prompt for choice selection."""
        mock_input.return_value = "2"
        choices = ["Option 1", "Option 2", "Option 3"]
        result = self.cli._prompt_choice("Choose", choices)
        self.assertEqual(result, "Option 2")
    
    @patch('builtins.input')
    def test_prompt_yes_no_yes(self, mock_input):
        """Test yes/no prompt with yes answer."""
        mock_input.return_value = "y"
        result = self.cli._prompt_yes_no("Continue?")
        self.assertTrue(result)
    
    @patch('builtins.input')
    def test_prompt_yes_no_no(self, mock_input):
        """Test yes/no prompt with no answer."""
        mock_input.return_value = "n"
        result = self.cli._prompt_yes_no("Continue?")
        self.assertFalse(result)
    
    @patch('builtins.input')
    def test_prompt_yes_no_default(self, mock_input):
        """Test yes/no prompt with default."""
        mock_input.return_value = ""
        result = self.cli._prompt_yes_no("Continue?", default=True)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
