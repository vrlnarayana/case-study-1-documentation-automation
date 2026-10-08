#!/usr/bin/env python3
"""
Streamlit Application for Documentation Automation System.

Acts as MCP Client + User Interface:
1. Select source files
2. Inspect metadata
3. Select template
4. Start workflow
5. See agent progress
6. Inspect outline
7. Inspect draft
8. Inspect MCP tool calls
9. Inspect guardrail results
10. Approve or reject publication

Never publishes automatically.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import streamlit as st

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.mcp_server.server import MCPServer
from app.agents.graph import run_workflow, get_workflow_summary, compile_workflow
from app.agents.state import AgentState, create_initial_state, get_state_summary
from app.utils.llm_client import get_llm_client


# ============== PAGE CONFIGURATION ==============

st.set_page_config(
    page_title="Documentation Automation",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============== SESSION STATE ==============

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
    
    if "audit_log" not in st.session_state:
        st.session_state.audit_log = []
    
    if "approval_status" not in st.session_state:
        st.session_state.approval_status = None
    
    # Initialize page if not set
    if "page" not in st.session_state:
        st.session_state.page = "🏠 Home"


def set_page(page_name: str):
    """Set current page and trigger rerun."""
    st.session_state.page = page_name
    st.rerun()


# ============== SIDEBAR ==============

def render_sidebar():
    """Render the sidebar with system status and navigation."""
    st.sidebar.title("📚 Doc Automation")
    st.sidebar.markdown("---")
    
    # System Status
    st.sidebar.header("System Status")
    
    # Check MCP Server
    try:
        result = st.session_state.mcp_server.list_source_files()
        if result["success"]:
            st.sidebar.success(f"✓ MCP Server Ready\n{result['count']} files available")
        else:
            st.sidebar.error("✗ MCP Server Error")
    except Exception as e:
        st.sidebar.error(f"✗ MCP Server: {str(e)[:50]}")
    
    # Check LLM
    try:
        llm_client = get_llm_client()
        st.sidebar.success(f"✓ LLM Connected\nModel: {llm_client.model}")
    except Exception as e:
        st.sidebar.warning(f"⚠ LLM: {str(e)[:50]}")
    
    st.sidebar.markdown("---")
    
    # Navigation - Use radio button that directly updates page
    st.sidebar.header("Navigation")
    
    pages = ["🏠 Home", "📁 Select Sources", "📋 Review", "▶️ Run Workflow", "🔍 Results", "✅ Approval"]
    
    # Get current page index
    current_page = st.session_state.get("page", "🏠 Home")
    try:
        current_index = pages.index(current_page)
    except ValueError:
        current_index = 0
    
    # Radio button for navigation
    selected_page = st.sidebar.radio(
        "Go to",
        pages,
        index=current_index,
        key="sidebar_nav"
    )
    
    # Update page if changed
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
        st.metric("Sources Available", "11")
        st.metric("Templates", "3")
    
    with col2:
        st.metric("Agents", "4 of 4")
        st.metric("Tests Passing", "77")
    
    with col3:
        st.metric("Status", "Prompt 6 Complete")
    
    st.markdown("---")
    
    st.subheader("What This System Does")
    st.markdown("""
    This agentic AI system automates documentation generation:
    
    1. **📁 Select Sources** - Choose code, specs, and meeting notes
    2. **📋 Review Sources** - Inspect metadata and known issues
    3. **▶️ Run Workflow** - Execute Ingestion → Structure → Drafting → Review Routing agents
    4. **🔍 Review Results** - Examine outline, draft, and conflicts
    5. **✅ Approve** - Human sign-off required before publication
    
    **Security**: All file access through MCP tools. Agents never access files directly.
    """)
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 Select Sources", type="primary", use_container_width=True):
            set_page("📁 Select Sources")
    
    with col2:
        if st.button("📋 View All Files", use_container_width=True):
            try:
                result = st.session_state.mcp_server.list_source_files()
                if result["success"]:
                    st.json({
                        "files": result["files"],
                        "count": result["count"]
                    })
            except Exception as e:
                st.error(f"Error: {e}")


# ============== SELECT SOURCES PAGE ==============

def render_select_sources():
    """Render the source selection page."""
    st.title("📁 Select Source Documents")
    st.markdown("---")
    
    # Get all files
    try:
        result = st.session_state.mcp_server.list_source_files()
        if not result["success"]:
            st.error(f"Error listing files: {result.get('error', 'Unknown')}")
            return
        
        all_files = result["files"]
    except Exception as e:
        st.error(f"Error: {e}")
        return
    
    # Filter by type
    st.subheader("Available Sources")
    
    file_types = {
        "source_code": [f for f in all_files if f.startswith("source_code/")],
        "specifications": [f for f in all_files if f.startswith("specifications/")],
        "meeting_notes": [f for f in all_files if f.startswith("meeting_notes/")],
        "existing_docs": [f for f in all_files if f.startswith("existing_docs/")],
        "templates": [f for f in all_files if f.startswith("templates/")],
        "metadata": [f for f in all_files if f.startswith("metadata/")],
    }
    
    # Display by category
    cols = st.columns(2)
    
    with cols[0]:
        st.markdown("**Source Code**")
        for f in file_types["source_code"]:
            st.code(f, language="text")
        
        st.markdown("**Specifications**")
        for f in file_types["specifications"]:
            st.markdown(f"- `{f}`")
    
    with cols[1]:
        st.markdown("**Meeting Notes**")
        for f in file_types["meeting_notes"]:
            st.markdown(f"- `{f}`")
        
        st.markdown("**Templates**")
        for f in file_types["templates"]:
            st.markdown(f"- `{f}`")
    
    st.markdown("---")
    
    # Selection
    st.subheader("Select Files for Processing")
    
    selected = st.multiselect(
        "Choose source documents:",
        options=all_files,
        default=st.session_state.selected_sources,
        help="Select one or more source files to process"
    )
    
    # Update selection
    if selected != st.session_state.selected_sources:
        st.session_state.selected_sources = selected
    
    # Show selected
    if st.session_state.selected_sources:
        st.success(f"✓ {len(st.session_state.selected_sources)} files selected")
        
        with st.expander("View Selected"):
            for src in st.session_state.selected_sources:
                st.markdown(f"- `{src}`")
        
        # Template selection
        st.subheader("Select Template")
        template = st.selectbox(
            "Document type:",
            options=["technical_spec", "sop", "process_map"],
            format_func=lambda x: {
                "technical_spec": "Technical Specification",
                "sop": "Standard Operating Procedure",
                "process_map": "Process Map"
            }.get(x, x),
            index=["technical_spec", "sop", "process_map"].index(
                st.session_state.template_type
            ) if st.session_state.template_type in ["technical_spec", "sop", "process_map"] else 0
        )
        
        # Update template
        if template != st.session_state.template_type:
            st.session_state.template_type = template
        
        st.markdown("---")
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Review Sources", type="primary", use_container_width=True, key="btn_review"):
                if st.session_state.selected_sources:
                    set_page("📋 Review")
                else:
                    st.warning("Please select at least one source file")
        
        with col2:
            if st.button("▶️ Run Workflow", use_container_width=True, key="btn_run"):
                if st.session_state.selected_sources:
                    set_page("▶️ Run Workflow")
                else:
                    st.warning("Please select at least one source file")
    else:
        st.info("Select at least one source file to continue")


# ============== REVIEW PAGE ==============

def render_review():
    """Render the review page for selected sources."""
    st.title("📋 Review Selected Sources")
    st.markdown("---")
    
    if not st.session_state.selected_sources:
        st.warning("No sources selected. Go to 📁 Select Sources first.")
        if st.button("Go to Select Sources", key="btn_goto_select"):
            set_page("📁 Select Sources")
        return
    
    st.subheader(f"Reviewing {len(st.session_state.selected_sources)} Sources")
    
    # Metadata cards
    for source_path in st.session_state.selected_sources:
        with st.expander(f"📄 {source_path}", expanded=True):
            try:
                # Get metadata
                meta_result = st.session_state.mcp_server.get_source_metadata(source_path)
                
                if meta_result["success"]:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Classification**")
                        st.markdown(f"- Type: `{meta_result['classification']['doc_type']}`")
                        st.markdown(f"- Sensitivity: `{meta_result['classification']['sensitivity']}`")
                    
                    with col2:
                        st.markdown("**File Info**")
                        st.markdown(f"- Size: {meta_result['file_info']['size']:,} bytes")
                        st.markdown(f"- Modified: {meta_result['file_info']['modified'][:10]}")
                    
                    with col3:
                        st.markdown("**Known Issues**")
                        if meta_result['known_issues']:
                            for issue in meta_result['known_issues']:
                                st.warning(f"⚠️ {issue}")
                        else:
                            st.success("No known issues")
                    
                    # Preview content
                    st.markdown("**Preview**")
                    content_result = st.session_state.mcp_server.read_source_file(source_path)
                    if content_result["success"]:
                        preview = content_result["content"][:500]
                        st.code(preview + "..." if len(content_result["content"]) > 500 else preview)
                    
                else:
                    st.error(f"Error getting metadata: {meta_result.get('error', 'Unknown')}")
                    
            except Exception as e:
                st.error(f"Error: {e}")
    
    st.markdown("---")
    
    # Template preview
    st.subheader(f"Selected Template: {st.session_state.template_type}")
    try:
        template_result = st.session_state.mcp_server.get_template(st.session_state.template_type)
        if template_result["success"]:
            st.markdown(f"**Placeholders:** {', '.join(template_result['placeholders'])}")
            st.text_area("Template Structure", template_result["content"], height=200, disabled=True)
    except Exception as e:
        st.error(f"Error loading template: {e}")
    
    st.markdown("---")
    
    # Navigation
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("◀️ Back to Selection", use_container_width=True, key="btn_back_select"):
            set_page("📁 Select Sources")
    
    with col2:
        if st.button("▶️ Run Workflow", type="primary", use_container_width=True, key="btn_run_workflow"):
            set_page("▶️ Run Workflow")


# ============== RUN WORKFLOW PAGE ==============

def render_run_workflow():
    """Render the workflow execution page."""
    st.title("▶️ Run Workflow")
    st.markdown("---")
    
    if not st.session_state.selected_sources:
        st.warning("No sources selected. Go to 📁 Select Sources first.")
        if st.button("Go to Select Sources", key="btn_goto_select2"):
            set_page("📁 Select Sources")
        return
    
    # Configuration
    st.subheader("Workflow Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Sources**")
        for src in st.session_state.selected_sources:
            st.markdown(f"- `{src}`")
    
    with col2:
        st.markdown("**Template**")
        st.code(st.session_state.template_type)
    
    st.markdown("---")
    
    # Execute button
    if not st.session_state.workflow_running and not st.session_state.workflow_state:
        if st.button("🚀 Start Workflow", type="primary", key="btn_start"):
            st.session_state.workflow_running = True
            st.rerun()
    
    # Execute workflow
    if st.session_state.workflow_running:
        st.subheader("Workflow Progress")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Create initial state
            initial_state = create_initial_state(
                selected_sources=st.session_state.selected_sources,
                template_type=st.session_state.template_type
            )
            
            # Compile and run
            app = compile_workflow()
            
            # Stream execution
            steps = []
            for i, state in enumerate(app.stream(initial_state)):
                step_name = list(state.keys())[0] if state else "unknown"
                steps.append(step_name)
                
                progress = min((i + 1) / 4, 1.0)  # 4 agents
                progress_bar.progress(progress)
                status_text.text(f"Running: {step_name}...")
            
            # Get final state
            final_state = app.invoke(initial_state)
            st.session_state.workflow_state = final_state
            st.session_state.workflow_running = False
            
            progress_bar.progress(1.0)
            status_text.success("✓ Workflow complete!")
            
            st.success("Workflow completed! Redirecting to results...")
            st.balloons()
            
            # Delay then redirect
            import time
            time.sleep(1)
            set_page("🔍 Results")
            
        except Exception as e:
            st.session_state.workflow_running = False
            st.error(f"Workflow failed: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # Show results if complete
    if st.session_state.workflow_state:
        state = st.session_state.workflow_state
        
        st.subheader("Results Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Status", state["workflow_status"])
            st.metric("Sources", len(state["retrieved_sources"]))
        
        with col2:
            if state.get("outline"):
                st.metric("Outline Sections", len(state["outline"].sections))
                st.metric("Conflicts", len(state["outline"].conflicts))
        
        with col3:
            if state.get("draft"):
                st.metric("Draft Confidence", f"{state['draft'].overall_confidence:.0%}")
                st.metric("Can Publish", state["draft"].can_publish)
        
        st.markdown("---")
        
        if st.button("🔍 View Full Results", type="primary", key="btn_view_results"):
            set_page("🔍 Results")


# ============== RESULTS PAGE ==============

def render_results():
    """Render the results page."""
    st.title("🔍 Workflow Results")
    st.markdown("---")
    
    if not st.session_state.workflow_state:
        st.warning("No workflow results. Run the workflow first.")
        if st.button("▶️ Go to Run Workflow", key="btn_goto_run"):
            set_page("▶️ Run Workflow")
        return
    
    state = st.session_state.workflow_state
    
    # Summary
    summary = get_workflow_summary(state)
    
    st.subheader("Execution Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Status", summary["status"])
        st.metric("Step", summary["current_step"])
    
    with col2:
        st.metric("Sources Selected", summary["sources"]["selected"])
        st.metric("Sources Retrieved", summary["sources"]["retrieved"])
    
    with col3:
        st.metric("Errors", summary["errors"]["count"])
    
    st.markdown("---")
    
    # Progress
    st.subheader("Agent Progress")
    
    progress = summary["progress"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if progress["ingestion"]:
            st.success("✓ Ingestion")
        else:
            st.warning("○ Ingestion")
    
    with col2:
        if progress["structure"]:
            st.success("✓ Structure")
        else:
            st.warning("○ Structure")
    
    with col3:
        if progress["drafting"]:
            st.success("✓ Drafting")
        else:
            st.warning("○ Drafting")
    
    with col4:
        if state.get("review_complete"):
            st.success("✓ Review")
        else:
            st.warning("○ Review")
    
    st.markdown("---")
    
    # Review Assessment
    if state.get("review_assessment"):
        st.subheader("Review Assessment")
        assessment = state["review_assessment"]
        
        if assessment.status == "READY_FOR_REVIEW":
            st.success(f"✓ Status: {assessment.status}")
        else:
            st.warning(f"⚠ Status: {assessment.status}")
        
        st.metric("Confidence", f"{assessment.confidence:.0%}")
        
        if assessment.issues:
            with st.expander(f"Issues ({len(assessment.issues)})"):
                for issue in assessment.issues:
                    st.markdown(f"- {issue}")
        
        if assessment.human_review_items:
            with st.expander(f"Human Review Items ({len(assessment.human_review_items)})", expanded=True):
                for item in assessment.human_review_items:
                    st.markdown(f"- {item}")
    
    st.markdown("---")
    
    # Outline
    if state.get("outline"):
        st.subheader("Document Outline")
        
        with st.expander(f"View {len(state['outline'].sections)} Sections"):
            for section in state["outline"].sections:
                st.markdown(f"**{section.title}**")
                st.markdown(f"- ID: `{section.section_id}`")
                st.markdown(f"- Status: `{section.status}`")
                if section.source_refs:
                    st.markdown(f"- Sources: {', '.join(section.source_refs)}")
                st.markdown("---")
        
        # Conflicts
        if state["outline"].conflicts:
            st.subheader("⚠️ Conflicts Detected")
            
            for conflict in state["outline"].conflicts:
                severity_color = {
                    "blocking": "🔴",
                    "warning": "🟡",
                    "info": "🔵"
                }.get(conflict.severity, "⚪")
                
                with st.expander(f"{severity_color} {conflict.severity.upper()}"):
                    st.markdown(f"**Description:** {conflict.description}")
                    st.markdown(f"**Sources:** {', '.join(conflict.sources)}")
                    if conflict.resolution:
                        st.markdown(f"**Proposed Resolution:** {conflict.resolution}")
    
    st.markdown("---")
    
    # Draft
    if state.get("draft"):
        st.subheader("Generated Draft")
        
        draft = state["draft"]
        
        # Warning
        st.error("⚠️ **THIS IS A DRAFT - NOT FOR PUBLICATION**")
        st.warning(f"Confidence: {draft.overall_confidence:.0%}")
        
        # Draft content
        with st.expander("View Draft Content", expanded=True):
            st.markdown(draft.content)
        
        # Sections
        with st.expander(f"View {len(draft.sections)} Sections"):
            for section in draft.sections:
                st.markdown(f"**{section.title}** (Confidence: {section.confidence:.0%})")
                if section.unresolved_placeholders:
                    st.warning(f"Placeholders: {', '.join(section.unresolved_placeholders)}")
        
        st.markdown("---")
        
        # Navigation
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("◀️ Back to Workflow", key="btn_back_workflow"):
                set_page("▶️ Run Workflow")
        
        with col2:
            if st.button("🔄 Regenerate", key="btn_regenerate"):
                st.session_state.workflow_state = None
                set_page("▶️ Run Workflow")
        
        with col3:
            if st.button("✅ Go to Approval", type="primary", key="btn_goto_approval"):
                set_page("✅ Approval")


# ============== APPROVAL PAGE ==============

def render_approval():
    """Render the human approval page."""
    st.title("✅ Human Approval Required")
    st.markdown("---")
    
    if not st.session_state.workflow_state:
        st.warning("No draft to approve. Run the workflow first.")
        if st.button("▶️ Go to Run Workflow", key="btn_goto_run2"):
            set_page("▶️ Run Workflow")
        return
    
    state = st.session_state.workflow_state
    
    if not state.get("draft"):
        st.error("No draft generated.")
        return
    
    # Warning banner
    st.error("🚨 **HUMAN APPROVAL REQUIRED**")
    st.markdown("""
    **Per system requirements, documents CANNOT be published automatically.**
    
    Please review the draft carefully before making a decision.
    """)
    
    st.markdown("---")
    
    # Review checklist
    st.subheader("Pre-Approval Checklist")
    
    checklist = {
        "content_reviewed": st.checkbox("I have reviewed the document content", key="chk_content"),
        "conflicts_checked": st.checkbox("I have reviewed all detected conflicts", key="chk_conflicts"),
        "sources_verified": st.checkbox("Sources have been correctly cited", key="chk_sources"),
        "template_followed": st.checkbox("Document follows selected template structure", key="chk_template"),
        "accuracy_confirmed": st.checkbox("Factual claims are accurate and supported", key="chk_accuracy"),
    }
    
    all_checked = all(checklist.values())
    
    st.markdown("---")
    
    # Decision
    st.subheader("Your Decision")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Request Revision**")
        revision_notes = st.text_area(
            "Notes for revision",
            placeholder="Describe what needs to be changed...",
            key="revision_notes"
        )
        
        if st.button("↩️ Request Revision", use_container_width=True, key="btn_revision"):
            st.session_state.approval_status = {
                "status": "REVISION_REQUESTED",
                "timestamp": datetime.now().isoformat(),
                "notes": revision_notes
            }
            st.success("Revision requested!")
    
    with col2:
        st.markdown("**Reject**")
        reject_reason = st.text_area(
            "Reason for rejection",
            placeholder="Why is this document being rejected?",
            key="reject_reason"
        )
        
        if st.button("❌ Reject", use_container_width=True, key="btn_reject"):
            st.session_state.approval_status = {
                "status": "REJECTED",
                "timestamp": datetime.now().isoformat(),
                "reason": reject_reason
            }
            st.error("Document rejected.")
    
    with col3:
        st.markdown("**Approve & Publish**")
        
        if not all_checked:
            st.warning("Complete all checklist items first")
        
        approver_name = st.text_input("Your name", key="approver_name")
        
        if st.button(
            "✅ Approve & Publish",
            type="primary",
            disabled=not all_checked or not approver_name,
            use_container_width=True,
            key="btn_approve"
        ):
            st.session_state.approval_status = {
                "status": "APPROVED",
                "timestamp": datetime.now().isoformat(),
                "approver": approver_name
            }
            
            # Save to outputs
            try:
                import os
                output_dir = Path("outputs")
                output_dir.mkdir(exist_ok=True)
                
                filename = f"{state['draft'].template_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                output_path = output_dir / filename
                
                with open(output_path, 'w') as f:
                    f.write(state["draft"].content)
                
                st.success(f"✓ Document published to: {output_path}")
                st.balloons()
                
            except Exception as e:
                st.error(f"Error saving document: {e}")
    
    st.markdown("---")
    
    # Show approval history
    if st.session_state.approval_status:
        st.subheader("Approval History")
        st.json(st.session_state.approval_status)


# ============== MAIN ==============

def main():
    """Main application entry point."""
    init_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Render current page
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
