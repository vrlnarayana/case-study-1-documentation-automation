"""
State definitions for Documentation Automation workflow.
Uses Pydantic for structured data and TypedDict for LangGraph state.
"""

from typing import TypedDict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ============== Pydantic Models ==============

class SourceDocument(BaseModel):
    """Represents a retrieved source document."""
    path: str = Field(description="Relative path within seed_data/")
    content: str = Field(description="Document content")
    doc_type: Literal["source_code", "requirements", "meeting_notes", "template", "existing_doc", "metadata"] = Field(
        description="Type of document"
    )
    classification: str = Field(default="standard", description="Document classification")
    sensitivity: Literal["public", "internal", "confidential", "restricted"] = Field(
        default="internal",
        description="Sensitivity level"
    )
    retrieved_at: datetime = Field(default_factory=datetime.now)


class Conflict(BaseModel):
    """Represents a conflict between sources."""
    description: str = Field(description="Description of the conflict")
    sources: List[str] = Field(description="List of conflicting source paths")
    severity: Literal["blocking", "warning", "info"] = Field(
        description="Severity of the conflict"
    )
    resolution: Optional[str] = Field(default=None, description="Proposed resolution if any")


class OutlineSection(BaseModel):
    """Represents a section in the document outline."""
    section_id: str = Field(description="Unique section identifier")
    title: str = Field(description="Section title")
    content_summary: str = Field(description="Summary of expected content")
    source_refs: List[str] = Field(default_factory=list, description="Source file references")
    status: Literal["complete", "incomplete", "flagged"] = Field(
        default="incomplete",
        description="Section completion status"
    )


class DocumentOutline(BaseModel):
    """Represents the structured outline of a document."""
    template_type: Literal["technical_spec", "sop", "process_map"] = Field(
        description="Type of document being created"
    )
    title: str = Field(description="Document title")
    sections: List[OutlineSection] = Field(default_factory=list, description="Document sections")
    conflicts: List[Conflict] = Field(default_factory=list, description="Detected conflicts")
    missing_info: List[str] = Field(default_factory=list, description="Missing information items")
    created_at: datetime = Field(default_factory=datetime.now)


class DraftSection(BaseModel):
    """Represents a generated section in the draft."""
    section_id: str = Field(description="Section identifier matching outline")
    title: str = Field(description="Section title")
    generated_content: str = Field(description="Generated markdown content")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0 to 1.0"
    )
    sources_cited: List[str] = Field(default_factory=list, description="Sources cited")
    unresolved_placeholders: List[str] = Field(
        default_factory=list,
        description="Unresolved placeholder markers"
    )


class DocumentDraft(BaseModel):
    """Represents the generated document draft."""
    template_type: Literal["technical_spec", "sop", "process_map"] = Field(
        description="Type of document"
    )
    title: str = Field(description="Document title")
    content: str = Field(description="Complete document content (markdown)")
    sections: List[DraftSection] = Field(default_factory=list, description="Individual sections")
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence score"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    can_publish: Literal["yes", "no", "pending_review"] = Field(
        default="pending_review",
        description="Publication readiness"
    )


class WorkflowError(BaseModel):
    """Represents a workflow error."""
    step: str = Field(description="Workflow step where error occurred")
    message: str = Field(description="Error message")
    details: Optional[str] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now)


# ============== LangGraph State ==============

class ReviewAssessment(BaseModel):
    """Assessment from Review Routing Agent."""
    status: Literal["READY_FOR_REVIEW", "NEEDS_REVISION"] = Field(
        description="Routing decision"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in assessment"
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of identified issues"
    )
    human_review_items: List[str] = Field(
        default_factory=list,
        description="Items requiring human attention"
    )
    assessment_time: datetime = Field(default_factory=datetime.now)


class AgentState(TypedDict):
    """Complete state for the LangGraph workflow.
    
    This TypedDict represents the state passed between nodes in the graph.
    Each field is Optional until populated by the corresponding agent.
    """
    # Input
    selected_sources: List[str]
    template_type: Literal["technical_spec", "sop", "process_map"]
    
    # Ingestion Agent
    retrieved_sources: List[SourceDocument]
    ingestion_complete: bool
    ingestion_errors: List[WorkflowError]
    
    # Structure Agent
    outline: Optional[DocumentOutline]
    structure_complete: bool
    structure_errors: List[WorkflowError]
    
    # Drafting Agent
    draft: Optional[DocumentDraft]
    drafting_complete: bool
    drafting_errors: List[WorkflowError]
    
    # Review Routing Agent (NEW)
    review_assessment: Optional[ReviewAssessment]
    review_complete: bool
    review_errors: List[WorkflowError]
    
    # Workflow
    current_step: str
    workflow_status: Literal["running", "completed", "failed", "halted"]
    errors: List[WorkflowError]


# ============== Helper Functions ==============

def create_initial_state(
    selected_sources: List[str],
    template_type: Literal["technical_spec", "sop", "process_map"]
) -> AgentState:
    """Create initial state for workflow execution.
    
    Args:
        selected_sources: List of source file paths to process
        template_type: Type of document to generate
        
    Returns:
        Initialized AgentState
    """
    return {
        "selected_sources": selected_sources,
        "template_type": template_type,
        "retrieved_sources": [],
        "ingestion_complete": False,
        "ingestion_errors": [],
        "outline": None,
        "structure_complete": False,
        "structure_errors": [],
        "draft": None,
        "drafting_complete": False,
        "drafting_errors": [],
        "review_assessment": None,
        "review_complete": False,
        "review_errors": [],
        "current_step": "initialized",
        "workflow_status": "running",
        "errors": [],
    }


def get_state_summary(state: AgentState) -> dict:
    """Get human-readable summary of current state.
    
    Args:
        state: Current workflow state
        
    Returns:
        Dictionary with summary information
    """
    return {
        "step": state["current_step"],
        "status": state["workflow_status"],
        "sources_selected": len(state["selected_sources"]),
        "sources_retrieved": len(state["retrieved_sources"]),
        "outline_created": state["outline"] is not None,
        "draft_created": state["draft"] is not None,
        "error_count": len(state["errors"]),
    }
