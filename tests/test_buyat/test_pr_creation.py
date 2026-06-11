"""Unit tests for PR creation functionality.

Tests PRDraftInfo, PRStatus, SupplierPRReadiness dataclasses and
AgenticBuyingClient/BuyAtClient PR creation methods.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
from pathlib import Path

from src.buyat.client import (
    AgenticBuyingClient,
    BuyAtClient,
    PRDraftInfo,
    PRStatus,
    SupplierPRReadiness,
    SupplierInfo,
    SupplierNotFoundError,
    BuyAtError,
    AgenticFlowError,
    AgenticResponse
)


class TestPRDataclasses:
    """Test PR-related dataclasses."""
    
    def test_pr_draft_info_creation(self):
        """Test PRDraftInfo dataclass creation."""
        pr_info = PRDraftInfo(
            pr_number="PR-12345",
            pr_url="https://buy.meta.com/pr/12345",
            status="draft",
            supplier_name="Test Supplier",
            amount=1000.00,
            description="Test purchase",
            created_at=datetime.utcnow()
        )
        
        assert pr_info.pr_number == "PR-12345"
        assert pr_info.status == "draft"
        assert pr_info.amount == 1000.00
        assert pr_info.supplier_name == "Test Supplier"
    
    def test_pr_status_creation(self):
        """Test PRStatus dataclass creation."""
        pr_status = PRStatus(
            pr_number="PR-12345",
            status="submitted",
            current_approver="john.doe@meta.com",
            approval_chain=["manager@meta.com", "director@meta.com"],
            po_number=None,
            blockers=None,
            last_updated=datetime.utcnow()
        )
        
        assert pr_status.pr_number == "PR-12345"
        assert pr_status.status == "submitted"
        assert pr_status.current_approver == "john.doe@meta.com"
        assert len(pr_status.approval_chain) == 2
    
    def test_supplier_pr_readiness_creation(self):
        """Test SupplierPRReadiness dataclass creation."""
        readiness = SupplierPRReadiness(
            supplier_name="Test Supplier",
            exists=True,
            is_active=True,
            can_proceed=True,
            blockers=None,
            tpa_status="active",
            tpa_expiry=datetime.utcnow() + timedelta(days=30)
        )
        
        assert readiness.supplier_name == "Test Supplier"
        assert readiness.exists is True
        assert readiness.can_proceed is True
        assert readiness.tpa_status == "active"
    
    def test_supplier_pr_readiness_with_blockers(self):
        """Test SupplierPRReadiness with blockers."""
        readiness = SupplierPRReadiness(
            supplier_name="Test Supplier",
            exists=True,
            is_active=False,
            can_proceed=False,
            blockers=["Supplier is inactive", "TPA expired"],
            tpa_status="expired"
        )
        
        assert readiness.can_proceed is False
        assert len(readiness.blockers) == 2
        assert "inactive" in readiness.blockers[0].lower()


class TestAgenticBuyingClientPRCreation:
    """Test AgenticBuyingClient PR creation methods."""
    
    @pytest.fixture
    def client(self):
        """Create AgenticBuyingClient with mocked browser."""
        client = AgenticBuyingClient(headless=True)
        client._page = Mock()
        client._assistant_open = True
        return client
    
    def test_create_pr_draft_draft_mode(self, client):
        """Test create_pr_draft with submit_for_approval=False (draft mode)."""
        # Mock send_message to return a response with PR details
        mock_response = AgenticResponse(
            message="PR created successfully. PR Number: PR-12345. "
                   "URL: https://buy.meta.com/pr/12345. Status: Draft.",
            has_followup=False,
            requires_confirmation=False
        )
        client.send_message = Mock(return_value=mock_response)
        
        pr_info = client.create_pr_draft(
            supplier_name="Test Supplier",
            amount=5000.00,
            description="Software licenses",
            justification="Needed for project X",
            cost_center="CC-12345",
            submit_for_approval=False
        )
        
        assert pr_info.pr_number == "PR-12345"
        assert pr_info.status == "draft"
        assert pr_info.supplier_name == "Test Supplier"
        assert pr_info.amount == 5000.00
        
        # Verify prompt includes draft instruction
        call_args = client.send_message.call_args[0][0]
        assert "DRAFT ONLY" in call_args
        assert "Do not submit for approval" in call_args
    
    def test_create_pr_draft_submit_mode(self, client):
        """Test create_pr_draft with submit_for_approval=True (submission mode)."""
        mock_response = AgenticResponse(
            message="PR submitted for approval. PR Number: PR-67890. "
                   "URL: https://buy.meta.com/pr/67890. Status: Submitted.",
            has_followup=False,
            requires_confirmation=False
        )
        client.send_message = Mock(return_value=mock_response)
        
        pr_info = client.create_pr_draft(
            supplier_name="Test Supplier",
            amount=10000.00,
            description="Hardware purchase",
            justification="Server upgrade",
            cost_center="CC-67890",
            submit_for_approval=True,
            delivery_date="2026-07-01"
        )
        
        assert pr_info.pr_number == "PR-67890"
        assert pr_info.status == "submitted"
        assert pr_info.submitted_at is not None
        
        # Verify prompt includes submit instruction
        call_args = client.send_message.call_args[0][0]
        assert "SUBMIT FOR APPROVAL IMMEDIATELY" in call_args
        assert "Delivery Date: 2026-07-01" in call_args
    
    def test_create_pr_draft_with_attachments(self, client):
        """Test create_pr_draft with document attachments."""
        mock_response = AgenticResponse(
            message="PR created with attachments. PR Number: PR-11111.",
            has_followup=False
        )
        client.send_message = Mock(return_value=mock_response)
        client.upload_document = Mock(return_value="doc_12345")
        
        pr_info = client.create_pr_draft(
            supplier_name="Test Supplier",
            amount=2500.00,
            description="Consulting services",
            justification="Project support",
            cost_center="CC-11111",
            submit_for_approval=False,
            attachments=["/path/to/quote.pdf", "/path/to/sow.docx"]
        )
        
        # Verify upload_document was called for each attachment
        assert client.upload_document.call_count == 2
        
        # Verify prompt includes attachment references
        call_args = client.send_message.call_args[0][0]
        assert "Attached Documents:" in call_args
        assert "doc_12345" in call_args
    
    def test_check_pr_status(self, client):
        """Test check_pr_status method."""
        mock_response = AgenticResponse(
            message="PR PR-12345 status: Submitted. "
                   "Current approver: manager@meta.com. "
                   "Approval chain: manager@meta.com, director@meta.com. "
                   "No PO yet.",
            has_followup=False
        )
        client.send_message = Mock(return_value=mock_response)
        
        pr_status = client.check_pr_status("PR-12345")
        
        assert pr_status.pr_number == "PR-12345"
        assert pr_status.status == "submitted"
        assert pr_status.current_approver == "manager@meta.com"
        assert len(pr_status.approval_chain) == 2
        
        # Verify correct prompt was sent
        call_args = client.send_message.call_args[0][0]
        assert "PR-12345" in call_args
        assert "current status" in call_args.lower()
    
    def test_check_pr_status_approved(self, client):
        """Test check_pr_status for approved PR."""
        mock_response = AgenticResponse(
            message="PR PR-12345 status: Approved. "
                   "PO Number: PO-99999. "
                   "Approved by: director@meta.com",
            has_followup=False
        )
        client.send_message = Mock(return_value=mock_response)
        
        pr_status = client.check_pr_status("PR-12345")
        
        assert pr_status.status == "approved"
        assert pr_status.po_number == "PO-99999"
    
    def test_upload_document_success(self, client):
        """Test successful document upload."""
        # Mock page elements
        mock_button = Mock()
        mock_button.is_visible.return_value = True
        mock_button.get_attribute.return_value = "file"
        client._page.locator.return_value.first = mock_button
        
        doc_id = client.upload_document("/path/to/document.pdf")
        
        assert doc_id == "document.pdf"
        mock_button.set_input_files.assert_called_once_with("/path/to/document.pdf")
    
    def test_upload_document_no_button(self, client):
        """Test upload_document when button not found."""
        mock_button = Mock()
        mock_button.is_visible.return_value = False
        client._page.locator.return_value.first = mock_button
        
        with pytest.raises(AgenticFlowError, match="File upload button not found"):
            client.upload_document("/path/to/document.pdf")
    
    def test_extract_pr_number(self, client):
        """Test PR number extraction from messages."""
        assert client._extract_pr_number("PR Number: PR-12345") == "PR-12345"
        assert client._extract_pr_number("PR#67890 created") == "PR-67890"
        assert client._extract_pr_number("PR 11111 submitted") == "PR-11111"
        assert client._extract_pr_number("No PR here") is None
    
    def test_extract_pr_url(self, client):
        """Test PR URL extraction from messages."""
        url = client._extract_pr_url("See PR at https://buy.meta.com/pr/12345")
        assert url == "https://buy.meta.com/pr/12345"
        assert client._extract_pr_url("No URL here") is None
    
    def test_parse_pr_status(self, client):
        """Test PR status parsing."""
        assert client._parse_pr_status("PR is approved") == "approved"
        assert client._parse_pr_status("PR was rejected") == "rejected"
        assert client._parse_pr_status("PR submitted for approval") == "submitted"
        assert client._parse_pr_status("PR is in draft") == "draft"
        assert client._parse_pr_status("Unknown status") == "unknown"


class TestBuyAtClientPRCreation:
    """Test BuyAtClient PR creation methods."""
    
    @pytest.fixture
    def client(self):
        """Create BuyAtClient with mocked agentic client."""
        client = BuyAtClient(headless=True, use_agentic=True)
        client._agentic_client = Mock(spec=AgenticBuyingClient)
        client._agentic_client.is_started.return_value = True
        return client
    
    def test_create_pr_draft_success(self, client):
        """Test successful PR draft creation via BuyAtClient."""
        # Mock supplier search
        supplier_info = SupplierInfo(
            name="Test Supplier",
            exists=True,
            supplier_id="SUP-123",
            status="active",
            is_active=True
        )
        client.search_supplier = Mock(return_value=supplier_info)
        
        # Mock PR creation
        expected_pr = PRDraftInfo(
            pr_number="PR-12345",
            pr_url="https://buy.meta.com/pr/12345",
            status="draft",
            supplier_name="Test Supplier",
            amount=5000.00,
            description="Test purchase"
        )
        client._agentic_client.create_pr_draft.return_value = expected_pr
        
        pr_info = client.create_pr_draft(
            supplier_name="Test Supplier",
            amount=5000.00,
            description="Test purchase",
            justification="Business need",
            cost_center="CC-12345",
            submit_for_approval=False
        )
        
        assert pr_info.pr_number == "PR-12345"
        assert pr_info.status == "draft"
        
        # Verify supplier was checked
        client.search_supplier.assert_called_once_with("Test Supplier", use_cache=False)
        
        # Verify agentic client was called
        client._agentic_client.create_pr_draft.assert_called_once()
    
    def test_create_pr_draft_supplier_not_found(self, client):
        """Test PR creation when supplier not found."""
        client.search_supplier = Mock(
            side_effect=SupplierNotFoundError("Supplier not found")
        )
        
        with pytest.raises(SupplierNotFoundError):
            client.create_pr_draft(
                supplier_name="Nonexistent Supplier",
                amount=1000.00,
                description="Test",
                justification="Test",
                cost_center="CC-123"
            )
    
    def test_create_pr_draft_supplier_inactive(self, client):
        """Test PR creation when supplier is inactive."""
        supplier_info = SupplierInfo(
            name="Test Supplier",
            exists=True,
            status="inactive",
            is_active=False
        )
        client.search_supplier = Mock(return_value=supplier_info)
        
        with pytest.raises(BuyAtError, match="not active"):
            client.create_pr_draft(
                supplier_name="Test Supplier",
                amount=1000.00,
                description="Test",
                justification="Test",
                cost_center="CC-123"
            )
    
    def test_create_pr_draft_with_submit_verifies_readiness(self, client):
        """Test that submit_for_approval=True triggers readiness check."""
        supplier_info = SupplierInfo(
            name="Test Supplier",
            exists=True,
            status="active",
            is_active=True
        )
        client.search_supplier = Mock(return_value=supplier_info)
        
        # Mock readiness check with blockers
        readiness = SupplierPRReadiness(
            supplier_name="Test Supplier",
            exists=True,
            is_active=True,
            can_proceed=False,
            blockers=["TPA expired"]
        )
        client.verify_supplier_for_pr = Mock(return_value=readiness)
        
        with pytest.raises(BuyAtError, match="not ready for PR creation"):
            client.create_pr_draft(
                supplier_name="Test Supplier",
                amount=1000.00,
                description="Test",
                justification="Test",
                cost_center="CC-123",
                submit_for_approval=True
            )
        
        client.verify_supplier_for_pr.assert_called_once_with("Test Supplier")
    
    def test_verify_supplier_for_pr_ready(self, client):
        """Test supplier verification when ready."""
        supplier_info = SupplierInfo(
            name="Test Supplier",
            exists=True,
            status="active",
            is_active=True
        )
        client.search_supplier = Mock(return_value=supplier_info)
        
        # Mock TPA client
        with patch('src.buyat.client.TPAClient') as mock_tpa_class:
            mock_tpa = Mock()
            mock_tpa.get_tpa_status.return_value = {
                "status": "active",
                "expiry_date": datetime.utcnow() + timedelta(days=30)
            }
            mock_tpa_class.return_value = mock_tpa
            
            readiness = client.verify_supplier_for_pr("Test Supplier")
            
            assert readiness.exists is True
            assert readiness.is_active is True
            assert readiness.can_proceed is True
            assert readiness.tpa_status == "active"
            assert readiness.blockers is None
    
    def test_verify_supplier_for_pr_with_blockers(self, client):
        """Test supplier verification with blockers."""
        supplier_info = SupplierInfo(
            name="Test Supplier",
            exists=True,
            status="inactive",
            is_active=False
        )
        client.search_supplier = Mock(return_value=supplier_info)
        
        readiness = client.verify_supplier_for_pr("Test Supplier")
        
        assert readiness.exists is True
        assert readiness.is_active is False
        assert readiness.can_proceed is False
        assert len(readiness.blockers) > 0
        assert "not active" in readiness.blockers[0].lower()
    
    def test_verify_supplier_for_pr_not_found(self, client):
        """Test supplier verification when supplier not found."""
        client.search_supplier = Mock(
            side_effect=SupplierNotFoundError("Not found")
        )
        
        readiness = client.verify_supplier_for_pr("Nonexistent")
        
        assert readiness.exists is False
        assert readiness.can_proceed is False
        assert len(readiness.blockers) > 0
