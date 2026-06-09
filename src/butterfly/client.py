"""Butterfly Forms API client for programmatic form submission.

This module provides a wrapper around EntButterflyFormResponseMutator for
submitting Butterfly forms programmatically. It implements the two-step
submission pattern: create response + run rules.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ButterflyFormError(Exception):
    """Base exception for Butterfly form operations."""
    pass


class ValidationError(ButterflyFormError):
    """Raised when form data validation fails."""
    pass


class SubmissionError(ButterflyFormError):
    """Raised when form submission fails."""
    pass


class FormStatus(Enum):
    """Status of a form submission."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class FormResponse:
    """Represents a Butterfly form response."""
    form_id: str
    response_id: str
    status: FormStatus
    submitted_at: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


class ButterflyClient:
    """Client for interacting with Butterfly Forms API.
    
    This client wraps EntButterflyFormResponseMutator and provides
    methods for submitting forms programmatically with validation,
    error handling, and retry logic.
    """
    
    # Form IDs from the implementation plan
    FORM_IDS = {
        "supplier_onboarding": "983940998852772",
        "yubikey_request": "1556853164947065",
        "statement_of_work": "362229256183108",
        "csc_program_setup": "3295502980761487",
        "combined_onboarding_tpa": "1125599821621684",
    }
    
    def __init__(self, schema_path: str = "config/form_schemas.json"):
        """Initialize the Butterfly client.
        
        Args:
            schema_path: Path to the form schemas configuration file
        """
        self.schema_path = schema_path
        self.schemas = self._load_schemas()
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
    
    def _load_schemas(self) -> Dict[str, Any]:
        """Load form schemas from configuration file."""
        try:
            with open(self.schema_path, 'r') as f:
                config = json.load(f)
                return config.get("forms", {})
        except FileNotFoundError:
            logger.warning(f"Schema file not found at {self.schema_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema file: {e}")
            raise ValidationError(f"Invalid schema file: {e}")
    
    def _validate_field(self, field_name: str, value: Any, field_schema: Dict[str, Any]) -> List[str]:
        """Validate a single field against its schema.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            field_schema: Schema definition for the field
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        field_type = field_schema.get("type")
        required = field_schema.get("required", False)
        
        # Check required fields
        if required and (value is None or value == ""):
            errors.append(f"Field '{field_name}' is required")
            return errors
        
        # Skip validation for optional empty fields
        if not required and (value is None or value == ""):
            return errors
        
        # Type-specific validation
        if field_type == "email":
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, str(value)):
                errors.append(f"Field '{field_name}' must be a valid email address")
        
        elif field_type == "phone":
            import re
            pattern = r'^\+?[1-9]\d{1,14}$'
            if not re.match(pattern, str(value)):
                errors.append(f"Field '{field_name}' must be a valid phone number")
        
        elif field_type == "url":
            import re
            pattern = r'^https?://.+'
            if not re.match(pattern, str(value)):
                errors.append(f"Field '{field_name}' must be a valid URL")
        
        elif field_type == "currency":
            import re
            pattern = r'^\$?[0-9]+(\.[0-9]{2})?$'
            if not re.match(pattern, str(value)):
                errors.append(f"Field '{field_name}' must be a valid currency amount")
        
        elif field_type == "integer":
            try:
                int(value)
            except (ValueError, TypeError):
                errors.append(f"Field '{field_name}' must be an integer")
        
        # String length validation
        if field_type in ["string", "text", "email"] and isinstance(value, str):
            validation = field_schema.get("validation", {})
            min_length = validation.get("min_length")
            max_length = validation.get("max_length")
            
            if min_length and len(value) < min_length:
                errors.append(f"Field '{field_name}' must be at least {min_length} characters")
            if max_length and len(value) > max_length:
                errors.append(f"Field '{field_name}' must be at most {max_length} characters")
        
        # Integer range validation
        if field_type == "integer":
            validation = field_schema.get("validation", {})
            min_val = validation.get("min")
            max_val = validation.get("max")
            
            try:
                int_val = int(value)
                if min_val is not None and int_val < min_val:
                    errors.append(f"Field '{field_name}' must be at least {min_val}")
                if max_val is not None and int_val > max_val:
                    errors.append(f"Field '{field_name}' must be at most {max_val}")
            except (ValueError, TypeError):
                pass  # Already handled above
        
        return errors
    
    def validate_form_data(self, form_name: str, data: Dict[str, Any]) -> List[str]:
        """Validate form data against schema.
        
        Args:
            form_name: Name of the form (key in schemas)
            data: Form data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if form_name not in self.schemas:
            errors.append(f"Unknown form: {form_name}")
            return errors
        
        form_schema = self.schemas[form_name]
        fields = form_schema.get("fields", {})
        
        # Validate each field in the schema
        for field_name, field_schema in fields.items():
            value = data.get(field_name)
            field_errors = self._validate_field(field_name, value, field_schema)
            errors.extend(field_errors)
        
        return errors
    
    def _create_form_response(self, form_id: str, data: Dict[str, Any]) -> str:
        """Create a form response (step 1 of 2-step submission).
        
        This method wraps EntButterflyFormResponseMutator to create
        a draft form response.
        
        Args:
            form_id: Butterfly form ID
            data: Form field data
            
        Returns:
            Response ID of the created form response
            
        Raises:
            SubmissionError: If creation fails
        """
        # TODO: Implement actual EntButterflyFormResponseMutator call
        # This is a placeholder for the actual implementation
        logger.info(f"Creating form response for form {form_id}")
        
        # Simulate API call
        # In real implementation, this would call:
        # EntButterflyFormResponseMutator::create()
        #   ->setFormID(form_id)
        #   ->setFields(data)
        #   ->save()
        
        response_id = f"resp_{int(time.time())}"
        logger.info(f"Created form response {response_id}")
        return response_id
    
    def _run_form_rules(self, response_id: str) -> bool:
        """Run form rules (step 2 of 2-step submission).
        
        This executes the form's business rules, validations, and
        triggers the submission workflow.
        
        Args:
            response_id: ID of the form response to submit
            
        Returns:
            True if rules executed successfully
            
        Raises:
            SubmissionError: If rule execution fails
        """
        # TODO: Implement actual GraphQLButterflyFormSubmitHandler call
        logger.info(f"Running form rules for response {response_id}")
        
        # Simulate API call
        # In real implementation, this would call:
        # GraphQLButterflyFormSubmitHandler::runRules(response_id)
        
        return True
    
    def submit_form(
        self,
        form_name: str,
        data: Dict[str, Any],
        validate: bool = True,
        dry_run: bool = False
    ) -> FormResponse:
        """Submit a Butterfly form.
        
        Implements the two-step submission pattern:
        1. Create form response with EntButterflyFormResponseMutator
        2. Run rules with GraphQLButterflyFormSubmitHandler
        
        Args:
            form_name: Name of the form (from FORM_IDS or schema)
            data: Form field data
            validate: Whether to validate data before submission
            dry_run: If True, validate only without submitting
            
        Returns:
            FormResponse object with submission details
            
        Raises:
            ValidationError: If validation fails
            SubmissionError: If submission fails after retries
        """
        # Get form ID
        form_id = self.FORM_IDS.get(form_name)
        if not form_id:
            # Try to get from schema
            if form_name in self.schemas:
                form_id = self.schemas[form_name].get("form_id")
        
        if not form_id:
            raise ValidationError(f"Unknown form: {form_name}")
        
        # Validate data
        if validate:
            errors = self.validate_form_data(form_name, data)
            if errors:
                raise ValidationError(f"Validation failed: {'; '.join(errors)}")
        
        if dry_run:
            logger.info(f"Dry run: Form {form_name} validation passed")
            return FormResponse(
                form_id=form_id,
                response_id="dry_run",
                status=FormStatus.DRAFT,
                data=data
            )
        
        # Submit with retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Step 1: Create form response
                response_id = self._create_form_response(form_id, data)
                
                # Step 2: Run form rules
                success = self._run_form_rules(response_id)
                
                if success:
                    logger.info(f"Successfully submitted form {form_name} (response {response_id})")
                    return FormResponse(
                        form_id=form_id,
                        response_id=response_id,
                        status=FormStatus.SUBMITTED,
                        data=data
                    )
                else:
                    raise SubmissionError("Form rules execution failed")
            
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries exhausted
        error_msg = f"Failed to submit form after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise SubmissionError(error_msg)
    
    def get_form_status(self, response_id: str) -> FormResponse:
        """Get the status of a form submission.
        
        Args:
            response_id: ID of the form response
            
        Returns:
            FormResponse with current status
        """
        # TODO: Implement actual status check via Butterfly API
        logger.info(f"Checking status for response {response_id}")
        
        # Placeholder implementation
        return FormResponse(
            form_id="unknown",
            response_id=response_id,
            status=FormStatus.SUBMITTED
        )
    
    def submit_supplier_onboarding(self, data: Dict[str, Any], **kwargs) -> FormResponse:
        """Submit Supplier Onboarding Request form."""
        return self.submit_form("supplier_onboarding", data, **kwargs)
    
    def submit_yubikey_request(self, data: Dict[str, Any], **kwargs) -> FormResponse:
        """Submit YubiKey Request form."""
        return self.submit_form("yubikey_request", data, **kwargs)
    
    def submit_statement_of_work(self, data: Dict[str, Any], **kwargs) -> FormResponse:
        """Submit Statement of Work form."""
        return self.submit_form("statement_of_work", data, **kwargs)
    
    def submit_csc_program_setup(self, data: Dict[str, Any], **kwargs) -> FormResponse:
        """Submit CSC New Outsourced Program Setup form."""
        return self.submit_form("csc_program_setup", data, **kwargs)
    
    def submit_combined_onboarding_tpa(self, data: Dict[str, Any], **kwargs) -> FormResponse:
        """Submit Combined Supplier Onboarding + TPA form."""
        return self.submit_form("combined_onboarding_tpa", data, **kwargs)
