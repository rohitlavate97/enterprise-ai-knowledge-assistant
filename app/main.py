"""Enterprise AI Knowledge Assistant main FastAPI application."""

from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    description=(
        "Production-grade AI Knowledge Assistant supporting "
        "RAG and Multi-Agent workflows."
    ),
    version="0.1.0",
)

# Register versioned API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Check the health status of the application.

    Returns:
        dict[str, str]: Health status message.
    """
    return {"status": "healthy"}
