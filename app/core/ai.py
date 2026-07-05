"""PydanticAI agent configuration and model selection."""

import logging

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentResponse(BaseModel):
    """Structured response type for the AI knowledge assistant agent."""

    answer: str = Field(
        description="The detailed answer to the question based on the provided context."
    )
    has_sufficient_context: bool = Field(
        description=(
            "True if the context was sufficient to answer the question, "
            "False otherwise."
        )
    )
    confidence_score: float = Field(
        description="Self-assessed confidence score of the answer from 0.0 to 1.0."
    )


# Model selection based on environment and config
ai_model: Model

if settings.APP_ENV == "testing" or not settings.OPENAI_API_KEY:
    logger.info("Using TestModel for PydanticAI Agent (offline/testing mode).")
    # For structured outputs, TestModel will dynamically generate a valid instance
    ai_model = TestModel()
else:
    logger.info("Using OpenAIChatModel: %s", settings.OPENAI_MODEL)
    provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
    ai_model = OpenAIChatModel(
        settings.OPENAI_MODEL,
        provider=provider,
    )

# Instantiate the assistant agent with structured output type
assistant_agent = Agent(
    ai_model,
    output_type=AgentResponse,
    system_prompt=(
        "You are an enterprise AI knowledge assistant. "
        "Formulate a detailed, professional answer using ONLY the provided "
        "document context chunks. If the context does not contain enough "
        "information, set has_sufficient_context to False."
    ),
)
