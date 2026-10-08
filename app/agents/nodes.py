"""
Agent node implementations for the Documentation Automation workflow.
These are the core agent functions that execute within the LangGraph.
"""

from typing import Dict, Any, List
from datetime import datetime

from app.agents.state import (
    AgentState,
    SourceDocument,
    DocumentOutline,
    DocumentDraft,
    OutlineSection,
    DraftSection,
    Conflict,
    WorkflowError,
    ReviewAssessment,
)
from app.agents.prompts import get_template_structure
from app.mcp_server.tools.file_tools import (
    list_source_files,
    read_source_file,
    get_template,
    get_source_metadata,
    log_tool_call,
)
from app.utils.llm_client import get_llm_client


# ============== INGESTION AGENT ==============

def ingestion_agent(state: AgentState) -> AgentState:
    """Ingestion Agent: Retrieve and classify source documents via MCP.
    
    This agent:
    1. Retrieves each selected source file via MCP tools
    2. Classifies documents by type and sensitivity
    3. Populates retrieved_sources in state
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with retrieved sources
    """
    print(f"\n[Ingestion Agent] Starting for {len(state['selected_sources'])} sources...")
    
    errors = []
    retrieved = []
    
    for source_path in state["selected_sources"]:
        print(f"  - Retrieving: {source_path}")
        
        try:
            # Step 1: Read file content via MCP
            file_result = read_source_file(source_path)
            log_tool_call("read_source_file", {"path": source_path}, file_result)
            
            if not file_result.get("success"):
                error_msg = f"Failed to read {source_path}: {file_result.get('error', {}).get('message')}"
                print(f"    ERROR: {error_msg}")
                errors.append(WorkflowError(
                    step="ingestion",
                    message=error_msg,
                    details=str(file_result.get("error"))
                ))
                continue
            
            # Step 2: Get metadata via MCP
            metadata_result = get_source_metadata(source_path)
            log_tool_call("get_source_metadata", {"path": source_path}, metadata_result)
            
            if not metadata_result.get("success"):
                print(f"    WARNING: No metadata for {source_path}")
                classification = "standard"
                sensitivity = "internal"
                doc_type = "unknown"
            else:
                classification = metadata_result["classification"].get("classification", "standard")
                sensitivity = metadata_result["classification"].get("sensitivity", "internal")
                doc_type = metadata_result["classification"].get("doc_type", "unknown")
            
            # Step 3: Create SourceDocument
            source_doc = SourceDocument(
                path=source_path,
                content=file_result["content"],
                doc_type=doc_type,
                classification=classification,
                sensitivity=sensitivity,
            )
            
            retrieved.append(source_doc)
            print(f"    SUCCESS: Retrieved {len(source_doc.content)} chars, type={doc_type}")
            
        except Exception as e:
            error_msg = f"Exception retrieving {source_path}: {str(e)}"
            print(f"    ERROR: {error_msg}")
            errors.append(WorkflowError(
                step="ingestion",
                message=error_msg,
                details=str(e)
            ))
    
    # Update state
    state["retrieved_sources"] = retrieved
    state["ingestion_complete"] = True
    state["ingestion_errors"] = errors
    state["current_step"] = "ingestion_complete"
    
    if errors:
        state["errors"].extend(errors)
    
    # Set workflow status based on results
    if not retrieved:
        state["workflow_status"] = "failed"
    
    print(f"\n[Ingestion Agent] Complete: {len(retrieved)} sources retrieved, {len(errors)} errors")
    return state


# ============== STRUCTURE AGENT ==============

def structure_agent(state: AgentState) -> AgentState:
    """Structure Agent: Create outline and identify conflicts.
    
    This agent:
    1. Gets the template structure
    2. Creates document outline from sources
    3. Detects contradictions between sources
    4. Identifies missing information
    
    Args:
        state: Current workflow state with retrieved sources
        
    Returns:
        Updated state with document outline
    """
    print(f"\n[Structure Agent] Creating outline for {state['template_type']}...")
    
    errors = []
    
    # Check if we have sources to work with
    if not state.get("retrieved_sources"):
        error_msg = "No sources available to create outline"
        print(f"  ERROR: {error_msg}")
        errors.append(WorkflowError(
            step="structure",
            message=error_msg
        ))
        state["structure_errors"] = errors
        state["errors"].extend(errors)
        state["workflow_status"] = "failed"
        return state
    
    # Get template structure
    template_structure = get_template_structure(state["template_type"])
    
    # Get template content via MCP
    template_result = get_template(state["template_type"])
    log_tool_call("get_template", {"template_name": state["template_type"]}, template_result)
    
    if not template_result.get("success"):
        error_msg = f"Failed to get template: {template_result.get('error', {}).get('message')}"
        print(f"  ERROR: {error_msg}")
        errors.append(WorkflowError(
            step="structure",
            message=error_msg
        ))
        state["structure_errors"] = errors
        state["errors"].extend(errors)
        return state
    
    # Create outline sections based on template
    sections = []
    structure_lines = template_structure.strip().split('\n')
    section_id = 0
    
    for line in structure_lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Parse section number and title
            # Format: "1. Section Title"
            if '. ' in line:
                section_title = line.split('. ', 1)[1] if '. ' in line else line
            else:
                section_title = line
            
            section_id += 1
            
            # Map sources to sections (simplified logic)
            source_refs = [s.path for s in state["retrieved_sources"]]
            
            section = OutlineSection(
                section_id=f"sec_{section_id:02d}",
                title=section_title,
                content_summary=f"Content for {section_title} based on source materials",
                source_refs=source_refs[:2],  # Limit refs for demo
                status="incomplete"
            )
            sections.append(section)
            print(f"  - Created section: {section.title}")
    
    # Detect conflicts (simplified stub)
    conflicts = detect_conflicts_stub(state["retrieved_sources"])
    
    # Create document outline
    outline = DocumentOutline(
        template_type=state["template_type"],
        title=f"Generated {state['template_type'].replace('_', ' ').title()}",
        sections=sections,
        conflicts=conflicts,
        missing_info=[]  # Would be populated by more sophisticated analysis
    )
    
    # Update state
    state["outline"] = outline
    state["structure_complete"] = True
    state["structure_errors"] = errors
    state["current_step"] = "structure_complete"
    
    if errors:
        state["errors"].extend(errors)
    
    # Set workflow status based on results
    if not outline or not sections:
        state["workflow_status"] = "failed"
    
    print(f"\n[Structure Agent] Complete: {len(sections)} sections, {len(conflicts)} conflicts")
    return state


def detect_conflicts_stub(sources: List[SourceDocument]) -> List[Conflict]:
    """STUB: Detect contradictions between sources.
    
    Full implementation in later iterations.
    
    Args:
        sources: List of retrieved sources
        
    Returns:
        List of detected conflicts
    """
    conflicts = []
    
    # Check for known contradictions based on metadata
    has_billing_reqs = any("billing_requirements" in s.path for s in sources)
    has_meeting_notes = any("billing-system-review" in s.path for s in sources)
    
    if has_billing_reqs and has_meeting_notes:
        # Known contradiction from seed data
        conflicts.append(Conflict(
            description="Approval threshold discrepancy: Spec says $5,000 but meeting decision says $10,000",
            sources=["specifications/billing_requirements.md", "meeting_notes/billing-system-review.md"],
            severity="warning",
            resolution="Meeting decision should take precedence per DEC-001"
        ))
        print("  [Conflict Detected] Approval threshold discrepancy")
    
    return conflicts


# ============== DRAFTING AGENT ==============

