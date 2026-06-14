# OpenHarness Web Platform Design

> Date: 2026-06-15
> Status: Draft
> Scope: Minimal changes to make OpenHarness accessible via Web with session isolation

## Problem Statement

OpenHarness is designed as a single-user CLI tool. When used as a web platform foundation, it has two fundamental blockers:

1. **No web access**: The only UI is CLI (React TUI via stdin/stdout). FastAPI exists but only serves the financial pipeline, with no general QueryEngine integration.
2. **No session isolation**: All state (settings, credentials, sessions, memory) is keyed by project path without a user/session dimension. Concurrent web users will experience context mixing — conversations from different sessions bleed into each other.

The root cause: CLI mode achieves isolation through **process separation** (each `oh` invocation = one OS process = one RuntimeBundle). In a web server, multiple users share one process with no isolation mechanism.

## Design Goal

Make OpenHarness usable as a web-accessible agent platform foundation with minimal changes to the core engine. The approach:

- Phase 1: Web access + session isolation (this spec)
- Phase 2: Skills configured via code, callable through web
- Phase 3: Configurable/composable agent platform (future)

## Architecture Overview

### HTTP + SSE Dual-Channel Pattern

Server→client streaming uses SSE (industry standard, simple, proxy-friendly). Client→server actions use standard HTTP POST. Bidirectional interactions (permission prompts, AskUserQuestion) are handled by pausing the SSE stream with an interaction request, and resuming when the client POSTs a response.

```
┌──────────────────────────────────────────────────┐
│ FastAPI Server (single process)                  │
│                                                  │
│  WebRuntimePool                                  │
│  ┌─────────────┬──────────────┬────────────────┐│
│  │ session_abc │ session_def  │ session_ghi    ││
│  │ RuntimeBundle│ RuntimeBundle│ RuntimeBundle  ││
│  │ QueryEngine │ QueryEngine  │ QueryEngine    ││
│  │ ToolRegistry│ ToolRegistry │ ToolRegistry   ││
│  │ cwd=/proj/a │ cwd=/proj/b  │ cwd=/proj/c   ││
│  └─────────────┴──────────────┴────────────────┘│
│                                                  │
│  SSE channel (server → client):                  │
│    POST /sessions/{id}/chat ← per-turn SSE stream│
│                                                  │
│  HTTP POST channel (client → server):            │
│    POST /sessions                 ← create       │
│    POST /sessions/{id}/chat       ← send message │
│    POST /sessions/{id}/interact/{req_id} ← reply │
│    GET  /sessions                 ← list         │
│    DELETE /sessions/{id}          ← delete       │
│                                                  │
│  Internal bridge:                                │
│    SSE emits interaction_request →               │
│    asyncio.Future pauses agent loop →            │
│    POST /interact/{req_id} resolves Future →     │
│    SSE stream resumes                            │
└──────────────────────────────────────────────────┘
         ↕ SSE stream + HTTP POST
┌──────────────────────────────────────────────────┐
│ Web Frontend (Vue 3)                             │
│  Chat UI + Skill selector + Tool progress        │
│  Interaction modals (permission/question/edit)    │
└──────────────────────────────────────────────────┘
```

### Why HTTP+SSE over WebSocket

- SSE is simpler, more widely supported, works with any HTTP infrastructure
- Client→server actions (permission confirm, question answer) are low-frequency discrete operations — HTTP POST is sufficient
- SSE has built-in reconnection via `Last-Event-ID`
- Industry standard: OpenAI, Anthropic, Vercel AI SDK all use SSE for AI chat streaming
- WebSocket adds complexity (ping/pong, frame parsing, reconnect logic) without meaningful benefit for this use case

## WebRuntimePool Design

The core isolation mechanism, modeled after `ohmo/gateway/runtime.py` `OhmoSessionRuntimePool`.

### Dual-Coroutine Architecture

