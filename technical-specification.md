# Technical Specification: Documentation Automation System

**Version:** 1.0  
**Status:** Draft  
**Classification:** Internal  
**Last Updated:** 2024-01-15

---

## 1. Executive Summary

### 1.1 Business Problem
Documentation is a persistent productivity bottleneck in software engineering teams. Manual documentation processes are:
- Time-consuming (engineers spend 10-20% of time on docs)
- Error-prone (stale information, inconsistencies)
- Reactive rather than proactive (docs written after implementation)
- Difficult to maintain (scattered sources, no single source of truth)

### 1.2 Solution
An agentic AI system that automatically generates structured documentation from source artifacts (code, specs, meeting notes) through a multi-agent workflow with human oversight and safety guardrails.

### 1.3 Target Outcomes
- Reduce documentation time by 70%
- Improve documentation accuracy and consistency
- Enable proactive documentation (generated as code is written)
- Maintain human control over publication through approval gates

---

## 2. User Journey

### 2.1 Primary Actor: Documentation Manager

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Select    │────▶│   Review    │────▶│   Approve   │
│   Sources   │     │   Draft     │     │  & Publish  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  - Source code       - Outline          - Audit trail
  - Requirements      - Draft doc        - Published doc
  - Meeting notes     - Guardrail        - Notification
  - Templates           results
```

### 2.2 User Flow

1. **Discovery:** User identifies source documents that need documentation
2. **Selection:** User selects files via Streamlit UI
3. **Inspection:** User reviews metadata and classification
4. **Configuration:** User selects template (technical-spec, SOP, process-map)
5. **Execution:** System runs multi-agent workflow automatically
6. **Monitoring:** User watches agent progress in real-time
7. **Review:** User examines outline, draft, and guardrail results
8. **Decision:** User approves, rejects, or requests revision
9. **Publication:** Approved documents published with audit trail

---

## 3. Actors

| Actor | Role | Goals | Pain Points |
|-------|------|-------|-------------|
| **Documentation Manager** | Reviews and approves generated docs | Ensure accuracy, maintain standards | Time pressure, technical complexity |
| **Software Engineer** | Creates source code and specs | Focus on coding, not documentation | Writing docs is tedious |
| **Compliance Officer** | Ensures regulatory requirements | Audit trails, approvals | Verifying documentation completeness |
| **System (Agentic)** | Automates documentation generation | Consistency, speed, coverage | Requires human oversight |

---

## 4. Agents

### 4.1 Agent Pipeline

```
Ingestion Agent    →    Structure Agent    →    Drafting Agent    →    Review Routing Agent
     │                       │                       │                       │
     ▼                       ▼                       ▼                       ▼
Retrieve &            Create outline        Generate draft      Identify issues
classify sources    from sources          from outline        Route decisions
via MCP             Flag conflicts        Apply template      Human review queue
```

### 4.2 Agent Responsibilities

#### Ingestion Agent
**Purpose:** Retrieve and classify all source materials

**Inputs:**
- Selected file paths from user
- Template type selection

**Outputs:**
- Retrieved content (via MCP tools)
- Content classification
- Source metadata summary

**Actions:**
1. Call `list_source_files()` to discover available files
2. Call `read_source_file(path)` for each selected file
3. Call `get_source_metadata(path)` for classification
4. Call `get_template(template_name)` for template content
5. Classify content types and sensitivity
6. Validate all sources are accessible

**Error Handling:**
- Missing files → Log error, continue with available sources
- Unsupported types → Reject with clear message
- Classification mismatch → Flag for review

---

#### Structure Agent
**Purpose:** Create document outline and identify conflicts

**Inputs:**
- Retrieved source content (from Ingestion Agent)
- Template structure requirements
- Source metadata

**Outputs:**
- Document outline (structured JSON/Markdown)
- Conflict report (contradictions between sources)
- Missing information list
- Flag severity assessment

**Actions:**
1. Parse template structure requirements
2. Map source content to template sections
3. Identify contradictions between sources
4. Flag ambiguous requirements
5. Mark sections requiring manual input
6. Generate structured outline

**Conflict Detection:**
- Compare specification vs meeting notes
- Identify outdated statements
- Flag missing requirements
- Assess severity (blocking vs warning)

---

#### Drafting Agent
**Purpose:** Generate document draft from outline

**Inputs:**
- Structured outline (from Structure Agent)
- Template with placeholders
- Source content

**Outputs:**
- Completed document draft
- Unresolved placeholder list
- Confidence scores per section

**Actions:**
1. Process outline sections sequentially
2. Generate content for each section
3. Apply template formatting
4. Mark unresolved placeholders
5. Add source citations where applicable
6. Generate confidence assessment

**Constraints:**
- CANNOT publish directly
- MUST flag low-confidence sections
- MUST cite sources for factual claims

---

#### Review Routing Agent
**Purpose:** Assess draft quality and route appropriately

**Inputs:**
- Document draft
- Conflict report
- Guardrail results
- Confidence scores

**Outputs:**
- Routing decision: `READY_FOR_REVIEW` or `NEEDS_REVISION`
- Issue summary (missing info, contradictions, unsupported claims)
- Required human review items

**Actions:**
1. Assess document completeness
2. Verify all conflicts are addressed or flagged
3. Check confidence thresholds
4. Evaluate guardrail results
5. Make routing decision
6. Generate review checklist

**Routing Rules:**
- `NEEDS_REVISION` if: blocking conflicts unresolved, low confidence sections, guardrail failures
- `READY_FOR_REVIEW` if: minor issues flagged, human review items documented

**Critical Rule:** Agent NEVER approves its own document. Always routes to human.

---

## 5. LangGraph Workflow

### 5.1 State Schema

```python
from typing import TypedDict, List, Optional, Literal
from pydantic import BaseModel

