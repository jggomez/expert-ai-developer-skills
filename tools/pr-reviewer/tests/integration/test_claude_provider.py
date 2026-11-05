"""Claude Managed Agents provider: read-only session, budget and result handling."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace as NS
from typing import ClassVar

import pytest

pytest.importorskip("anthropic")

import anthropic

from pr_reviewer.adapters.providers.claude_managed import (
    READ_ONLY_TOOLS,
    SUBMIT_TOOL,
    ClaudeManagedProvider,
    create_reviewer_resources,
    to_cents,
)
from pr_reviewer.application.ports import ProviderError, ReviewRequest
from pr_reviewer.domain.models import DiffBundle, FileDiff

FINDING = {
    "file": "app.py", "line": 1, "severity": "high", "category": "cost",
    "confidence": "high", "title": "N+1", "impact": "One call per order",
}


def tool_use(name=SUBMIT_TOOL, payload=None, event_id="sevt_1"):
    return NS(type="agent.custom_tool_use", id=event_id, name=name, input=payload if payload is not None else {"findings": [FINDING]})


def idle(reason="end_turn"):
    return NS(type="session.status_idle", stop_reason=NS(type=reason))


class FakeStream:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        return iter(self.events)

    def __exit__(self, *exc):
        return False


class FakeClient:
    """Records every call to the Managed Agents API."""

    def __init__(self, events=(), stream_error=None):
        self.uploads, self.sent = [], []
        self.created = None
        self.stream_error = stream_error
        self.agent_args, self.env_args = None, None
        usage = NS(
            input_tokens=100, output_tokens=50, cache_read_input_tokens=400,
            cache_creation=None, list_cost=NS(amount="37", currency="USD"),
        )

        def upload(**kwargs):
            self.uploads.append(kwargs)
            return NS(id=f"file_{len(self.uploads)}")

        def create(**kwargs):
            self.created = kwargs
            return NS(id="sesn_1")

        def stream(**kwargs):
            if self.stream_error:
                raise self.stream_error
            self.stream_kwargs = kwargs
            return FakeStream(events)

        def send(**kwargs):
            self.sent.extend(kwargs["events"])

        self.files = NS(upload=upload)
        self.beta = NS(
            sessions=NS(
                create=create,
                retrieve=lambda **_: NS(usage=usage),
                events=NS(stream=stream, send=send),
            ),
        )


def request(tmp_path: Path, files=("app.py",)) -> ReviewRequest:
    for name in files:
        path = tmp_path / name
        if name != "gone.py":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x = 1\n")
    bundle = DiffBundle(base="a" * 40, head="b" * 40, files=[FileDiff(path=f, patch=f"+{f}\n") for f in files])
    return ReviewRequest(bundle=bundle, workspace=tmp_path, budget_usd="0.50")


def provider(client, **kwargs) -> ClaudeManagedProvider:
    return ClaudeManagedProvider(client=client, agent_id="agent_1", environment_id="env_1", **kwargs)


def sent_types(client) -> list[str]:
    return [e["type"] for e in client.sent]


def test_session_is_forced_to_read_only_tools_whatever_the_stored_agent_says(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle()])

    # Act
    provider(client).review(request(tmp_path))

    # Assert
    agent = client.created["agent"]
    assert (agent["type"], agent["id"]) == ("agent_with_overrides", "agent_1")
    assert agent["model"]["id"] == "claude-opus-5-5"
    assert "untrusted" in agent["system"]
    toolset = agent["tools"][0]
    assert toolset["default_config"]["enabled"] is False
    assert {c["name"] for c in toolset["configs"]} == set(READ_ONLY_TOOLS) == {"read", "glob", "grep"}
    assert all(c["enabled"] for c in toolset["configs"])
    assert [t["name"] for t in agent["tools"][1:]] == [SUBMIT_TOOL]


def test_session_carries_the_dollar_budget_in_cents(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle()])

    # Act
    provider(client).review(request(tmp_path))

    # Assert
    assert client.created["budget"] == {"type": "limit", "max_list_cost": {"amount": "50", "currency": "USD"}}
    assert client.created["environment_id"] == "env_1"


@pytest.mark.parametrize(("value", "cents"), [("1", "100"), ("0.50", "50"), ("2.5", "250"), ("0.01", "1")])
def test_budget_is_converted_without_float_rounding(value: str, cents: str):
    # Act / Assert
    assert to_cents(value) == cents


@pytest.mark.parametrize("value", ["0", "-1", "abc", "0.001"])
def test_invalid_budgets_are_rejected(value: str):
    # Act / Assert
    with pytest.raises(ProviderError, match="budget"):
        to_cents(value)


def test_changed_files_are_uploaded_with_expiry_under_stable_names(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle()])

    # Act
    provider(client).review(request(tmp_path, files=("src/app.py", "b.py")))

    # Assert
    assert all(u["expires_in_seconds"] == 3600 for u in client.uploads)
    assert [u["file"][0] for u in client.uploads] == ["changed-file-1", "changed-file-2"]
    assert client.created["resources"] == [
        {"type": "file", "file_id": "file_1", "mount_path": "/repo/src/app.py"},
        {"type": "file", "file_id": "file_2", "mount_path": "/repo/b.py"},
    ]


def test_files_outside_the_clean_copy_or_with_unsafe_paths_are_not_uploaded(tmp_path: Path):
    # Arrange: AGENTS.md is in the diff but was removed from the clean copy
    client = FakeClient([tool_use(), idle()])
    bundle = DiffBundle(
        base="a" * 40, head="b" * 40,
        files=[FileDiff(path=p, patch="+x\n") for p in ("AGENTS.md", "../secret", "a\nb.py", "app.py")],
    )
    (tmp_path / "app.py").write_text("x = 1\n")
    outside = tmp_path.parent / "secret"
    outside.write_text("token\n")

    # Act
    provider(client).review(ReviewRequest(bundle=bundle, workspace=tmp_path))

    # Assert
    assert [r["mount_path"] for r in client.created["resources"]] == ["/repo/app.py"]


def test_oversized_files_stay_out_but_their_diff_is_still_reviewed(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle()])
    req = request(tmp_path)
    (tmp_path / "app.py").write_bytes(b"x" * 2_000_000)

    # Act
    provider(client).review(req)

    # Assert
    assert client.uploads == []
    assert "+app.py" in client.sent[0]["content"][0]["text"]


def test_findings_usage_and_reported_cost_are_returned(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle()])

    # Act
    output = provider(client).review(request(tmp_path))

    # Assert
    assert output.result.findings[0].title == "N+1"
    assert (output.usage.input_tokens, output.usage.cached_input_tokens, output.usage.output_tokens) == (500, 400, 50)
    assert output.usage.reported_cost_usd == pytest.approx(0.37)
    assert output.model == "claude-opus-5-5"


def test_prompt_is_sent_with_the_diff_and_tells_the_agent_what_it_can_see(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle()])

    # Act
    provider(client).review(request(tmp_path))

    # Assert
    message = client.sent[0]
    text = message["content"][0]["text"]
    assert message["type"] == "user.message"
    assert "+app.py" in text
    assert "/mnt/session/uploads/repo" in text
    assert SUBMIT_TOOL in text


def test_accepted_findings_are_acknowledged(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle()])

    # Act
    provider(client).review(request(tmp_path))

    # Assert
    result = client.sent[-1]
    assert (result["type"], result["custom_tool_use_id"]) == ("user.custom_tool_result", "sevt_1")
    assert not result.get("is_error")


def test_invalid_findings_are_returned_to_the_agent_to_correct(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(payload={"findings": [{"file": "a.py"}]}), tool_use(event_id="sevt_2"), idle()])

    # Act
    output = provider(client).review(request(tmp_path))

    # Assert
    assert client.sent[1]["is_error"] is True
    assert len(output.result.findings) == 1


def test_repeated_invalid_findings_stop_the_review(tmp_path: Path):
    # Arrange
    bad = {"findings": "nope"}
    client = FakeClient([tool_use(payload=bad, event_id=f"sevt_{i}") for i in range(5)])

    # Act / Assert
    with pytest.raises(ProviderError, match="invalid findings"):
        provider(client).review(request(tmp_path))
    assert "user.interrupt" in sent_types(client)


def test_unknown_custom_tools_are_refused(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(name="run_shell"), tool_use(event_id="sevt_2"), idle()])

    # Act
    provider(client).review(request(tmp_path))

    # Assert
    assert client.sent[1]["is_error"] is True


def test_paused_tool_calls_are_always_denied_because_nobody_is_watching(tmp_path: Path):
    # Arrange
    paused = NS(type="agent.tool_use", id="sevt_9", evaluated_permission="ask", name="read")
    client = FakeClient([paused, tool_use(), idle()])

    # Act
    provider(client).review(request(tmp_path))

    # Assert
    confirmation = client.sent[1]
    assert (confirmation["type"], confirmation["tool_use_id"], confirmation["result"]) == ("user.tool_confirmation", "sevt_9", "deny")


def test_requires_action_idle_does_not_end_the_review(tmp_path: Path):
    # Arrange
    client = FakeClient([idle("requires_action"), tool_use(), idle()])

    # Act
    output = provider(client).review(request(tmp_path))

    # Assert
    assert len(output.result.findings) == 1


def test_budget_stop_is_reported_with_the_cost_spent(tmp_path: Path):
    # Arrange
    client = FakeClient([idle("budget_reached")])

    # Act
    with pytest.raises(ProviderError, match="budget_reached") as caught:
        provider(client).review(request(tmp_path))

    # Assert
    assert caught.value.usage.reported_cost_usd == pytest.approx(0.37)
    assert caught.value.model == "claude-opus-5-5"


def test_submitted_findings_survive_a_budget_stop(tmp_path: Path):
    # Arrange
    client = FakeClient([tool_use(), idle("budget_reached")])

    # Act
    output = provider(client).review(request(tmp_path))

    # Assert
    assert len(output.result.findings) == 1


def test_finishing_without_findings_is_an_error_not_a_clean_review(tmp_path: Path):
    # Arrange
    client = FakeClient([idle()])

    # Act / Assert
    with pytest.raises(ProviderError, match="submit"):
        provider(client).review(request(tmp_path))


def test_terminated_session_is_an_error(tmp_path: Path):
    # Arrange
    client = FakeClient([NS(type="session.status_terminated")])

    # Act / Assert
    with pytest.raises(ProviderError, match="terminated"):
        provider(client).review(request(tmp_path))


def test_time_limit_interrupts_the_session(tmp_path: Path):
    # Arrange
    client = FakeClient([NS(type="agent.message"), idle()])

    # Act
    with pytest.raises(ProviderError, match="time limit"):
        provider(client, timeout_seconds=-1).review(request(tmp_path))

    # Assert
    assert "user.interrupt" in sent_types(client)


def test_stream_failures_are_reported_as_provider_errors(tmp_path: Path):
    # Arrange
    client = FakeClient(stream_error=anthropic.APIConnectionError(request=None))

    # Act / Assert
    with pytest.raises(ProviderError, match="connection"):
        provider(client).review(request(tmp_path))


@pytest.mark.parametrize(
    ("agent", "environment", "missing"),
    [(None, "env_1", "claude-agent-id"), ("agent_1", None, "claude-environment-id")],
)
def test_missing_ids_explain_the_setup_command(tmp_path: Path, agent, environment, missing: str):
    # Arrange
    target = ClaudeManagedProvider(client=FakeClient(), agent_id=agent, environment_id=environment)

    # Act / Assert
    with pytest.raises(ProviderError, match=f"{missing}.*setup-claude"):
        target.review(request(tmp_path))


def test_missing_key_is_explained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    target = ClaudeManagedProvider(agent_id="agent_1", environment_id="env_1")

    # Act / Assert
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        target.review(request(tmp_path))


def test_setup_creates_a_network_less_environment_and_a_read_only_agent():
    # Arrange
    calls = {}

    def record(name, result):
        def _call(**kwargs):
            calls[name] = kwargs
            return NS(id=result)
        return _call

    client = NS(beta=NS(agents=NS(create=record("agent", "agent_9")), environments=NS(create=record("env", "env_9"))))

    # Act
    agent_id, environment_id = create_reviewer_resources(client)

    # Assert
    assert (agent_id, environment_id) == ("agent_9", "env_9")
    assert calls["env"]["config"] == {"type": "cloud", "networking": {"type": "limited"}}
    assert calls["agent"]["tools"][0]["default_config"]["enabled"] is False


class StubApi(BaseHTTPRequestHandler):
    """Speaks just enough of the HTTP API for the real SDK."""

    log: ClassVar[list[tuple[str, str, dict]]] = []
    USAGE: ClassVar[dict] = {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0, "list_cost": {"amount": "2", "currency": "USD"}}

    def log_message(self, *args):
        return

    def _json(self, body: dict):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        type(self).log.append(("GET", path, {}))
        if path.endswith("/stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            events = [
                {"type": "agent.custom_tool_use", "id": "sevt_1", "name": SUBMIT_TOOL, "input": {"findings": [FINDING]},
                 "processed_at": "2026-11-04T00:00:00Z"},
                {"type": "session.status_idle", "id": "sevt_2", "stop_reason": {"type": "end_turn"},
                 "processed_at": "2026-11-04T00:00:00Z"},
            ]
            for event in events:
                self.wfile.write(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
            return
        self._json({"id": "sesn_1", "type": "session", "status": "idle", "usage": self.USAGE})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        path = self.path.split("?")[0]
        is_json = "json" in self.headers.get("Content-Type", "")
        type(self).log.append(("POST", path, json.loads(raw) if is_json and raw else {}))
        if path.endswith("/files"):
            self._json({
                "id": "file_1", "type": "file", "filename": "changed-file-1", "mime_type": "text/plain",
                "size_bytes": 6, "created_at": "2026-11-04T00:00:00Z",
            })
        elif path.endswith("/sessions"):
            self._json({"id": "sesn_1", "type": "session", "status": "idle", "usage": self.USAGE})
        else:
            self._json({"data": []})


@pytest.fixture
def stub_api():
    StubApi.log = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubApi)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_real_sdk_drives_the_whole_session_over_http(tmp_path: Path, stub_api: str):
    # Arrange
    client = anthropic.Anthropic(api_key="test-key", base_url=stub_api, max_retries=0)

    # Act
    output = provider(client).review(request(tmp_path))

    # Assert
    assert output.result.findings[0].title == "N+1"
    assert output.usage.reported_cost_usd == pytest.approx(0.02)
    paths = [(method, path) for method, path, _ in StubApi.log]
    assert ("POST", "/v1/files") in paths
    assert ("POST", "/v1/sessions") in paths
    assert ("GET", "/v1/sessions/sesn_1/events/stream") in paths
    bodies = [body for _, path, body in StubApi.log if path == "/v1/sessions/sesn_1/events"]
    assert [body["events"][0]["type"] for body in bodies] == ["user.message", "user.custom_tool_result"]
