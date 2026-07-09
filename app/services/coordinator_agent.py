"""PydanticAI and LangGraph Coordinator Agent configuration and execution service."""

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import ai_model
from app.models.user import User
from app.services.document_agent import (
    AgentDeps as DocDeps,
    document_agent,
)
from app.services.research_agent import (
    AgentDeps as ResearchDeps,
    research_agent,
)

logger = logging.getLogger(__name__)


class RoutingDecision(BaseModel):
    """Schema representing the routing decision made by the Coordinator."""

    next_agent: str = Field(
        description="The next agent to route to: 'research', 'document', or 'direct'."
    )
    routing_reason: str = Field(
        description="The reasoning behind selecting this particular agent."
    )


class CoordinatorResponse(BaseModel):
    """Structured response type returned by the Coordinator Agent."""

    selected_agent: str = Field(
        description=(
            "The specialist agent that handled the request: "
            "'research', 'document', or 'direct'."
        )
    )
    routing_reason: str = Field(
        description="The explanation of why this specialist agent was selected."
    )
    summary: str = Field(description="A concise summary of the resolved answer.")
    detailed_findings: str = Field(
        description="Detailed, markdown-formatted response or findings."
    )
    documents_referenced: list[str] = Field(
        description="List of document IDs, point IDs, or filenames cited."
    )
    confidence_score: float = Field(
        description="Self-assessed confidence score from 0.0 to 1.0."
    )


class CoordinatorState(TypedDict):
    """State schema managed within the LangGraph Coordinator state graph."""

    query: str
    db: AsyncSession
    current_user: User
    next_agent: str
    routing_reason: str
    output: CoordinatorResponse | None


# Routing agent that analyzes queries and determines the next node
router_agent = Agent(
    ai_model,
    output_type=RoutingDecision,
    system_prompt=(
        "You are the central routing agent for an enterprise AI knowledge assistant.\n"
        "Analyze the user's query and decide which specialist agent should handle it:\n"
        "1. Route to 'research' if the query asks to search documents, "
        "compares policy contents, performs deep research, "
        "or asks about web-search facts.\n"
        "2. Route to 'document' if the query asks to list files, "
        "check status of files, inspect document metadata, "
        "or delete a document.\n"
        "3. Route to 'direct' if the query is a simple greeting, "
        "chit-chat, or general info that does not require "
        "searching files or checking upload status."
    ),
)

# Direct response agent for greetings and general chat
direct_agent = Agent(
    ai_model,
    system_prompt=(
        "You are the Coordinator Agent. Answer the user's greeting or general "
        "chit-chat query directly in a friendly, professional tone. "
        "Do not mention other agents or tools."
    ),
)


# LangGraph Node 1: Router
async def route_query_node(state: CoordinatorState) -> dict[str, Any]:
    """Node that decides which specialist agent to route the query to."""
    logger.info("Coordinator Node: Routing query='%s'", state["query"])
    try:
        decision = await router_agent.run(state["query"])
        return {
            "next_agent": decision.output.next_agent,
            "routing_reason": decision.output.routing_reason,
        }
    except Exception as err:
        logger.error("Coordinator routing failed: %s", str(err))
        # Fallback safely to direct agent in case of routing LLM issues
        return {
            "next_agent": "direct",
            "routing_reason": (
                f"Routing failed with error: {str(err)}. Falling back to direct."
            ),
        }


# LangGraph Node 2: Research Specialist Agent Execution
async def run_research_node(state: CoordinatorState) -> dict[str, Any]:
    """Node that executes the specialist Research Agent."""
    logger.info("Coordinator Node: Launching Research Agent...")
    try:
        deps = ResearchDeps(db=state["db"], current_user=state["current_user"])
        result = await research_agent.run(state["query"], deps=deps)
        output = CoordinatorResponse(
            selected_agent="research",
            routing_reason=state["routing_reason"],
            summary=result.output.summary,
            detailed_findings=result.output.detailed_findings,
            documents_referenced=result.output.sources_cited,
            confidence_score=result.output.confidence_score,
        )
        return {"output": output}
    except Exception as err:
        logger.error("Coordinator Research Agent invocation failed: %s", str(err))
        return {
            "output": CoordinatorResponse(
                selected_agent="research",
                routing_reason=state["routing_reason"],
                summary="Research Agent failed.",
                detailed_findings=f"Error executing Research Agent: {str(err)}",
                documents_referenced=[],
                confidence_score=0.0,
            )
        }


# LangGraph Node 3: Document Specialist Agent Execution
async def run_document_node(state: CoordinatorState) -> dict[str, Any]:
    """Node that executes the specialist Document Agent."""
    logger.info("Coordinator Node: Launching Document Agent...")
    try:
        deps = DocDeps(db=state["db"], current_user=state["current_user"])
        result = await document_agent.run(state["query"], deps=deps)
        output = CoordinatorResponse(
            selected_agent="document",
            routing_reason=state["routing_reason"],
            summary=result.output.response_summary,
            detailed_findings=result.output.document_details,
            documents_referenced=result.output.documents_referenced,
            confidence_score=1.0,  # document operations are deterministic lookup events
        )
        return {"output": output}
    except Exception as err:
        logger.error("Coordinator Document Agent invocation failed: %s", str(err))
        return {
            "output": CoordinatorResponse(
                selected_agent="document",
                routing_reason=state["routing_reason"],
                summary="Document Agent failed.",
                detailed_findings=f"Error executing Document Agent: {str(err)}",
                documents_referenced=[],
                confidence_score=0.0,
            )
        }


# LangGraph Node 4: Direct Response compile
async def run_direct_node(state: CoordinatorState) -> dict[str, Any]:
    """Node that handles simple greetings or direct chat."""
    logger.info("Coordinator Node: Answering query directly...")
    try:
        result = await direct_agent.run(state["query"])
        output = CoordinatorResponse(
            selected_agent="direct",
            routing_reason=state["routing_reason"],
            summary="General conversation response.",
            detailed_findings=result.output,
            documents_referenced=[],
            confidence_score=1.0,
        )
        return {"output": output}
    except Exception as err:
        logger.error("Coordinator direct answer failed: %s", str(err))
        return {
            "output": CoordinatorResponse(
                selected_agent="direct",
                routing_reason=state["routing_reason"],
                summary="Chit-chat agent failed.",
                detailed_findings=f"Error running direct agent: {str(err)}",
                documents_referenced=[],
                confidence_score=0.0,
            )
        }


# Conditional routing function
def route_next_agent(state: CoordinatorState) -> str:
    """Read the routing decision from state and return the next node target name."""
    next_node = state.get("next_agent", "direct")
    # Prevent invalid path mappings by falling back to direct
    if next_node not in ["research", "document", "direct"]:
        return "direct"
    return next_node


# Build and compile the LangGraph Orchestrator state graph
builder = StateGraph(CoordinatorState)
builder.add_node("route", route_query_node)
builder.add_node("research", run_research_node)
builder.add_node("document", run_document_node)
builder.add_node("direct", run_direct_node)

builder.add_edge(START, "route")
builder.add_conditional_edges(
    "route",
    route_next_agent,
    {
        "research": "research",
        "document": "document",
        "direct": "direct",
    },
)
builder.add_edge("research", END)
builder.add_edge("document", END)
builder.add_edge("direct", END)

coordinator_graph = builder.compile()