class SourceDocument(BaseModel):
    path: str
    content: str
    doc_type: Literal["source_code", "requirements", "meeting_notes", "template", "existing_doc"]
    classification: str
    sensitivity: Literal["public", "internal", "confidential", "restricted"]

class Conflict(BaseModel):
    description: str
    sources: List[str]
    severity: Literal["blocking", "warning", "info"]
    resolution: Optional[str] = None

class OutlineSection(BaseModel):
    section_id: str
    title: str
    content_summary: str
    source_refs: List[str]
    status: Literal["complete", "incomplete", "flagged"]

class DocumentOutline(BaseModel):
    template_type: Literal["technical_spec", "sop", "process_map"]
    sections: List[OutlineSection]
    conflicts: List[Conflict]
    missing_info: List[str]

class DraftSection(BaseModel):
    section_id: str
    generated_content: str
    confidence: float  # 0.0 to 1.0
    sources_cited: List[str]
    unresolved_placeholders: List[str]

class DocumentDraft(BaseModel):
    template_type: str
    content: str
    sections: List[DraftSection]
    overall_confidence: float

class GuardrailResult(BaseModel):
    hook_name: Literal["pre_hook", "post_hook"]
    passed: bool
    findings: List[str]
    severity: Literal["blocking", "warning", "info"]
    requires_human_review: bool

class ReviewDecision(BaseModel):
    status: Literal["READY_FOR_REVIEW", "NEEDS_REVISION"]
    issues: List[str]
    human_review_items: List[str]
    confidence: float

class AgentState(TypedDict):
    # Input
    selected_sources: List[str]
    template_type: str
    
    # Ingestion
    retrieved_sources: List[SourceDocument]
    ingestion_errors: List[str]
    
    # Structure
    outline: Optional[DocumentOutline]
    conflicts: List[Conflict]
    
    # Drafting
    draft: Optional[DocumentDraft]
    drafting_errors: List[str]
    
    # Guardrails
    pre_hook_result: Optional[GuardrailResult]
    post_hook_result: Optional[GuardrailResult]
    
    # Review
    review_decision: Optional[ReviewDecision]
    
    # Workflow
    current_step: str
    errors: List[str]
