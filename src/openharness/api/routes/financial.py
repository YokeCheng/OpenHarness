"""Financial hotspot pipeline API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from openharness.api.schemas import (
    FinancialHotspotPipelineRequest,
    FinancialHotspotPipelineResponse,
)
from openharness.api.utils import execute_financial_hotspot_pipeline


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["financial"])


@router.post(
    "/financial-hotspot-pipeline",
    response_model=FinancialHotspotPipelineResponse,
    summary="Execute financial hotspot pipeline",
    description="Execute the complete financial hotspot pipeline: scanner → copywriter → renderer",
)
async def financial_hotspot_pipeline(
    request: Request,
    pipeline_request: FinancialHotspotPipelineRequest,
) -> FinancialHotspotPipelineResponse:
    """
    Execute the financial hotspot pipeline.

    Args:
        request: FastAPI request object
        pipeline_request: Pipeline input parameters

    Returns:
        FinancialHotspotPipelineResponse with article, visual theme, infographic path, and status
    """
    try:
        # Extract context from request if available, otherwise create minimal context
        context = getattr(request.state, "tool_context", None)

        result = await execute_financial_hotspot_pipeline(
            topic=pipeline_request.topic,
            content=pipeline_request.content,
            content_type=pipeline_request.content_type,
            product_data=pipeline_request.product_data,
            context=context,
        )

        return FinancialHotspotPipelineResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error in pipeline: {e}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Pipeline execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")