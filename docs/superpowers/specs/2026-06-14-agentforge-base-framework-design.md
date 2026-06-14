# AgentForge — OpenHarness Base Framework Extraction Design

Date: 2026-06-14

## Goal

Create a `base-framework` branch in the OpenHarness repo that contains only the generic agent infrastructure, with all OpenHarness-specific business code removed. This branch serves as the starting point for any new project — fork the repo, check out `base-framework`, add your own tools/skills.

## Strategy

- **No renaming** — `openharness` stays as the package name. It IS the base framework.
- **No restructuring** — keep the same directory layout, imports, and module boundaries.
- **Branch-based** — `base-framework` branch lives in the same repo alongside `main`.
- **New project flow** — fork repo → check out `base-framework` → add business tools/skills.

## What to Remove

### Business Tools (3 files)
- `src/openharness/tools/financial_hotspot_scanner.py`
- `src/openharness/tools/financial_copywriter.py`
- `src/openharness/tools/infographic_renderer.py`

### Business Templates (1 package)
- `src/openharness/templates/` (xingfengxiang brand template, HTML/CSS)

### Business Skills/Plans (docs only, not code)
- `docs/superpowers/plans/2026-06-07-financial-*`
- `docs/superpowers/specs/2026-06-07-financial-*`

### Business Test Data
- `test_e2e_chip_stocks/`
- `tests/api/test_financial_pipeline.py`

### Business API Routes
- `src/openharness/api/routes/financial.py` (if it exists in base-framework branch)
- `src/openharness/api/routes/execute.py` (generic but was financial-demo-specific)

### Business Frontend Components (if present)
- Any financial hotspot form components

### Business Assets
- Brand images (长图-logo, 汇添富科创等 PNG files)
- `openharness-web-interface.html` (one-off demo)
- `test-web-interface.html` (one-off demo)

## What to Keep (Framework Layer)

All FRAMEWORK-classified modules remain untouched:

| Module | Purpose |
|--------|---------|
| `api/` | LLM provider abstraction (Claude, OpenAI, Codex, Copilot clients) |
| `auth/` | Credential storage, external auth |
| `config/` | Settings, paths, schema |
| `engine/` | QueryEngine, stream events, messages, cost tracking |
| `permissions/` | Permission modes, checker |
| `hooks/` | Hook lifecycle system |
| `tools/` (base + 40 generic tools) | Bash, file ops, grep, glob, web, MCP, etc. |
| `skills/` | Skill loading, registry, frontmatter |
| `commands/` | Slash command dispatch |
| `mcp/` | Model Context Protocol client |
| `memory/` | Conversation persistence, search |
| `services/` | Cron, LSP, session, compact, token estimation |
| `channels/` | Multi-channel messaging (Slack, Discord, etc.) |
| `swarm/` | Multi-agent orchestration |
| `coordinator/` | Agent coordination mode |
| `sandbox/` | Docker sandboxed execution |
| `plugins/` | Plugin system |
| `personalization/` | User personalization |
| `prompts/` | System prompt construction |
| `state/` | App state management |
| `tasks/` | Background task management |
| `utils/` | Shell, fs, network helpers |
| `bridge/` | CLI-engine session bridge |
| `autopilot/` | Autonomous execution mode |

UI layer also stays (needed for web API):
| `ui/` | TUI app, runtime builder, permission dialog |
| `api/routes/` | `/chat`, `/health` SSE endpoints |
| `cli.py` | CLI entry point |

## What to Adjust (Not Remove)

### `api/routes/` — remove financial, keep chat
- Remove `financial.py` route
- Remove `execute.py` route (was demo-specific)
- Keep `chat.py` (generic SSE agent loop)

### `api/schemas.py` — remove financial schemas
- Remove `FinancialHotspotPipelineRequest/Response`
- Remove `ExecuteRequest/Response`
- Keep `ChatRequest`, `ChatResponseRequest`, `HealthCheckResponse`

### `api/main.py` — remove financial route registration
- Remove financial router include
- Keep chat router

### `tools/__init__.py` or registry — remove financial tool registration
- Remove `financial_hotspot_scanner`, `financial_copywriter`, `infographic_renderer` from tool registry

### Frontend — remove financial demo pages
- Remove `HomeView` financial demo cards
- Keep `ChatView`, `ToolCard`, `ModePicker`, `ConfirmDialog`

## Branch Creation Steps

1. From `main`, create `base-framework` branch
2. Delete all business files listed above
3. Clean up imports/registrations that reference deleted modules
4. Verify `python -m openharness` starts correctly (engine + generic tools)
5. Verify web frontend (`/chat`) works
6. Commit with message: `chore: extract base framework — remove financial business modules`

## New Project Workflow

For each new project:

1. Fork OpenHarness → `github.com/Yokecheng/<new-project>`
2. Clone the fork
3. `git checkout base-framework`
4. Add project-specific tools in `src/openharness/tools/`
5. Add project-specific skills in `src/openharness/skills/`
6. Add project-specific routes in `src/openharness/api/routes/`
7. Register new tools/skills in the appropriate registries
8. Commit on a new branch (e.g. `main` or `<project>-business`)

## What's NOT in V1

- Separate pip package (openharness stays as monorepo package)
- Template project generator (`oh init` command)
- Business plugin system (future consideration)
- Configurable tool/skill discovery via directory scanning
