"""Antigravity provider: read-only agent, budget and result handling."""

import asyncio
import logging
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("google.antigravity")

from google.antigravity import BuiltinTools, LocalAgentConfig
from google.antigravity.types import StopReason, UsageMetadata

from pr_reviewer.adapters.providers.antigravity import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_MODEL,
    READ_ONLY_TOOLS,
    AntigravityProvider,
    build_config,
    is_overload,
)
from pr_reviewer.application.ports import ProviderError, ReviewRequest
from pr_reviewer.domain.models import DiffBundle, FileDiff

FINDING = {
    "file": "a.py", "line": 1, "severity": "high", "category": "cost",
    "confidence": "high", "title": "N+1", "impact": "One call per order",
}


class FakeResponse:
    def __init__(self, data, stop_reason, usage):
        self._data, self.stop_reason, self.usage_metadata = data, stop_reason, usage

    async def structured_output(self):
        return self._data


class FakeAgent:
    """Records what the provider sends and returns a scripted response."""

    last = None

    def __init__(self, config, *, data=None, stop=StopReason.UNSPECIFIED, error=None):
        self.config, self.data, self.stop, self.error = config, data, stop, error
        self.prompt = None
        self.cwd = None
        FakeAgent.last = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def chat(self, prompt):
        self.prompt = prompt
        self.cwd = Path.cwd().resolve()
        if self.error:
            raise self.error
        usage = UsageMetadata(
            prompt_token_count=1000,
            cached_content_token_count=400,
            candidates_token_count=100,
            thoughts_token_count=50,
        )
        return FakeResponse(self.data, self.stop, usage)


def request(tmp_path: Path) -> ReviewRequest:
    bundle = DiffBundle(base="a" * 40, head="b" * 40, files=[FileDiff(path="a.py", patch="+x\n")])
    return ReviewRequest(bundle=bundle, workspace=tmp_path, max_tokens=5000)


def provider(**script) -> AntigravityProvider:
    async def no_wait(_: float) -> None:
        return None

    return AntigravityProvider(agent_factory=lambda config: FakeAgent(config, **script), sleep=no_wait)


@pytest.fixture(autouse=True)
def api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def test_config_is_accepted_by_the_real_sdk_and_exposes_only_read_tools(tmp_path: Path):
    # Act
    config = build_config(request(tmp_path), model="gemini-3.8-flash")

    # Assert
    assert isinstance(config, LocalAgentConfig)
    enabled = set(config.capabilities.enabled_tools)
    assert enabled == set(READ_ONLY_TOOLS)
    for dangerous in (
        BuiltinTools.RUN_COMMAND, BuiltinTools.EDIT_FILE, BuiltinTools.CREATE_FILE,
        BuiltinTools.SEARCH_WEB, BuiltinTools.READ_URL_CONTENT, BuiltinTools.INVOKE_SUBAGENT,
        BuiltinTools.RUN_WORKFLOW, BuiltinTools.SCHEDULE,
    ):
        assert dangerous not in enabled
    assert config.capabilities.enable_subagents is False
    assert config.workspaces == [str(tmp_path)]


def test_config_denies_by_default_and_sets_the_token_budget(tmp_path: Path):
    # Act
    config = build_config(request(tmp_path), model="gemini-3.8-flash")

    # Assert
    assert config.budget_config.max_total_tokens == 5000
    decisions = {(p.tool, p.decision.value) for p in config.policies}
    assert ("*", "deny") in {(tool, decision.lower()) for tool, decision in decisions}
    allowed = {tool for tool, decision in decisions if decision.lower() == "approve"}
    assert allowed == {str(tool) for tool in READ_ONLY_TOOLS}


def test_review_returns_findings_and_counts_thinking_as_output(tmp_path: Path):
    # Act
    output = provider(data={"findings": [FINDING]}).review(request(tmp_path))

    # Assert
    assert output.result.findings[0].title == "N+1"
    assert (output.usage.input_tokens, output.usage.cached_input_tokens, output.usage.output_tokens) == (1000, 400, 150)
    assert output.model == "gemini-3.8-flash"


def test_agent_runs_from_the_clean_workspace_and_receives_the_diff(tmp_path: Path):
    # Act
    provider(data={"findings": []}).review(request(tmp_path))

    # Assert
    assert FakeAgent.last.cwd == tmp_path.resolve()
    assert "+x" in FakeAgent.last.prompt


def test_budget_stop_is_reported_with_the_tokens_spent(tmp_path: Path):
    # Act
    with pytest.raises(ProviderError, match="MAX_TOTAL_TOKENS_EXCEEDED") as caught:
        provider(data=None, stop=StopReason.MAX_TOTAL_TOKENS_EXCEEDED).review(request(tmp_path))

    # Assert
    assert caught.value.usage.input_tokens == 1000
    assert caught.value.model == "gemini-3.8-flash"


def test_missing_structured_output_is_an_error_not_a_clean_review(tmp_path: Path):
    # Act / Assert
    with pytest.raises(ProviderError, match="structured output"):
        provider(data=None).review(request(tmp_path))


class ScriptedAgents:
    """Hands out one fake agent per attempt and records the waits between them."""

    def __init__(self, *attempts: dict):
        self.attempts = list(attempts)
        self.calls = 0
        self.waits: list[float] = []

    def __call__(self, config) -> FakeAgent:
        script = self.attempts[min(self.calls, len(self.attempts) - 1)]
        self.calls += 1
        return FakeAgent(config, **script)

    async def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)

    def provider(self) -> AntigravityProvider:
        return AntigravityProvider(agent_factory=self, sleep=self.sleep)


