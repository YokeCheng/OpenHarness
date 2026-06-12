"""Chat API route — agent loop via QueryEngine, SSE streaming.

Supports per-request permission_mode switching and interactive
confirmation dialogs via SSE + /chat/response endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from openharness.api.schemas import ChatRequest, ChatResponseRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

# One runtime per server process; lazy-init on first request.
_runtime_lock = asyncio.Lock()
_runtime: Any = None  # RuntimeBundle or None

# Pending responses: request_id → asyncio.Future
# When a permission_request or question_request is emitted, the SSE stream
# pauses and stores the request_id here. POST /chat/response resolves the Future.
_pending_responses: dict[str, asyncio.Future] = {}


async def _get_runtime():
    """Lazily initialize the OpenHarness runtime (engine + tools + auth)."""
    global _runtime
    if _runtime is not None:
        return _runtime
    async with _runtime_lock:
        if _runtime is not None:
            return _runtime
        from openharness.ui.runtime import build_runtime
        logger.info("Initializing OpenHarness agent runtime...")
        _runtime = await build_runtime(
            cwd=str(Path.cwd()),
        )
        logger.info("Runtime ready — model=%s", _runtime.engine.model)
        return _runtime


async def _reset_runtime():
    """Force re-init on next request (e.g. after auth change)."""
    global _runtime
    _runtime = None


@router.post(
    "/chat",
    summary="Send a prompt to the agent and receive streaming SSE response",
)
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
) -> StreamingResponse:
    """
    Execute a prompt through the full OpenHarness agent loop (QueryEngine).

    Returns SSE events:
    - text_delta: incremental assistant text
    - tool_start: tool execution starting (tool_name, tool_input)
    - tool_complete: tool execution finished (tool_name, output)
    - tool_error: tool execution failed
    - turn_complete: assistant turn finished (usage stats)
    - permission_request: tool needs user confirmation (request_id, tool_name, description)
    - question_request: agent asks a question with options (request_id, title, options)
    - execution_complete: entire request done
    - execution_error: unrecoverable error
    """
    try:
        bundle = await _get_runtime()
    except Exception as e:
        logger.error("Runtime init failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent runtime failed to start: {e}")

    engine = bundle.engine

    # Override model/max_turns if requested
    if chat_request.model:
        engine.set_model(chat_request.model)
    if chat_request.max_turns is not None:
        engine.set_max_turns(chat_request.max_turns)

    # Set permission mode per request
    from openharness.permissions.modes import PermissionMode
    from openharness.permissions.checker import PermissionChecker
    from openharness.config.settings import PermissionSettings

    mode = PermissionMode(chat_request.permission_mode)
    checker = PermissionChecker(PermissionSettings(mode=mode))
    engine.set_permission_checker(checker)

    # Create SSE-based permission_prompt callback
    async def _sse_permission_prompt(tool_name: str, reason: str) -> bool:
        """Emit permission_request SSE event and await user response."""
        request_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        _pending_responses[request_id] = future

        # Emit permission_request event — the generator must yield it
        # We use a queue to pass the event to the SSE stream generator
        event_queue.put_nowait(
            {"event": "permission_request", "data": {
                "request_id": request_id,
                "tool_name": tool_name,
                "description": reason,
            }}
        )

        # Await user response via /chat/response endpoint
        try:
            result = await future
            return result.get("allowed", False)
        finally:
            _pending_responses.pop(request_id, None)

    # Event queue for injecting SSE events from callbacks
    event_queue: asyncio.Queue = asyncio.Queue()
    engine.set_permission_prompt(_sse_permission_prompt)

    async def sse_stream():
        try:
            yield f"data: {json.dumps({'event': 'execution_start', 'data': {'prompt': chat_request.prompt}})}\n\n"

            async for event in engine.submit_message(chat_request.prompt):
                evt_data = _serialize_event(event)
                yield f"data: {json.dumps(evt_data)}\n\n"

                # Drain any callback-generated events from the queue
                while not event_queue.empty():
                    cb_event = event_queue.get_nowait()
                    yield f"data: {json.dumps(cb_event)}\n\n"

            # Final drain of any remaining queued events
            while not event_queue.empty():
                cb_event = event_queue.get_nowait()
                yield f"data: {json.dumps(cb_event)}\n\n"

            yield f"data: {json.dumps({'event': 'execution_complete', 'data': {'status': 'success'}})}\n\n"
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {json.dumps({'event': 'execution_error', 'data': {'message': str(e)}})}\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")


@router.post(
    "/chat/response",
    summary="Respond to a permission or question prompt from the agent",
)
async def chat_response_endpoint(
    request: Request,
    response_request: ChatResponseRequest,
) -> dict:
    """
    Resolve a pending permission_request or question_request.

    The SSE stream pauses when a dialog is emitted. This endpoint
    receives the user's choice and resumes the stream.
    """
    future = _pending_responses.get(response_request.request_id)
    if future is None:
        raise HTTPException(status_code=404, detail=f"No pending request with id {response_request.request_id}")

    if future.done():
        raise HTTPException(status_code=400, detail=f"Request {response_request.request_id} already resolved")

    # Resolve the Future with the user's response
    if response_request.type == "permission_response":
        allowed = response_request.allowed if response_request.allowed is not None else False
        future.set_result({"allowed": allowed, "type": "permission_response"})
    elif response_request.type == "question_response":
        future.set_result({"answer": response_request.answer, "type": "question_response"})
    else:
        raise HTTPException(status_code=400, detail=f"Unknown response type: {response_request.type}")

    return {"status": "ok", "request_id": response_request.request_id}


def _serialize_event(event: Any) -> dict:
    """Convert a StreamEvent to a JSON-serializable SSE payload."""
    from openharness.engine.stream_events import (
        AssistantTextDelta,
        AssistantTurnComplete,
        ToolExecutionStarted,
        ToolExecutionCompleted,
        ErrorEvent,
        StatusEvent,
        CompactProgressEvent,
    )

    if isinstance(event, AssistantTextDelta):
        return {"event": "text_delta", "data": {"text": event.text}}

    if isinstance(event, AssistantTurnComplete):
        usage = {}
        if event.usage:
            usage = {"input_tokens": event.usage.input_tokens, "output_tokens": event.usage.output_tokens}
        return {"event": "turn_complete", "data": {"usage": usage}}

    if isinstance(event, ToolExecutionStarted):
        return {"event": "tool_start", "data": {"tool_name": event.tool_name, "tool_input": event.tool_input}}

    if isinstance(event, ToolExecutionCompleted):
        return {"event": "tool_complete", "data": {"tool_name": event.tool_name, "output": event.output, "is_error": event.is_error}}

    if isinstance(event, ErrorEvent):
        return {"event": "error", "data": {"message": event.message, "recoverable": event.recoverable}}

    if isinstance(event, StatusEvent):
        return {"event": "status", "data": {"message": event.message}}

    if isinstance(event, CompactProgressEvent):
        return {"event": "compact_progress", "data": {"phase": event.phase, "trigger": event.trigger, "message": event.message}}

    # Fallback for unknown event types
    return {"event": "unknown", "data": {"type": type(event).__name__}}