```

### 5.2 Graph Structure

```
                    ┌─────────────┐
                    │    Start    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Pre-Hook   │──(guardrail)──┐
                    │  (Source    │               │
                    │  Check)     │               │
                    └──────┬──────┘               │
                           │                      │
              (failed)     │      (passed)        │
                    ┌──────┴──────┐                │
                    ▼             ▼                │
              ┌─────────┐   ┌─────────────┐        │
              │  Halt   │   │  Ingestion  │        │
              │  (Error)│   │    Agent    │        │
              └─────────┘   └──────┬──────┘        │
                                   │                │
                                   ▼                │
                            ┌─────────────┐         │
                            │   Structure │         │
                            │    Agent    │         │
                            └──────┬──────┘         │
                                   │                │
                                   ▼                │
                            ┌─────────────┐         │
                            │   Drafting  │         │
                            │    Agent    │         │
                            └──────┬──────┘         │
                                   │                │
                                   ▼                │
                            ┌─────────────┐         │
                            │  Post-Hook  │─────────┤
                            │  (Output    │         │
                            │   Check)    │         │
                            └──────┬──────┘         │
                                   │                │
              (failed)     │      (passed)          │
                    ┌──────┴──────┐                │
                    ▼             ▼                  │
              ┌─────────┐   ┌─────────────┐        │
              │  Halt   │   │    Review   │          │
              │(Revisio)│   │   Routing   │          │
              └─────────┘   │    Agent    │          │
                            └──────┬──────┘          │
                                   │                 │
              ┌────────────────────┼────────────────┐│
              │                    │                ││
              ▼                    ▼                ▼│
        ┌───────────┐        ┌───────────┐    ┌─────────┐
        │   NEEDS   │        │   READY   │    │  Halt   │
        │  REVISION │        │  FOR REV  │    │(Blockin)│
        │           │        │           │    └─────────┘
        └───────────┘        └─────┬─────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   Human     │
                            │   Review    │
                            │   (UI)      │
                            └──────┬──────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
              ┌─────────┐   ┌─────────┐   ┌─────────┐
              │ Approve │   │  Reject │   │ Request │
              │ Publish │   │  Delete │   │ Revision│
              └─────────┘   └─────────┘   └─────────┘
```

### 5.3 Node Definitions

| Node | Function | Input State | Output State |
|------|----------|-------------|--------------|
| `pre_hook` | Validate source classification | `selected_sources` | `pre_hook_result`, halt if failed |
| `ingestion` | Retrieve all sources via MCP | `selected_sources` | `retrieved_sources`, `ingestion_errors` |
| `structure` | Create outline, detect conflicts | `retrieved_sources` | `outline`, `conflicts` |
| `drafting` | Generate document draft | `outline`, `retrieved_sources` | `draft`, `drafting_errors` |
| `post_hook` | Validate output | `draft` | `post_hook_result`, halt if failed |
| `review_routing` | Assess and route | `draft`, `conflicts`, `post_hook_result` | `review_decision` |
| `human_gate` | Await human decision | `review_decision` | Final state (approve/reject/revise) |

---

## 6. MCP Client/Server Interaction

### 6.1 MCP Server Responsibilities

The MCP server provides controlled access to domain resources. Agents NEVER access files directly.

#### Tool Definitions

```python
# Tool: list_source_files()
# Purpose: Discover available source files
# Returns: List of file paths relative to seed_data/
# Errors: ServerError if seed_data inaccessible

# Tool: read_source_file(path)
# Purpose: Read file content
# Parameters: path (str) - relative path within seed_data/
# Validation:
#   - Path must start with seed_data/
#   - Path must not contain ".." (traversal prevention)
#   - File must exist
#   - File type must be supported (.py, .md, .yaml, .json)
# Returns: File content as string
# Errors: PathValidationError, FileNotFoundError, UnsupportedTypeError

# Tool: get_template(template_name)
# Purpose: Retrieve document template
# Parameters: template_name (str) - one of: "technical-spec", "sop", "process-map"
# Returns: Template content as string
# Errors: TemplateNotFoundError

# Tool: get_source_metadata(path)
# Purpose: Get classification and metadata for source
# Parameters: path (str) - relative path within seed_data/
# Returns: JSON object with classification, sensitivity, known_issues
# Errors: PathValidationError, MetadataNotFoundError
```

### 6.2 MCP Client (Streamlit)

The Streamlit app acts as the MCP client:
1. Connects to MCP server via stdio or HTTP
2. Exposes UI for selecting sources and templates
3. Displays agent progress and intermediate results
4. Implements human approval gate
5. Logs all MCP calls for audit

### 6.3 Security Model

```
Agent ──X──▶ Filesystem
Agent ──✓──▶ MCP Server ──✓──▶ seed_data/ (validated paths only)
```

All file access mediated through MCP tools with:
- Path validation (prevent directory traversal)
- Type checking (only supported formats)
- Access logging (every call recorded)
- Scope restriction (only seed_data/ exposed)

---

## 7. Streamlit Screens

### 7.1 Screen Flow

```
[Home] ──▶ [Select Sources] ──▶ [Review Sources] ──▶ [Select Template]
                                              │
                                              ▼
