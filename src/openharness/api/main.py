"""FastAPI application for OpenHarness agent API."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from openharness.api.routes.chat import router as chat_router
from openharness.api.schemas import HealthCheckResponse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenHarness Agent API",
    description="RESTful + SSE API for the OpenHarness agent loop",
    version="0.1.9",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="healthy", version="0.1.9")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Include router — chat is the only route now
app.include_router(chat_router)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8002"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"

    uvicorn.run(
        "openharness.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )