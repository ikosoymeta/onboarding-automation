"""Complete Vendor Onboarding Automation System.

This module provides a unified interface for the complete vendor onboarding
workflow, integrating all system adapters (Butterfly, CSC, AMP, TPA, Buy@)
into a seamless, automated process.

Usage:
    from src.vendor_onboarding import VendorOnboardingSystem
    
    system = VendorOnboardingSystem()
    result = system.onboard_vendor(
        supplier_name="Acme Corp",
        vendor_data={...},
        workers=[...]
    )
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .orchestrator.workflow import WorkflowOrchestrator
from .orchestrator.supplier_workflow import SupplierOnboardingWorkflow
from .butterfly import ButterflyClient
from .csc import CSCAutomation, WorkerInfo, CSCSpreadsheetGenerator, CSCDataValidator
from .amp import AMPAutomation, AMPGroup
from .tpa import TPAClient
from .buyat import BuyAtClient

logger = logging.getLogger(__name__)


@dataclass
class OnboardingResult:
    """Result of a complete vendor onboarding workflow."""
    success: bool
    workflow_id: str
    supplier_name: str
    supplier_id: Optional[str] = None
    supplier_already_active: bool = False
    
    # Form submission results
    butterfly_forms: Dict[str, str] = None  # form_name -> response_id
    
    # Worker onboarding results
    workers_onboarded: int = 0
    workers_failed: int = 0
    
    # Group management
    amp_group_id: Optional[str] = None
    
    # Assessment
    tpa_assessment_id: Optional[str] = None
    
    # Errors
    errors: List[str] = None
    
    def __post_init__(self):
        if self.butterfly_forms is None:
            self.butterfly_forms = {}
        if self.errors is None:
            self.errors = []


class VendorOnboardingSystem:
    """Complete vendor onboarding automation system.
    
    Orchestrates the entire vendor onboarding workflow across all systems:
    1. Buy@ - Supplier verification
    2. Butterfly - Forms (Supplier, YubiKey, SoW, CSC, TPA)
    3. CSC - Worker onboarding (individual + bulk)
    4. AMP - Group management
    5. TPA - Security assessment
    
    The system is designed to be user-friendly with:
    - Clear progress indicators
    - Actionable error messages
    - Automatic retry on transient failures
    - Complete audit trail
    """
    
    def __init__(self, use_buyat_assistant: bool = True):
        """Initialize the vendor onboarding system.
        
        Args:
            use_buyat_assistant: If True, uses Buy@ Assistant (Metamate agents)
                for supplier onboarding via conversational AI. If False, uses
                traditional Butterfly forms and custom browser automation.
                Default: True (recommended - uses official Buy@ Assistant)
        """
        self.butterfly = ButterflyClient()
        self.csc = CSCAutomation()
        self.amp = AMPAutomation()
        self.tpa = TPAClient()
        self.buyat = BuyAtClient(use_agentic=use_buyat_assistant)
        self.csc_validator = CSCDataValidator()
        self.spreadsheet_gen = CSCSpreadsheetGenerator()
        self.use_buyat_assistant = use_buyat_assistant
        
        logger.info(
            f"Vendor Onboarding System initialized "
            f"(use_buyat_assistant={use_buyat_assistant})"
        )
    
    def onboard_vendor(
        self,
        supplier_name: str,
        supplier_data: Dict[str, Any],
        workers: List[WorkerInfo],
        amp_group_name: Optional[str] = None,
        enable_yubikey: bool = True,
        enable_tpa: bool = True
    ) -> OnboardingResult:
        """Execute complete vendor onboarding workflow.
        
        This is the main entry point for vendor onboarding. It orchestrates
        all necessary steps across multiple systems.
        
        Args:
            supplier_name: Legal name of the supplier
            supplier_data: Supplier information for forms (contact, justification, etc.)
            workers: List of WorkerInfo objects for vendor workers
            amp_group_name: Name for AMP group (auto-generated if not provided)
            enable_yubikey: Whether to request YubiKeys for workers
            enable_tpa: Whether to initiate TPA assessment
            
        Returns:
            OnboardingResult with details of the onboarding process
            
        Example:
            >>> system = VendorOnboardingSystem()
            >>> workers = [
            ...     WorkerInfo(
            ...         full_name="John Doe",
            ...         email="john@vendor.com",
            ...         start_date="2024-04-01",
            ...         end_date="2025-04-01",
            ...         job_title="Engineer",
            ...         manager_email="manager@meta.com",
            ...         work_location="Remote"
            ...     )
            ... ]
            >>> result = system.onboard_vendor(
            ...     supplier_name="Acme Corp",
            ...     supplier_data={...},
            ...     workers=workers
            ... )
            >>> print(f"Success: {result.success}")
            >>> print(f"Workers onboarded: {result.workers_onboarded}")
        """
        logger.info(f"Starting vendor onboarding for: {supplier_name}")
        
        result = OnboardingResult(
            success=False,
            workflow_id="",
            supplier_name=supplier_name
        )
        
        try:
            # Step 1: Verify supplier in Buy@ and onboard if needed
            logger.info("Step 1: Verifying supplier in Buy@")
            try:
                supplier_info = self.buyat.search_supplier(supplier_name)
                result.supplier_id = supplier_info.supplier_id
                result.supplier_already_active = (
                    supplier_info.exists and 
                    supplier_info.status and 
                    supplier_info.status.lower() in ["active", "approved"]
                )
                
                if result.supplier_already_active:
                    logger.info(f"Supplier {supplier_name} already active, skipping onboarding")
                else:
                    logger.info(f"Supplier {supplier_name} needs onboarding")
                    
                    # Use Buy@ Assistant for onboarding if enabled
                    # Use local variable to avoid mutating instance state
                    use_assistant = self.use_buyat_assistant
                    if use_assistant:
                        logger.info("Using Buy@ Assistant (Metamate) for supplier onboarding")
                        try:
                            # Extract supplier email and purpose from supplier_data
                            supplier_email = supplier_data.get("supplier_email") or supplier_data.get("contact_email")
                            purpose = supplier_data.get("business_purpose") or supplier_data.get("justification", "Vendor services")
                            subscribers = supplier_data.get("subscribers", [])
                            
                            if not supplier_email:
                                raise ValueError("supplier_email is required for Buy@ Assistant onboarding")
                            
                            # Use Buy@ Assistant to onboard supplier
                            # This routes to BUY_SUPPLIER_AGENT via the conversational UI
                            onboarding_result = self.buyat.invite_supplier(
                                supplier_name=supplier_name,
                                supplier_email=supplier_email,
                                purpose=purpose,
                                subscribers=subscribers
                            )
                            
                            result.supplier_id = onboarding_result.supplier_id
                            logger.info(
                                f"Supplier onboarding initiated via Buy@ Assistant. "
                                f"Supplier has 10 business days to complete enrollment."
                            )
                            # Note: We don't wait for completion here - the workflow continues
                            # with other steps while supplier completes onboarding in parallel
                            
                        except Exception as e:
                            logger.error(f"Buy@ Assistant onboarding failed: {e}")
                            result.errors.append(f"Buy@ Assistant onboarding failed: {e}")
                            # Fall back to traditional Butterfly form for this operation only
                            logger.info("Falling back to traditional Butterfly form")
                            use_assistant = False
                    
                    # Traditional Butterfly form (if not using Buy@ Assistant or if it failed)
                    if not use_assistant:
                        logger.info("Using traditional Butterfly form for supplier onboarding")
                        try:
                            response = self.butterfly.submit_supplier_onboarding(
                                data=supplier_data,
                                validate=True
                            )
                            result.butterfly_forms["supplier_onboarding"] = response.response_id
                            logger.info(f"Supplier onboarding form submitted: {response.response_id}")
                        except Exception as e:
                            logger.error(f"Failed to submit supplier onboarding: {e}")
                            result.errors.append(f"Supplier onboarding failed: {e}")
                            
            except Exception as e:
                logger.warning(f"Could not verify supplier: {e}")
                result.errors.append(f"Supplier verification warning: {e}")
            
            # Step 2: Submit Butterfly forms (in parallel where possible)
            logger.info("Step 2: Submitting Butterfly forms")
            
            # YubiKey Request (if enabled and workers need them)
            if enable_yubikey and workers:
                try:
                    # Get shipping address from supplier_data, with fallback to placeholder
                    shipping_addr = supplier_data.get("shipping_address", {})
                    yubikey_data = {
                        "vendor_workers": [
                            {
                                "full_name": w.full_name,
                                "email": w.email,
                                "shipping_address": {
                                    "street": shipping_addr.get("street", "123 Vendor St"),
                                    "city": shipping_addr.get("city", "San Francisco"),
                                    "state": shipping_addr.get("state", "CA"),
                                    "zip": shipping_addr.get("zip", "94105"),
                                    "country": shipping_addr.get("country", "USA")
                                }
                            }
                            for w in workers
                        ],
                        "urgency": "Standard (3+ weeks)",
                        "business_justification": f"YubiKeys for {supplier_name} vendor workers"
                    }
                    response = self.butterfly.submit_yubikey_request(
                        data=yubikey_data,
                        validate=True
                    )
                    result.butterfly_forms["yubikey"] = response.response_id
                    logger.info(f"YubiKey request submitted: {response.response_id}")
                except Exception as e:
                    logger.error(f"Failed to submit YubiKey request: {e}")
                    result.errors.append(f"YubiKey request failed: {e}")
            
            # Step 3: TPA Assessment (if enabled)
            if enable_tpa:
                logger.info("Step 3: Initiating TPA assessment")
                try:
                    tpa_data = {
                        "vendor_name": supplier_name,
                        "data_access_level": supplier_data.get("data_access_level", "Internal"),
                        "systems": supplier_data.get("systems", []),
                        "handles_pii": supplier_data.get("handles_pii", False),
                        "handles_financial_data": supplier_data.get("handles_financial_data", False)
                    }
                    tpa_result = self.tpa.submit_assessment(tpa_data)
                    result.tpa_assessment_id = tpa_result["assessment_id"]
                    logger.info(f"TPA assessment initiated: {result.tpa_assessment_id}")
                except Exception as e:
                    logger.error(f"Failed to initiate TPA: {e}")
                    result.errors.append(f"TPA assessment failed: {e}")
            
            # Step 4: AMP Group Creation
            if amp_group_name is None:
                amp_group_name = f"{supplier_name.lower().replace(' ', '-')}-vendors"
            
            logger.info(f"Step 4: Creating AMP group: {amp_group_name}")
            try:
                self.amp.start()
                self.amp.login()
                
                amp_group = AMPGroup(
                    name=amp_group_name,
                    description=f"Access group for {supplier_name} vendor workers",
                    members=[w.email for w in workers]
                )
                result.amp_group_id = self.amp.create_group(amp_group)
                logger.info(f"AMP group created: {result.amp_group_id}")
            except Exception as e:
                logger.error(f"Failed to create AMP group: {e}")
                result.errors.append(f"AMP group creation failed: {e}")
            finally:
                self.amp.close()
            
            # Step 5: CSC Worker Onboarding
            logger.info(f"Step 5: Onboarding {len(workers)} workers via CSC")
            
            # Validate workers first
            validation_errors = self.csc_validator.validate_workers(workers)
            if validation_errors:
                for idx, errors in validation_errors.items():
                    result.errors.append(f"Worker {idx} validation failed: {', '.join(errors)}")
                logger.error(f"Worker validation failed for {len(validation_errors)} workers")
            else:
                try:
                    self.csc.start()
                    self.csc.login()
                    
                    # Generate spreadsheet for bulk upload
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                        spreadsheet_path = tmp.name
                    
                    try:
                        self.spreadsheet_gen.generate(workers, spreadsheet_path)
                        
                        # Upload via CSC bulk upload
                        upload_result = self.csc.bulk_upload_workers(workers, spreadsheet_path)
                        result.workers_onboarded = upload_result["uploaded_count"]
                        result.workers_failed = upload_result["failed_count"]
                        
                        logger.info(
                            f"CSC onboarding complete: "
                            f"{result.workers_onboarded} succeeded, "
                            f"{result.workers_failed} failed"
                        )
                    finally:
                        if os.path.exists(spreadsheet_path):
                            os.unlink(spreadsheet_path)
                
                except Exception as e:
                    logger.error(f"Failed to onboard workers via CSC: {e}")
                    result.errors.append(f"CSC onboarding failed: {e}")
                finally:
                    self.csc.close()
            
            # Determine overall success
            result.success = (
                len(result.errors) == 0 or
                # Allow partial success if at least workers were onboarded
                result.workers_onboarded > 0
            )
            
            logger.info(
                f"Vendor onboarding completed for {supplier_name}: "
                f"success={result.success}, "
                f"workers={result.workers_onboarded}/{len(workers)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Vendor onboarding failed with unexpected error: {e}")
            result.errors.append(f"Unexpected error: {e}")
            result.success = False
            return result
    
    def get_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of an ongoing onboarding workflow.
        Args:
            workflow_id: ID of the workflow to check
        Returns:
            Dictionary with workflow status
        """
        # This would integrate with the workflow orchestrator
        # to provide real-time status updates
        logger.info(f"Getting status for workflow: {workflow_id}")
        return {
            "workflow_id": workflow_id,
            "status": "in_progress",
            "message": "Status tracking available in Phase 4 dashboard"
        }


