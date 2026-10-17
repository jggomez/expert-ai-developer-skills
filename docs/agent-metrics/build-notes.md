# agent-meter — Build Notes for State 2 implementers (from 11A hand-back, 2026-10-16)

Track 11A is DONE (241 tests green; ruff + mypy --strict clean). Public API to build on:
- `model.py`: `SCHEMA_VERSION`, `Host`, `TaskStatus`, `RunStatus`, `DurationSource`, `DiagnosticKind`, `UntrackedReason`, `FileFingerprint`, `SessionUnit` (`.fingerprint`), `ProjectRef`, `SessionRecord`, `TaskRecord`, `AgentRunRecord`, `CallRecord`, `ToolUseRecord`, `UntrackedRecord`, `Diagnostic`, `UnitBatch`, `ReaderOptions`.
- `tests/fixtures/records.py`: `make_file`, `make_unit`, `make_project`, `make_session`, `make_task`, `make_agent_run`, `make_call`, `make_tool_use`, `make_untracked`, `make_diagnostic`, `make_options`, `make_batch`, `ts()`, `BASE_TS` (factories accept overrides, reject unknown fields).
- Fake hosts for integration tests: `tests/fixtures/claude.py` (`ClaudeHome`, `ClaudeSession`), `tests/fixtures/antigravity.py` (`build_root`, `AgyConversation`), `tests/fixtures/scenarios.py` (`claude_standard_session()`, `agy_standard_conversations()`); canary `AGENT-METER-CANARY-7f3a` in `tests/fixtures/canary.py`.

Facts every track must respect:
- `pyproject.toml` (11B-core) must set pytest `pythonpath = ["src", "."]` (tests import `tests.fixtures.*`), register markers `contract`, `integration`, `bigquery`, `e2e`, `perf`, `privacy`; default `addopts` deselects `bigquery`, `e2e`, `perf`. `pricing.yaml` and `sql/**` are package data. Runtime deps: `duckdb`, `PyYAML`; extra `[bigquery]`: `google-cloud-bigquery`. Python >= 3.11. Add `__pycache__/` etc. to a `tools/agent-meter/.gitignore`.
- There is no `agent_meter/__init__.py` yet (namespace package works); 11B-core owns `__init__.py` and `__main__.py`.
- Empty `UnitBatch` (unreadable/vanished unit) must NEVER delete stored rows (BR-15).
- `owner_rank` is compared as a string (Claude `0|1:<ISO ms Z>:<sid>`, Antigravity `"0"` / `"1:<holder id>"`).
- Antigravity `workspace_path` is a raw `file://` URI accepted by `ProjectResolver.resolve()`; on a path-cache hit `ProjectRef.remote_url` is `None` — never overwrite a known remote with `None`.
- `pricing.resolve_price(... prompt_tokens=...)`: prompt tokens = input + cache_read + cache_write_5m + cache_write_1h.
- On `SessionEnd` / Antigravity `fullyIdle`, the collector may mark the last task done via `dataclasses.replace`.
- `ProjectResolver` takes optional `temp_roots`; non-git directories get a `path:` id (ADR §3.7 wins over PRD BR-08 wording); `$HOME`/temp roots are `(unassigned)`.
- `store_agent_descriptions` is reserved for v2 and currently ignored (descriptions are always salted hashes); `setup` no longer asks about it (M-2, option a).

Track split for State 2 (disjoint ownership; contracts.md §1 11B row is split in two):
- **11B-core**: `__init__.py`, `__main__.py`, `paths.py`, `config.py`, `locking.py`, `store.py`, `collector.py`, `summary.py`, `notify.py`, `hook.py`, `cli.py`, `sql/duckdb/**`, `tools/agent-meter/pyproject.toml`, `tools/agent-meter/README.md`, `tools/agent-meter/.gitignore`, tests `test_store`, `test_collector`, `test_summary`, `test_cli`, `test_hook`, `test_locking`, `test_config`, `tests/integration/**`.
- **11B-setup**: `setup/**`, `scheduler/**`, tests `test_setup_*`, `test_scheduler`.
- **11C**: `report/**`, `tests/unit/test_report.py`.
- **11D**: `sinks/**`, `sql/bigquery/**`, `docs/agent-metrics/looker-studio.md`, `tests/unit/test_outbox.py`, `tests/unit/test_bigquery_sink.py`, `tests/cloud/**`.
- Cross-track calls go through the contract signatures only; `cli.py` imports `report`, `sinks`, `setup`, `scheduler` lazily inside handlers. If a dependency module is not written yet, code against the contract and test your own module with fakes; never write files you do not own.

Test command until `pyproject.toml` exists:
`cd tools/agent-meter && PYTHONPATH=src:. uv run --no-project --python 3.11 --with pytest --with pyyaml --with duckdb python -m pytest <paths> -q`
After it exists: `cd tools/agent-meter && uv run --python 3.11 --extra dev pytest -q` (or the equivalent 11B-core documents in README).
