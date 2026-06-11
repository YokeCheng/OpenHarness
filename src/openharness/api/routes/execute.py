"""Generic execute API routes."""

from __future__ import annotations

import asyncio
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
        logger.error("Validation error in execute: %s", e)
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except RuntimeError as e:
        logger.error("Execution error: %s", e)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error in execute: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/execute/stream")
async def execute_stream(
    request: Request,
    execute_request: ExecuteRequest,
):
    """Execute prompt with SSE streaming output."""
    context = getattr(request.state, "tool_context", None)

    # Create a queue for SSE events
    sse_queue = asyncio.Queue()

    async def sse_callback(event_type: str, data: dict):
        """Callback function to send events to the SSE queue."""
        event_data = {
            "event": event_type,
            "data": data
        }
        await sse_queue.put(json.dumps(event_data))

    async def event_generator():
        # Send initial start event
        await sse_queue.put(json.dumps({
            "event": "execution_start",
            "data": {"prompt": execute_request.prompt, "force_skill": execute_request.force_skill}
        }))

        try:
            # Execute with SSE callback for real-time streaming
            result = await execute_prompt_via_existing_mechanism(
                prompt=execute_request.prompt,
                force_skill=execute_request.force_skill,
                execution_mode="stream",
                context_override=execute_request.context,
                tool_context=context,
                sse_callback=sse_callback,
            )

            # Send final completion event
            await sse_queue.put(json.dumps({
                "event": "execution_complete",
                "data": result
            }))

        except Exception as e:
            # Send error event
            await sse_queue.put(json.dumps({
                "event": "execution_error",
                "data": {"message": str(e)}
            }))

        # Signal end of stream
        await sse_queue.put(None)

    async def sse_stream():
        """Stream events from the queue as proper SSE format."""
        # Start the execution in the background
        generator_task = asyncio.create_task(event_generator())

        try:
            while True:
                event_json = await sse_queue.get()
                if event_json is None:
                    break
                yield f"data: {event_json}\n\n"
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'event': 'stream_error', 'data': {'message': str(e)}})}\n\n"
        finally:
            # Ensure the generator task completes
            await generator_task

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream"
    )