The key design challenge: when the agent loop pauses for a permission prompt or AskUserQuestion, the SSE stream must still emit the interaction request event to the client. The solution uses an `asyncio.Queue` to decouple the agent loop from SSE streaming:

- **Coroutine A (agent loop)**: Runs `run_query()` in a background task, converts `StreamEvent` tuples to `SSEEvent` objects, puts them on an `asyncio.Queue`
- **Coroutine B (SSE stream)**: Reads from the queue and yields SSE events to the FastAPI `StreamingResponse`
- When permission_prompt() or ask_user_prompt() is called, it puts an interaction request SSE event on the queue **before** creating and awaiting an `asyncio.Future`
- SSE stream yields the interaction request event, then naturally pauses (no new events on queue until the Future is resolved)
- Client responds via `POST /interact/{req_id}`, which resolves the Future
- Agent loop resumes, puts more events on the queue
- SSE stream continues yielding

```python
class WebChatSession:
    """One active chat turn with its own event queue and pending interactions."""

    event_queue: asyncio.Queue[SSEEvent]
    pending_interactions: dict[str, asyncio.Future]
    agent_task: asyncio.Task

    async def start_agent_loop(self, bundle: RuntimeBundle, message: str):
        """Coroutine A: run agent loop, put events on queue."""
        # Inject web-specific permission_prompt and ask_user_prompt
        context = build_query_context(bundle, self)
        context.permission_prompt = self.web_permission_prompt
        context.ask_user_prompt = self.web_ask_user_prompt

        async for event, usage in run_query(context, messages):
            sse_event = stream_event_to_sse(event)
            await self.event_queue.put(sse_event)

    async def stream_sse(self) -> AsyncIterator[SSEEvent]:
        """Coroutine B: read from queue, yield SSE events."""
        while True:
            event = await self.event_queue.get()
            yield event
            if event.type in ("assistant_complete", "error"):
                break  # End of turn
```

```python
class WebRuntimePool:
    """Manages web session RuntimeBundles with per-session isolation."""

    _bundles: dict[str, RuntimeBundle]       # session_id → bundle
    _session_configs: dict[str, SessionConfig]  # session_id → config

    def create_session(self, config: SessionConfig) -> SessionInfo:
        """Create a new session with isolated RuntimeBundle.

        - build_runtime() with per-session cwd, model, settings
        - Register tools via create_default_tool_registry()
        - Load skills via load_skill_registry()
        - Return session_id and available skills/tools info
        """

    def get_bundle(self, session_id: str) -> RuntimeBundle | None:
        """Get existing session bundle. None if session doesn't exist."""

    async def chat(self, session_id: str, message: str) -> AsyncIterator[SSEEvent]:
        """Execute one agent turn, yield SSE events.

        Creates a WebChatSession, starts agent loop as background task,
        then yields events from the session's event_queue.
        When agent pauses for interaction, event_queue still emits
        the interaction_request event before going idle.
        """

    def resolve_interaction(self, session_id: str, req_id: str, response: str):
        """Resolve a pending interaction Future.

        Called by POST /sessions/{id}/interact/{req_id}
        Resolves the Future, allowing agent loop to continue.
        """

    def destroy_session(self, session_id: str):
        """Close session: close_runtime(), remove from pool."""

    def list_sessions(self) -> list[SessionInfo]:
        """List all active sessions with summary info."""

    def load_session(self, session_id: str, snapshot_path: str) -> SessionInfo:
        """Restore a session from a saved snapshot."""
```

### SessionConfig

```python
class SessionConfig(BaseModel):
    """Per-session configuration — replaces global settings for web sessions."""

    session_id: str = ""  # auto-generated if empty
    cwd: str              # working directory for this session
    model: str = ""       # override model (empty = use default)
    provider_profile: str = ""  # override provider profile
    skill_dirs: list[str] = []  # additional skill directories
    permission_mode: str = "default"  # default / plan / full_auto
    system_prompt_extra: str = ""  # additional instructions
    api_key: str = ""     # per-session API key override (optional)
```

## API Endpoint Specifications

