# Documentation Automation System

An agentic AI system that reads source artifacts and produces structured documentation through a multi-agent workflow with human oversight.

**Status:** Prompt 6 Complete - Review Routing Agent with Quality Assessment Implemented

---

## Current Implementation

### Agents (4 of 4)

```
Ingestion → Structure → Drafting → Review Routing
    ✓          ✓          ✓            ✓
```

### MCP Server (4 Tools)

```
✓ list_source_files()     - List available sources
✓ read_source_file(path)  - Read file content (with security)
✓ get_template(name)      - Get document templates
✓ get_source_metadata(path) - Get classification metadata
```

**Security Features:**
- ✓ Path validation prevents directory traversal (`../`)
- ✓ Absolute paths blocked
- ✓ Only `seed_data/` directory exposed
- ✓ File type validation (.py, .md, .yaml, .json, .txt)
- ✓ File size limits (10MB max)
- ✓ All calls logged to `mcp_server.log`

**Not Yet Implemented:**
- Guardrails (Prompt 7)

---

## Project Structure

```
.
├── app/
│   ├── agents/
│   │   ├── __init__.py           # Module exports
│   │   ├── state.py              # TypedDict + Pydantic models
│   │   ├── prompts.py            # Agent prompts
│   │   ├── nodes.py              # Agent implementations
│   │   └── graph.py              # LangGraph workflow
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py             # Full MCP server
│   │   └── tools/
│   │       ├── __init__.py
│   │       └── file_tools.py     # Delegates to server
│   ├── utils/
│   │   ├── __init__.py
│   │   └── llm_client.py         # Qwen/OpenAI client
│   ├── guardrails/               # Empty (Prompt 7)
│   └── streamlit_app.py          # Streamlit UI (NEW)
├── seed_data/                    # Fictional training data
│   ├── source_code/              # 3 Python services
│   ├── specifications/           # 2 requirement specs
│   ├── meeting_notes/            # 1 meeting notes
│   ├── existing_docs/            # 1 example doc
│   ├── templates/                # 3 templates
│   └── metadata/                 # classification.yaml
├── outputs/                      # Published documents
├── tests/
│   ├── test_agents.py            # 17 agent tests
│   ├── test_mcp_tools.py         # 34 MCP tests
│   └── test_streamlit.py         # 11 UI tests
├── run_demo.py                   # Demo script
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Demo

```bash
python3 run_demo.py
```

This executes 3 demo workflows:
- Single source document → technical spec
- Multiple sources with conflicts → technical spec  
- Multiple sources → SOP

### 3. Run Tests

```bash
python3 -m pytest tests/test_agents.py -v
```

All 17 tests should pass.

---

## How It Works

### Workflow Execution

```python
from app.agents import run_workflow

final_state = run_workflow(
    selected_sources=[
        "source_code/billing_service.py",
        "specifications/billing_requirements.md"
    ],
    template_type="technical_spec"
)

# Access results
print(final_state["draft"].content)  # Generated document
print(final_state["draft"].can_publish)  # "no" - requires human review
```

### State Schema

The workflow uses a strongly-typed `AgentState` with:
- `selected_sources`: Input file paths
- `retrieved_sources`: List of `SourceDocument` objects
- `outline`: `DocumentOutline` with sections and conflicts
- `draft`: `DocumentDraft` with generated content
- `workflow_status`: "running" | "completed" | "failed"

### MCP Tools (FULLY IMPLEMENTED)

All tools have real filesystem access with security:

- `list_source_files()`: List available files
- `read_source_file(path)`: Read file content (validated paths)
- `get_template(name)`: Get document template
- `get_source_metadata(path)`: Get classification + known issues

**Security**: Path validation prevents directory traversal (`../`), only `seed_data/` exposed.

### Streamlit UI

**6 Screens:**
1. **Home** - System overview and quick actions
2. **Select Sources** - File browser and selection
3. **Review** - Metadata inspection and conflict preview
4. **Run Workflow** - Execute agents with progress tracking
5. **Results** - View outline, draft, and conflicts
6. **Approval** - Human approval gate (REQUIRED)

**Features:**
- Real-time agent progress monitoring
- Conflict detection visualization
- Pre-approval checklist
- Audit trail logging
- **NEVER auto-publishes** - human gate mandatory

### LLM Configuration

Configured for Qwen 3.8-27b via LiteLLM:
- Base URL: `http://52.140.126.42:4000/v1`
- Model: `qwen3.8-27b`
- Supports JSON generation for structured outputs

