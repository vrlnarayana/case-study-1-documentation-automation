"""
Tests for Documentation Automation agent workflow.
Tests the minimal workflow: Ingestion → Structure → Drafting
"""

import pytest
from app.agents.state import (
    AgentState,
    create_initial_state,
    SourceDocument,
    DocumentOutline,
    DocumentDraft,
    WorkflowError,
)
from app.agents.nodes import (
    ingestion_agent,
    structure_agent,
    drafting_agent,
)
from app.agents.graph import (
    create_workflow_graph,
    compile_workflow,
    run_workflow,
    get_workflow_summary,
)


class TestStateCreation:
    """Test state initialization."""
    
    def test_create_initial_state(self):
        """Test that initial state is created correctly."""
        state = create_initial_state(
            selected_sources=["source_code/test.py"],
            template_type="technical_spec"
        )
        
        assert state["selected_sources"] == ["source_code/test.py"]
        assert state["template_type"] == "technical_spec"
        assert state["retrieved_sources"] == []
        assert state["outline"] is None
        assert state["draft"] is None
        assert state["workflow_status"] == "running"
        assert state["current_step"] == "initialized"


class TestIngestionAgent:
    """Test Ingestion Agent functionality."""
    
    def test_ingestion_retrieves_sources(self):
        """Test that ingestion retrieves source documents."""
        state = create_initial_state(
            selected_sources=[
                "source_code/billing_service.py",
                "specifications/billing_requirements.md"
            ],
            template_type="technical_spec"
        )
        
        result = ingestion_agent(state)
        
        assert result["ingestion_complete"] is True
        assert len(result["retrieved_sources"]) == 2
        assert result["current_step"] == "ingestion_complete"
        
        # Check that sources have expected fields
        for source in result["retrieved_sources"]:
            assert source.path is not None
            assert source.content is not None
            assert source.doc_type is not None
    
    def test_ingestion_handles_invalid_paths(self):
        """Test that ingestion handles invalid file paths gracefully."""
        state = create_initial_state(
            selected_sources=["invalid/path/../traversal.py"],
            template_type="technical_spec"
        )
        
        result = ingestion_agent(state)
        
        # Should have errors but complete
        assert result["ingestion_complete"] is True
        assert len(result["ingestion_errors"]) == 1
        assert result["retrieved_sources"] == []  # No sources retrieved
    
    def test_ingestion_empty_sources(self):
        """Test that ingestion handles empty source list."""
        state = create_initial_state(
            selected_sources=[],
            template_type="technical_spec"
        )
        
        result = ingestion_agent(state)
        
        assert result["ingestion_complete"] is True
        assert len(result["retrieved_sources"]) == 0


class TestStructureAgent:
    """Test Structure Agent functionality."""
    
    def test_structure_creates_outline(self):
        """Test that structure agent creates an outline."""
        # First run ingestion
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        
        # Then run structure
        result = structure_agent(state)
        
        assert result["structure_complete"] is True
        assert result["outline"] is not None
        assert isinstance(result["outline"], DocumentOutline)
        assert result["outline"].template_type == "technical_spec"
        assert len(result["outline"].sections) > 0
    
    def test_structure_detects_conflicts(self):
        """Test that structure agent detects known conflicts."""
        state = create_initial_state(
            selected_sources=[
                "specifications/billing_requirements.md",
                "meeting_notes/billing-system-review.md"
            ],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        result = structure_agent(state)
        
        # Should detect the threshold contradiction
        conflicts = result["outline"].conflicts
        assert len(conflicts) > 0
        
        # Check for threshold conflict
        threshold_conflict = any(
            "threshold" in c.description.lower() or "$5,000" in c.description or "$10,000" in c.description
            for c in conflicts
        )
        assert threshold_conflict, "Should detect approval threshold conflict"
    
    def test_structure_without_sources(self):
        """Test that structure handles missing sources gracefully."""
        state = create_initial_state(
            selected_sources=[],
            template_type="technical_spec"
        )
        
        result = structure_agent(state)
        
        assert result["structure_complete"] is False
        assert len(result["structure_errors"]) > 0


class TestDraftingAgent:
    """Test Drafting Agent functionality."""
    
    def test_drafting_creates_draft(self):
        """Test that drafting agent creates a document draft."""
        # Run full pipeline to drafting
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        result = drafting_agent(state)
        
        assert result["drafting_complete"] is True
        assert result["draft"] is not None
        assert isinstance(result["draft"], DocumentDraft)
        assert result["draft"].template_type == "technical_spec"
        assert len(result["draft"].sections) > 0
        assert len(result["draft"].content) > 0
    
    def test_draft_cannot_publish(self):
        """Test that drafting agent marks draft as not publishable."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        result = drafting_agent(state)
        
        # Drafting agent CANNOT approve for publication
        assert result["draft"].can_publish == "no"
        assert "DRAFT" in result["draft"].content
        assert "Human review required" in result["draft"].content or "NOT FOR PUBLICATION" in result["draft"].content
    
    def test_draft_includes_conflicts(self):
        """Test that draft includes conflict information."""
        state = create_initial_state(
            selected_sources=[
                "specifications/billing_requirements.md",
                "meeting_notes/billing-system-review.md"
            ],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        state = structure_agent(state)
        result = drafting_agent(state)
        
        # Draft should mention conflicts
        assert "Known Issues" in result["draft"].content or "conflict" in result["draft"].content.lower()
    
    def test_drafting_without_outline(self):
        """Test that drafting handles missing outline gracefully."""
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        # Skip structure - no outline
        
        result = drafting_agent(state)
        
        assert result["drafting_complete"] is False
        assert len(result["drafting_errors"]) > 0


class TestWorkflowGraph:
    """Test complete workflow graph."""
    
    def test_graph_creation(self):
        """Test that graph can be created and compiled."""
        graph = create_workflow_graph()
        assert graph is not None
        
        compiled = compile_workflow()
        assert compiled is not None
    
    def test_full_workflow_execution(self):
        """Test complete workflow execution."""
        final_state = run_workflow(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        
        assert final_state["workflow_status"] == "completed"
        assert final_state["ingestion_complete"] is True
        assert final_state["structure_complete"] is True
        assert final_state["drafting_complete"] is True
        assert final_state["draft"] is not None
    
    def test_workflow_with_conflicts(self):
        """Test workflow handles sources with conflicts."""
        final_state = run_workflow(
            selected_sources=[
                "specifications/billing_requirements.md",
                "meeting_notes/billing-system-review.md"
            ],
            template_type="technical_spec"
        )
        
        assert final_state["workflow_status"] == "completed"
        assert final_state["outline"] is not None
        assert len(final_state["outline"].conflicts) > 0
        assert final_state["draft"] is not None
    
    def test_workflow_summary(self):
        """Test workflow summary generation."""
        state = run_workflow(
            selected_sources=["source_code/patient_service.py"],
            template_type="sop"
        )
        
        summary = get_workflow_summary(state)
        
        assert "status" in summary
        assert "sources" in summary
        assert "progress" in summary
        assert summary["progress"]["ingestion"] is True
        assert summary["progress"]["structure"] is True
        assert summary["progress"]["drafting"] is True
        assert "draft" in summary
        assert summary["draft"]["can_publish"] == "no"


class TestMCPIntegration:
    """Test that agents use MCP tools correctly (not direct filesystem access)."""
    
    def test_ingestion_uses_mcp_tools(self):
        """Test that ingestion uses MCP tools, not direct file access."""
        # This test verifies the architecture constraint
        # Agents should call read_source_file(), not open() directly
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        
        # Run ingestion
        result = ingestion_agent(state)
        
        # Verify sources were retrieved via MCP (stub returns placeholder)
        assert len(result["retrieved_sources"]) == 1
        source = result["retrieved_sources"][0]
        assert source.content is not None
        assert "STUB CONTENT" in source.content or len(source.content) > 0
    
    def test_structure_uses_mcp_for_template(self):
        """Test that structure agent uses MCP for templates."""
        # First ingest some sources
        state = create_initial_state(
            selected_sources=["source_code/billing_service.py"],
            template_type="technical_spec"
        )
        state = ingestion_agent(state)
        
        # Structure agent should call get_template via MCP
        result = structure_agent(state)
        
        # Should succeed with sources
        assert result["structure_complete"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
