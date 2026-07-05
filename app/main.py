"""Enterprise AI Knowledge Assistant main FastAPI application."""

from fastapi import FastAPI

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    description=(
        "Production-grade AI Knowledge Assistant supporting "
        "RAG and Multi-Agent workflows."
    ),
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Check the health status of the application.

    Returns:
        dict[str, str]: Health status message.
    """
    return {"status": "healthy"}