### Session Management

#### POST /api/v1/sessions — Create Session

```json
// Request
{
  "cwd": "/path/to/project",
  "model": "qwen-max",           // optional
  "provider_profile": "dashscope", // optional
  "permission_mode": "default",   // optional
  "skill_dirs": [],               // optional
  "system_prompt_extra": ""       // optional
}

// Response
{
  "session_id": "abc123",
  "status": "ready",
  "model": "qwen-max",
  "available_skills": [
    {"name": "financial_hotspot_pipeline", "description": "..."},
    {"name": "debug", "description": "..."}
  ],
  "available_tools": ["bash", "read_file", "web_search", ...]
}
```

#### GET /api/v1/sessions — List Sessions

```json
// Response
[
  {
    "session_id": "abc123",
    "cwd": "/path/to/project",
    "model": "qwen-max",
    "created_at": "2026-06-15T10:00:00Z",
    "message_count": 5,
    "last_activity": "2026-06-15T10:30:00Z"
  }
]
```

#### DELETE /api/v1/sessions/{id} — Destroy Session

```json
// Response
{"status": "destroyed", "session_id": "abc123"}
```

### Chat Endpoint

#### POST /api/v1/sessions/{id}/chat — Send Message (SSE Response)

If `Accept: text/event-stream` → SSE streaming response.
If `Accept: application/json` → synchronous JSON response (for simple use cases).

```json
// Request
{
  "message": "分析一下最近的金融热点",
  "skill": "",  // optional: force a specific skill
  "images": []  // optional: base64 encoded images
}
```

SSE response events:

```
event: assistant_delta
data: {"text": "我来分析一下..."}

event: tool_started
data: {"tool_name": "financial_hotspot_scanner", "tool_input": {...}}

event: tool_completed
data: {"tool_name": "financial_hotspot_scanner", "output": "...", "is_error": false}

event: assistant_delta
data: {"text": "根据扫描结果，当前热点包括..."}

event: assistant_complete
data: {"usage": {"input_tokens": 5000, "output_tokens": 3000}}
```

### Interaction Endpoint

#### POST /api/v1/sessions/{id}/interact/{req_id} — Resolve Interaction

```json
// Permission response
{
  "response": "allow"  // or "deny"
}

// Question response
{
  "response": "GLM-4"  // free text answer
}

// Edit approval response
{
  "response": "once"  // or "always" or "reject"
}

// Response (always immediate)
{
  "status": "resolved",
  "req_id": "p1"
}
```

### Health Check

#### GET /api/v1/health

```json
{
  "status": "healthy",
  "version": "0.1.9",
  "active_sessions": 3
}
```

## SSE Event Types

Complete event type coverage for all agent loop outputs:

| Event | Direction | Data | Description |
|-------|-----------|------|-------------|
| `session_ready` | server→client | `{session_id, model, tools, skills}` | Session initialized |
| `assistant_delta` | server→client | `{text}` | Token-by-token streaming |
| `assistant_complete` | server→client | `{usage}` | Turn complete |
| `tool_started` | server→client | `{tool_name, tool_input}` | Tool execution beginning |
| `tool_completed` | server→client | `{tool_name, output, is_error}` | Tool finished |
| `compact_progress` | server→client | `{phase, trigger}` | Context compaction progress |
| `status` | server→client | `{message}` | Status updates (retry, waiting) |
| `error` | server→client | `{message, recoverable}` | Error event |
| `permission_request` | server→client | `{req_id, tool, command/file_path, reason}` | **Pause** — needs user approval |
| `question_request` | server→client | `{req_id, question, options}` | **Pause** — needs user answer |
| `edit_diff_request` | server→client | `{req_id, file_path, diff}` | **Pause** — needs edit approval |
| `session_end` | server→client | `{session_id}` | Session terminated |

Events marked **Pause** cause the SSE stream to stay open but emit no further events until the client resolves the interaction via `POST /interact/{req_id}`.

