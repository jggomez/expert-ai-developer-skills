"""Builder for synthetic Claude Code transcripts (``~/.claude/projects/<slug>/<sid>.jsonl``).

Shapes follow the keys observed on real data (spike-notes §1/§6.3); every content-like
slot (prompts, assistant text, thinking, tool inputs/outputs, file paths, subagent
descriptions) carries ``CANARY`` so privacy tests can prove readers never surface it.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tests.fixtures.canary import CANARY

__all__ = [
    "CANARY",
    "ClaudeHome",
    "ClaudeSession",
    "LineWriter",
    "at",
    "tool_use",
    "usage",
]

T0 = datetime(2026, 10, 16, 14, 0, 0, tzinfo=UTC)
CWD = "/Users/dev/work/demo-repo"


def at(seconds: float) -> str:
    """ISO timestamp ``T0 + seconds`` in Claude's millisecond ``Z`` format."""
    value = T0 + timedelta(seconds=seconds)
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


def usage(
    input: int = 100,
    output: int = 50,
    cache_5m: int = 0,
    cache_1h: int = 0,
    cache_read: int = 1_000,
    *,
    thinking: int | None = None,
    speed: str | None = None,
    geo: str | None = None,
    iterations: Sequence[dict[str, Any]] | None = None,
    legacy_cache_only: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "input_tokens": input,
        "output_tokens": output,
        "cache_creation_input_tokens": cache_5m + cache_1h,
        "cache_read_input_tokens": cache_read,
        "service_tier": "standard",
        "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
    }
    if not legacy_cache_only:
        body["cache_creation"] = {
            "ephemeral_5m_input_tokens": cache_5m,
            "ephemeral_1h_input_tokens": cache_1h,
        }
    if thinking is not None:
        body["output_tokens_details"] = {"thinking_tokens": thinking}
    if speed is not None:
        body["speed"] = speed
    if geo is not None:
        body["inference_geo"] = geo
    body["iterations"] = (
        list(iterations)
        if iterations is not None
        else [{"type": "message", "input_tokens": input, "output_tokens": output}]
    )
    return body


def tool_use(name: str, tool_id: str, **inputs: Any) -> dict[str, Any]:
    return {"type": "tool_use", "id": tool_id, "name": name, "input": inputs}


@dataclass
class LineWriter:
    """Appends Claude-shaped JSONL lines; returns each line's ``uuid``."""

    session_id: str
    version: str = "2.1.229"
    cwd: str = CWD
    is_sidechain: bool = False
    agent_id: str | None = None
    lines: list[dict[str, Any]] = field(default_factory=list)
    _counter: int = 0

    def _uuid(self) -> str:
        self._counter += 1
        prefix = self.agent_id or self.session_id
        return f"{prefix}-u{self._counter:04d}"

    def _base(
        self, kind: str, ts: float, parent: str | None, uuid: str | None
    ) -> dict[str, Any]:
        line: dict[str, Any] = {
            "type": kind,
            "uuid": uuid or self._uuid(),
            "parentUuid": parent,
            "timestamp": at(ts),
            "sessionId": self.session_id,
            "cwd": self.cwd,
            "gitBranch": f"feature/{CANARY}",
            "version": self.version,
            "isSidechain": self.is_sidechain,
            "userType": "external",
            "entrypoint": "cli",
            "slug": f"slug-{CANARY}",
        }
        if self.agent_id is not None:
            line["agentId"] = self.agent_id
        return line

    def raw(self, obj: dict[str, Any]) -> None:
        self.lines.append(obj)

    def prompt(
        self,
        ts: float,
        prompt_id: str,
        *,
        parent: str | None = None,
        uuid: str | None = None,
    ) -> str:
        line = self._base("user", ts, parent, uuid)
        line["promptId"] = prompt_id
        line["message"] = {"role": "user", "content": f"please do the thing {CANARY}"}
        self.lines.append(line)
        return str(line["uuid"])

    def assistant(
        self,
        ts: float,
        request_id: str | None,
        *,
        parent: str | None,
        model: str = "claude-opus-5-5",
        use: dict[str, Any] | None = None,
        tools: Sequence[dict[str, Any]] = (),
        message_id: str | None = None,
        api_error: bool = False,
        uuid: str | None = None,
    ) -> str:
        line = self._base("assistant", ts, parent, uuid)
        if request_id is not None:
            line["requestId"] = request_id
        if api_error:
            line["isApiErrorMessage"] = True
        line["advisorModel"] = "claude-opus-5-5"
        line["message"] = {
            "id": message_id or f"msg-{request_id or line['uuid']}",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [
                {
                    "type": "thinking",
                    "thinking": f"thinking about {CANARY}",
                    "signature": CANARY,
                },
                {"type": "text", "text": f"answer {CANARY}"},
                *tools,
            ],
            "stop_reason": "tool_use" if tools else "end_turn",
            "usage": use if use is not None else usage(),
        }
        self.lines.append(line)
        return str(line["uuid"])

    def tool_result(
        self,
        ts: float,
        prompt_id: str | None,
        *,
        parent: str,
        tool_use_id: str,
        is_error: bool = False,
    ) -> str:
        line = self._base("user", ts, parent, None)
        if prompt_id is not None:
            line["promptId"] = prompt_id
        line["sourceToolAssistantUUID"] = parent
        line["toolUseResult"] = {"stdout": f"output {CANARY}", "stderr": CANARY}
        line["message"] = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "is_error": is_error,
                    "content": f"result {CANARY}",
                }
            ],
        }
        self.lines.append(line)
        return str(line["uuid"])

    def turn_duration(self, ts: float, *, parent: str, duration_ms: int) -> str:
        line = self._base("system", ts, parent, None)
        line.update(
            {
                "subtype": "turn_duration",
                "durationMs": duration_ms,
                "messageCount": 4,
                "isMeta": False,
            }
        )
        self.lines.append(line)
        return str(line["uuid"])

    def attachment(self, ts: float, *, parent: str) -> str:
        line = self._base("attachment", ts, parent, None)
        line["attachment"] = {"type": "file", "content": CANARY}
        self.lines.append(line)
        return str(line["uuid"])

    def noise(self) -> None:
        """Line types that carry no usage and must be ignored."""
        self.lines.append(
            {
                "type": "file-history-snapshot",
                "messageId": "m",
                "snapshot": {"text": CANARY},
            }
        )
        self.lines.append(
            {"type": "last-prompt", "lastPrompt": CANARY, "sessionId": self.session_id}
        )
        self.lines.append(
            {"type": "ai-title", "aiTitle": CANARY, "sessionId": self.session_id}
        )
        self.lines.append(
            {
                "type": "brand-new-line-type",
                "payload": {"x": CANARY},
                "sessionId": self.session_id,
            }
        )

    def encode(self) -> bytes:
        return b"".join(json.dumps(line).encode("utf-8") + b"\n" for line in self.lines)


