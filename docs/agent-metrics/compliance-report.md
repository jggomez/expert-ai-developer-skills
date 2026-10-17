# agent-meter — Compliance & Release Audit (Track 11, Phase 5 / State 4)

- Auditor: compliance-verifier (read-only). Date: 2026-10-17. Branch: `feature/agent-metrics` (Track 11 work uncommitted; nothing on `main`).
- Scope: `tools/agent-meter/**`, `plugins/{claude,antigravity}/agent-metrics/**`, `skills/agent-metrics/**`, `docs/agent-metrics/**`, `tests/structure/test_agent_*`, shared edits (`.claude-plugin/marketplace.json`, `README.md`, `skills/README.md`, `scripts/sync_agents.py`, `scripts/sync_plugin_skills.py`).
- **Verdict (audit 1): REJECTED** — 1 HIGH open. Becomes APPROVED once H-1 is fixed and re-verified; M-1 and M-2 strongly recommended in the same loop.
- Saved verbatim-in-substance by the orchestrator from the auditor's hand-back (the auditor's rules forbid it writing report files).

## 1. Automated gates (executed)
| Gate | Command | Result |
|---|---|---|
| Lint | `cd tools/agent-meter && uv run --python 3.11 --extra dev ruff check .` | All checks passed (exit 0) |
| Types | `uv run --python 3.11 --extra dev mypy --strict src` | no issues in 47 source files (exit 0) |
| Format | `uv run --python 3.11 --extra dev ruff format --check .` | 24 files would be reformatted (exit 1) — L-1 |
| Package tests | `uv run --python 3.11 --extra dev pytest -q` | 726 passed, 6 deselected |
| Repo tests | `python3 -m pytest -q tests/` | 142 passed (incl. DC-01..04, plugin structure) |
| Hook syntax | `node --check plugins/*/agent-metrics/hooks/*.js` | both OK |
| JSON | runbook §4.3 | 69 files valid |
| Hook fast path | `python -X importtime -m agent_meter hook --host claude-code --event task-end` with canary payload | stdout empty, exit 0, 0 duckdb/yaml/google imports; Antigravity garbage stdin → `{}`, exit 0 |
| I-2 | `python -X importtime -m agent_meter --help` | 0 google modules |
| Secrets | regex scan | only test fakes asserting tokens never leak — acceptable |
| Smells | `detect_smells.py tools/agent-meter/src` | 58 Long Method, 50 High Complexity, 19 Long Parameter List, 2 Large Class — L-8 |

## 2. Findings by severity

### HIGH
**H-1 — `uninstall --purge` recursively deletes an unvalidated directory (data loss; OWASP A04/A01).**
- `cli.py:1033-1042` runs `shutil.rmtree(ctx.home.root)`; root comes from `--home` → `$AGENT_METER_HOME` → `~/.agent-meter` (`paths.py:86-97`) with no validation; `--yes` skips the prompt.
- Reproduced: `AGENT_METER_HOME=<scratch>/fakeuser agent-meter uninstall --purge --yes --keep-scheduler` deleted the dir including a foreign `Documents/thesis.txt`, exit 0. Realistic trigger: `AGENT_METER_HOME="$HOME/$UNSET"` → whole home deleted. PRD US-11/§6 scope `--purge` to `~/.agent-meter/`.
- Related: `paths.py:95-96` chmods any chosen home to 0700 (`--home ~/Documents` silently changes mode; `--home /tmp` raises PermissionError).
- Fix: refuse (exit 2) when root is `/`, `$HOME`/`Path.home()`, an ancestor of `$HOME`, or a mount point; refuse when root contains entries outside the known agent-meter set (`meter.duckdb`, `meter.duckdb.wal`, `lock`, `config.toml`, `projects.yaml`, `pricing.local.yaml`, `secret`, `install.json`, `last-summary.txt`, `state/`, `logs/`, `backups/`, `outbox/`, `.tmp` files); optionally require a marker `.agent-meter-home` created by `AppHome.resolve`; delete only known entries then `rmdir`; chmod only dirs agent-meter created / marked. Tests: refuses `$HOME` root; refuses dir with a foreign file even with `--yes` (file survives); purges a genuine home; `--home` on an existing foreign dir does not change its mode.

