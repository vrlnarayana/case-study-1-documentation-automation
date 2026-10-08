"""
LangGraph workflow definition for Documentation Automation.
Implements: Ingestion Agent → Structure Agent → Drafting Agent
"""

from typing import Literal, Any
from langgraph.graph import StateGraph, END

from app.agents.state import AgentState, create_initial_state
from app.agents.nodes import ingestion_agent, structure_agent, drafting_agent, review_routing_agent


# ============== CONDITIONAL FUNCTIONS ==============

def should_continue_after_ingestion(state: AgentState) -> Literal["structure", "end"]:
    """Determine next step after ingestion.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name
    """
    # Check if ingestion completed with at least some sources
    if state.get("ingestion_complete") and state.get("retrieved_sources"):
        # Even with errors, if we have sources we can continue
        return "structure"
    else:
        # No sources retrieved - halt
        return "end"


def should_continue_after_structure(state: AgentState) -> Literal["drafting", "end"]:
    """Determine next step after structure.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name
    """
    # Check if outline was created
    if state.get("structure_complete") and state.get("outline"):
        return "drafting"
    else:
        # Failed to create outline
        return "end"


def should_continue_after_drafting(state: AgentState) -> Literal["review", "end"]:
    """Determine next step after drafting.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name
    """
    # Check if draft was created
    if state.get("drafting_complete") and state.get("draft"):
        return "review"
    else:
        # Failed to create draft
        return "end"


def should_continue_after_review(state: AgentState) -> Literal["complete", "end"]:
    """Determine next step after review routing.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name
    """
    # Always complete (even if NEEDS_REVISION, workflow is done)
    # Human will decide whether to revise
    if state.get("review_complete"):
        return "complete"
    else:
        return "end"


# ============== GRAPH CONSTRUCTION ==============

def create_workflow_graph() -> StateGraph:
    """Create the LangGraph workflow.
    
    Returns:
        Configured StateGraph ready for compilation
    """
    # Create the graph with our state type
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("ingestion", ingestion_agent)
    workflow.add_node("structure", structure_agent)
    workflow.add_node("drafting", drafting_agent)
    workflow.add_node("review", review_routing_agent)
    
    # Define edges
    # Start -> Ingestion
    workflow.set_entry_point("ingestion")
    
    # Ingestion -> Structure (conditional)
    workflow.add_conditional_edges(
        "ingestion",
        should_continue_after_ingestion,
        {
            "structure": "structure",
            "end": END
        }
    )
    
    # Structure -> Drafting (conditional)
    workflow.add_conditional_edges(
        "structure",
        should_continue_after_structure,
        {
            "drafting": "drafting",
            "end": END
        }
    )
    
    # Drafting -> Review (conditional)
    workflow.add_conditional_edges(
        "drafting",
        should_continue_after_drafting,
        {
            "review": "review",
            "end": END
        }
    )
    
    # Review -> End (conditional)
    workflow.add_conditional_edges(
        "review",
        should_continue_after_review,
        {
            "complete": END,
            "end": END
        }
    )
    
    return workflow


def compile_workflow() -> Any:
    """Compile the workflow graph.
    
    Returns:
        Compiled graph ready for execution
    """
    workflow = create_workflow_graph()
    return workflow.compile()


# ============== EXECUTION FUNCTIONS ==============

def run_workflow(
    selected_sources: list[str],
    template_type: Literal["technical_spec", "sop", "process_map"]
) -> AgentState:
    """Execute the complete workflow.
    
    Args:
        selected_sources: List of source file paths
        template_type: Type of document to generate
        
    Returns:
        Final workflow state
    """
    print("=" * 60)
    print("DOCUMENTATION AUTOMATION WORKFLOW")
    print("=" * 60)
    print(f"Sources: {len(selected_sources)}")
    print(f"Template: {template_type}")
    print("=" * 60)
    
    # Create initial state
    initial_state = create_initial_state(selected_sources, template_type)
    
    # Compile and run workflow
    app = compile_workflow()
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETE")
    print("=" * 60)
    print(f"Status: {final_state['workflow_status']}")
    print(f"Final Step: {final_state['current_step']}")
    print(f"Sources Retrieved: {len(final_state['retrieved_sources'])}")
    print(f"Outline Created: {final_state['outline'] is not None}")
    print(f"Draft Created: {final_state['draft'] is not None}")
    print(f"Review Complete: {final_state['review_complete']}")
    print(f"Total Errors: {len(final_state['errors'])}")
    
    if final_state.get("draft"):
        draft = final_state["draft"]
        print(f"Draft Confidence: {draft.overall_confidence:.2f}")
        print(f"Can Publish: {draft.can_publish}")
    
    if final_state.get("review_assessment"):
        assessment = final_state["review_assessment"]
        print(f"Review Status: {assessment.status}")
        print(f"Review Confidence: {assessment.confidence:.2f}")
        print(f"Issues Found: {len(assessment.issues)}")
        print(f"Human Review Items: {len(assessment.human_review_items)}")
    
    print("=" * 60)
    
    return final_state


def run_workflow_stream(
    selected_sources: list[str],
    template_type: Literal["technical_spec", "sop", "process_map"]
):
    """Execute workflow with streaming for real-time updates.
    
    Args:
        selected_sources: List of source file paths
        template_type: Type of document to generate
        
    Yields:
        State updates after each node execution
    """
    initial_state = create_initial_state(selected_sources, template_type)
    
    app = compile_workflow()
    
    for state in app.stream(initial_state):
        yield state


# ============== WORKFLOW STATUS HELPERS ==============

def get_workflow_summary(state: AgentState) -> dict:
    """Get human-readable summary of workflow execution.
    
    Args:
        state: Final workflow state
        
    Returns:
        Summary dictionary
    """
    summary = {
        "status": state["workflow_status"],
        "current_step": state["current_step"],
        "sources": {
            "selected": len(state["selected_sources"]),
            "retrieved": len(state["retrieved_sources"]),
            "list": [s.path for s in state["retrieved_sources"]]
        },
        "progress": {
            "ingestion": state["ingestion_complete"],
            "structure": state["structure_complete"],
            "drafting": state["drafting_complete"]
        },
        "errors": {
            "count": len(state["errors"]),
            "messages": [e.message for e in state["errors"]]
        }
    }
    
    if state.get("outline"):
        summary["outline"] = {
            "title": state["outline"].title,
            "sections": len(state["outline"].sections),
            "conflicts": len(state["outline"].conflicts)
        }
    
    if state.get("draft"):
        summary["draft"] = {
            "title": state["draft"].title,
            "sections": len(state["draft"].sections),
            "confidence": state["draft"].overall_confidence,
            "can_publish": state["draft"].can_publish,
            "content_length": len(state["draft"].content)
        }
    
    if state.get("review_assessment"):
        summary["review"] = {
            "status": state["review_assessment"].status,
            "confidence": state["review_assessment"].confidence,
            "issues_count": len(state["review_assessment"].issues),
            "human_items_count": len(state["review_assessment"].human_review_items)
        }
    
    return summary


# Make app available at module level
app = compile_workflow()
