# agent-meter — Orchestrator Pre-Spike Findings (2026-10-16)

> Read-only investigation done by the orchestrator during planning on the developer's real local data.
> Only metadata and counts were inspected; no prompt/code content is reproduced here.
> Input for `architect-engineer` (State 1 spike + ADR-001). All numbers are snapshots of 2026-10-16.

## 1. Claude Code (`~/.claude/projects/`)
- Main transcripts: `<project-slug>/<session-id>.jsonl`; subagents: `<project-slug>/<session-id>/subagents/agent-<agentId>.jsonl` + `agent-<agentId>.meta.json` (`agentType`, `description`, `toolUseId`, `spawnDepth`).
- Line types seen: `assistant`, `user`, `attachment`, `system` (subtypes `turn_duration` with `durationMs` + `messageCount`, `stop_hook_summary`, `compact_boundary`, `away_summary`, `scheduled_task_fire`, `local_command`, `informational`), `last-prompt`, `ai-title`, `mode`, `permission-mode`, `agent-name`, `queue-operation`, `file-history-snapshot`, `file-history-delta`, `cost-state`.
- Usage: `message.usage` with `input_tokens`, `output_tokens` (+ `output_tokens_details.thinking_tokens`), `cache_creation_input_tokens` (+ `cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens`), `cache_read_input_tokens`, `server_tool_use.{web_search_requests,web_fetch_requests}`, `service_tier`, `iterations[]`.
- **Dedup**: one API response is written as several lines sharing `requestId` → summing lines overcounts ~1.8x (15,333 lines vs 11,068 unique requests at the time).
- Per-line metadata: `sessionId`, `cwd`, `gitBranch`, `version` (e.g. `2.1.229`), `entrypoint`, `isSidechain`, `timestamp`, `promptId` (on prompt/user lines and on subagent lines).
- Models seen: `claude-sonnet-5`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-4-5-20251001`, `<synthetic>` (exclude).
- Task linkage: subagent lines carry the parent `promptId`. Assigning **main-thread assistant lines** to a task by naive `promptId` propagation failed in a quick test (main thread showed 1 call for a task with 315 subagent calls) → resolve via `parentUuid` chain from the prompt line.
- `turn_duration` is not present in every session (714 turns found in total) → derive from timestamps as fallback.
- Observed turn duration: P50 35 s, P95 ~951 s.

## 2. Antigravity CLI (`~/.gemini/antigravity-cli/`)
- Transcript: `brain/<conversation-id>/.system_generated/logs/transcript_full.jsonl` (+ `transcript.jsonl` and `logs/chunks/{transcript,transcript_full}/0000000N.jsonl` — same steps, read only one source).
- Step fields: `step_index`, `source`, `type` (`GENERIC`, `PLANNER_RESPONSE`, `SYSTEM_MESSAGE`, `USER_INPUT`, `CHECKPOINT`, `ERROR_MESSAGE`), `status`, `created_at` (second precision), `content`, `thinking`, `tool_calls`, `error`, and on `PLANNER_RESPONSE`: `input_tokens`, `cache_read_tokens`, `output_tokens`. No model field.
- `conversation_summaries.db` table `conversation_summaries`: `conversation_id` (== `brain/<id>`, verified), `workspace_uris`, `parent_conversation_id`, `nesting_depth` (max 1 seen), `agent_name`, `step_count`, `last_user_input_time`, `status`, `killed`, …
- Subagents: 407 of 791 conversations have a parent. `brain/<parent>/.system_generated/subagents/<uuid>.json` = `{conversationId, spawnStepIndex, state, subagentDescriptor}`; 53/53 children of the largest parent resolved to a parent `USER_INPUT` range via `spawnStepIndex`.
- Per-conversation DB `conversations/<id>.db`: tables `trajectory_meta(trajectory_id, cascade_id, …)`, `steps`, `gen_metadata(idx, data, size)`, `executor_metadata`, `parent_references`, `trajectory_metadata_blob`, `battle_mode_infos`.

### 2.1 `gen_metadata.data` protobuf (decoded with a schema-less wire-format walker)
| Field path | Meaning | Confidence |
| :--- | :--- | :--- |
| `1.4.2` | input tokens | **Verified**: 2,244/2,244 calls equal transcript `input_tokens` (40 conversations) |
| `1.4.5` | cache-read tokens | **Verified** (same check) |
| `1.4.3` | output tokens | **Verified** (same check) |
| `1.20` (repeated `{1: key, 2: value}`) | `last_step_index`, `trajectory_id`, `request_id`, `last_execution_id`, `cascade_id`, `root_cascade_id`, `parent_cascade_id`, `model_enum`, `used_claude`, `used_claude_conservative`, `used_non_gemini_model` | Observed |
| step mapping | call belongs to transcript step `last_step_index + 1` | **Verified** |
| `1.19` | model id (e.g. `gemini-3.8-flash`, `gemini-3.6-flash`, `claude-sonnet-4-6`, `agy-demo-high`, `gemini-4-argon`, `gemini-default`) | Observed |
| `1.21` | model display name (e.g. `Gemini 3.6 Flash (High)`, `Claude Sonnet 4.6 (Thinking)`) — often absent | Observed |
| `1.11` / `1.12` | durations (`{1: seconds, 2: nanos}`); `1.11` p50 1.9 s / p95 3.6 s on IDE data — latency vs TTFT unknown | Hypothesis |
| `1.4.9`, `1.4.10`, `1.4.6`, `1.3` | unknown (thinking tokens? tool tokens? constant 24 in `1.4.6`) | Unknown |
| `1.9.4` | timestamp `{1: epoch seconds, 2: nanos}` | Likely |

### 2.2 **Open issue — transcript vs `gen_metadata` totals (must resolve in spike)**
| Source (all CLI conversations) | LLM calls | input | cache read | output |
| :--- | ---: | ---: | ---: | ---: |
| Transcripts (`PLANNER_RESPONSE` usage) | 25,248 | 213.4M | 2,659.8M | 15.91M |
| `gen_metadata`, raw rows | 96,023 | — | — | — |
| `gen_metadata`, dedup `(trajectory_id, last_step_index)` | 61,409 | 611.9M | 7,341.0M | 33.28M |
| `gen_metadata`, dedup + own trajectory only | 60,579 | 601.4M | 7,226.5M | 32.85M |

- 8,815 `request_id`s appear in more than one conversation DB; 35,445 rows reference a `trajectory_id` not owned by the DB they are in → **parent/child DBs contain copies** of each other's calls. Naive summing double-counts.
- Even after dedup, `gen_metadata` reports ~2.4x the calls and ~2.8x the tokens of the transcripts. All extra calls point to steps that have no usage in the transcript (`step_without_planner`), not to repeated planner steps.
- Hypotheses to test: (a) transcripts only record usage for `PLANNER_RESPONSE` steps while other steps (tool-call processing, checkpoints/summaries, browser/subagent orchestration) also consume model calls → `gen_metadata` is the complete source; (b) some `gen_metadata` rows are internal/non-billable or speculative generations; (c) residual cross-conversation duplication not captured by the `(trajectory_id, last_step_index)` key (try `request_id`, `last_execution_id`, `cascade_id`).
- Decision needed in ADR-001: canonical usage source for Antigravity (proposal: `gen_metadata` deduped by a verified key, transcript for steps/timing/task segmentation), and how to attribute copied rows to the owning conversation (`trajectory_meta.trajectory_id`).

## 3. Antigravity IDE (`~/.gemini/antigravity/`)
- Same layout as the CLI (`brain/`, `conversations/`), 141 `brain/` dirs, only 12 with `transcript_full.jsonl`, and those have **no token fields**.
- `conversations/`: 12 `.db` (Jul 2026; 366 `gen_metadata` calls, 2.66M input / 23.5M cache read / 0.37M output, all `gemini-3.6-flash`) and 100 legacy `.pb` files (May–Jun 2026, format unknown).
- No known session-exit hook.

## 4. Hook / settings locations seen
- Claude Code: `~/.claude/settings.json` (`hooks`).
- Gemini/Antigravity: `~/.gemini/settings.json` contains `hooks.BeforeTool` (`run_shell_command` → `~/.gemini/hooks/rtk-hook-gemini.sh`) — must be preserved by the settings merger; `~/.gemini/antigravity-cli/settings.json` exists; plugins in `~/.gemini/config/plugins/`. Which file and which events Antigravity CLI honors for user-level hooks is unverified.

## 5. GCP
- Target project `devhack-3f0c2` (from `~/Documents/devhack/webpage-devhack/.firebaserc`, alias `dev`).
- Local `gcloud`: active configuration `default` → account on another domain + project `overty-sphere`; second configuration `vibe-music` → personal account. Tokens were expired on 2026-10-16 → the wizard must pass the project explicitly and detect expired credentials.

## 6. Architect spike results (2026-10-16, `architect-engineer`)

> Read-only. The scratch scripts used a stdlib protobuf wire walker and inspected only keys, types, counts, lengths and numeric fields. String lengths (never contents) were used for one correlation. Numbers are live snapshots, so counts grew slightly during the run.

### 6.1 Antigravity canonical usage source — RESOLVED (confidence: high)
**Decision**: the conversation DB `conversations/<id>.db` is canonical:
- `gen_metadata` gives usage, model and latency
- `steps` gives the step timeline
- transcripts are used only for tool names, and as a usage fallback when a conversation has no DB

**Why `gen_metadata` showed ~2.4x the calls**: transcript coverage, not phantom calls.

| CLI DB class (463 DBs) | DBs | own `gen_metadata` calls | transcript calls with tokens |
| :--- | ---: | ---: | ---: |
| Transcript has token fields and covers every call | 248 | 14,334 | 14,334 |
| Transcript has **no token fields at all** (first step 2026-07-10 … 2026-10-05) | 146 | 34,545 | 0 |
| Transcript starts mid-conversation (742 of 788 missing steps come before its first line) | 32 | 11,690 | 10,902 |
| Brain dir without `transcript_full.jsonl` | 36 | 0 | 0 |
| Other | 1 | 31 | 32 |

- Transcripts with token fields all start on or after **2026-10-02**: the CLI added usage to transcripts then. Earlier conversations only have usage in the DB.
- On every step present in both sources, tokens are equal: **25,267 / 25,267, 0 mismatches**.
- Every own `gen_metadata` row maps to a `steps` row with `step_type = 15` (PLANNER_RESPONSE): 60,492 / 60,600; the remaining 108 map to other step types. Extra calls do **not** attach to tool, checkpoint or system steps.
- 26 transcript planner steps have tokens but no `gen_metadata` row. Hence the fallback is per conversation, not per step: a ≤ 0.1% gap, accepted.

**Dedup key and ownership**:

| Candidate key | Verdict |
| :--- | :--- |
| `(trajectory_id, last_step_index)` | **Chosen**: unique within own rows (60,600 rows, 0 dups); every cross-DB copy is byte-identical in tokens and `request_id` (33,785 / 33,785) |
| `request_id` | Rejected: absent on ~10% of rows (54,747 of 60,600 own rows have one) |
| `last_execution_id` | Rejected: shared by many calls (45,511 rows → 4,062 distinct) |
| `cascade_id` (kv) | Rejected: present on only 25,316 own rows and equal to the conversation id (per conversation, not per call) |

- `trajectory_meta` has exactly 1 row per DB (463/463). `cascade_id == conversation_id` (463/463), while `trajectory_id` ≠ conversation id.
- **Copies are history prefixes imported by a continued or forked top-level conversation, not parent/child copies.** All 67 (holder DB, foreign trajectory) pairs are declared in the holder's `parent_references` table, whose field `1` is the source `trajectory_id`, field `2` a step index and field `3` = 4. Every copied `last_step_index` is below the declared step. 0 copies occur between a parent and its subagent, which confirms the PLAN item "parent never repeats child usage".
- **Ownership rule**: a row belongs to the DB whose `trajectory_meta.trajectory_id` equals its key. Copies only count if no owner DB exists: 1 deleted trajectory, 830 unique calls (21M input / 229M cache-read tokens) found only as copies in 2 holders. The deterministic `owner_rank` picks a single holder.
- **Totals (CLI, owner-deduped)**: 60,600 calls, 601.6M input, 7,229.6M cache read, 32.9M output; plus 830 orphan calls.

**Field semantics**:

| Field | Meaning | Evidence |
| :--- | :--- | :--- |
| `1.4.9` | thinking tokens | `1.4.3 == 1.4.9 + 1.4.10` on 53,950 / 53,950 rows; corr(1.4.9, transcript `thinking` length) = 0.875 |
| `1.4.10` | visible output tokens (text + tool calls) | corr with visible length 0.989, ~3.5 chars/token |
| `1.4.3` | total output, **includes thinking** | price output on `1.4.3` only |
| `1.4.1` = `1.3` | internal model enum (e.g. 1318–1417) | equal on all rows |
| `1.4.6` | constant 24 | ignore |
| `1.17.2` | duplicate of `1.4` | ignore |
| `1.11` | **total call latency** (p50 3.7 s, p95 14.0 s, p99 31.8 s on CLI) | 8,422 / 8,422 consecutive calls start after the previous `1.9.4 + 1.11` (p01 gap 0.05 s) |
| `1.12` | unknown (≤ `1.11` in 94%, p50 0.06 s, p95 5.4 s); maybe a queue or first-byte delay | **not exposed** (unresolved, harmless) |
| `1.9.4.1` | call start epoch seconds | present on only ~14% of rows; step timestamp used instead |
| `1.19` | model id; empty on 934 own CLI rows (all `used_claude=true`) | those get `default_model` with `model_inferred` |

Other step-table facts:
- `steps.metadata` field `1.1` is the step `created_at` epoch, equal to the transcript on **133,290 / 133,290** steps. 80,013 more steps exist only in the DB.
- `step_type` map: 14 USER_INPUT, 15 PLANNER_RESPONSE, 132 GENERIC, 101 SYSTEM_MESSAGE, 23 CHECKPOINT, 17 ERROR_MESSAGE, 21 RUN_COMMAND, 8 VIEW_FILE, 7 GREP_SEARCH, 9 LIST_DIRECTORY, 25 FIND, 5 CODE_ACTION, 98 CONVERSATION_HISTORY, 139 DIRECTORY_RULES.
- Workspace: `trajectory_metadata_blob` field `1.1` (and `7`) is the workspace `file://` URI. It equals `conversation_summaries.workspace_uris` in 460/463 CLI conversations, and it is the project source for the IDE and app, which have no summaries DB.
- Subagent parent fallback: the `gen_metadata` key `parent_cascade_id` is present in 256 CLI DBs and always resolves to a known conversation.