### MEDIUM
**M-1 — PV-01 store check can give a false "clean".** `tests/unit/test_collector.py:251-258` and `tests/integration/test_cli_flows.py:37-38,85` grep raw `.duckdb` bytes; DuckDB string compression (FSST/dictionary) hides plaintext (20,000 high-cardinality canary rows after CHECKPOINT → `raw_bytes_contains_canary=False`). Fix: SQL-level dump helper over every base table/column (`information_schema.columns`, `CAST(col AS VARCHAR)`) or `EXPORT DATABASE ... (FORMAT CSV)` + grep; keep the raw-byte check as a second layer; use it in both tests and in `test_store.py` PV-05.

**M-2 — `store_agent_descriptions` is a no-op but the wizard asks for consent and docs promise it.** `build-notes.md:17`; schema has only `description_hash`; `setup/wizard.py:329-333` prompts; `docs/agent-metrics/README.md:86`, `PRD.md:70` claim it works. Fails safe. Fix (a, preferred for v1): remove the prompt and claims, mark key "reserved (v2), currently ignored", test the wizard no longer asks; or (b) implement local-only column via migration v2.

### LOW
- **L-1** `ruff format --check`: 24 files would be reformatted → dedicated `style:` commit or document it is not a gate.
- **L-2** DOUBLE in a money path: `sql/duckdb/views.sql:311` `billable_usd` via `CAST(... AS DOUBLE)`; ratios `:136,182,223,321,323`; BigQuery uses NUMERIC → last-digit drift. Agent cost `v_calls.cost_usd` is exact DECIMAL(38,9). Fix: DECIMAL operands or document the ratio/FX exception in ADR I-5; parity test for `v_client_month`.
- **L-3** Work-item tags uploaded in clear text even with `anonymize_projects` (`sinks/outbox.py:56`); tags often hold client names → add `tag` to `ANONYMIZED_COLUMNS` (or document) and extend PV-02.
- **L-4** `load_secret` non-atomic and silently regenerates an invalid salt (`paths.py:121-133`) → would change every hash/anonymized id. Fix: `O_CREAT|O_EXCL` + fsync + `os.replace`; raise a clear error on invalid existing salt (doctor: "secret corrupt"); enforce 0600 on read.
- **L-5** ADR I-1 wording allows only the marketplace entry, but README/skills README/sync scripts/PLAN/tests also mention agent-meter (allowlisted in DC-01). Behaviour correct → amend I-1 and PLAN DC-01.
- **L-6** PLAN.md partly stale: State 1 spike checklist items resolved by ADR still `[ ]`; layout row names `hooks/session-end-meter.js` (now `hooks/agent-meter-hook.js`); BQ-09 still mentions `require_partition_filter`; `acceptance.md` pending (QA-2).
- **L-7** Branch stacked on two unmerged governance commits (`beb2de3`, `d18a9fe`) → merge/rebase after the governance PR or target the PR at the governance branch; Conventional Commits with selective `git add`.
- **L-8** Smell debt (acceptable for v1): `Store` 553 lines (Divergent Change), `ClaudeCodeReader` 440 lines, long methods in `summary.py`, `pricing.py`, `hook.py`; `cli.py` 1,306 lines → v1.x refactor (split Store into ingest / reference / user-facts repositories).
- **L-9** Hook wrapper writes `error.message` to stderr (`agent-meter-hook.js:109`) — may contain paths; inconsistent with ADR §3.13.3 ("class name only") → print `error.name` / `error.code` only.

## 3. Privacy (BR-16/17, NFR-06, PV-01..05) — PASS (see M-1, M-2, L-3, L-4)
- Schema has no prompt/assistant text/tool I/O/path column; `path_map` hashes only; `diagnostics` holds `unit_hash`, `file_kind`, `error_class`; no cost column anywhere.
- Remote URLs normalized to credential-free `host/owner/repo` (`project_resolver.py:102-126`); non-git dirs `path:<sha256[:16]>`.
- `safe_label` allowlist regex applied to all free-text-ish slots (model, agent_type, tool name, speed, inference_geo, host_version).
- Descriptions as salted sha256; salt in `~/.agent-meter/secret` (0600).
- Task labels only on TTY in `tasks`; never in summary file, notifications, snapshot or report; read from transcripts, never `cli.log`.
- Hosts read-only: `open("rb")`, SQLite `mode=ro` + `PRAGMA query_only=1`; integration test compares digests/mtimes.
- Hook payload allowlisted and regex-validated; `prompt`/`last_assistant_message` dropped; canary absent from worker argv.
- Logs record stage + exception class only; outbox explicit column projection, HMAC-SHA256 anonymization, salt never in outbox, files 0600 / dirs 0700; ADC token in memory only, POSTed in body to tokeninfo, never in URLs or error texts.