---

## Key Features

### ✓ Multi-Agent Workflow
LangGraph orchestrates 3 agents in sequence with conditional routing.

### ✓ Conflict Detection
Structure Agent detects known contradictions (e.g., approval threshold $5K vs $10K).

### ✓ Structured State
Pydantic models ensure type safety and validation throughout.

### ✓ Safety: No Direct File Access
Agents call MCP tools only - no `open()`, `os.path`, or direct filesystem access.

### ✓ Draft Cannot Publish
Drafting Agent explicitly marks output as `"can_publish": "no"` with warnings.

### ✓ Audit Trail
All MCP tool calls logged with parameters and results.

---

## Known Limitations

1. **No Review Routing**: Missing the 4th agent that assesses quality
2. **No Guardrails**: Pre/post hooks not implemented
3. **Stub LLM**: Template-based generation (LLM integration ready but not active)

---

## Next Steps

### Prompt 6: Review Routing Agent
- Assess draft quality
- Identify missing information
- Route to revision or human review

### Prompt 7: Guardrails
- Pre-hook: Source classification check
- Post-hook: Output validation
- Gate: Human sign-off required

### Running the Streamlit App

```bash
# Set environment variables (optional - has defaults)
export LLM_BASE_URL="http://52.140.126.42:4000/v1"
export LLM_API_KEY="sk-XMb7UMpAAHOuPIxKMH7OiQ"
export LLM_MODEL="qwen3.8-27b"

# Run Streamlit
streamlit run app/streamlit_app.py

# Or with Python module
python3.11 -m streamlit run app/streamlit_app.py
```

The app will be available at: http://localhost:8501

---

## Architecture Rules

1. **Agents NEVER access files directly** - always through MCP tools
2. **Every iteration leaves the app runnable** - current state passes all tests
3. **Drafts CANNOT publish automatically** - human approval required
4. **Use structured state** - Pydantic models throughout
5. **Add tests for every change** - 62 tests, all passing

---

## Files Changed in Prompt 5

| File | Lines | Purpose |
|------|-------|---------|
| `app/streamlit_app.py` | 547 | Streamlit UI with 6 screens |
| `app/utils/llm_client.py` | 147 | Qwen/OpenAI LLM client |
| `tests/test_streamlit.py` | 170 | 11 UI integration tests |
| `.env.example` | 20 | Environment template |
| `outputs/` | - | Published documents directory |

**Total New Code:** ~884 lines (Prompt 5 only)  
**Cumulative:** ~3,363 lines (Prompts 1-5)

### Key Features Implemented:

1. **6-Screen UI**:
   - Home, Select Sources, Review, Run Workflow, Results, Approval
2. **MCP Client Integration**:
   - Real-time progress monitoring
   - File browsing and metadata display
3. **Human Approval Gate**:
   - Pre-approval checklist
   - Approve/Request Revision/Reject options
   - Audit trail logging
   - **NEVER auto-publishes**
4. **LLM Client**:
   - Configured for Qwen 3.8-27b
   - Supports JSON generation
   - Fallback to template generation
5. **Document Persistence**:
   - Approved docs saved to `outputs/`

### Test Results: 62/62 Passing
- 17 agent workflow tests
- 34 MCP tool tests (security, validation, integration)
- 11 Streamlit UI tests

---

**Note:** This is a training exercise for agentic AI system development. All seed data is fictional.
