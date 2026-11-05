"""Review with Claude Managed Agents.

Anthropic hosts the agent loop and a sandbox with no network. The sandbox only
receives the diff and the changed files, as read-only uploads that expire: no
repository is mounted, because a mounted repository loads its .claude/skills
with no review step, and a pull request could add instructions there.

Tools, instructions and model are sent with every session, so the behavior
comes from this code and not from a stored agent someone could have edited.
"""

from __future__ import annotations

import logging
import os
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import anthropic
import pydantic

from pr_reviewer.application.ports import ProviderError, ProviderOutput, ReviewRequest
from pr_reviewer.application.prompt import build_prompt, system_instructions
from pr_reviewer.domain.models import FileDiff, ReviewResult, ReviewUsage

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"
AGENT_NAME = "pr-reviewer"
SUBMIT_TOOL = "submit_findings"
READ_ONLY_TOOLS = ("read", "glob", "grep")
UPLOAD_ROOT = "/mnt/session/uploads"
REPO_MOUNT = "/repo"
UPLOAD_EXPIRY_SECONDS = 3600  # The shortest the API allows. Covers a runner that dies mid-review.
MAX_UPLOAD_BYTES = 1_000_000
MAX_INVALID_SUBMISSIONS = 3
REVIEW_TIMEOUT_SECONDS = 600.0
STREAM_READ_TIMEOUT_SECONDS = 240.0  # Generous: the model may think for a while between events.

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _inline_refs(node: Any, definitions: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str):
            return _inline_refs(definitions[reference.rsplit("/", 1)[1]], definitions)
        return {key: _inline_refs(value, definitions) for key, value in node.items() if key != "$defs"}
    if isinstance(node, list):
        return [_inline_refs(item, definitions) for item in node]
    return node


def _submit_schema() -> dict[str, Any]:
    schema = ReviewResult.model_json_schema()
    inlined: dict[str, Any] = _inline_refs(schema, schema.get("$defs", {}))
    inlined["required"] = ["findings"]
    return inlined


def session_tools() -> list[dict[str, Any]]:
    """Everything is off except reading, and the tool that returns the findings."""
    return [
        {
            "type": "agent_toolset_20260401",
            "default_config": {"enabled": False},
            "configs": [
                {"name": name, "enabled": True, "permission_policy": {"type": "always_allow"}}
                for name in READ_ONLY_TOOLS
            ],
        },
        {
            "type": "custom",
            "name": SUBMIT_TOOL,
            "description": "Submit the final review. Call it once, with an empty list when nothing matters.",
            "input_schema": _submit_schema(),
        },
    ]


def to_cents(value: str) -> str:
    """Convert a dollar amount to the integer cents string the API expects."""
    try:
        cents = Decimal(value) * 100
    except InvalidOperation as error:
        raise ProviderError(f"Invalid budget {value!r}: expected an amount in dollars") from error
    if cents < 1 or cents != cents.to_integral_value():
        raise ProviderError(f"Invalid budget {value!r}: use a positive amount in whole cents")
    return str(int(cents))


def create_reviewer_resources(client: Any = None) -> tuple[str, str]:
    """Create the persistent agent and environment. Run once, never per review."""
    client = client or anthropic.Anthropic()
    environment = client.beta.environments.create(
        name=AGENT_NAME,
        config={"type": "cloud", "networking": {"type": "limited"}},
    )
    agent = client.beta.agents.create(
        name=AGENT_NAME,
        model=DEFAULT_MODEL,
        system=system_instructions(),
        tools=session_tools(),
    )
    return agent.id, environment.id


def _uploadable(workspace: Path, file: FileDiff) -> Path | None:
    """Return the file in the clean copy, or None when it must stay out of the sandbox."""
    relative = Path(file.path)
    if _CONTROL.search(file.path) or relative.is_absolute() or ".." in relative.parts:
        return None
    path = (workspace / relative).resolve()
    if not path.is_relative_to(workspace.resolve()) or not path.is_file():
        return None
    return path if path.stat().st_size <= MAX_UPLOAD_BYTES else None


def _session_usage(session: Any) -> ReviewUsage:
    usage = session.usage
    cached = usage.cache_read_input_tokens or 0
    created = usage.cache_creation
    written = (
        (created.ephemeral_5m_input_tokens or 0) + (created.ephemeral_1h_input_tokens or 0) if created else 0
    )
    cost = usage.list_cost
    return ReviewUsage(
        input_tokens=(usage.input_tokens or 0) + cached + written,
        cached_input_tokens=cached,
        output_tokens=usage.output_tokens or 0,
        reported_cost_usd=float(Decimal(cost.amount) / 100) if cost else None,
    )


class _ReviewStopped(Exception):
    """The session cannot produce a review and should be interrupted."""


