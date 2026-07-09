# Milestone 16: Multi-Agent Orchestration (Central Coordinator via LangGraph)

## Goal
Design and build the **Coordinator Agent**, the central routing and orchestrating agent of the platform. Using a **LangGraph state graph**, the Coordinator analyzes user queries, decides which specialized agent (Research Agent or Document Agent) should handle the task, executes the specialist node, and compiles a unified, structured final response. The orchestrator must support multi-tenant isolation, logging, comprehensive unit/integration testing, and frontend workspace integration.

## Status
- [x] Define the Coordinator Agent routing schemas and orchestrator state (`app/services/coordinator_agent.py`)
- [x] Implement the routing decision agent (`router_agent`) and the direct response agent (`direct_agent`)
- [x] Construct the LangGraph workflow structure (nodes: `route`, `research`, `document`, `direct` + conditional edges)
- [x] Integrate the Coordinator Agent into the FastAPI layout (`app/api/v1/agents.py`)
- [x] Implement multi-agent routing test suites and integration tests under `tests/test_coordinator_agent.py`
- [x] Add a "Multi-Agent Coordinator Workspace" interface tab in the Streamlit frontend with step-by-step thinking feedback
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **LangGraph for State Graph Coordination:** LangGraph manages the state machine (router -> specialist agents -> compiler), ensuring clean routing logic that decouples coordination from individual agent business logic.
- **PydanticAI Router with Structured Outputs:** The Coordinator's routing node uses a dedicated PydanticAI agent returning a typed routing decision. This prevents non-deterministic prompt engineering failures and guarantees robust routing.
- **Structured Coordinator Schema:** The final response maps select agent info, routing reason, summary, markdown details, and cited sources into a single schema for frontend consistency.

## Completed Tasks Record
* *Commit 40:* Implement Coordinator Agent, routing PydanticAI models, direct chat agent, and the LangGraph workflow.
* *Commit 41:* Integrate Coordinator Agent endpoint in `app/api/v1/agents.py` and register in router.
* *Commit 42:* Update Streamlit UI workspace, write unit/integration test suite `tests/test_coordinator_agent.py`, clean up formatting/linting, and update CHANGELOG.
