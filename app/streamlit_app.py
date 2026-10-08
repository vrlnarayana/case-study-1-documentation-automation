#!/usr/bin/env python3
"""
Streamlit Application for Documentation Automation System.

Acts as MCP Client + User Interface with Real-time Monitoring.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from app.mcp_server.server import MCPServer
from app.agents.graph import run_workflow, get_workflow_summary, compile_workflow
from app.agents.state import AgentState, create_initial_state
from app.utils.llm_client import get_llm_client


st.set_page_config(
    page_title="Documentation Automation",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize Streamlit session state."""
    if "mcp_server" not in st.session_state:
        st.session_state.mcp_server = MCPServer()
    
    if "selected_sources" not in st.session_state:
        st.session_state.selected_sources = []
    
    if "template_type" not in st.session_state:
        st.session_state.template_type = "technical_spec"
    
    if "workflow_state" not in st.session_state:
        st.session_state.workflow_state = None
    
    if "workflow_running" not in st.session_state:
        st.session_state.workflow_running = False
    
    if "workflow_step" not in st.session_state:
        st.session_state.workflow_step = 0
    
    if "mcp_calls" not in st.session_state:
        st.session_state.mcp_calls = []
    
    if "page" not in st.session_state:
        st.session_state.page = "🏠 Home"


def set_page(page_name: str):
    """Set current page and trigger rerun."""
    st.session_state.page = page_name
    st.rerun()


def log_mcp_call(tool_name: str, params: Dict, success: bool, error: str = None):
    """Log an MCP tool call."""
    call_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "params": str(params)[:100],
        "success": success,
        "error": error
    }
    st.session_state.mcp_calls.insert(0, call_entry)
    if len(st.session_state.mcp_calls) > 20:
        st.session_state.mcp_calls = st.session_state.mcp_calls[:20]


def reset_workflow():
    """Reset workflow state."""
    st.session_state.workflow_running = False
    st.session_state.workflow_step = 0
    st.session_state.workflow_state = None
    st.session_state.mcp_calls = []


# ============== SIDEBAR ==============

def render_sidebar():
    """Render the sidebar with system status and navigation."""
    st.sidebar.title("📚 Doc Automation")
    st.sidebar.markdown("---")
    
    # System Status
    st.sidebar.header("🔧 System Status")
    
    # MCP Server
    try:
        result = st.session_state.mcp_server.list_source_files()
        if result["success"]:
            st.sidebar.success(f"✅ MCP Server\n{result['count']} files available")
        else:
            st.sidebar.error("❌ MCP Error")
    except Exception as e:
        st.sidebar.error(f"❌ MCP: {str(e)[:30]}")
    
    # LLM
    try:
        llm_client = get_llm_client()
        st.sidebar.success(f"✅ LLM: {llm_client.model}")
    except Exception as e:
        st.sidebar.warning(f"⚠️ LLM: {str(e)[:30]}")
    
    st.sidebar.markdown("---")
    
    # Recent MCP Calls
    if st.session_state.mcp_calls:
        st.sidebar.header("📡 Recent MCP Calls")
        for call in st.session_state.mcp_calls[:5]:
            status = "✅" if call["success"] else "❌"
            st.sidebar.markdown(f"{status} `{call['tool']}`")
    
    st.sidebar.markdown("---")
    
    # Navigation
    st.sidebar.header("Navigation")
    pages = ["🏠 Home", "📁 Select Sources", "📋 Review", "▶️ Run Workflow", "🔍 Results", "✅ Approval"]
    
    current_page = st.session_state.get("page", "🏠 Home")
    try:
        current_index = pages.index(current_page)
    except ValueError:
        current_index = 0
    
    selected_page = st.sidebar.radio("Go to", pages, index=current_index)
    
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Documentation Automation System v1.0")


# ============== HOME PAGE ==============

def render_home():
    """Render the home page."""
    st.title("Welcome to Documentation Automation")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sources", "11")
    with col2:
        st.metric("MCP Calls", len(st.session_state.mcp_calls))
    with col3:
        st.metric("Tests", "77")
    
    st.markdown("---")
    
    if st.session_state.workflow_running:
        st.info("⏳ Workflow is running...")
    elif st.session_state.workflow_state:
        st.success("✅ Workflow completed!")
    else:
        st.warning("No workflow running. Select sources to begin.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📁 Select Sources", type="primary", use_container_width=True):
            set_page("📁 Select Sources")
    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            reset_workflow()
            st.session_state.selected_sources = []
            st.rerun()


# ============== SELECT SOURCES PAGE ==============

