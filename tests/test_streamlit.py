"""
Tests for Streamlit UI components.
Tests the MCP client interface and human approval workflow.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mcp_server.server import MCPServer
from app.agents.graph import run_workflow, get_workflow_summary


class TestStreamlitIntegration:
    """Test Streamlit UI integration points."""
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance."""
        return MCPServer()
    
    def test_list_files_for_ui(self, mcp_server):
        """Test that file listing works for UI."""
        result = mcp_server.list_source_files()
        
        assert result["success"] is True
        assert len(result["files"]) > 0
        
        # Verify all expected file types present
        files = result["files"]
        assert any(".py" in f for f in files)
        assert any(".md" in f for f in files)
    
    def test_metadata_for_ui_display(self, mcp_server):
        """Test that metadata is formatted for UI display."""
        result = mcp_server.get_source_metadata("source_code/billing_service.py")
        
        assert result["success"] is True
        assert "classification" in result
        assert "file_info" in result
        assert "known_issues" in result
        
        # UI needs these fields
        assert "doc_type" in result["classification"]
        assert "sensitivity" in result["classification"]
        assert "size" in result["file_info"]
    
    def test_workflow_for_ui(self):
        """Test that workflow can be run from UI context."""
        state = run_workflow(
            selected_sources=["source_code/patient_service.py"],
            template_type="sop"
        )
        
        summary = get_workflow_summary(state)
        
        # UI needs these fields
        assert "status" in summary
        assert "progress" in summary
        assert "sources" in summary
        assert "errors" in summary
        
        # Verify progress is boolean-friendly
        assert isinstance(summary["progress"]["ingestion"], bool)
        assert isinstance(summary["progress"]["structure"], bool)
        assert isinstance(summary["progress"]["drafting"], bool)


class TestHumanApprovalWorkflow:
    """Test human approval requirements."""
    
    def test_draft_requires_approval(self):
        """Test that draft is marked as requiring approval."""
        state = run_workflow(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        
        assert state["draft"] is not None
        assert state["draft"].can_publish == "no"
        assert "NOT FOR PUBLICATION" in state["draft"].content or "Human review required" in state["draft"].content
    
    def test_draft_contains_warnings(self):
        """Test that draft contains appropriate warnings."""
        state = run_workflow(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        
        draft = state["draft"]
        
        # Should have warnings about draft status
        assert "DRAFT" in draft.content
        assert draft.overall_confidence < 1.0  # Not 100% confident


class TestTemplateTypes:
    """Test all template types work in UI."""
    
    def test_technical_spec_template(self):
        """Test technical spec template."""
        state = run_workflow(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        
        assert state["workflow_status"] == "completed"
        assert state["draft"] is not None
    
    def test_sop_template(self):
        """Test SOP template."""
        state = run_workflow(
            selected_sources=["source_code/appointment_service.py"],
            template_type="sop"
        )
        
        assert state["workflow_status"] == "completed"
        assert state["draft"] is not None
    
    def test_process_map_template(self):
        """Test process map template."""
        state = run_workflow(
            selected_sources=["meeting_notes/billing-system-review.md"],
            template_type="process_map"
        )
        
        assert state["workflow_status"] == "completed"
        assert state["draft"] is not None


class TestMultiSourceSelection:
    """Test selecting multiple sources."""
    
    def test_multiple_sources_detect_conflicts(self):
        """Test that multiple sources with conflicts are detected."""
        state = run_workflow(
            selected_sources=[
                "specifications/billing_requirements.md",
                "meeting_notes/billing-system-review.md"
            ],
            template_type="technical_spec"
        )
        
        assert state["workflow_status"] == "completed"
        assert state["outline"] is not None
        
        # Should detect the threshold conflict
        assert len(state["outline"].conflicts) > 0
        
        # Conflict should be in draft
        assert state["draft"] is not None


class TestErrorHandling:
    """Test UI error handling."""
    
    def test_invalid_file_handled_gracefully(self):
        """Test that invalid files are handled gracefully."""
        server = MCPServer()
        
        result = server.read_source_file("nonexistent/file.py")
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"]["code"] == "FILE_NOT_FOUND"
    
    def test_traversal_blocked(self):
        """Test that UI cannot access files outside seed_data."""
        server = MCPServer()
        
        result = server.read_source_file("../etc/passwd")
        
        assert result["success"] is False
        assert result["error"]["code"] == "PATH_VALIDATION_ERROR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
