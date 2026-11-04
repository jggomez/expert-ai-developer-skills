"""Antigravity provider: read-only agent, budget and result handling."""

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("google.antigravity")

from google.antigravity import BuiltinTools, LocalAgentConfig
from google.antigravity.types import StopReason, UsageMetadata

from pr_reviewer.models import DiffBundle, FileDiff
from pr_reviewer.providers.antigravity import (
    READ_ONLY_TOOLS,
    AntigravityProvider,
    build_config,
)
from pr_reviewer.providers.base import ProviderError, ReviewRequest

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
    return AntigravityProvider(agent_factory=lambda config: FakeAgent(config, **script))


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
