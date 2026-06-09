"""TPA API client for Third Party Assessment automation.

Provides programmatic access to TPA system for initiating and tracking
vendor security assessments.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class TPAError(Exception):
    """Base exception for TPA operations."""
    pass


class AssessmentNotFoundError(TPAError):
    """Raised when assessment is not found."""
    pass


class AssessmentStatus(Enum):
    """Status of a TPA assessment."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_INFO = "needs_info"


@dataclass
class AssessmentResult:
    """Result of a TPA assessment."""
    assessment_id: str
    status: AssessmentStatus
    vendor_name: str
    risk_level: Optional[str] = None
    findings: List[str] = None
    recommendations: List[str] = None
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if self.findings is None:
            self.findings = []
        if self.recommendations is None:
            self.recommendations = []


class TPAClient:
    """Client for interacting with TPA API.
    
    Automates Third Party Assessment submissions and tracks their status.
    """
    
    def __init__(self, base_url: str = "https://www.internalfb.com/tpa/api"):
        """Initialize TPA client.
        
        Args:
            base_url: Base URL for TPA API
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.max_retries = 3
        self.retry_delay = 2.0
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to TPA API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            JSON response as dictionary
            
        Raises:
            TPAError: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise TPAError(f"API request failed after {self.max_retries} attempts: {e}")
    
    def submit_assessment(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a new TPA assessment.
        
        Args:
            assessment_data: Assessment details including:
                - vendor_name: Name of the vendor
                - data_access_level: Level of data access (Public, Internal, Confidential, Highly Confidential)
                - systems: List of systems vendor will access
                - handles_pii: Whether vendor handles PII
                - handles_financial_data: Whether vendor handles financial data
                - security_questionnaire: Completed questionnaire data
                
        Returns:
            Dictionary with assessment_id and status
            
        Raises:
            TPAError: If submission fails
        """
        logger.info(f"Submitting TPA assessment for vendor: {assessment_data.get('vendor_name')}")
        
        try:
            response = self._make_request(
                "POST",
                "/assessments",
                json=assessment_data,
                headers={"Content-Type": "application/json"}
            )
            
            assessment_id = response.get("assessment_id")
            status = response.get("status", "submitted")
            
            logger.info(f"TPA assessment submitted: {assessment_id}")
            
            return {
                "assessment_id": assessment_id,
                "status": AssessmentStatus(status),
                "vendor_name": assessment_data.get("vendor_name")
            }
            
        except Exception as e:
            logger.error(f"Failed to submit TPA assessment: {e}")
            raise TPAError(f"Assessment submission failed: {e}")
    
    def get_assessment_status(self, assessment_id: str) -> AssessmentResult:
        """Get the status of a TPA assessment.
        
        Args:
            assessment_id: ID of the assessment to check
            
        Returns:
            AssessmentResult with current status and details
            
        Raises:
            AssessmentNotFoundError: If assessment not found
            TPAError: If status check fails
        """
        logger.info(f"Checking status for assessment: {assessment_id}")
        
        try:
            response = self._make_request(
                "GET",
                f"/assessments/{assessment_id}"
            )
            
            status = AssessmentStatus(response.get("status", "draft"))
            
            return AssessmentResult(
                assessment_id=assessment_id,
                status=status,
                vendor_name=response.get("vendor_name", ""),
                risk_level=response.get("risk_level"),
                findings=response.get("findings", []),
                recommendations=response.get("recommendations", []),
                completed_at=response.get("completed_at")
            )
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise AssessmentNotFoundError(f"Assessment {assessment_id} not found")
            raise TPAError(f"Failed to get assessment status: {e}")
    
    def poll_assessment_completion(
        self,
        assessment_id: str,
        timeout: int = 3600,
        poll_interval: int = 60
    ) -> AssessmentResult:
        """Poll TPA assessment until completion or timeout.
        
        Args:
            assessment_id: ID of the assessment to poll
            timeout: Maximum time to wait in seconds (default: 1 hour)
            poll_interval: Time between polls in seconds (default: 1 minute)
            
        Returns:
            Final AssessmentResult
            
        Raises:
            TPAError: If timeout reached or polling fails
        """
        logger.info(f"Polling assessment {assessment_id} for completion (timeout: {timeout}s)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.get_assessment_status(assessment_id)
            
            if result.status in [AssessmentStatus.APPROVED, AssessmentStatus.REJECTED]:
                logger.info(f"Assessment {assessment_id} completed with status: {result.status.value}")
                return result
            
            logger.debug(f"Assessment {assessment_id} still in progress: {result.status.value}")
            time.sleep(poll_interval)
        
        raise TPAError(f"Assessment {assessment_id} did not complete within {timeout} seconds")
    
    def submit_questionnaire(
        self,
        assessment_id: str,
        questionnaire_data: Dict[str, Any]
    ) -> bool:
        """Submit risk assessment questionnaire for an existing assessment.
        
        Args:
            assessment_id: ID of the assessment
            questionnaire_data: Questionnaire responses
            
        Returns:
            True if submission successful
            
        Raises:
            TPAError: If submission fails
        """
        logger.info(f"Submitting questionnaire for assessment: {assessment_id}")
        
        try:
            self._make_request(
                "POST",
                f"/assessments/{assessment_id}/questionnaire",
                json=questionnaire_data,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Questionnaire submitted for assessment {assessment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit questionnaire: {e}")
            raise TPAError(f"Questionnaire submission failed: {e}")