## 4. Security (OWASP-relevant) — PASS except destructive operations (H-1)
- Settings merger: realpath, ownership check, invalid JSON/duplicate keys/non-object roots refused, managed policies (`allowManagedHooksOnly`) fail closed, TOCTOU `PlanStale`, backups 0600 `O_EXCL` in 0700 dir before any write, atomic mkstemp+fsync+`os.replace`+dir fsync, shell-quoted prefix, idempotent, BR-19 uninstall, `~/.gemini/settings.json` never targeted.
- Subprocess: argv lists only, no `shell=True`; hook worker detached with allowlisted argv; osascript text as argv; git with `GIT_TERMINAL_PROMPT=0` + timeout; gcloud with timeout, prompts disabled, project id validated; fixes only after confirmation; Node wrapper exact allowlist, `shell:false`, hard timeout SIGKILL.
- Scheduler quoting: plistlib; systemd quoting with `%%`; cron `shlex.quote` + marker-scoped edits.
- SQL: all values bound; f-strings interpolate only internal constants; BigQuery identifiers regex-validated; DDL via `string.Template` with validated values.
- YAML `safe_load`/`safe_dump` only; TOML via `tomllib`.
- HTML: `html.escape(quote=True)` everywhere, JSON island escapes `<>&`, SVG labels escaped, JS uses only `textContent`/`getAttribute`, zero external URLs, report 0600 atomic.
- Dependencies: `duckdb>=1.1,<2`, `PyYAML>=6.0`, `pytz>=2023.3`; `google-cloud-bigquery` only in extra, imported lazily. Note: record `pytz` in ADR Delta 10. `uv.lock` gitignored (informational).

## 5. ADR §7 invariants
| Id | Result | Evidence |
|---|---|---|
| I-1 Decoupling | PASS (wording L-5) | no repo-folder imports; DC-01/02/04 green |
| I-2 Optional cloud | PASS | 0 google modules at import; lazy `importlib` |
| I-3 Read-only hosts | PASS | `rb` opens; SQLite ro + query_only |
| I-4 Hook | PASS | always exit 0; dispatched before argparse/duckdb; Claude stdout empty, Antigravity `{}` |
| I-5 Money | PASS for cost (L-2 for FX/ratios) | `v_calls.cost_usd` DECIMAL(38,9); floats rejected |
| I-6 Unpriced | PASS | no `COALESCE(cost, 0)`; `≥ $X (N calls unpriced)` |
| I-7 BigQuery | PASS | only `load_table_from_file` + DDL |
| I-8 Privacy | PASS (test robustness M-1) | columns match contracts §4 |
| I-9 Natural keys | PASS | deterministic ids; owner_rank merge; ST-01 |
| I-10 Parity | Not verifiable offline | needs L4 |
| BR-15 empty batch | PASS | `_merge_fact` early return |
| Unknown tokens None | PASS | nullable token columns; RD-15 |

## 6. Decoupling & dual ecosystem — PASS
Antigravity `hooks.json` named-hook format without top-level `description` (relative `./hooks/` cwd resolution to confirm at L6); Claude manifest explicit `"hooks": "./hooks.json"` preserved by `sync_agents.py`; zero cross-ecosystem tool names; skill bundled only in agent-metrics plugins; shared edits additive only.

## 7. Anti-lazy code & quality — PASS
No TODO/FIXME/placeholder markers; no bare `except:`; `except BaseException` blocks clean up and re-raise; `except Exception` blocks record diagnostics with stated reasons.

## 8. Governance
PLAN.md counts match reality (stale items in L-6); repo slug consistent (29 occurrences = git remote); nothing on `main`; branch name compliant; stacking noted (L-7).

## 9. Remediation routing (loop 1)
1. code-implementer: H-1 (required) + L-4, L-9.
2. code-implementer/qa: M-1 SQL-level canary dump helper.
3. orchestrator + product decision: M-2, L-5, L-6, L-2, L-3 recorded in ADR/PLAN.
4. Before ship: L-1 formatting, L-7 branch base.
5. Re-run compliance-verifier → APPROVED if H-1 verified and no new CRITICAL/HIGH.
