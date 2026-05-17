# AGENTS.md - Job Hunter

## Dev Commands

```bash
# Run all tests (mocks everywhere, no real API/db needed)
pytest tests/ -v

# Run single test file
pytest tests/test_db.py -v

# Run the MCP server (stdio mode)
python server.py
```

Tests use `unittest.mock` and tempfile SQLite DBs. No env vars or credentials needed.

## Architecture

- **Entrypoint:** `server.py` — MCP stdio server, registers 15 tools, dispatches to `tools/*.py`
- **Layers:** `tools/` (tool handlers) → `engine/` (business logic) → `llm/` / `browser/` / `db/` (adapters)
- **DB:** SQLite WAL at `data/boss_hunter.db` (gitignored). `db/schema.py` defines tables + `MIGRATIONS` list.
- **Matching:** Two-phase — `rule_filter()` quick-pass, then `llm_deep_match()` if rule score ≥ `MATCH_RULE_LLM_THRESHOLD`. Final = rule×0.3 + LLM×0.7.
- **Browser:** `BossOperator` wraps `boss-agent-cli` (pip package).
- **LLM:** OpenAI-compatible via `httpx.Client`, defaults to DeepSeek (`LLM_BASE_URL=https://api.deepseek.com`).

## Data Flow

```
Agent (MCP stdio) → server.py → tools/*.py → engine/ → llm|browser|db
```

Job state machine: `new → analyzed → matched → greeted → replied`

## Conventions

- Tool handlers return `{"ok": True/False, ...}` dicts; `ok: False` mut use `"error"` key.
- All tool code is synchronous; `server.py` dispatches via `asyncio.to_thread()`.
- New tool: add handler in `tools/`, register in `server.py` in 3 places: `TOOLS` list, `_import_tools()`, `_call_tool_sync()` dispatch chain.
- DB schema migrations: append to `MIGRATIONS` list in `db/schema.py`.
- `db/client.py:update_job()` validates columns against `JOB_COLUMN_WHITELIST` — add new column names there if extending the jobs table.
- Preferences use discrete keys (`salary_min`, `salary_max`) — never a single `salary` key.
- `tools/greeting.py:greeting_send()` auto-generates a 12-char `batch_id` via `uuid.uuid4().hex[:12]`.
- `tools/match.py:job_match()` auto-caches `resume_text` via `db.save_resume()` when passed.

## Key Gotchas

### Security

- **`.env` contains a real API key.** It is in `.gitignore` and not tracked, but rotate the key if it was ever committed or exposed.

### Code quality gaps (not yet addressed)

- No lint/format/typecheck config (`ruff`, `mypy`, etc.).
- No CI pipeline (`.github/workflows/`).
- `requirements.txt` uses `>=` without lockfile.

### LLM config pitfall

- `llm/client.py` hardcodes `/v1/chat/completions`. If `LLM_BASE_URL` already includes `/v1`, the path doubles up. Set only the base domain (e.g. `https://api.deepseek.com`).

### Preference key naming

- All preference keys are singular lowercase: `cities`, `salary_min`, `salary_max`, `keywords_must`, `keywords_bonus`, `blacklist`, `company`, `welfare`. No nested objects — each is a top-level key.