## Bidirectional Interaction Flow

### Permission Confirmation Flow

```
Server (SSE)                     Client (HTTP)
  │                                │
  │ ← agent calls bash tool       │
  │ ← PermissionChecker returns   │
  │   requires_confirmation=True  │
  │                                │
  │ → SSE: permission_request     │
  │   {req_id:"p1", tool:"bash",  │
  │    command:"pip install..."}  │
  │ → asyncio.Future() ⏸️          │
  │   SSE stream idle, no events  │
  │                                │
  │                                │ → User sees modal in UI
  │                                │ → User clicks "Allow"
  │                                │
  │                                │ → POST /sessions/abc/interact/p1
  │                                │   {"response": "allow"}
  │                                │
  │ → Future.resolve("allow") ▶️  │
  │ → agent loop continues        │
  │ → SSE: tool_started           │
  │ → SSE: tool_completed         │
  │ → SSE: assistant_complete     │
```

### AskUserQuestion Flow

Same pattern as permission, but:

- SSE event type is `question_request` with `{req_id, question, options}`
- POST response is `{"response": "user's answer text"}`

### Edit Approval Flow

Same pattern, but:

- SSE event type is `edit_diff_request` with `{req_id, file_path, diff}`
- POST response is `{"response": "once"/"always"/"reject"}`

## QueryEngine Interaction Adapter

The current QueryEngine passes `permission_prompt` and `ask_user_prompt` as callable functions. In CLI mode, these call stdin/stdout. In web mode, they create Futures.

```python
# New adapter in web_runtime_pool.py

class WebInteractionAdapter:
    """Converts QueryEngine's callback-based interaction to Future-based SSE interaction.

    Lives inside WebChatSession. When permission_prompt/ask_user_prompt is called
    from within _execute_tool_call() in the agent loop, this adapter:

    1. Generates a unique req_id
    2. Puts an interaction_request SSE event on the session's event_queue
       (Coroutine B reads this and yields it to the SSE client)
    3. Creates an asyncio.Future and registers it in pending_interactions
    4. Awaits the Future (Coroutine A pauses here; Coroutine B is idle)
    5. When POST /interact/{req_id} resolves the Future, returns the result
    """

    def __init__(self, event_queue: asyncio.Queue, pending_interactions: dict[str, asyncio.Future]):
        self.event_queue = event_queue
        self.pending_interactions = pending_interactions

    async def permission_prompt(self, tool_name: str, input_data: dict, reason: str) -> str:
        """Called by QueryEngine when permission needs confirmation.

        Puts permission_request SSE event on queue BEFORE awaiting Future.
        Returns "allow" or "deny" when Future is resolved.
        """
        req_id = f"perm_{uuid4().hex[:8]}"
        future = asyncio.Future()
        self.pending_interactions[req_id] = future

        await self.event_queue.put(SSEEvent(
            type="permission_request",
            data={"req_id": req_id, "tool": tool_name,
                  "command": input_data.get("command", ""),
                  "file_path": input_data.get("file_path", ""),
                  "reason": reason}
        ))
        result = await future
        return result

    async def ask_user_prompt(self, question: str, options: list[str] | None) -> str:
        """Called by QueryEngine when agent wants to ask user a question.

        Same pattern: put question_request SSE event, await Future.
        Returns user's answer text.
        """
        req_id = f"ques_{uuid4().hex[:8]}"
        future = asyncio.Future()
        self.pending_interactions[req_id] = future

        await self.event_queue.put(SSEEvent(
            type="question_request",
            data={"req_id": req_id, "question": question,
                  "options": options or []}
        ))
        result = await future
        return result

    def resolve_interaction(self, req_id: str, response: str):
        """Called by POST /interact/{req_id}. Resolves the pending Future."""
        future = self.pending_interactions.pop(req_id, None)
        if future and not future.done():
            future.set_result(response)
```

