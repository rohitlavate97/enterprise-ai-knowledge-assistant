# Milestone 14: Research Agent (First Specialist Agent with Tool Calling)

## Goal
Design and build the **Research Agent**, the first specialized agent in the platform. Equipped with scoped, read-only tools, the agent performs deep research across ingested documents and public knowledge. The implementation must follow PydanticAI specifications, support tool-calling, multi-tenant isolation, guardrails, observability, and evaluation suites.

## Status
- [x] Define the Research Agent's goal, versioned prompt, and guardrails (`app/services/research_agent.py`)
- [x] Implement MCP-compatible read-only tools (`search_knowledge_base`, `read_document_chunk`, `search_web`) and register them to the agent
- [x] Integrate the Research Agent into the FastAPI API layout (`app/api/v1/agents.py`)
- [x] Implement tool-calling mock test suites and deterministic refusal tests under `tests/test_research_agent.py`
- [x] Create a lightweight evaluation suite verifying the agent's reasoning, tool selection, and citation grounding
- [x] Add a "Research Workspace" interface tab in the Streamlit frontend with step-by-step tool execution feedback
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **MCP-Ready Tool Design:** Tools accept structured Pydantic schemas as inputs and return JSON dicts, ensuring they can be exposed directly via Model Context Protocol (MCP) servers later without code rewrites.
- **Strict Read-Only Sandboxing:** The Research Agent is granted only query and fetch privileges. Out-of-scope write actions (e.g. deleting, mailing, creating records) are gated by system guardrails and rejected with professional refusals.
- **Traceable Execution Logs (Observability):** Every step of the agent execution (prompts, tool calls, tool results) is logged to facilitate admin monitoring and debugging.

## Completed Tasks Record
* *Commit 34:* Implement Research Agent, PydanticAI tools (`search_knowledge_base`, `read_document_chunk`, `search_web`), and dependencies.
* *Commit 35:* Integrate Research Agent endpoint in `app/api/v1/agents.py` and register in router.
* *Commit 36:* Update Streamlit UI workspace, write unit/integration test suite `tests/test_research_agent.py`, clean up formatting/linting, and update CHANGELOG.
