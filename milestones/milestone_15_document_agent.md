# Milestone 15: Document Agent (Specialist Agent for Document Metadata and Lifecycles)

## Goal
Design and build the **Document Agent**, a specialized agent for querying, listing, inspecting, and requesting deletion of documents within tenant/department boundaries. The agent uses PydanticAI, supports tool-calling, enforces tenant-isolation (multi-tenancy), logs execution step-by-step for observability, and includes complete testing and frontend workspace integration.

## Status
- [x] Define the Document Agent's goal, instructions, and prompt (`app/services/document_agent.py`)
- [x] Implement MCP-compatible read-only and gated tools (`list_my_documents`, `get_document_info`, `check_document_status`, `delete_document`) and register them
- [x] Integrate the Document Agent into the FastAPI layout (`app/api/v1/agents.py`)
- [x] Implement tool-calling mock test suites and deterministic refusal/scoping tests under `tests/test_document_agent.py`
- [x] Create a lightweight evaluation suite verifying the agent's tool selection and tenant boundaries
- [x] Add a "Document Agent Workspace" interface tab in the Streamlit frontend with step-by-step tool execution feedback
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **Multi-Tenant Isolation Scoping:** The agent is given access to tools that check user credentials from `AgentDeps` to filter document listings and detail fetches, ensuring a user in one department cannot query or see another department's documents.
- **Strict Read-Only Deletion Safe-Gating:** Because human-in-the-loop approval gating is not yet implemented (scheduled for a future milestone), any deletion action requested via the agent is politely refused by the tool and prompt, explaining that it is blocked pending administrative approval.
- **Traceable Execution Logs:** Step-by-step updates of agent activities (prompts, tool invocations, results) are logged for administrator audit tracking.

## Completed Tasks Record
* *Commit 37:* Implement Document Agent service, PydanticAI tools (`list_my_documents`, `get_document_info`, `check_document_status`, `delete_document`), and DTO response.
* *Commit 38:* Integrate Document Agent endpoint in `app/api/v1/agents.py` and register in router.
* *Commit 39:* Update Streamlit UI workspace, write unit/integration test suite `tests/test_document_agent.py`, clean up formatting/linting, and update CHANGELOG.
