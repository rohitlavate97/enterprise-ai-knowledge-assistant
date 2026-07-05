"""Service layer wrapping PydanticAI reasoning and generation."""

import logging

from app.core.ai import AgentResponse, assistant_agent

logger = logging.getLogger(__name__)


class AIService:
    """Service layer coordinating AI reasoning requests."""

    async def answer_with_context(
        self, question: str, context_chunks: list[str]
    ) -> AgentResponse:
        """Pass retrieved context chunks and query to PydanticAI for reasoning."""
        logger.info(
            "Requesting agent answer (chunks count: %d)", len(context_chunks)
        )

        # 1. Format prompt with context
        context_str = "\n---\n".join(context_chunks)
        prompt = (
            f"Question: {question}\n\n"
            f"Retrieved Context:\n{context_str}\n"
        )

        # 2. Run agent
        result = await assistant_agent.run(prompt)

        # PydanticAI automatically validates the response against AgentResponse!
        return result.output


ai_service = AIService()
