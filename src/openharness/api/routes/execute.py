"""Generic execute API routes."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from openharness.api.schemas import ExecuteRequest, ExecuteResponse
from openharness.api.utils import execute_prompt_via_existing_mechanism

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["execute"])


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    summary="Execute natural language prompt",
    description="Execute a natural language prompt through the OpenHarness skill system",
)
async def execute_prompt(
    request: Request,
    execute_request: ExecuteRequest,
) -> ExecuteResponse:
    """
    Execute a natural language prompt through the OpenHarness skill system.

    Args:
        request: FastAPI request object
        execute_request: Execution parameters including prompt and options

    Returns:
        ExecuteResponse with execution result and optional trace information
    """
    try:
        # Extract context from request if available, otherwise create minimal context
        context = getattr(request.state, "tool_context", None)

        result = await execute_prompt_via_existing_mechanism(
            prompt=execute_request.prompt,
            force_skill=execute_request.force_skill,
            execution_mode=execute_request.execution_mode,
            context_override=execute_request.context,
            tool_context=context,
        )

        return ExecuteResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error in execute: {e}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except RuntimeError as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in execute: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def _sse_generator(prompt: str, execution_mode: str, context):
    """Generate SSE events for streaming execution output."""
    try:
        result = await execute_prompt_via_existing_mechanism(
            prompt=prompt,
            execution_mode="stream",
            tool_context=context,
            sse_callback=lambda event_data: event_data
        )

        # For now, send a simple completion event
        yield f"data: {json.dumps({'status': 'complete', 'result': result})}\n\n"

    except Exception as e:
        error_data = {"status": "error", "message": str(e)}
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/execute/stream")
async def execute_stream(
    request: Request,
    execute_request: ExecuteRequest,
):
    """Execute prompt with SSE streaming output."""
    context = getattr(request.state, "tool_context", None)

    async def event_generator():
        yield f"data: {json.dumps({'message': f'Starting execution: {execute_request.prompt}'})}\n\n"

        try:
            # This will be enhanced in Task 3 to actually stream events
            result = await execute_prompt_via_existing_mechanism(
                prompt=execute_request.prompt,
                force_skill=execute_request.force_skill,
                execution_mode="stream",
                context_override=execute_request.context,
                tool_context=context,
            )
            yield f"data: {json.dumps({'status': 'complete', 'result': result})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )