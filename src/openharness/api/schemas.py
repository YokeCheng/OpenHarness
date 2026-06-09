"""Pydantic models for financial hotspot pipeline API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class FinancialHotspotPipelineRequest(BaseModel):
    """Request model for financial hotspot pipeline endpoint."""

    topic: str = Field(
        ...,
        description="The financial topic to analyze",
        min_length=1,
        max_length=200,
    )
    content_type: str = Field(
        default="xingfengxiang",
        description="Content type/framework for the article",
        pattern="^(xingfengxiang|standard|knowledge_popularization)$",
    )
    product_data: Optional[str] = Field(
        default=None,
        description="Product recommendation data as JSON string",
    )


class FinancialHotspotPipelineResponse(BaseModel):
    """Response model for financial hotspot pipeline endpoint."""

    article: str = Field(..., description="Generated financial article content")
    visual_theme: dict[str, Any] = Field(..., description="Visual theme suggestions")
    infographic_path: str = Field(..., description="Path to generated infographic PNG")
    status: str = Field(..., description="Pipeline execution status")


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")


class ExecuteRequest(BaseModel):
    """Request model for generic execute endpoint."""

    prompt: str = Field(
        ...,
        description="Natural language prompt to execute",
        min_length=1,
        max_length=2000,
    )
    force_skill: Optional[str] = Field(
        default=None,
        description="Force execution of specific skill name",
    )
    execution_mode: str = Field(
        default="simple",
        description="Execution detail level: simple, detailed, or stream",
        pattern="^(simple|detailed|stream)$",
    )
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional execution context (cwd, model, etc.)",
    )


class ExecuteResponse(BaseModel):
    """Response model for generic execute endpoint."""

    status: str = Field(..., description="Execution status: success or error")
    execution_trace: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Detailed execution trace when execution_mode is detailed or verbose",
    )
    result: dict[str, Any] = Field(..., description="Final execution result")
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is error",
    )