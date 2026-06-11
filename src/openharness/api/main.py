"""FastAPI application for OpenHarness financial hotspot pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from openharness.api.routes.execute import router as execute_router
from openharness.api.routes.financial import router as financial_router
from openharness.api.schemas import HealthCheckResponse


# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenHarness Financial Hotspot Pipeline API",
    description="RESTful API for the financial hotspot pipeline",
    version="0.1.9",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_tool_context(request: Request, call_next):
    """Add tool execution context to request state."""
    from openharness.tools.base import ToolExecutionContext
    request.state.tool_context = ToolExecutionContext(cwd=Path.cwd())
    response = await call_next(request)
    return response


@app.get("/api/v1/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    return HealthCheckResponse(status="healthy", version="0.1.9")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(financial_router)
app.include_router(execute_router)


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info")

    uvicorn.run(
        "src.openharness.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )