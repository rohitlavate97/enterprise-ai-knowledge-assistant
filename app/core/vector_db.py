"""Qdrant Vector Database client configuration and initialization."""

import logging

from qdrant_client import QdrantClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize client. For testing or local-development fallback, use in-memory.
if settings.APP_ENV == "testing" or not settings.QDRANT_HOST:
    logger.info("Initializing in-memory Qdrant Client for isolated execution.")
    qdrant_client = QdrantClient(location=":memory:")
else:
    try:
        logger.info(
            "Connecting to remote Qdrant server at %s:%d",
            settings.QDRANT_HOST,
            settings.QDRANT_PORT,
        )
        qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY
            if settings.QDRANT_API_KEY
            else None,
            timeout=5,
        )
    except Exception as err:
        logger.warning(
            "Could not connect to Qdrant server (%s). "
            "Falling back to in-memory Qdrant client.",
            str(err),
        )
        qdrant_client = QdrantClient(location=":memory:")
