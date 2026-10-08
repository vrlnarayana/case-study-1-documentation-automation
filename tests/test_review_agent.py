"""
Tests for Review Routing Agent.
Tests quality assessment, issue detection, and routing decisions.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.state import (
    AgentState,
    create_initial_state,
    DocumentDraft,
    DocumentOutline,
    DraftSection,
    OutlineSection,
    Conflict,
    ReviewAssessment,
)
from app.agents.nodes import (
    ingestion_agent,
    structure_agent,
    drafting_agent,
    review_routing_agent,
)


class TestReviewRoutingBasics:
    """Test Review Routing Agent basic functionality."""
    
    def test_review_requires_draft(self):
        """Test that review requires a draft."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        
        # Try to run review without draft
        result = review_routing_agent(state)
        
        assert result["review_complete"] is False
        assert len(result["review_errors"]) > 0
    
    def test_review_never_approves(self):
        """Test that Review Routing never approves for publication."""
        # Run full pipeline
        state = create_initial_state(
            selected_sources=["source_code/patient_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        result = review_routing_agent(state)
        
        assert result["review_complete"] is True
        assert result["review_assessment"] is not None
        
        # Review agent never sets status to "APPROVED"
        # Only routes to READY_FOR_REVIEW or NEEDS_REVISION
        assert result["review_assessment"].status in ["READY_FOR_REVIEW", "NEEDS_REVISION"]
    
    def test_review_creates_assessment(self):
        """Test that review creates assessment object."""
        # Run pipeline to drafting
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        result = review_routing_agent(state)
        
        assessment = result["review_assessment"]
        
        assert isinstance(assessment, ReviewAssessment)
        assert hasattr(assessment, "status")
        assert hasattr(assessment, "confidence")
        assert hasattr(assessment, "issues")
        assert hasattr(assessment, "human_review_items")


class TestReviewIssueDetection:
    """Test issue detection in review."""
    
    def test_review_detects_low_confidence(self):
        """Test that review flags low confidence drafts."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        
        # Lower the confidence
        state["draft"].overall_confidence = 0.4
        
        result = review_routing_agent(state)
        
        assert result["review_assessment"] is not None
        # Should flag low confidence
        assert any("confidence" in issue.lower() for issue in result["review_assessment"].issues) or \
               result["review_assessment"].status == "NEEDS_REVISION"
    
    def test_review_detects_missing_sections(self):
        """Test that review detects missing sections."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        
        # Remove a section from draft
        original_count = len(state["draft"].sections)
        state["draft"].sections.pop()
        
        result = review_routing_agent(state)
        
        # Should detect missing sections
        assert result["review_assessment"] is not None
        # Check for issues or revision status
        if result["review_assessment"].issues:
            issues_text = str(result["review_assessment"].issues).lower()
            assert "missing" in issues_text or "section" in issues_text
    
    def test_review_detects_placeholders(self):
        """Test that review flags unresolved placeholders."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        
        # Add placeholders to a section
        state["draft"].sections[0].unresolved_placeholders = ["{{PLACEHOLDER: test}}"]
        
        result = review_routing_agent(state)
        
        # Should flag placeholders
        assert result["review_assessment"] is not None
        issues = " ".join(result["review_assessment"].issues).lower()
        human_items = " ".join(result["review_assessment"].human_review_items).lower()
        
        assert "placeholder" in issues or "placeholder" in human_items


class TestReviewConflictHandling:
    """Test handling of conflicts in review."""
    
    def test_review_detects_conflicts(self):
        """Test that review detects conflicts from outline."""
        state = create_initial_state(
            selected_sources=[
                "specifications/billing_requirements.md",
                "meeting_notes/billing-system-review.md"
            ],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        result = review_routing_agent(state)
        
        # Should have detected conflicts in review
        assert result["review_assessment"] is not None
        
        # Conflicts should be flagged for human review
        human_items = result["review_assessment"].human_review_items
        assert len(human_items) > 0 or len(result["review_assessment"].issues) > 0
    
    def test_review_requires_human_for_conflicts(self):
        """Test that conflicts trigger human review requirement."""
        state = create_initial_state(
            selected_sources=[
                "specifications/billing_requirements.md",
                "meeting_notes/billing-system-review.md"
            ],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        result = review_routing_agent(state)
        
        # Even if status is READY_FOR_REVIEW, should have human items
        assert result["review_assessment"] is not None
        if result["review_assessment"].status == "READY_FOR_REVIEW":
            assert len(result["review_assessment"].human_review_items) > 0


class TestReviewRoutingDecisions:
    """Test routing decisions."""
    
    def test_ready_for_review_when_good(self):
        """Test READY_FOR_REVIEW when draft is acceptable."""
        state = create_initial_state(
            selected_sources=["source_code/patient_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        
        # Ensure good confidence
        state["draft"].overall_confidence = 0.8
        
        result = review_routing_agent(state)
        
        assert result["review_assessment"].status == "READY_FOR_REVIEW"
    
    def test_needs_revision_when_bad(self):
        """Test NEEDS_REVISION when draft has major issues."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        
        # Force low confidence
        state["draft"].overall_confidence = 0.3
        
        result = review_routing_agent(state)
        
        # Should recommend revision
        assert result["review_assessment"].status == "NEEDS_REVISION"
    
    def test_always_has_human_items(self):
        """Test that READY_FOR_REVIEW always has human items."""
        state = create_initial_state(
            selected_sources=["source_code/appointment_service.py"],
            template_type="sop"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        result = review_routing_agent(state)
        
        # Even for good drafts, should have human review items
        assert result["review_assessment"] is not None
        if result["review_assessment"].status == "READY_FOR_REVIEW":
            # Should require human approval
            human_items_text = str(result["review_assessment"].human_review_items).lower()
            assert "human" in human_items_text or "approval" in human_items_text or \
                   len(result["review_assessment"].human_review_items) > 0


class TestReviewAssessmentStructure:
    """Test assessment structure and fields."""
    
    def test_assessment_has_all_fields(self):
        """Test that assessment has all required fields."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        result = review_routing_agent(state)
        
        assessment = result["review_assessment"]
        
        # Check all required fields
        assert hasattr(assessment, "status")
        assert hasattr(assessment, "confidence")
        assert hasattr(assessment, "issues")
        assert hasattr(assessment, "human_review_items")
        
        # Check types
        assert isinstance(assessment.status, str)
        assert isinstance(assessment.confidence, (int, float))
        assert isinstance(assessment.issues, list)
        assert isinstance(assessment.human_review_items, list)
    
    def test_confidence_is_bounded(self):
        """Test that confidence is between 0 and 1."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        state = drafting_agent(state)
        result = review_routing_agent(state)
        
        confidence = result["review_assessment"].confidence
        assert 0.0 <= confidence <= 1.0


class TestFullWorkflowWithReview:
    """Test complete workflow including review."""
    
    def test_complete_workflow_with_review(self):
        """Test that complete workflow includes review step."""
        from app.agents.graph import run_workflow, get_workflow_summary
        
        state = run_workflow(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        
        # All 4 agents should have run
        assert state["ingestion_complete"] is True
        assert state["structure_complete"] is True
        assert state["drafting_complete"] is True
        assert state["review_complete"] is True
        
        # Should have review assessment
        assert state["review_assessment"] is not None
        
        # Summary should include review
        summary = get_workflow_summary(state)
        assert "review" in summary
        assert "status" in summary["review"]
    
    def test_workflow_status_after_review(self):
        """Test that workflow status is set after review."""
        from app.agents.graph import run_workflow
        
        state = run_workflow(
            selected_sources=["source_code/patient_service.py"],
            template_type="sop"
        )
        
        # Status should reflect review decision
        assert state["workflow_status"] in ["completed", "needs_revision"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