def render_select_sources():
    """Render the source selection page."""
    st.title("📁 Select Source Documents")
    st.markdown("---")
    
    try:
        result = st.session_state.mcp_server.list_source_files()
        log_mcp_call("list_source_files", {}, result["success"])
        
        if not result["success"]:
            st.error(f"Error: {result.get('error', 'Unknown')}")
            return
        
        all_files = result["files"]
    except Exception as e:
        st.error(f"Error: {e}")
        return
    
    st.success(f"✅ MCP Server responded: {len(all_files)} files")
    
    selected = st.multiselect(
        "Choose source documents:",
        options=all_files,
        default=st.session_state.selected_sources
    )
    
    if selected != st.session_state.selected_sources:
        st.session_state.selected_sources = selected
    
    if st.session_state.selected_sources:
        st.success(f"✓ {len(st.session_state.selected_sources)} files selected")
        
        template = st.selectbox(
            "Document type:",
            options=["technical_spec", "sop", "process_map"],
            index=["technical_spec", "sop", "process_map"].index(st.session_state.template_type)
            if st.session_state.template_type in ["technical_spec", "sop", "process_map"] else 0
        )
        
        if template != st.session_state.template_type:
            st.session_state.template_type = template
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Review Sources", type="primary", use_container_width=True):
                set_page("📋 Review")
        with col2:
            if st.button("▶️ Run Workflow", use_container_width=True):
                set_page("▶️ Run Workflow")
    else:
        st.info("Select at least one source file")


# ============== REVIEW PAGE ==============

def render_review():
    """Render the review page."""
    st.title("📋 Review Selected Sources")
    st.markdown("---")
    
    if not st.session_state.selected_sources:
        st.warning("No sources selected.")
        if st.button("Go to Select Sources"):
            set_page("📁 Select Sources")
        return
    
    for source_path in st.session_state.selected_sources:
        with st.expander(f"📄 {source_path}", expanded=True):
            try:
                meta = st.session_state.mcp_server.get_source_metadata(source_path)
                log_mcp_call("get_source_metadata", {"path": source_path}, meta["success"])
                
                if meta["success"]:
                    st.markdown(f"**Type:** `{meta['classification']['doc_type']}`")
                    st.markdown(f"**Size:** {meta['file_info']['size']:,} bytes")
                
            except Exception as e:
                st.error(f"Error: {e}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Back", use_container_width=True):
            set_page("📁 Select Sources")
    with col2:
        if st.button("▶️ Run Workflow", type="primary", use_container_width=True):
            set_page("▶️ Run Workflow")


# ============== RUN WORKFLOW PAGE ==============