[Publish] ◀── [Approve] ◀── [Review Results] ◀── [Monitor Progress]
```

### 7.2 Screen Specifications

#### Screen 1: Home
- Welcome message
- System status overview
- Start new documentation button
- Recent documents list

#### Screen 2: Select Sources
- File tree/browser of seed_data/
- Multi-select checkboxes
- Search/filter functionality
- Selected files preview panel
- Proceed button

#### Screen 3: Review Sources
- Table of selected files with metadata
- Classification badges
- Known issues warnings
- Edit selection button
- Confirm and proceed button

#### Screen 4: Select Template
- Template cards (technical-spec, SOP, process-map)
- Preview of each template
- Template description
- Select and start button

#### Screen 5: Monitor Progress
- Real-time agent progress indicators
- Current agent name
- Steps completed/total
- MCP call log (expandable)
- Cancel button

#### Screen 6: Review Results
- Document outline panel (collapsible)
- Draft document preview (Markdown rendered)
- Conflict report (if any)
- Guardrail results (pass/fail with details)
- Confidence score
- Decision buttons: Approve / Request Revision / Reject

#### Screen 7: Approve
- Final document preview
- Publication confirmation
- Audit trail display
- Confirm publish button

#### Screen 8: Publish
- Success confirmation
- Published document location
- Download link
- Start new document button

---

## 8. Guardrails

### 8.1 Pre-Hook: Source Classification Check

**Purpose:** Ensure sources are appropriate for automated processing

**Implementation:** Deterministic Python function (not LLM)

```python
def pre_classification_check(sources: List[SourceDocument]) -> GuardrailResult:
    findings = []
    requires_review = False
    severity = "info"
    
    for source in sources:
        if source.sensitivity == "restricted":
            findings.append(f"RESTRICTED source: {source.path}")
            severity = "blocking"
        elif source.sensitivity == "confidential":
            findings.append(f"CONFIDENTIAL source: {source.path} - requires review")
            requires_review = True
            severity = max(severity, "warning")
        
        if source.classification == "decision_record":
            findings.append(f"Decision record may contain contradictions: {source.path}")
            requires_review = True
            severity = max(severity, "warning")
    
    return GuardrailResult(
        hook_name="pre_hook",
        passed=severity != "blocking",
        findings=findings,
        severity=severity,
        requires_human_review=requires_review
    )
```

**Behavior:**
- RESTRICTED sources → Block workflow
- CONFIDENTIAL sources → Allow with review flag
- Decision records → Allow with review flag

### 8.2 Post-Hook: Output Review Check

**Purpose:** Validate generated document before human review

```python
def post_output_check(draft: DocumentDraft) -> GuardrailResult:
    findings = []
    requires_review = False
    severity = "info"
    
    # Check for unresolved placeholders
    unresolved = sum(len(s.unresolved_placeholders) for s in draft.sections)
    if unresolved > 0:
        findings.append(f"{unresolved} unresolved placeholders in draft")
        requires_review = True
        severity = "warning"
    
    # Check confidence threshold
    if draft.overall_confidence < 0.7:
        findings.append(f"Low overall confidence: {draft.overall_confidence:.2f}")
        requires_review = True
        severity = "warning"
    
    # Check for empty sections
    empty_sections = [s.section_id for s in draft.sections if not s.generated_content.strip()]
    if empty_sections:
        findings.append(f"Empty sections: {', '.join(empty_sections)}")
        severity = "blocking"
    
    return GuardrailResult(
        hook_name="post_hook",
        passed=severity != "blocking",
        findings=findings,
        severity=severity,
        requires_human_review=requires_review
    )
```

**Behavior:**
- Empty sections → Block workflow
- Low confidence → Allow with review flag
- Unresolved placeholders → Allow with review flag

### 8.3 Gate: Human Sign-Off

**Purpose:** Final human approval before publication

**Implementation:** Streamlit UI component with explicit action required

**Behavior:**
- Document NEVER publishes automatically
- User MUST explicitly click "Approve and Publish"
- All alternatives (reject, request revision) recorded
- Decision logged in audit trail

---

## 9. Human Approval Workflow

### 9.1 Approval States

```
DRAFT_CREATED
    │
    ▼