@dataclass
class SubagentSpec:
    writer: LineWriter
    meta: dict[str, Any] | None


class ClaudeSession(LineWriter):
    """A main transcript plus optional subagent transcripts and ``meta.json`` files."""

    def __init__(
        self,
        session_id: str,
        *,
        version: str = "2.1.229",
        cwd: str = CWD,
        slug: str = "-Users-dev-work-demo-repo",
    ) -> None:
        super().__init__(session_id=session_id, version=version, cwd=cwd)
        self.slug = slug
        self.subagents: dict[str, SubagentSpec] = {}

    def subagent(
        self,
        agent_id: str,
        *,
        agent_type: str | None = "code-implementer",
        tool_use_id: str | None = None,
        spawn_depth: int | None = 1,
        parent_agent_id: str | None = None,
        stopped: bool = False,
        meta: bool = True,
    ) -> LineWriter:
        writer = LineWriter(
            session_id=self.session_id,
            version=self.version,
            cwd=self.cwd,
            is_sidechain=True,
            agent_id=agent_id,
        )
        body: dict[str, Any] | None = None
        if meta:
            body = {
                "description": f"Implement {CANARY} feature",
                "requestShape": "x",
                "requestNonInteractive": True,
            }
            if agent_type is not None:
                body["agentType"] = agent_type
            if tool_use_id is not None:
                body["toolUseId"] = tool_use_id
            if spawn_depth is not None:
                body["spawnDepth"] = spawn_depth
            if parent_agent_id is not None:
                body["parentAgentId"] = parent_agent_id
            if stopped:
                body["stoppedByUser"] = True
        self.subagents[agent_id] = SubagentSpec(writer, body)
        return writer


class ClaudeHome:
    """A synthetic ``~/.claude`` root."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "projects").mkdir(parents=True, exist_ok=True)

    def main_path(self, session: ClaudeSession) -> Path:
        return self.root / "projects" / session.slug / f"{session.session_id}.jsonl"

    def write(self, session: ClaudeSession, *, tail: bytes = b"") -> Path:
        main = self.main_path(session)
        main.parent.mkdir(parents=True, exist_ok=True)
        main.write_bytes(session.encode() + tail)
        for agent_id, spec in session.subagents.items():
            sub_dir = main.parent / session.session_id / "subagents"
            sub_dir.mkdir(parents=True, exist_ok=True)
            (sub_dir / f"agent-{agent_id}.jsonl").write_bytes(spec.writer.encode())
            if spec.meta is not None:
                (sub_dir / f"agent-{agent_id}.meta.json").write_text(
                    json.dumps(spec.meta), encoding="utf-8"
                )
        return main
