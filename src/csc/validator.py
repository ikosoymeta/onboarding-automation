"""CSC data validator for worker information.

Validates worker data against CSC requirements before submission.
Provides user-friendly error messages with clear instructions on how to fix issues.
"""

import re
import logging
from typing import List, Dict
from datetime import datetime

from .automation import WorkerInfo

logger = logging.getLogger(__name__)


class CSCDataValidator:
    """Validates worker data for CSC onboarding.
    
    Provides clear, actionable validation messages to help users
    correct data issues before submission.
    """
    
    # CSC-specific validation rules
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    DATE_FORMAT = "%Y-%m-%d"
    VALID_LOCATIONS = ["Remote", "Onsite", "Hybrid"]
    
    def __init__(self):
        """Initialize validator."""
        pass
    
    def validate_worker(self, worker: WorkerInfo) -> List[str]:
        """Validate a single worker's information.
        
        Returns user-friendly error messages with specific instructions
        on how to fix each issue.
        
        Args:
            worker: Worker information to validate
            
        Returns:
            List of validation error messages (empty if valid).
            Each message includes what is wrong and how to fix it.
        """
        errors = []
        
        # Validate full name
        if not worker.full_name or not worker.full_name.strip():
            errors.append(
                "Full Name is required. Please enter the worker's full legal name "
                "(e.g., 'John Doe')."
            )
        elif len(worker.full_name) > 100:
            errors.append(
                f"Full Name '{worker.full_name}' is too long ({len(worker.full_name)} characters). "
                f"Must be 100 characters or less."
            )
        
        # Validate email
        if not worker.email:
            errors.append(
                "Email Address is required. Please enter a valid email address "
                "(e.g., worker@company.com)."
            )
        elif not re.match(self.EMAIL_PATTERN, worker.email):
            errors.append(
                f"Email Address '{worker.email}' is invalid. "
                f"Please enter a valid email format (e.g., worker@company.com)."
            )
        
        # Validate dates
        try:
            start_date = datetime.strptime(worker.start_date, self.DATE_FORMAT)
        except ValueError:
            errors.append(
                f"Start Date '{worker.start_date}' is invalid. "
                f"Please use YYYY-MM-DD format (e.g., 2024-04-01)."
            )
            start_date = None
        
        try:
            end_date = datetime.strptime(worker.end_date, self.DATE_FORMAT)
        except ValueError:
            errors.append(
                f"End Date '{worker.end_date}' is invalid. "
                f"Please use YYYY-MM-DD format (e.g., 2025-04-01)."
            )
            end_date = None
        
        if start_date and end_date and start_date >= end_date:
            errors.append(
                f"End Date ({worker.end_date}) must be after Start Date ({worker.start_date}). "
                f"Please ensure the contract end date is later than the start date."
            )
        
        # Validate job title
        if not worker.job_title or not worker.job_title.strip():
            errors.append(
                "Job Title is required. Please enter the worker's job title or role "
                "(e.g., 'Software Engineer', 'Product Designer')."
            )
        
        # Validate manager email
        if not worker.manager_email:
            errors.append(
                "Manager Email is required. Please enter the Meta manager's email address."
            )
        elif not re.match(self.EMAIL_PATTERN, worker.manager_email):
            errors.append(
                f"Manager Email '{worker.manager_email}' is invalid. "
                f"Please enter a valid Meta email address."
            )
        
        # Validate work location
        if worker.work_location not in self.VALID_LOCATIONS:
            errors.append(
                f"Work Location '{worker.work_location}' is invalid. "
                f"Must be exactly one of: {', '.join(self.VALID_LOCATIONS)} "
                f"(case-sensitive)."
            )
        
        # Validate office location for onsite/hybrid
        if worker.work_location in ["Onsite", "Hybrid"]:
            if not worker.office_location or not worker.office_location.strip():
                errors.append(
                    f"Office Location is required for {worker.work_location} workers. "
                    f"Please specify the Meta office location (e.g., 'Menlo Park', 'New York')."
                )
        
        # Validate phone (if provided)
        if worker.phone:
            # Simple phone validation - at least 10 digits
            digits = re.sub(r'\D', '', worker.phone)
            if len(digits) < 10:
                errors.append(
                    f"Phone Number '{worker.phone}' is invalid. "
                    f"Must contain at least 10 digits. Include country code if outside US "
                    f"(e.g., +1-555-0123)."
                )
        
        return errors
    
    def validate_workers(self, workers: List[WorkerInfo]) -> Dict[int, List[str]]:
        """Validate multiple workers.
        
        Args:
            workers: List of workers to validate
            
        Returns:
            Dictionary mapping worker index (0-based) to list of errors.
            Empty dict means all workers are valid.
        """
        results = {}
        for idx, worker in enumerate(workers):
            errors = self.validate_worker(worker)
            if errors:
                results[idx] = errors
        return results