class ClaudeManagedProvider:
    name = "claude"

    def __init__(
        self,
        *,
        client: Any = None,
        agent_id: str | None = None,
        environment_id: str | None = None,
        timeout_seconds: float = REVIEW_TIMEOUT_SECONDS,
    ):
        self._client = client
        self._agent_id = agent_id
        self._environment_id = environment_id
        self._timeout_seconds = timeout_seconds

    def _resolved_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderError("Set ANTHROPIC_API_KEY through the api-key input")
        return anthropic.Anthropic()

    def review(self, request: ReviewRequest) -> ProviderOutput:
        for value, label in ((self._agent_id, "claude-agent-id"), (self._environment_id, "claude-environment-id")):
            if not value:
                raise ProviderError(f"Set {label}: run `pr-reviewer setup-claude` once to create it")
        client = self._resolved_client()
        model = request.model or DEFAULT_MODEL
        budget = to_cents(request.budget_usd)
        try:
            session = client.beta.sessions.create(
                agent={
                    "type": "agent_with_overrides",
                    "id": self._agent_id,
                    "model": {"id": model, "effort": DEFAULT_EFFORT},
                    "system": system_instructions(request.rubric),
                    "tools": session_tools(),
                },
                environment_id=self._environment_id,
                title=f"pr-reviewer {request.bundle.head[:7]}",
                budget={"type": "limit", "max_list_cost": {"amount": budget, "currency": "USD"}},
                resources=self._upload_files(client, request),
            )
            return self._follow(client, session.id, request, model)
        except anthropic.APIError as error:
            detail = f"{type(error).__name__}: {error}"[:200]
            raise ProviderError(f"Claude API connection or request failed: {detail}", model=model) from error

    def _upload_files(self, client: Any, request: ReviewRequest) -> list[dict[str, str]]:
        resources: list[dict[str, str]] = []
        for file in request.bundle.files:
            path = _uploadable(request.workspace, file)
            if path is None:
                continue
            # A neutral upload name: the real path is chosen by the pull request author.
            name = f"changed-file-{len(resources) + 1}"
            uploaded = client.files.upload(
                file=(name, path.read_bytes(), "text/plain"),
                expires_in_seconds=UPLOAD_EXPIRY_SECONDS,
            )
            resources.append({"type": "file", "file_id": uploaded.id, "mount_path": f"{REPO_MOUNT}/{file.path}"})
        return resources

    def _follow(self, client: Any, session_id: str, request: ReviewRequest, model: str) -> ProviderOutput:
        try:
            result, stop_reason = self._stream(client, session_id, request)
        except (_ReviewStopped, anthropic.APIError) as error:
            self._interrupt(client, session_id)
            if isinstance(error, anthropic.APIError):
                raise
            raise ProviderError(str(error), usage=self._final_usage(client, session_id), model=model) from error

        usage = self._final_usage(client, session_id)
        if result is None:
            raise ProviderError(f"The agent stopped without calling {SUBMIT_TOOL}: {stop_reason}", usage=usage, model=model)
        return ProviderOutput(result=result, usage=usage, model=model)

    def _stream(self, client: Any, session_id: str, request: ReviewRequest) -> tuple[ReviewResult | None, str]:
        deadline = time.monotonic() + self._timeout_seconds
        events = client.beta.sessions.events
        result: ReviewResult | None = None
        invalid = 0

        def send(event: dict[str, Any]) -> None:
            events.send(session_id=session_id, events=[event])

        note = (
            f"The full text of each changed file is under {UPLOAD_ROOT}{REPO_MOUNT}. Only changed files are "
            f"available, so do not claim something is duplicated elsewhere. When done, call {SUBMIT_TOOL} once."
        )
        prompt = build_prompt(request.bundle, workspace_note=note)

        # Open the stream first, so that no event is missed.
        with events.stream(session_id=session_id, timeout=STREAM_READ_TIMEOUT_SECONDS) as stream:
            send({"type": "user.message", "content": [{"type": "text", "text": prompt}]})
            for event in stream:
                if time.monotonic() > deadline:
                    raise _ReviewStopped(f"The agent exceeded the {self._timeout_seconds:g}s time limit")

                if event.type == "agent.custom_tool_use":
                    accepted = self._accept(event)
                    if accepted is None:
                        invalid += 1
                        if invalid >= MAX_INVALID_SUBMISSIONS:
                            raise _ReviewStopped("The agent kept returning invalid findings")
                    else:
                        result = accepted
                    send(_tool_reply(event.id, accepted))
                elif event.type == "agent.tool_use" and getattr(event, "evaluated_permission", None) == "ask":
                    # Nobody is watching this run, so a paused call is refused.
                    send({"type": "user.tool_confirmation", "tool_use_id": event.id, "result": "deny"})
                elif event.type == "session.status_idle" and event.stop_reason.type != "requires_action":
                    return result, event.stop_reason.type
                elif event.type == "session.status_terminated":
                    return result, "session terminated"
                elif event.type == "session.error":
                    logger.warning("Session error: %s", getattr(event, "error", "unknown"))
        return result, "stream closed"

    @staticmethod
    def _accept(event: Any) -> ReviewResult | None:
        if event.name != SUBMIT_TOOL:
            return None
        try:
            return ReviewResult.model_validate(event.input)
        except pydantic.ValidationError:
            return None

    def _interrupt(self, client: Any, session_id: str) -> None:
        """Stop the agent so that it spends no more. The budget still caps it if this fails."""
        try:
            client.beta.sessions.events.send(session_id=session_id, events=[{"type": "user.interrupt"}])
        except anthropic.APIError:
            logger.warning("Could not interrupt session %s", session_id, exc_info=True)

    def _final_usage(self, client: Any, session_id: str) -> ReviewUsage:
        return _session_usage(client.beta.sessions.retrieve(session_id=session_id))


def _tool_reply(event_id: str, accepted: ReviewResult | None) -> dict[str, Any]:
    reply: dict[str, Any] = {"type": "user.custom_tool_result", "custom_tool_use_id": event_id}
    if accepted is None:
        text = f"Rejected. Call {SUBMIT_TOOL} with findings that match its schema."
        return {**reply, "is_error": True, "content": [{"type": "text", "text": text}]}
    return {**reply, "content": [{"type": "text", "text": "Findings recorded. The review is finished."}]}