REVIEW_PENDING ──(request revision)──▶ REVISION_REQUESTED
    │                                      │
    │(reject)                              │(revise complete)
    ▼                                      ▼
REJECTED                            BACK_TO_REVIEW
    │                                      │
    │(approve)                            │(approve)
    ▼                                      ▼
APPROVED ◀─────────────────────────────────┘
    │
    ▼
PUBLISHED
```

### 9.2 Approval UI Requirements

- **Approve Button:** Prominent, requires confirmation dialog
- **Reject Button:** Requires reason input
- **Request Revision Button:** Opens form for revision notes
- **Audit Display:** Shows complete decision history

### 9.3 Audit Trail

Every action recorded:
- Timestamp
- Actor (user ID)
- Action (approve/reject/request_revision)
- Document version
- Reason (if provided)
- MCP calls made
- Agent outputs

---

## 10. Failure Cases

### 10.1 System Failures

| Failure | Cause | Response |
|---------|-------|----------|
| MCP Server unavailable | Network, process crash | Halt workflow, display error, allow retry |
| File not found | Moved/deleted source | Log error, skip file, continue with warning |
| Template not found | Missing template | Halt, prompt user to select different template |
| LLM API error | Rate limit, timeout | Retry with backoff (3x), then halt with error |
| State corruption | Bug, race condition | Halt, log state, require manual intervention |

### 10.2 Agent Failures

| Failure | Cause | Response |
|---------|-------|----------|
| Ingestion partial failure | Some files unreadable | Continue with available, flag missing |
| Structure conflict unresolved | Contradiction not addressed | Flag for review, continue |
| Draft incomplete | Missing information | Mark placeholders, flag for review |
| Review routing error | Assessment failure | Default to NEEDS_REVISION, log error |

### 10.3 Guardrail Failures

| Failure | Cause | Response |
|---------|-------|----------|
| Pre-hook blocking | RESTRICTED source | Halt immediately, require source removal |
| Pre-hook warning | CONFIDENTIAL source | Continue with review flag |
| Post-hook blocking | Empty sections | Halt, return to drafting |
| Post-hook warning | Low confidence | Continue to review with flag |

### 10.4 Human Decision Failures

| Failure | Cause | Response |
|---------|-------|----------|
| Approval timeout | User session expired | Save draft, notify user, require restart |
| Browser crash | Client-side issue | Recover from last saved state |
| Accidental approval | User error | Require confirmation dialog, allow undo within 5 min |

---

## 11. Evaluation Cases

### 11.1 Success Cases

**Case E1: Complete Technical Spec Generation**
- Sources: billing_service.py + billing_requirements.md + billing-system-review.md
- Template: technical-spec
- Expected: Complete document with contradictions flagged, human approves

**Case E2: SOP Generation**
- Sources: appointment_requirements.md + billing_requirements.md
- Template: sop
- Expected: Procedure document with clear steps

**Case E3: Process Map Generation**
- Sources: billing_service.py + meeting_notes
- Template: process-map
- Expected: Flowchart-style documentation

### 11.2 Edge Cases

**Case X1: Single Source**
- Only one source file selected
- Expected: Document generated with limited scope warning

**Case X2: Contradiction Heavy**
- Multiple sources with contradictions
- Expected: Conflicts clearly flagged, document blocked until addressed

**Case X3: Missing Information**
- Sources have gaps
- Expected: Placeholders marked, flagged for human input

### 11.3 Failure Injection Cases (for Step 10)

**Case F1: Hallucinated Fact**
- Agent invents non-existent requirement
- Detection: Compare against sources, flag unsupported claim

**Case F2: Ignored Contradiction**
- Agent misses threshold discrepancy ($5K vs $10K)
- Detection: Structure agent should flag, Review Routing should catch

**Case F3: Missing Requirement**
- Agent omits partial payment handling
- Detection: Section incomplete, post-hook flags

**Case F4: Incorrect Template Usage**
- Agent puts SOP content in technical-spec
- Detection: Template structure validation

---

## 12. Project Structure

```
app/
├── streamlit_app.py              # MCP client + UI (600-800 lines)
│   ├── UI Components
│   ├── MCP Client Connection
│   ├── Human Gate Implementation
│   └── Audit Logging
│
├── agents/
│   ├── graph.py                  # LangGraph workflow definition (300-400 lines)
│   ├── state.py                  # TypedDict and Pydantic models (150-200 lines)
│   ├── prompts.py                # Agent prompts as constants (200-300 lines)
│   └── nodes.py                  # Individual agent node implementations (400-500 lines)
│       ├── ingestion_node
│       ├── structure_node
│       ├── drafting_node
│       └── review_routing_node
│
├── mcp_server/
│   ├── server.py                 # MCP server entry point (100 lines)
│   └── tools/
│       ├── __init__.py
│       ├── file_tools.py         # list_source_files, read_source_file (150 lines)
│       ├── template_tools.py     # get_template (50 lines)
│       └── metadata_tools.py     # get_source_metadata (100 lines)
│
├── guardrails/
│   ├── __init__.py
│   ├── pre_hooks.py              # Source classification checks (100 lines)
│   ├── post_hooks.py             # Output validation (100 lines)
│   └── gates.py                  # Human approval gate logic (100 lines)
│
├── utils/
│   ├── __init__.py
│   ├── audit.py                  # Audit trail logging (100 lines)
│   └── validators.py             # Path validation, type checking (100 lines)
│
├── seed_data/                    # Source documents (fictional training data)
│   ├── source_code/
│   ├── specifications/
│   ├── meeting_notes/
│   ├── existing_docs/
│   ├── templates/
│   └── metadata/
│
├── outputs/                      # Generated documents (pending approval)
│   └── .gitkeep
│
├── evaluations/                  # Test results
│   └── .gitkeep
│
├── tests/
│   ├── __init__.py
│   ├── test_mcp_tools.py         # MCP tool unit tests (200 lines)
│   ├── test_agents.py            # Agent integration tests (300 lines)
│   ├── test_guardrails.py        # Guardrail tests (150 lines)
│   └── test_workflow.py          # End-to-end workflow tests (200 lines)
│
├── requirements.txt
├── .env.example                  # Environment variable template
└── README.md                     # Project documentation
```

---

## 13. Dependencies

### 13.1 Core Dependencies

```
# requirements.txt
langgraph>=0.0.50
langchain>=0.1.0
streamlit>=1.28.0
pydantic>=2.0.0
python-dotenv>=1.0.0