### 6.2 Antigravity roots — NEW FINDING
| Root | Product (per the CLI's embedded docs) | `.db` | legacy `.pb` | calls (own) | tokens in / cache / out | models |
| :--- | :--- | ---: | ---: | ---: | :--- | :--- |
| `~/.gemini/antigravity-cli/` | CLI | 463 | 52 (51 alongside a `.db` of the same id) | 60,600 | see 6.1 | `gemini-3.8-flash` (most), `agy-demo-high`, `gemini-3.8-flash-n`, `gemini-3.7-flash-control`, `gemini-3.6-flash`, `gemini-4-argon`, `claude-sonnet-4-6`, `gemini-default`, `gemini-pro-default`, … |
| `~/.gemini/antigravity-ide/` | **IDE** (missed in §3) | 45 (2026-05-19 … 2026-10-08) | 105 (2026-05-19 … 2026-06-02) | 5,573 | 56.2M / 430.2M / 3.2M | `gemini-3-flash-a`, `gemini-3.7-flash`, `claude-sonnet-4-6`, `gemini-default`, `claude-opus-4-6-thinking`, `gemini-3-flash-b` |
| `~/.gemini/antigravity/` | **"Antigravity 2.0"** (not the IDE) | 12 (Jul 2026) | 100 (same 100 ids as in `antigravity-ide/`, different bytes) | 366 | 2.66M / 23.5M / 0.37M | `gemini-3.6-flash` |

- No IDE or app conversation has subagents.
- **Legacy `.pb` files are not recoverable.** Byte entropy is 7.996–7.998 bits/byte, there is no common magic, and only ~50% of first bytes are plausible protobuf tags (random). These are encrypted or compressed blobs, so they are reported as untracked, with ids deduplicated across roots: 105 IDE plus 1 CLI `.pb`-only.

### 6.3 Claude Code segmentation — RESOLVED (confidence: high)
- `promptId` appears on **every `user` line**, both real prompts and tool results (7,880 tool-result lines), and **never on `assistant` lines** (0 / 15,475).
- Nearest-`user`-ancestor resolution via `parentUuid` reached a prompt for 15,475 / 15,475 assistant lines, and agreed with file-order propagation on 15,475 / 15,475. The earlier failed test probably took ids only from "real" prompt lines: 1,063 assistant lines resolve to a `promptId` carried only by meta or tool-result lines (sessions resumed or compacted from earlier history). **Task id = `promptId` of any `user` line.**
- `system/turn_duration`: 712 / 712 reach a `promptId` through `parentUuid`, giving `reported_ms`.
- **Subagents**:
  - 102 runs with `meta.json`. Keys: `agentType`, `description`, `toolUseId`, `spawnDepth`; also `requestShape`, `requestNonInteractive`, `parentAgentId` (7, all `spawnDepth = 2`), `isFork` (2), `model` (2), `stoppedByUser` (1).
  - Assistant lines in subagent files carry no `promptId`.
  - The first `promptId` in a subagent file equals the spawn prompt in 100 / 100 resolvable cases.
  - **51 subagents later carry 2–13 newer `promptId`s** (background agents outliving the prompt), so a run must be attributed to its **spawn** task, not to per-line ids.
- Nested runs: `parentAgentId` equals the owner of the spawning `tool_use` in 7 / 7 cases, and every nested `toolUseId` is found in a sibling subagent transcript.
- **Dedup**:
  - 11,161 requests (non-synthetic); 8,212 `requestId`s span several lines.
  - In 676 of them `output_tokens` grows across lines, and the last line is always the maximum, so "first line wins" undercounts output tokens by **15.6%** on this machine. The rule is **max output per `requestId`**.
  - 83 `requestId`s appear in two files: 81 main–main (resumed sessions) and 2 main–fork. A deterministic `owner_rank` is needed.
- `usage.iterations[]` always holds 1 entry of type `message`, equal to the top-level usage (16,398 / 16,398).
- `advisorModel` (`claude-opus-5-5`) appears on 8,412 lines with no separate advisor usage, so nothing extra is billed. Unknown iteration types raise a diagnostic.
- Present on lines and stored for future pricing: `usage.speed`, `usage.inference_geo`. Errors: `isApiErrorMessage` (16 lines), tool_result `is_error` (210).
- Retention: the earliest main transcript is from 2026-09-21; `cleanupPeriodDays` is unset (host default). Size: 373 MB; full JSON parse 2.5 s (largest file 187 MB, 0.86 s).

### 6.4 Hooks — RESOLVED for Antigravity (documented and log-confirmed), Claude Code from documentation knowledge
**Antigravity**: the authoritative source is the hook documentation embedded in the `agy` binary (`~/.local/bin/agy`, section "Lifecycle Hooks (`hooks.json`)").
- **Events**: `SessionStart`, `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation` and `Stop`. There is **no `SessionEnd`, `SubagentStop` or `UserPromptSubmit`**.
- `Stop` fires "when the execution loop terminates", i.e. once per user turn (task).
- **stdin (camelCase)**:
  - common: `conversationId`, `workspacePaths[]`, `transcriptPath` (the path names the product: `antigravity-cli/`, `antigravity-ide/`, `antigravity/`), `artifactDirectoryPath`, `modelName`
  - `Stop` adds: `executionNum`, `terminationReason` (`NO_TOOL_CALL`, `MAX_INVOCATIONS`, `ERROR`, `USER_CANCELED`, …), `error`, `fullyIdle`
- **stdout must be a JSON object.** For `Stop`, `decision:"continue"` blocks the stop and any other value allows it, so `{}` is a safe no-op. Hooks run **synchronously and block the agent loop**. The default timeout is 30 s, and the working directory is the folder containing `hooks.json`.
- **File format**: each top-level key is a **named hook** object (`{"enabled": bool, "<Event>": [...]}`). Tool events use `{matcher, hooks:[…]}`; the other events take a flat handler list.
- **Locations**: workspace `.agents/hooks.json`, global `~/.gemini/config/hooks.json` (absent today), and plugins `~/.gemini/config/plugins/<name>/hooks.json`.
- `cli.log` confirms the loader: `hooks_manager.go: loaded 1 named hooks from 3 hooks.json file(s)`.
- **Repo bug (outside Track 11)**: the CLI logs, repeated over 1,900 times, `failed to parse hooks.json … cannot unmarshal string into Go struct field .description of type jsonhook.JSONHookSpec`. **Any `hooks.json` with a top-level string key (e.g. `"description"`) fails to load entirely.** This affects **all 9** repo plugins, `plugins/antigravity/{docs-and-quality,git-workflow,multi-agent-ops,python-backend,senior-data-engineer,senior-dev,senior-dev-flutter,shared-context,sql-query-optimizer}/hooks.json`, and the installed `~/.gemini/config/plugins/shared-context/hooks.json`. Only Google's telemetry plugin loads.
- `~/.gemini/settings.json` (`hooks.BeforeTool` → `rtk-hook-gemini.sh`, matcher `run_shell_command`) is **Gemini CLI**, not Antigravity. agent-meter never edits it.
- `~/.gemini/antigravity-cli/settings.json` has no `hooks` key, but it does have a `statusLine` command (a possible future display channel).
- **Privacy note**: `cli.log` contains user prompt text (`HandleUserInput … text: …`), so agent-meter must never read it.

**Claude Code**: no user-level hooks today (`~/.claude/settings.json` has no `hooks` key; plugins enabled).
- **`SessionEnd`** stdin: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `reason`. It cannot block; output is not shown to the user after exit.
- **`Stop`** stdin: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `stop_hook_active`; newer versions may add content fields, which the parser discards. It fires at the end of every main-agent turn, i.e. per task. `SubagentStop` fires per subagent.
- **Visible channels**: exit-0 stdout and stderr are not shown in the normal UI. The JSON `systemMessage` field displays a user-facing notice; whether it reaches model context must be **verified at L6** before enabling (`claude_inline_summary = false`). The default visible channels are the macOS notification, `last-summary.txt` and `agent-meter last`.
- **Per-task trigger decision**: Claude Code `Stop` (not `SubagentStop`), and Antigravity `Stop` with `fullyIdle = true` from a top-level conversation. Session summary: Claude Code `SessionEnd`. Antigravity has no session-end hook, so its "session summary" is `agent-meter last`, plus scheduler closure after 24 h of idleness.

### 6.5 Project resolution facts
- 139 distinct workspace directories were seen: 71 git repos with an `origin` remote (27 Antigravity + 44 Claude Code), 11 non-git, 1 `$HOME`, and **56 that no longer exist**.
- Of the missing 56, 3 are deleted worktrees (a `worktrees` path segment under an existing repo) and 53 have no git ancestor.
- Hence the design: a persistent `path_map(sha256(path) → project_id)` filled while paths still exist, a worktree-segment heuristic, and path ids as the fallback.
- `workspace_uris` is a JSON list (795 single, 1 double) or a plain string (4).
- `git rev-parse` plus `remote get-url` over all 139 paths took 1.1 s in total.

### 6.6 Environment facts for the package
- System `python3` is 3.10.8 (no `tomllib`). `uv` is installed and `pipx` is not, so `uv tool install` provisions Python ≥ 3.11.
- PyYAML 6.0.3 is present globally (irrelevant for an isolated tool venv); DuckDB is not installed.
- `gcloud` and `bq` are installed (not invoked: credentials known to be expired). `node` 23.8 and `npx` are available (for `ccusage` at L5).

### 6.7 Checklist status (PLAN.md "State 1 spike")
| Item | Status |
| :--- | :--- |
| Antigravity CLI session-exit hook and payload | **Resolved**: no session-exit event; `Stop` per turn with the payload above |
| `1.11`/`1.12`, `1.4.9`/`1.4.10` | **Resolved** except `1.12` (not exposed) |
| IDE legacy `.pb` | **Resolved**: not recoverable (encrypted/compressed), reported as untracked |
| IDE hook / extension point | **Documented, not empirically verified**: same `hooks.json` engine (the embedded docs list an IDE `transcriptPath`); default is still scheduler + `Stop` hook, verify at L6 |
| Claude Code `SessionEnd` payload and visible channel | **Resolved from documentation knowledge**; `systemMessage` visibility to verify at L6 |
| Claude Code task segmentation, nested subagents | **Resolved** (6.3) |
| Antigravity parent never repeats child usage | **Resolved**: 0 parent/child copies; copies come only from `parent_references` prefixes |
| Standalone hook registration | **Resolved**: Claude `~/.claude/settings.json`; Antigravity `~/.gemini/config/hooks.json` (named hook) |
| BigQuery free tier / sandbox / load-job limits | **To verify at L4** (no network verification in this spike). PLAN's 60-day sandbox expiry stands as stated, unverified |
| Looker Studio Linking API | **To verify at L4**: URL shape in ADR §3.11, manual fallback mandatory |
| `devhack-3f0c2` billing / API / IAM | **Not checked** (expired credentials, by instruction); wizard checks designed in ADR §3.11 |
| Per-task display trigger | **Resolved**: `Stop` on both hosts |