def drafting_agent(state: AgentState) -> AgentState:
    """Drafting Agent: Generate document draft from outline.
    
    This agent:
    1. Processes outline sections sequentially
    2. Generates content for each section
    3. Applies template formatting
    4. Marks unresolved placeholders
    5. CANNOT publish directly
    
    Args:
        state: Current workflow state with outline
        
    Returns:
        Updated state with document draft
    """
    print(f"\n[Drafting Agent] Generating professional draft...")
    
    errors = []
    
    if not state.get("outline"):
        error_msg = "No outline available for drafting"
        print(f"  ERROR: {error_msg}")
        errors.append(WorkflowError(
            step="drafting",
            message=error_msg
        ))
        state["drafting_errors"] = errors
        state["errors"].extend(errors)
        return state
    
    outline = state["outline"]
    sources = state["retrieved_sources"]
    
    # Generate sections
    draft_sections = []
    full_content_parts = []
    
    # Add professional document header
    header = f"""# {outline.title}

| Field | Value |
|-------|-------|
| **Document Type** | {outline.template_type.replace('_', ' ').title()} |
| **Generated** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| **Status** | DRAFT - Requires Human Review |
| **Classification** | Internal |

---

## Executive Summary

This document provides comprehensive documentation based on source materials. 
It was generated through an automated documentation system and requires human 
review before publication.

**Source Documents:** {len(sources)} files processed
**Template Used:** {outline.template_type.replace('_', ' ').title()}
**Total Sections:** {len(outline.sections)}

---

## Table of Contents

"""
    
    # Build table of contents
    for i, section in enumerate(outline.sections, 1):
        header += f"{i}. {section.title}\n"
    
    header += "\n---\n\n"
    full_content_parts.append(header)
    
    # Generate each section
    for section in outline.sections:
        print(f"  - Generating section: {section.title}")
        
        # Generate professional content
        content = generate_section_content(
            section=section,
            sources=sources,
            template_type=outline.template_type
        )
        
        draft_section = DraftSection(
            section_id=section.section_id,
            title=section.title,
            generated_content=content,
            confidence=0.75,  # Will be refined by LLM
            sources_cited=section.source_refs,
            unresolved_placeholders=[]
        )
        
        draft_sections.append(draft_section)
        
        # Add to full content
        full_content_parts.append(content)
        full_content_parts.append("\n\n")
    
    # Add known issues section
    if outline.conflicts:
        full_content_parts.append("---\n\n")
        full_content_parts.append("## Known Issues and Conflicts\n\n")
        full_content_parts.append("The following issues were detected during document generation:\n\n")
        
        for i, conflict in enumerate(outline.conflicts, 1):
            severity_emoji = {"blocking": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(conflict.severity, "•")
            full_content_parts.append(f"{i}. **{severity_emoji} [{conflict.severity.upper()}]** {conflict.description}\n\n")
            full_content_parts.append(f"   - **Affected Sources:** {', '.join(conflict.sources)}\n")
            if conflict.resolution:
                full_content_parts.append(f"   - **Proposed Resolution:** {conflict.resolution}\n")
            full_content_parts.append("\n")
    
    # Add professional footer
    footer = f"""

---

## Document Metadata

- **Generation Time:** {datetime.now().isoformat()}
- **System:** Documentation Automation System
- **Version:** 1.0
- **Review Required:** Yes

---

**⚠️ IMPORTANT NOTICE**

This document was automatically generated and requires human review before publication.
Please verify all technical details, ensure citations are accurate, and confirm
that the content meets your organization's documentation standards.

**DO NOT PUBLISH WITHOUT APPROVAL**

---

*Generated by Documentation Automation System*
*© 2024 - All rights reserved*
"""
    full_content_parts.append(footer)
    
    # Calculate overall confidence
    confidences = [s.confidence for s in draft_sections]
    overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    # Create draft
    draft = DocumentDraft(
        template_type=outline.template_type,
        title=outline.title,
        content="".join(full_content_parts),
        sections=draft_sections,
        overall_confidence=overall_confidence,
        can_publish="no"  # Drafting agent CANNOT approve for publication
    )
    
    # Update state
    state["draft"] = draft
    state["drafting_complete"] = True
    state["drafting_errors"] = errors
    state["current_step"] = "drafting_complete"
    
    if errors:
        state["errors"].extend(errors)
    
    # Set workflow status based on results
    if draft and draft_sections:
        state["workflow_status"] = "completed"
    else:
        state["workflow_status"] = "failed"
    
    print(f"\n[Drafting Agent] Complete: {len(draft_sections)} sections, confidence={overall_confidence:.2f}")
    print(f"  ** DRAFT CREATED - NOT FOR PUBLICATION **")
    return state


def generate_section_content(
    section: OutlineSection,
    sources: List[SourceDocument],
    template_type: str
) -> str:
    """Generate professional content for a section using LLM or template fallback.
    
    Args:
        section: Outline section to generate
        sources: Available source documents
        template_type: Type of document
        
    Returns:
        Generated content as markdown
    """
    from app.agents.prompts import (
        DRAFTING_SYSTEM_PROMPT,
        DRAFTING_SECTION_PROMPT,
        get_template_structure
    )
    
    # Find relevant sources
    relevant_sources = [s for s in sources if s.path in section.source_refs]
    
    # Try LLM-based generation first
    try:
        # Build source content
        source_contents_list = []
        for source in relevant_sources[:2]:  # Limit to 2 for context
            doc_type = source.doc_type.replace('_', ' ').title()
            preview = source.content[:1000]
            source_contents_list.append(f"### {source.path} ({doc_type})\n{preview}\n")
        
        source_contents = "\n".join(source_contents_list) if source_contents_list else "No specific sources."
        
        # Build prompt
        prompt = DRAFTING_SECTION_PROMPT.format(
            template_type=template_type.replace('_', ' ').title(),
            title=section.title,
            section_id=section.section_id,
            section_title=section.title,
            content_summary=section.content_summary,
            source_refs=", ".join(section.source_refs) if section.source_refs else "None",
            source_contents=source_contents,
            template_guidance=get_template_structure(template_type)
        )
        
        # Call LLM
        llm_client = get_llm_client()
        result = llm_client.generate_json(
            prompt=prompt,
            system_prompt=DRAFTING_SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=1500
        )
        
        if result.get("success") and "generated_content" in result:
            content = result["generated_content"]
            # Ensure proper formatting
            if not content.startswith(f"## {section.title}"):
                content = f"## {section.title}\n\n{content}"
            return content
        else:
            # Fall through to template
            pass
            
    except Exception as e:
        print(f"  [Drafting] LLM unavailable: {str(e)[:80]}")
    
    # Template-based fallback
    content_parts = []
    content_parts.append(f"## {section.title}\n\n")
    content_parts.append(f"This section documents {section.title.lower()}. ")
    content_parts.append(f"The following information is derived from source materials.\n\n")
    
    if relevant_sources:
        content_parts.append("### Source Analysis\n\n")
        for source in relevant_sources:
            doc_type = source.doc_type.replace('_', ' ').title()
            content_parts.append(f"**{source.path}** ({doc_type})\n\n")
            preview = source.content[:800]
            content_parts.append(f"```\n{preview}\n```\n\n")
            content_parts.append(f"*Source: {source.path}*\n\n")
    else:
        content_parts.append("{{PLACEHOLDER: Content to be added from source review}}\n\n")
    
    content_parts.append("---\n\n")
    content_parts.append("*Auto-generated content - requires human review*\n")
    
    return "".join(content_parts)


# ============== REVIEW ROUTING AGENT ==============

def review_routing_agent(state: AgentState) -> AgentState:
    """Review Routing Agent: Assess draft quality and route appropriately.
    
    This agent:
    1. Analyzes draft completeness
    2. Identifies missing information
    3. Detects unsupported claims
    4. Reviews conflict handling
    5. NEVER approves for publication - only routes
    
    Args:
        state: Current workflow state with draft
        
    Returns:
        Updated state with review assessment
    """
    print(f"\n[Review Routing Agent] Assessing draft quality...")
    
    errors = []
    
    if not state.get("draft"):
        error_msg = "No draft available for review"
        print(f"  ERROR: {error_msg}")
        errors.append(WorkflowError(
            step="review_routing",
            message=error_msg
        ))
        state["review_errors"] = errors
        state["errors"].extend(errors)
        return state
    
    draft = state["draft"]
    outline = state.get("outline")
    sources = state.get("retrieved_sources", [])
    
    # Collect issues
    issues = []
    human_review_items = []
    
    # Check 1: Completeness - does draft match outline?
    if outline:
        outline_sections = {s.section_id for s in outline.sections}
        draft_sections = {s.section_id for s in draft.sections}
        
        missing_sections = outline_sections - draft_sections
        if missing_sections:
            issues.append(f"Missing sections: {', '.join(missing_sections)}")
    
    # Check 2: Confidence level
    if draft.overall_confidence < 0.6:
        issues.append(f"Low overall confidence: {draft.overall_confidence:.2f}")
    
    # Check 3: Unresolved placeholders
    placeholder_count = sum(len(s.unresolved_placeholders) for s in draft.sections)
    if placeholder_count > 0:
        issues.append(f"{placeholder_count} unresolved placeholders")
        human_review_items.append("Review and fill in placeholder content")
    
    # Check 4: Conflicts from outline
    if outline and outline.conflicts:
        blocking_conflicts = [c for c in outline.conflicts if c.severity == "blocking"]
        warning_conflicts = [c for c in outline.conflicts if c.severity == "warning"]
        
        if blocking_conflicts:
            issues.append(f"{len(blocking_conflicts)} blocking conflicts not resolved")
        
        for conflict in warning_conflicts:
            human_review_items.append(f"Review conflict: {conflict.description[:100]}")
    
    # Check 5: Missing source citations
    sections_without_citations = [
        s.title for s in draft.sections
        if not s.sources_cited and "placeholder" not in s.generated_content.lower()
    ]
    if sections_without_citations:
        issues.append(f"Sections lacking source citations: {', '.join(sections_without_citations[:3])}")
    
    # Try LLM-based assessment (if available)
    try:
        from app.agents.prompts import (
            REVIEW_ROUTING_SYSTEM_PROMPT,
            REVIEW_ASSESSMENT_PROMPT
        )
        
        llm_client = get_llm_client()
        
        # Prepare prompt
        conflicts_text = "\n".join([
            f"- [{c.severity}] {c.description}" 
            for c in (outline.conflicts if outline else [])
        ]) or "No conflicts detected"
        
        sources_text = "\n".join([f"- {s.path} ({s.doc_type})" for s in sources])
        
        prompt = REVIEW_ASSESSMENT_PROMPT.format(
            draft_content=draft.content[:2000],  # First 2000 chars
            outline_content=str(outline) if outline else "No outline",
            conflicts=conflicts_text,
            sources=sources_text
        )
        
        result = llm_client.generate_json(
            prompt=prompt,
            system_prompt=REVIEW_ROUTING_SYSTEM_PROMPT,
            temperature=0.3
        )
        
        if result.get("success"):
            # Use LLM assessment
            llm_status = result.get("status", "NEEDS_REVISION")
            llm_confidence = result.get("confidence", 0.5)
            llm_issues = result.get("issues", [])
            llm_human_items = result.get("human_review_items", [])
            
            # Merge LLM findings with our checks
            issues.extend(llm_issues)
            human_review_items.extend(llm_human_items)
            
            # Use more conservative status
            status = "NEEDS_REVISION" if issues else llm_status
            confidence = min(draft.overall_confidence, llm_confidence)
        else:
            # Fall back to rule-based assessment
            status = "NEEDS_REVISION" if issues else "READY_FOR_REVIEW"
            confidence = draft.overall_confidence
            
    except Exception as e:
        print(f"  WARNING: LLM assessment failed: {e}")
        # Rule-based fallback
        status = "NEEDS_REVISION" if issues else "READY_FOR_REVIEW"
        confidence = draft.overall_confidence
    
    # CRITICAL: Never auto-approve
    if status == "READY_FOR_REVIEW" and not human_review_items:
        # Still require human review even if draft looks good
        human_review_items.append("Final human approval required before publication")
    
    # Create assessment
    assessment = ReviewAssessment(
        status=status,
        confidence=confidence,
        issues=issues,
        human_review_items=human_review_items
    )
    
    # Update state
    state["review_assessment"] = assessment
    state["review_complete"] = True
    state["review_errors"] = errors
    state["current_step"] = "review_complete"
    
    if errors:
        state["errors"].extend(errors)
    
    # Set workflow status
    if status == "NEEDS_REVISION":
        state["workflow_status"] = "needs_revision"
    else:
        state["workflow_status"] = "completed"
    
    print(f"\n[Review Routing Agent] Complete")
    print(f"  Status: {status}")
    print(f"  Confidence: {confidence:.2f}")
    print(f"  Issues: {len(issues)}")
    print(f"  Human Review Items: {len(human_review_items)}")
    print(f"  ** AGENT NEVER APPROVES - ROUTING DECISION ONLY **")
    
    return state


# ============== Utility Functions ==============

def get_error_summary(state: AgentState) -> Dict[str, Any]:
    """Get summary of errors in current state.
    
    Args:
        state: Current workflow state
        
    Returns:
        Error summary dictionary
    """
    return {
        "ingestion_errors": len(state.get("ingestion_errors", [])),
        "structure_errors": len(state.get("structure_errors", [])),
        "drafting_errors": len(state.get("drafting_errors", [])),
        "total_errors": len(state.get("errors", [])),
        "has_blocking_errors": any(
            e for e in state.get("errors", [])
        ),
    }