# MCP
mcp>=0.1.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### 13.2 Optional Dependencies

```
# For LLM (choose one)
openai>=1.0.0
anthropic>=0.8.0

# For development
black>=23.0.0
mypy>=1.5.0
```

---

## 14. Configuration

### 14.1 Environment Variables (.env)

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
# or ANTHROPIC_API_KEY=sk-ant-...

# MCP Configuration
MCP_SERVER_PATH=./mcp_server/server.py
MCP_TRANSPORT=stdio

# Application
LOG_LEVEL=INFO
OUTPUT_DIR=./outputs
AUDIT_LOG_PATH=./outputs/audit.log

# Guardrails
CONFIDENCE_THRESHOLD=0.7
MAX_RETRIES=3
```

### 14.2 Seed Data Configuration

Managed via `seed_data/metadata/source-classification.yaml` (already created).

---

## 15. Success Criteria

### 15.1 Functional Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| FR-01 | Agents access files only via MCP | Code review, integration test |
| FR-02 | All 4 agents execute in sequence | Workflow test |
| FR-03 | Guardrails block unsafe operations | Unit tests |
| FR-04 | Human approval required before publish | UI test |
| FR-05 | Audit trail records all actions | Log inspection |
| FR-06 | Intentional issues detected and flagged | Evaluation test |

### 15.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Workflow completion time | < 60 seconds |
| NFR-02 | MCP tool response time | < 200ms |
| NFR-03 | UI responsiveness | < 100ms feedback |
| NFR-04 | Test coverage | > 70% |

---

## 16. Open Questions

1. **LLM Provider:** Should we default to OpenAI or support multiple providers?
2. **MCP Transport:** stdio (simpler) or HTTP (scalable)?
3. **State Persistence:** In-memory only or SQLite for recovery?
4. **Multi-document:** Support batch processing multiple docs?

---

**Generated By:** Manual specification creation  
**Review Status:** Draft - requires technical review  
**Next Step:** Prompt 3 - Build minimal workflow (Ingestion → Structure → Drafting)

---

**Note:** This is a technical specification for a training exercise in agentic AI documentation automation.