def render_run_workflow():
    """Render the workflow execution page."""
    st.title("▶️ Run Workflow")
    st.markdown("---")
    
    if not st.session_state.selected_sources:
        st.warning("No sources selected.")
        if st.button("Go to Select Sources"):
            set_page("📁 Select Sources")
        return
    
    # Show configuration
    st.subheader("Configuration")
    st.markdown(f"**Sources:** {len(st.session_state.selected_sources)}")
    st.markdown(f"**Template:** `{st.session_state.template_type}`")
    
    st.markdown("---")
    
    # Start button
    if not st.session_state.workflow_running and not st.session_state.workflow_state:
        if st.button("🚀 Start Workflow", type="primary"):
            reset_workflow()
            st.session_state.workflow_running = True
            st.rerun()
    
    # Run workflow
    if st.session_state.workflow_running:
        st.subheader("⏳ Workflow Progress")
        
        # Progress bar
        progress_bar = st.progress(0)
        
        # Status area
        status_area = st.empty()
        
        # MCP calls area
        mcp_area = st.empty()
        
        try:
            from app.agents.nodes import (
                ingestion_agent, structure_agent, 
                drafting_agent, review_routing_agent
            )
            
            # Create initial state
            initial_state = create_initial_state(
                selected_sources=st.session_state.selected_sources,
                template_type=st.session_state.template_type
            )
            
            # Step 1: Ingestion
            status_area.info("📥 Step 1/4: Ingestion Agent - Retrieving sources...")
            progress_bar.progress(0.1)
            
            state = ingestion_agent(initial_state)
            
            # Log MCP calls
            for source in state["retrieved_sources"]:
                log_mcp_call("read_source_file", {"path": source.path}, True)
                log_mcp_call("get_source_metadata", {"path": source.path}, True)
            
            if not state["ingestion_complete"]:
                st.error("❌ Ingestion failed!")
                st.session_state.workflow_running = False
                return
            
            status_area.success(f"✅ Ingestion complete - Retrieved {len(state['retrieved_sources'])} sources")
            progress_bar.progress(0.25)
            
            # Step 2: Structure
            status_area.info("🏗️ Step 2/4: Structure Agent - Creating outline...")
            progress_bar.progress(0.3)
            
            state = structure_agent(state)
            log_mcp_call("get_template", {"template_name": st.session_state.template_type}, True)
            
            if not state["structure_complete"]:
                st.error("❌ Structure failed!")
                st.session_state.workflow_running = False
                return
            
            status_area.success(f"✅ Structure complete - Created {len(state['outline'].sections)} sections")
            progress_bar.progress(0.5)
            
            # Step 3: Drafting
            status_area.info("✍️ Step 3/4: Drafting Agent - Generating content... (This may take 1-2 minutes)")
            progress_bar.progress(0.6)
            
            state = drafting_agent(state)
            
            if not state["drafting_complete"]:
                st.error("❌ Drafting failed!")
                st.session_state.workflow_running = False
                return
            
            status_area.success(f"✅ Drafting complete - Generated {len(state['draft'].sections)} sections")
            progress_bar.progress(0.8)
            
            # Step 4: Review
            status_area.info("🔍 Step 4/4: Review Agent - Assessing quality...")
            progress_bar.progress(0.9)
            
            state = review_routing_agent(state)
            
            if not state["review_complete"]:
                st.error("❌ Review failed!")
                st.session_state.workflow_running = False
                return
            
            # Complete
            st.session_state.workflow_state = state
            st.session_state.workflow_running = False
            
            progress_bar.progress(1.0)
            status_area.empty()
            
            st.success("🎉 Workflow completed successfully!")
            st.balloons()
            
            st.markdown("---")
            st.subheader("📊 Summary")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Sources", len(state["retrieved_sources"]))
            with col2:
                st.metric("Sections", len(state["outline"].sections))
            with col3:
                st.metric("Confidence", f"{state['draft'].overall_confidence:.0%}")
            
            if st.button("🔍 View Full Results", type="primary"):
                set_page("🔍 Results")
                
        except Exception as e:
            st.session_state.workflow_running = False
            st.error(f"Workflow failed: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Show results if complete
    if st.session_state.workflow_state and not st.session_state.workflow_running:
        state = st.session_state.workflow_state
        
        st.subheader("Results Summary")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", state["workflow_status"])
        with col2:
            if state.get("draft"):
                st.metric("Confidence", f"{state['draft'].overall_confidence:.0%}")
        with col3:
            if state.get("review_assessment"):
                st.metric("Review", state["review_assessment"].status)
        
        if st.button("🔍 View Full Results"):
            set_page("🔍 Results")


# ============== RESULTS PAGE ==============

def render_results():
    """Render the results page."""
    st.title("🔍 Workflow Results")
    st.markdown("---")
    
    if not st.session_state.workflow_state:
        st.warning("No workflow results.")
        if st.button("Run Workflow"):
            set_page("▶️ Run Workflow")
        return
    
    state = st.session_state.workflow_state
    
    st.subheader("Execution Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", state["workflow_status"])
    with col2:
        st.metric("Sources", len(state["retrieved_sources"]))
    with col3:
        st.metric("MCP Calls", len(st.session_state.mcp_calls))
    
    st.markdown("---")
    
    if state.get("draft"):
        st.subheader("📄 Generated Document")
        
        draft = state["draft"]
        
        st.error("⚠️ DRAFT - REQUIRES HUMAN REVIEW")
        
        with st.expander("View Full Document", expanded=True):
            st.markdown(draft.content)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Regenerate"):
                reset_workflow()
                st.session_state.workflow_state = None
                set_page("▶️ Run Workflow")
        with col2:
            if st.button("✅ Go to Approval", type="primary"):
                set_page("✅ Approval")


# ============== APPROVAL PAGE ==============

def render_approval():
    """Render the approval page."""
    st.title("✅ Human Approval Required")
    st.markdown("---")
    
    if not st.session_state.workflow_state:
        st.warning("No draft to approve.")
        if st.button("Run Workflow"):
            set_page("▶️ Run Workflow")
        return
    
    state = st.session_state.workflow_state
    
    if not state.get("draft"):
        st.error("No draft generated.")
        return
    
    st.subheader("📡 Generation Log")
    st.markdown(f"**MCP Calls:** {len(st.session_state.mcp_calls)}")
    
    st.markdown("---")
    
    st.error("🚨 HUMAN APPROVAL REQUIRED")
    
    checklist = {
        "content": st.checkbox("I reviewed the content", key="chk_content"),
        "sources": st.checkbox("Sources cited correctly", key="chk_sources"),
        "accuracy": st.checkbox("Claims are accurate", key="chk_accuracy"),
    }
    
    all_checked = all(checklist.values())
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("↩️ Request Revision", use_container_width=True):
            st.success("Revision requested!")
    
    with col2:
        if st.button("❌ Reject", use_container_width=True):
            st.error("Document rejected.")
    
    with col3:
        approver_name = st.text_input("Your name", key="approver_name")
        if st.button("✅ Approve", type="primary", disabled=not all_checked or not approver_name, use_container_width=True):
            try:
                output_dir = Path("outputs")
                output_dir.mkdir(exist_ok=True)
                
                filename = f"{state['draft'].template_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                output_path = output_dir / filename
                
                with open(output_path, 'w') as f:
                    f.write(state["draft"].content)
                
                st.success(f"✓ Published to: {output_path}")
                st.balloons()
                
            except Exception as e:
                st.error(f"Error: {e}")


# ============== MAIN ==============

def main():
    """Main entry point."""
    init_session_state()
    render_sidebar()
    
    page = st.session_state.page
    
    if page == "🏠 Home":
        render_home()
    elif page == "📁 Select Sources":
        render_select_sources()
    elif page == "📋 Review":
        render_review()
    elif page == "▶️ Run Workflow":
        render_run_workflow()
    elif page == "🔍 Results":
        render_results()
    elif page == "✅ Approval":
        render_approval()


if __name__ == "__main__":
    main()
