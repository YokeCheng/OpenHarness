"""Pydantic models for OpenHarness API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    prompt: str = Field(
        ...,
        description="Natural language prompt to send to the agent",
        min_length=1,
        max_length=4000,
    )
    model: Optional[str] = Field(
        default=None,
        description="Override model for this request",
    )
    max_turns: Optional[int] = Field(
        default=None,
        description="Maximum agent loop turns",
    )
    permission_mode: Optional[str] = Field(
        default="full_auto",
        description="Permission mode for this request: default, plan, or full_auto",
        pattern="^(default|plan|full_auto)$",
    )


class ChatResponseRequest(BaseModel):
    """Request model for responding to permission/question prompts via /chat/response."""

    request_id: str = Field(..., description="ID of the pending request to respond to")
    type: str = Field(
        ...,
        description="Response type: permission_response or question_response",
        pattern="^(permission_response|question_response)$",
    )
    answer: Optional[str] = Field(
        default=None,
        description="Selected answer (for question_response: option value; for permission_response: 'y' or 'n')",
    )
    allowed: Optional[bool] = Field(
        default=None,
        description="Whether to allow the tool call (for permission_response)",
    )