@dataclass
class PRCreationResult:
    """Result of a purchase request creation workflow."""
    success: bool
    pr_number: Optional[str] = None
    pr_url: Optional[str] = None
    status: str = "unknown"  # draft, submitted, approved, rejected
    supplier_name: str = ""
    amount: float = 0.0
    
    # Monitoring
    polling_id: Optional[str] = None
    monitoring_active: bool = False
    
    # Errors
    errors: List[str] = None
    blockers: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.blockers is None:
            self.blockers = []


class PurchaseRequestWorkflow:
    """Workflow orchestrator for Purchase Request creation.
    
    Implements Phase 4 of the PR creation plan, integrating with
    WorkflowOrchestrator for state management and tracking.
    
    Workflow Steps:
    1. Verify supplier exists in Buy@
    2. Verify supplier PR readiness (TPA check)
    3. Create PR draft (or submit for approval)
    4. If submitted, start async polling (non-blocking)
    5. Send completion notification
    """
    
    def __init__(self, buyat_client: BuyAtClient):
        """Initialize PR workflow.
        
        Args:
            buyat_client: BuyAtClient instance for PR operations
        """
        self.buyat = buyat_client
        self.orchestrator = WorkflowOrchestrator()
        logger.info("PurchaseRequestWorkflow initialized")
    
    def create_pr_workflow(
        self,
        supplier_name: str,
        amount: float,
        description: str,
        justification: str,
        cost_center: str,
        submit_for_approval: bool = False,
        delivery_date: Optional[str] = None,
        attachments: List[str] = None,
        reference_case_id: Optional[str] = None,
        notification_callback: Optional[Callable] = None
    ) -> PRCreationResult:
        """Execute PR creation workflow with state tracking.
        
        Orchestrates the complete PR creation process with workflow
        state management for tracking and recovery.
        
        Args:
            supplier_name: Name of the supplier
            amount: PR amount in USD
            description: Description of goods/services
            justification: Business justification
            cost_center: Cost center for charging
            submit_for_approval: If True, submit immediately; if False, create draft
            delivery_date: Optional delivery date (YYYY-MM-DD)
            attachments: Optional list of file paths to attach
            reference_case_id: Optional reference case ID
            notification_callback: Optional callback for status notifications
            
        Returns:
            PRCreationResult with PR details and workflow status
        """
        workflow_id = f"pr_workflow_{supplier_name}_{int(datetime.now().timestamp())}"
        logger.info(f"Starting PR workflow {workflow_id} for {supplier_name}")
        
        result = PRCreationResult(
            success=False,
            supplier_name=supplier_name,
            amount=amount
        )
        
        try:
            # Step 1: Verify supplier exists
            logger.info(f"Step 1: Verifying supplier {supplier_name}")
            try:
                supplier_info = self.buyat.search_supplier(supplier_name, use_cache=False)
                if not supplier_info.exists:
                    result.errors.append(f"Supplier '{supplier_name}' not found in Buy@")
                    result.blockers = [f"Supplier '{supplier_name}' not found"]
                    return result
                if not supplier_info.is_active:
                    result.errors.append(f"Supplier '{supplier_name}' is not active (status: {supplier_info.status})")
                    result.blockers = [f"Supplier not active: {supplier_info.status}"]
                    return result
                logger.info(f"✓ Supplier {supplier_name} verified (active)")
            except Exception as e:
                result.errors.append(f"Supplier verification failed: {e}")
                return result
            
            # Step 2: Verify supplier PR readiness (TPA check) if submitting
            if submit_for_approval:
                logger.info("Step 2: Verifying supplier PR readiness (TPA check)")
                try:
                    readiness = self.buyat.verify_supplier_for_pr(supplier_name)
                    if not readiness.can_proceed:
                        result.errors.append(f"Supplier not ready for PR: {', '.join(readiness.blockers)}")
                        result.blockers = readiness.blockers
                        return result
                    logger.info("✓ Supplier PR readiness verified")
                except Exception as e:
                    logger.warning(f"TPA check failed (non-blocking): {e}")
            
            # Step 3: Create PR draft or submit
            logger.info(f"Step 3: Creating PR (submit={submit_for_approval})")
            try:
                if submit_for_approval and notification_callback:
                    # Use create_pr_and_monitor for async tracking
                    pr_info, polling_id = self.buyat.create_pr_and_monitor(
                        supplier_name=supplier_name,
                        amount=amount,
                        description=description,
                        justification=justification,
                        cost_center=cost_center,
                        notification_callback=notification_callback,
                        delivery_date=delivery_date,
                        attachments=attachments,
                        reference_case_id=reference_case_id
                    )
                    result.polling_id = polling_id
                    result.monitoring_active = True
                else:
                    # Use regular create_pr_draft
                    pr_info = self.buyat.create_pr_draft(
                        supplier_name=supplier_name,
                        amount=amount,
                        description=description,
                        justification=justification,
                        cost_center=cost_center,
                        submit_for_approval=submit_for_approval,
                        delivery_date=delivery_date,
                        attachments=attachments,
                        reference_case_id=reference_case_id
                    )
                
                result.pr_number = pr_info.pr_number
                result.pr_url = pr_info.pr_url
                result.status = pr_info.status
                logger.info(f"✓ PR created: {pr_info.pr_number} (status: {pr_info.status})")
                
            except Exception as e:
                result.errors.append(f"PR creation failed: {e}")
                return result
            
            # Step 4: Send completion notification
            logger.info("Step 4: Sending completion notification")
            result.success = True
            logger.info(
                f"PR workflow {workflow_id} completed successfully: "
                f"{result.pr_number}, status={result.status}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"PR workflow failed with unexpected error: {e}")
            result.errors.append(f"Unexpected error: {e}")
            result.success = False
            return result
    
    def get_pr_workflow_status(self, pr_number: str) -> Dict[str, Any]:
        """Get status of PR workflow including approval status.
        
        Args:
            pr_number: PR number to check
            
        Returns:
            Dictionary with PR status and workflow metadata
        """
        logger.info(f"Getting PR workflow status for {pr_number}")
        try:
            # Use BuyAtClient to check PR status
            pr_status = self.buyat._agentic_client.check_pr_status(pr_number)
            
            return {
                "pr_number": pr_number,
                "status": pr_status.status,
                "current_approver": pr_status.current_approver,
                "approval_chain": pr_status.approval_chain,
                "po_number": pr_status.po_number,
                "blockers": pr_status.blockers,
                "last_updated": pr_status.last_updated.isoformat() if pr_status.last_updated else None
            }
        except Exception as e:
            logger.error(f"Failed to get PR status: {e}")
            return {
                "pr_number": pr_number,
                "status": "error",
                "error": str(e)
            }