def test_an_empty_answer_is_retried_with_a_new_agent_and_tokens_add_up(tmp_path: Path):
    # Arrange: a model 503 only logs a warning in the SDK and ends with no output.
    agents = ScriptedAgents({"data": None}, {"data": {"findings": [FINDING]}})

    # Act
    output = agents.provider().review(request(tmp_path))

    # Assert
    assert agents.calls == 2
    assert len(agents.waits) == 1
    assert len(output.result.findings) == 1
    assert output.usage.input_tokens == 2 * 1000


def test_retries_stop_and_the_error_names_the_likely_cause(tmp_path: Path):
    # Arrange
    agents = ScriptedAgents({"data": None})

    # Act
    with pytest.raises(ProviderError, match=r"3 attempts.*overloaded") as caught:
        agents.provider().review(request(tmp_path))

    # Assert
    assert agents.calls == 3
    assert len(agents.waits) == 2
    assert caught.value.usage.input_tokens == 3 * 1000


class OverloadedAgent(FakeAgent):
    """The real failure: the SDK logs a 503 and the turn then never ends."""

    async def chat(self, prompt):
        logging.warning("System step error (HTTP %s): %s", 503, "high demand")
        await asyncio.Event().wait()


def test_a_503_stops_a_hung_attempt_and_the_last_attempt_uses_the_fallback_model(tmp_path: Path):
    # Arrange
    agents: list[LocalAgentConfig] = []

    def factory(config: LocalAgentConfig) -> FakeAgent:
        agents.append(config)
        if len(agents) < 3:
            return OverloadedAgent(config)
        return FakeAgent(config, data={"findings": [FINDING]})

    async def no_wait(_: float) -> None:
        return None

    provider = AntigravityProvider(agent_factory=factory, sleep=no_wait, timeout_seconds=5)

    # Act
    output = provider.review(request(tmp_path))

    # Assert
    assert [config.model for config in agents] == [DEFAULT_MODEL, DEFAULT_MODEL, DEFAULT_FALLBACK_MODEL]
    assert output.model == DEFAULT_FALLBACK_MODEL
    assert len(output.result.findings) == 1


def test_a_configured_fallback_model_is_used(tmp_path: Path):
    # Arrange
    agents = ScriptedAgents({"data": None})
    configured = replace(request(tmp_path), fallback_model="gemini-custom")
    seen: list[str] = []
    original = agents.__call__

    def factory(config: LocalAgentConfig) -> FakeAgent:
        seen.append(config.model)
        return original(config)

    # Act
    with pytest.raises(ProviderError):
        AntigravityProvider(agent_factory=factory, sleep=agents.sleep).review(configured)

    # Assert
    assert seen[-1] == "gemini-custom"


@pytest.mark.parametrize("message", ["System step error (HTTP 500): boom", "Something else (HTTP 503)"])
def test_the_overload_watch_ignores_other_log_lines_and_keeps_only_transient_codes(message: str):
    # Arrange
    record = logging.LogRecord("root", logging.WARNING, __file__, 1, message, None, None)
    expected = message.startswith("System step error")

    # Act / Assert
    assert is_overload(record) is expected


def test_the_overload_watch_ignores_client_errors():
    # Arrange
    record = logging.LogRecord("root", logging.WARNING, __file__, 1, "System step error (HTTP 404): x", None, None)

    # Act / Assert
    assert is_overload(record) is False


def test_a_budget_stop_is_never_retried(tmp_path: Path):
    # Arrange
    agents = ScriptedAgents({"data": None, "stop": StopReason.MAX_TOTAL_TOKENS_EXCEEDED})

    # Act
    with pytest.raises(ProviderError, match="stopped early"):
        agents.provider().review(request(tmp_path))

    # Assert
    assert agents.calls == 1
    assert agents.waits == []


def test_invalid_structured_output_is_an_error(tmp_path: Path):
    # Act / Assert
    with pytest.raises(ProviderError, match="invalid"):
        provider(data={"findings": [{"file": "a.py"}]}).review(request(tmp_path))


def test_missing_credentials_are_explained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    # Act / Assert
    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        provider(data={"findings": []}).review(request(tmp_path))


def test_model_can_be_overridden(tmp_path: Path):
    # Arrange
    base = request(tmp_path)
    custom = ReviewRequest(bundle=base.bundle, workspace=tmp_path, model="gemini-3.5-flash-lite")

    # Act
    output = provider(data={"findings": []}).review(custom)

    # Assert
    assert output.model == "gemini-3.5-flash-lite"


def test_hung_agent_is_stopped_by_the_time_limit(tmp_path: Path):
    # Arrange
    class HungAgent(FakeAgent):
        async def chat(self, prompt):
            await asyncio.sleep(30)

    slow = AntigravityProvider(agent_factory=HungAgent, timeout_seconds=0.01)

    # Act / Assert
    with pytest.raises(ProviderError, match="time limit"):
        slow.review(request(tmp_path))


def test_read_only_tool_list_is_exact():
    # Act / Assert
    assert {str(t) for t in READ_ONLY_TOOLS} == {
        "view_file", "list_directory", "search_directory", "find_file", "finish",
    }
