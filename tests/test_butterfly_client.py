"""Unit tests for Butterfly Forms API client."""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.butterfly.client import (
    ButterflyClient,
    ButterflyFormError,
    ValidationError,
    SubmissionError,
    FormStatus,
    FormResponse
)


class TestButterflyClient(unittest.TestCase):
    """Test cases for ButterflyClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary schema file for testing
        self.schema_data = {
            "forms": {
                "test_form": {
                    "form_id": "123456",
                    "name": "Test Form",
                    "fields": {
                        "name": {
                            "type": "string",
                            "required": True,
                            "validation": {
                                "min_length": 1,
                                "max_length": 100
                            }
                        },
                        "email": {
                            "type": "email",
                            "required": True
                        },
                        "age": {
                            "type": "integer",
                            "required": False,
                            "validation": {
                                "min": 0,
                                "max": 120
                            }
                        }
                    }
                }
            }
        }
        
        self.temp_schema = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(self.schema_data, self.temp_schema)
        self.temp_schema.close()
        
        self.client = ButterflyClient(schema_path=self.temp_schema.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_schema.name)
    
    def test_load_schemas(self):
        """Test loading schemas from file."""
        self.assertIn("test_form", self.client.schemas)
        self.assertEqual(self.client.schemas["test_form"]["form_id"], "123456")
    
    def test_validate_field_required(self):
        """Test validation of required fields."""
        field_schema = {"type": "string", "required": True}
        
        # Empty value should fail
        errors = self.client._validate_field("name", "", field_schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("required", errors[0])
        
        # None value should fail
        errors = self.client._validate_field("name", None, field_schema)
        self.assertEqual(len(errors), 1)
        
        # Valid value should pass
        errors = self.client._validate_field("name", "John", field_schema)
        self.assertEqual(len(errors), 0)
    
    def test_validate_field_email(self):
        """Test email field validation."""
        field_schema = {"type": "email", "required": True}
        
        # Valid email
        errors = self.client._validate_field("email", "test@example.com", field_schema)
        self.assertEqual(len(errors), 0)
        
        # Invalid email
        errors = self.client._validate_field("email", "invalid-email", field_schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("email", errors[0].lower())
    
    def test_validate_field_string_length(self):
        """Test string length validation."""
        field_schema = {
            "type": "string",
            "required": True,
            "validation": {"min_length": 3, "max_length": 10}
        }
        
        # Too short
        errors = self.client._validate_field("name", "ab", field_schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("at least 3", errors[0])
        
        # Too long
        errors = self.client._validate_field("name", "a" * 11, field_schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("at most 10", errors[0])
        
        # Valid length
        errors = self.client._validate_field("name", "valid", field_schema)
        self.assertEqual(len(errors), 0)
    
    def test_validate_field_integer_range(self):
        """Test integer range validation."""
        field_schema = {
            "type": "integer",
            "required": True,
            "validation": {"min": 0, "max": 100}
        }
        
        # Too low
        errors = self.client._validate_field("age", -1, field_schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("at least 0", errors[0])
        
        # Too high
        errors = self.client._validate_field("age", 101, field_schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("at most 100", errors[0])
        
        # Valid
        errors = self.client._validate_field("age", 50, field_schema)
        self.assertEqual(len(errors), 0)
    
    def test_validate_form_data_valid(self):
        """Test validation of valid form data."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
        
        errors = self.client.validate_form_data("test_form", data)
        self.assertEqual(len(errors), 0)
    
    def test_validate_form_data_invalid(self):
        """Test validation of invalid form data."""
        data = {
            "name": "",  # Required but empty
            "email": "invalid-email",  # Invalid format
            "age": 150  # Out of range
        }
        
        errors = self.client.validate_form_data("test_form", data)
        self.assertEqual(len(errors), 3)
    
    def test_validate_form_data_unknown_form(self):
        """Test validation with unknown form name."""
        errors = self.client.validate_form_data("unknown_form", {})
        self.assertEqual(len(errors), 1)
        self.assertIn("Unknown form", errors[0])
    
    @patch.object(ButterflyClient, '_create_form_response')
    @patch.object(ButterflyClient, '_run_form_rules')
    def test_submit_form_success(self, mock_run_rules, mock_create):
        """Test successful form submission."""
        mock_create.return_value = "resp_123"
        mock_run_rules.return_value = True
        
        data = {
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        response = self.client.submit_form("test_form", data)
        
        self.assertEqual(response.form_id, "123456")
        self.assertEqual(response.response_id, "resp_123")
        self.assertEqual(response.status, FormStatus.SUBMITTED)
        mock_create.assert_called_once()
        mock_run_rules.assert_called_once_with("resp_123")
    
    @patch.object(ButterflyClient, '_create_form_response')
    @patch.object(ButterflyClient, '_run_form_rules')
    def test_submit_form_dry_run(self, mock_run_rules, mock_create):
        """Test dry run mode (validation only)."""
        data = {
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        response = self.client.submit_form("test_form", data, dry_run=True)
        
        self.assertEqual(response.response_id, "dry_run")
        self.assertEqual(response.status, FormStatus.DRAFT)
        mock_create.assert_not_called()
        mock_run_rules.assert_not_called()
    
    def test_submit_form_validation_failure(self):
        """Test form submission with validation errors."""
        data = {
            "name": "",  # Invalid
            "email": "invalid"  # Invalid
        }
        
        with self.assertRaises(ValidationError) as context:
            self.client.submit_form("test_form", data)
        
        self.assertIn("Validation failed", str(context.exception))
    
    @patch.object(ButterflyClient, '_create_form_response')
    def test_submit_form_retry_logic(self, mock_create):
        """Test retry logic on submission failure."""
        # Fail twice, succeed on third attempt
        mock_create.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            "resp_123"
        ]
        
        with patch.object(self.client, '_run_form_rules', return_value=True):
            data = {"name": "John", "email": "john@example.com"}
            response = self.client.submit_form("test_form", data)
            
            self.assertEqual(response.response_id, "resp_123")
            self.assertEqual(mock_create.call_count, 3)
    
    @patch.object(ButterflyClient, '_create_form_response')
    def test_submit_form_max_retries_exceeded(self, mock_create):
        """Test failure after max retries exceeded."""
        mock_create.side_effect = Exception("Persistent error")
        
        data = {"name": "John", "email": "john@example.com"}
        
        with self.assertRaises(SubmissionError) as context:
            self.client.submit_form("test_form", data)
        
        self.assertIn("Failed to submit form after", str(context.exception))
        self.assertEqual(mock_create.call_count, 3)


if __name__ == '__main__':
    unittest.main()