This adapter is injected into `QueryContext` as `permission_prompt` and `ask_user_prompt` when creating a web session. The core engine loop (`run_query()`) calls these callbacks at the same points it currently calls the CLI versions — **no engine code changes required**.

## Session Isolation Fixes

### Per-Session cwd (replaces os.chdir)

Current: `os.chdir(cwd)` in `run_backend_host()` — process-wide, breaks multi-user.

Fix: Remove `os.chdir()`. Pass cwd through session state:

- `SessionConfig.cwd` → stored in `RuntimeBundle`
- `ToolExecutionContext.cwd` → already supports per-execution cwd
- `QueryEngine` → uses `cwd` from `QueryContext`
- All tools that need cwd → read from `ToolExecutionContext.cwd` (they already do)

Most tools already receive cwd from `ToolExecutionContext`. The only call that needs change is `os.chdir()` in `backend_host.py`, which is CLI-specific and won't be called in web mode.

### Per-Session Settings (replaces global settings.json)

Current: `load_settings()` reads `~/.openharness/settings.json` — single global file.

Fix: Load global settings once at server startup as defaults. Each session overrides specific fields from `SessionConfig`:

```python
def build_web_runtime(session_config: SessionConfig) -> RuntimeBundle:
    """Build a RuntimeBundle with per-session settings overrides."""
    base_settings = load_settings()  # global defaults

    # Override per-session fields
    if session_config.model:
        base_settings.model = session_config.model
    if session_config.provider_profile:
        base_settings.active_profile = session_config.provider_profile
    if session_config.permission_mode:
        base_settings.permission.mode = session_config.permission_mode

    # Use session_config.cwd instead of os.chdir()
    cwd = Path(session_config.cwd).resolve()

    # Build runtime with overridden settings and explicit cwd
    return build_runtime(
        cwd=cwd,
        settings=base_settings,
        extra_skill_dirs=session_config.skill_dirs,
        system_prompt_extra=session_config.system_prompt_extra,
    )
```

### Per-Session Tool Metadata

Current: `QueryEngine._tool_metadata` is instance-scoped. Already isolated per engine instance.

No changes needed — each `RuntimeBundle` has its own `QueryEngine` with its own `_tool_metadata`.

### Per-Session Memory

Current: Memory is project-level (keyed by cwd path hash). In web mode, different users on the same project would share memory.

Deferred to Phase 3. For Phase 1, memory remains project-scoped since the initial use case is a single team creating investment research agents. Multi-user memory isolation will be added when needed.

## Implementation Changes

### New Files

| File | Lines | Description |
|------|-------|-------------|
| `src/openharness/web_runtime_pool.py` | ~250 | WebRuntimePool + WebInteractionAdapter + SessionConfig |
| `src/openharness/api/routes/session.py` | ~150 | Session CRUD + chat SSE + interact POST endpoints |
| `src/openharness/api/routes/sse_bridge.py` | ~100 | StreamEvent → SSE event format adapter |

### Modified Files

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/openharness/api/main.py` | ~20 | Register session routes, update app title |
| `src/openharness/ui/runtime.py` | ~30 | `build_runtime()` accept explicit cwd and settings override params |
| `src/openharness/engine/query.py` | ~15 | `run_query()` accept Future-based permission/ask callbacks (currently accepts callable, no change needed — the adapter is the callable) |
| `frontend/` | ~300 | Chat UI component with SSE listener + interaction modals |

**Note**: The `WebInteractionAdapter.permission_prompt()` and `ask_user_prompt()` methods are regular async callables. They plug into the same callback slots that CLI mode uses. **QueryEngine.run_query() requires zero code changes** — it already accepts `permission_prompt` and `ask_user_prompt` as callables in `QueryContext`.

### Core Engine — Zero Changes

These files are NOT modified:

- `engine/query_engine.py` — uses callbacks, no change
- `engine/query.py` — uses QueryContext, no change
- `tools/` — all 43+ tools use ToolExecutionContext, no change
- `skills/` — skill system works as-is, no change
- `permissions/checker.py` — pure logic, no change
- `memory/` — project-scoped for Phase 1, no change
- `auth/` — uses global settings for provider resolution, no change for Phase 1

## Frontend Requirements

### Chat UI (Vue 3)

Core components:

1. **ChatView** — Main chat interface
   - Message list (user + assistant messages)
   - Input box with skill selector dropdown
   - SSE connection management

2. **SSEListener** — SSE event handler
   - Connect to `GET /sessions/{id}/stream`
   - Dispatch events: `assistant_delta` → append to message, `tool_started/completed` → show progress, `interaction_request` → show modal

3. **InteractionModal** — Permission/Question/Edit approval dialog
   - Display tool name, command, or question
   - Allow/Deny buttons → POST to `/interact/{req_id}`
   - Question input → POST answer to `/interact/{req_id}`

4. **SessionManager** — Session CRUD
   - Create new session (select cwd, model, skill)
   - List sessions
   - Delete sessions

5. **SkillSelector** — Dropdown to pick or force a skill
   - Lists available skills from session creation response
   - Optional: force skill before sending message

### SSE Connection Lifecycle

```
1. POST /api/v1/sessions → get session_id + available skills/tools
2. POST /api/v1/sessions/{id}/chat → SSE streaming response
   - Request body: {message, skill?, images?}
   - Response: text/event-stream with per-turn events
3. Read SSE events → update UI in real-time
4. If interaction_request (permission/question/edit) → show modal
   - POST /api/v1/sessions/{id}/interact/{req_id}
5. When assistant_complete → SSE stream closes (end of turn)
6. Next message → POST /sessions/{id}/chat again → new SSE stream
```

Note: SSE stream is **per-chat-turn**, not per-session. Each `POST /chat` opens a new SSE stream. This matches how most AI chat platforms work (OpenAI, Anthropic, Vercel AI SDK). The session state (conversation history, tool_metadata) persists on the server between turns — only the SSE connection is closed.

## Phasing

### Phase 1 — Web Access + Session Isolation (This Spec)

Goal: OpenHarness accessible via web, multiple sessions don't conflict.

- WebRuntimePool with session isolation
- HTTP + SSE dual-channel API
- Bidirectional interaction adapter
- Vue 3 chat frontend
- Per-session cwd and settings override
- Core engine: zero changes

### Phase 2 — Skills Callable via Web

Goal: Skills written as code, configured into system, callable through web.

- Skill loading from configurable directories
- Skill selector in web UI
- Skill execution with SSE progress
- Skill result display (text, images, artifacts)

### Phase 3 — Configurable Agent Platform

Goal: Configure agents through UI without writing code.

- Agent definition UI (select tools, skills, model, permission mode)
- Multi-agent pipeline UI (DAG editor)
- Per-user memory isolation
- Multi-user authentication system
- Database-backed session persistence (Redis/PostgreSQL)
- Global singleton removal (TaskManager, BridgeManager, etc.)
- Horizontal scaling support

## Open Issues (Deferred)

1. **Global singletons**: TaskManager, BridgeManager, TeamRegistry remain global in Phase 1. They work fine for single-user web access. Multi-user isolation deferred to Phase 3.

2. **Authentication**: No user auth in Phase 1. The web server is trusted-network/internal deployment. Real auth (JWT/OAuth) deferred to Phase 3.

3. **Memory isolation**: Project-scoped memory shared across sessions in Phase 1. Acceptable for same-team use. Per-user memory deferred to Phase 3.

4. **Credentials**: Global `credentials.json` shared in Phase 1. Per-session API key override via `SessionConfig.api_key` works for simple cases. Full credential isolation deferred to Phase 3.

5. **Horizontal scaling**: Single-process deployment in Phase 1. Session state in memory only. Redis/DB persistence deferred to Phase 3.

6. **Long-lived SSE vs per-turn SSE**: Per-turn SSE chosen for simplicity. Long-lived SSE (one connection per session) is an optimization for Phase 2 if needed.
