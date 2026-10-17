"""Builder for synthetic Antigravity roots (CLI / IDE / app share the layout).

Layout (spike-notes §2, §6):
  <root>/conversations/<id>.db                         per-conversation SQLite (real DDL, synthetic rows)
  <root>/conversations/<id>.pb                         legacy encrypted blob (random bytes)
  <root>/brain/<id>/.system_generated/logs/transcript_full.jsonl
  <root>/brain/<id>/.system_generated/logs/chunks/transcript_full/00000001.jsonl   (same steps; must be ignored)
  <root>/brain/<parent>/.system_generated/subagents/<uuid>.json
  <root>/conversation_summaries.db                      CLI only

Protobuf blobs are encoded with ``protowriter``; every content-like slot carries ``CANARY``.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.fixtures.canary import CANARY
from tests.fixtures.protowriter import Msg, Value, encode, kv_entries

__all__ = [
    "CHECKPOINT",
    "ERROR",
    "GENERIC",
    "PLANNER",
    "SYSTEM",
    "T0",
    "USER_INPUT",
    "AgyCall",
    "AgyConversation",
    "AgyStep",
    "build_root",
    "gen_blob",
    "step_ts",
]

T0 = datetime(2026, 10, 16, 14, 0, 0, tzinfo=UTC)

USER_INPUT, PLANNER, ERROR, CHECKPOINT, SYSTEM, GENERIC = 14, 15, 17, 23, 101, 132
_TYPE_NAMES = {
    USER_INPUT: "USER_INPUT",
    PLANNER: "PLANNER_RESPONSE",
    ERROR: "ERROR_MESSAGE",
    CHECKPOINT: "CHECKPOINT",
    SYSTEM: "SYSTEM_MESSAGE",
    GENERIC: "GENERIC",
}

# Exact DDL observed on real CLI databases (schema only, no data).
CONVERSATION_DDL = (
    "CREATE TABLE `trajectory_meta` (`trajectory_id` text,`cascade_id` text,`trajectory_type` integer,`source` integer,PRIMARY KEY (`trajectory_id`))",
    "CREATE TABLE `steps` (`idx` integer,`step_type` integer NOT NULL DEFAULT 0,`status` integer NOT NULL DEFAULT 0,`has_subtrajectory` numeric NOT NULL DEFAULT false,`metadata` blob,`error_details` blob,`permissions` blob,`task_details` blob,`render_info` blob,`step_payload` blob,`step_format` integer NOT NULL DEFAULT 0,PRIMARY KEY (`idx`))",
    "CREATE INDEX `idx_steps_status` ON `steps`(`status`)",
    "CREATE INDEX `idx_steps_step_type` ON `steps`(`step_type`)",
    "CREATE TABLE `gen_metadata` (`idx` integer,`data` blob,`size` integer NOT NULL DEFAULT 0,PRIMARY KEY (`idx`))",
    "CREATE TABLE `executor_metadata` (`idx` integer,`data` blob,PRIMARY KEY (`idx`))",
    "CREATE TABLE `parent_references` (`idx` integer,`data` blob,PRIMARY KEY (`idx`))",
    'CREATE TABLE `trajectory_metadata_blob` (`id` text DEFAULT "main",`data` blob,PRIMARY KEY (`id`))',
    "CREATE TABLE `battle_mode_infos` (`idx` integer,`data` blob,PRIMARY KEY (`idx`))",
)
SUMMARIES_DDL = 'CREATE TABLE `conversation_summaries` (`conversation_id` text,`title` text NOT NULL DEFAULT "",`preview` text NOT NULL DEFAULT "",`step_count` integer NOT NULL DEFAULT 0,`last_modified_time` datetime NOT NULL,`workspace_uris` text NOT NULL,`status` text NOT NULL DEFAULT "",`source` text NOT NULL DEFAULT "",`project_id` text NOT NULL DEFAULT "",`agent_name` text NOT NULL DEFAULT "",`parent_conversation_id` text NOT NULL DEFAULT "",`nesting_depth` integer NOT NULL DEFAULT 0,`battle_id` text NOT NULL DEFAULT "",`winning_conversation_id` text NOT NULL DEFAULT "",`not_fully_idle` numeric NOT NULL DEFAULT false,`killed` numeric NOT NULL DEFAULT false,`last_user_input_time` datetime NOT NULL,`last_user_input_step_index` integer NOT NULL DEFAULT -1,`app_data_dir` text NOT NULL DEFAULT "", raw_summary BLOB, group_id TEXT NOT NULL DEFAULT \'\',PRIMARY KEY (`conversation_id`))'


def step_ts(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


@dataclass(frozen=True)
class AgyStep:
    idx: int
    step_type: int
    at: float | None  # seconds after T0; None → no timestamp in metadata
    status: str = "DONE"
    tool_calls: tuple[tuple[str, dict[str, object]], ...] = ()
    tokens: tuple[int, int, int] | None = (
        None  # transcript (input, cache_read, output) on planner steps
    )
    error: str | None = None


@dataclass(frozen=True)
class AgyCall:
    last_step_index: int
    input: int = 1_000
    cache_read: int = 10_000
    output: int = 200
    thinking: int = 50
    visible: int = 150
    model: str = "gemini-3.8-flash"
    label: str | None = None
    latency: tuple[int, int] | None = (2, 500_000_000)
    trajectory_id: str | None = None  # None → the conversation's own trajectory
    usage: bool = True
    usage_fields: Sequence[int] | None = (
        None  # override which usage subfields exist (renamed layout)
    )
    drop_keys: tuple[str, ...] = ()
    extra_kv: dict[str, str] = field(default_factory=dict)
    start_at: float | None = None  # 1.9.4 call start
    raw: bytes | None = None  # replace the whole blob (corruption tests)


@dataclass
class AgyConversation:
    conversation_id: str
    trajectory_id: str
    steps: list[AgyStep] = field(default_factory=list)
    calls: list[AgyCall] = field(default_factory=list)
    workspace_uri: str | None = "file:///Users/dev/work/demo-repo"
    parent_id: str | None = None
    agent_name: str = ""
    spawn_step_index: int | None = None
    db: bool = True
    transcript: bool = True
    transcript_tokens: bool = True
    chunks: bool = True
    parent_refs: tuple[tuple[str, int], ...] = ()
    summary_parent: bool = True  # write parent link into conversation_summaries
    subagent_json: bool = True  # write parent's subagents/<uuid>.json
    legacy_pb: bool = False
    in_summaries: bool = True  # row present in conversation_summaries.db


def gen_blob(call: AgyCall, own_trajectory: str) -> bytes:
    if call.raw is not None:
        return call.raw
    kv = {
        "last_step_index": str(call.last_step_index),
        "trajectory_id": call.trajectory_id or own_trajectory,
        "request_id": f"req-{call.last_step_index}",
        "model_enum": "1318",
        "used_claude": "false",
        "used_claude_conservative": "false",
        "used_non_gemini_model": "false",
        **call.extra_kv,
    }
    for key in call.drop_keys:
        kv.pop(key, None)
    inner: list[tuple[int, Value]] = [(3, 1318)]
    if call.usage:
        values = {
            1: 1318,
            2: call.input,
            3: call.output,
            5: call.cache_read,
            6: 24,
            9: call.thinking,
            10: call.visible,
        }
        wanted = call.usage_fields if call.usage_fields is not None else list(values)
        usage_fields = [(n, values.get(n, 7)) for n in wanted]
        inner.append((4, Msg(tuple(usage_fields))))
        inner.append((17, Msg.of((2, call.input))))
    if call.start_at is not None:
        start = T0 + timedelta(seconds=call.start_at)
        start_msg = Msg.of((1, int(start.timestamp())), (2, start.microsecond * 1000))
        inner.append((9, Msg.of((4, start_msg))))
    if call.latency is not None:
        inner.append((11, Msg.of((1, call.latency[0]), (2, call.latency[1]))))
    inner.append((12, Msg.of((2, 43_072_541))))
    inner.append((19, call.model))
    if call.label is not None:
        inner.append((21, call.label))
    inner.extend(kv_entries(20, kv))
    return encode(
        [
            (2, Msg.of((1, f"prompt text {CANARY}"))),
            (4, Msg.of((1, CANARY))),
            (8, f"system {CANARY}"),
            (1, Msg(tuple(inner))),
        ]
    )


def _step_metadata(at: float | None) -> bytes:
    fields: list[tuple[int, Value]] = []
    if at is not None:
        moment = step_ts(at)
        fields.append(
            (1, Msg.of((1, int(moment.timestamp())), (2, moment.microsecond * 1000)))
        )
    fields.append((3, 1))
    fields.append((8, Msg.of((1, f"meta {CANARY}"))))
    return encode(fields)


def _write_db(path: Path, conv: AgyConversation) -> None:
    with sqlite3.connect(path) as con:
        for ddl in CONVERSATION_DDL:
            con.execute(ddl)
        con.execute(
            "INSERT INTO trajectory_meta VALUES (?, ?, 4, 17)",
            (conv.trajectory_id, conv.conversation_id),
        )
        for step in conv.steps:
            con.execute(
                "INSERT INTO steps (idx, step_type, status, metadata, step_payload) VALUES (?, ?, 3, ?, ?)",
                (
                    step.idx,
                    step.step_type,
                    _step_metadata(step.at),
                    encode([(1, f"payload {CANARY}")]),
                ),
            )
        for index, call in enumerate(conv.calls):
            data = gen_blob(call, conv.trajectory_id)
            con.execute(
                "INSERT INTO gen_metadata VALUES (?, ?, ?)", (index, data, len(data))
            )
        blob_fields: list[tuple[int, Value]] = []
        if conv.workspace_uri is not None:
            blob_fields.append((1, Msg.of((1, conv.workspace_uri), (3, f"{CANARY}"))))
            blob_fields.append((7, conv.workspace_uri))
        blob_fields.append((2, Msg.of((1, f"rules {CANARY}"))))
        con.execute(
            "INSERT INTO trajectory_metadata_blob VALUES ('main', ?)",
            (encode(blob_fields),),
        )
        for index, (source_trajectory, step_index) in enumerate(conv.parent_refs):
            con.execute(
                "INSERT INTO parent_references VALUES (?, ?)",
                (index, encode([(1, source_trajectory), (2, step_index), (3, 4)])),
            )
        con.execute(
            "INSERT INTO executor_metadata VALUES (0, ?)",
            (encode([(1, f"exec {CANARY}")]),),
        )


def _transcript_line(step: AgyStep, with_tokens: bool) -> dict[str, object]:
    line: dict[str, object] = {
        "step_index": step.idx,
        "source": "MODEL" if step.step_type == PLANNER else "SYSTEM",
        "type": _TYPE_NAMES.get(step.step_type, "GENERIC"),
        "status": step.status,
        "created_at": step_ts(step.at).strftime("%Y-%m-%dT%H:%M:%SZ")
        if step.at is not None
        else "",
        "content": f"content {CANARY}",
    }
    if step.step_type == PLANNER:
        line["thinking"] = f"thinking {CANARY}"
    if with_tokens and step.tokens is not None:
        line["input_tokens"], line["cache_read_tokens"], line["output_tokens"] = (
            step.tokens
        )
    if step.tool_calls:
        line["tool_calls"] = [
            {"name": name, "args": args} for name, args in step.tool_calls
        ]
    if step.error is not None:
        line["error"] = step.error
    line["future_field"] = {"nested": CANARY}
    return line


def build_root(
    root: Path, conversations: Sequence[AgyConversation], *, summaries: bool = True
) -> Path:
    """Materialize the conversations under ``root`` and return it."""
    (root / "conversations").mkdir(parents=True, exist_ok=True)
    (root / "brain").mkdir(parents=True, exist_ok=True)
    (root / "cli.log").write_text(f"HandleUserInput text: {CANARY}\n", encoding="utf-8")
    for conv in conversations:
        if conv.db:
            _write_db(root / "conversations" / f"{conv.conversation_id}.db", conv)
        if conv.legacy_pb:
            (root / "conversations" / f"{conv.conversation_id}.pb").write_bytes(
                os.urandom(256)
            )
        brain = root / "brain" / conv.conversation_id / ".system_generated"
        if conv.transcript:
            logs = brain / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            payload = "".join(
                json.dumps(_transcript_line(s, conv.transcript_tokens)) + "\n"
                for s in conv.steps
            )
            (logs / "transcript_full.jsonl").write_text(payload, encoding="utf-8")
            (logs / "transcript.jsonl").write_text(payload, encoding="utf-8")
            if conv.chunks:
                for name in ("transcript", "transcript_full"):
                    chunk = logs / "chunks" / name
                    chunk.mkdir(parents=True, exist_ok=True)
                    (chunk / "00000001.jsonl").write_text(payload, encoding="utf-8")
        if conv.parent_id is not None and conv.subagent_json:
            sub_dir = (
                root / "brain" / conv.parent_id / ".system_generated" / "subagents"
            )
            sub_dir.mkdir(parents=True, exist_ok=True)
            (sub_dir / f"uuid-{conv.conversation_id}.json").write_text(
                json.dumps(
                    {
                        "conversationId": conv.conversation_id,
                        "subagentDescriptor": {
                            "typeName": conv.agent_name or "worker",
                            "role": f"Role {CANARY}",
                        },
                        "state": "COMPLETED",
                        "spawnStepIndex": conv.spawn_step_index,
                        "workspaceUris": [conv.workspace_uri],
                    }
                ),
                encoding="utf-8",
            )
    if summaries:
        with sqlite3.connect(root / "conversation_summaries.db") as con:
            con.execute(SUMMARIES_DDL)
            for conv in (c for c in conversations if c.in_summaries):
                uris = json.dumps([conv.workspace_uri]) if conv.workspace_uri else "[]"
                con.execute(
                    "INSERT INTO conversation_summaries (conversation_id, title, preview, last_modified_time, "
                    "workspace_uris, agent_name, parent_conversation_id, nesting_depth, last_user_input_time) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        conv.conversation_id,
                        f"title {CANARY}",
                        f"preview {CANARY}",
                        "2026-10-16 14:00:00",
                        uris,
                        conv.agent_name,
                        conv.parent_id
                        if conv.summary_parent and conv.parent_id
                        else "",
                        1 if conv.parent_id else 0,
                        "2026-10-16 14:00:00",
                    ),
                )
    return root
