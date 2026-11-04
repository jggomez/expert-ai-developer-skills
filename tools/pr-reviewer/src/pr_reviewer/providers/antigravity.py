"""Review with the Google Antigravity SDK.

The agent can only read the clean workspace. It has no shell, network, write
or subagent tools, so text in the diff cannot make it act on the outside world.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import Callable
from typing import Any

import pydantic
from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig, LocalAgentConfig
from google.antigravity.hooks import policy
from google.antigravity.types import BudgetConfig, StopReason, UsageMetadata

from pr_reviewer.models import ReviewResult, ReviewUsage
from pr_reviewer.prompt import build_prompt, system_instructions
from pr_reviewer.providers.base import ProviderError, ProviderOutput, ReviewRequest

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_MODEL_CALLS = 20
MAX_TOOL_CALLS = 40
REVIEW_TIMEOUT_SECONDS = 600.0

READ_ONLY_TOOLS = (
    BuiltinTools.VIEW_FILE,
    BuiltinTools.LIST_DIR,
    BuiltinTools.SEARCH_DIR,
    BuiltinTools.FIND_FILE,
    BuiltinTools.FINISH,
)

AgentFactory = Callable[[LocalAgentConfig], Any]


def build_config(request: ReviewRequest, *, model: str) -> LocalAgentConfig:
    """Configuration of a read-only agent with a hard token budget."""
    return LocalAgentConfig(
        model=model,
        api_key=os.environ.get("GEMINI_API_KEY"),
        system_instructions=system_instructions(),
        response_schema=ReviewResult,
        workspaces=[str(request.workspace)],
        capabilities=CapabilitiesConfig(enable_subagents=False, enabled_tools=list(READ_ONLY_TOOLS)),
        policies=[policy.deny_all(), *(policy.allow(str(tool)) for tool in READ_ONLY_TOOLS)],
        budget_config=BudgetConfig(
            max_total_tokens=request.max_tokens,
            max_model_calls=MAX_MODEL_CALLS,
            max_tool_calls=MAX_TOOL_CALLS,
        ),
    )


def _usage(metadata: UsageMetadata | None) -> ReviewUsage:
    if metadata is None:
        return ReviewUsage()
    return ReviewUsage(
        input_tokens=metadata.prompt_token_count or 0,
        cached_input_tokens=metadata.cached_content_token_count or 0,
        output_tokens=(metadata.candidates_token_count or 0) + (metadata.thoughts_token_count or 0),
    )


def _has_credentials() -> bool:
    vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1")
    return bool(os.environ.get("GEMINI_API_KEY")) or vertex


class AntigravityProvider:
    name = "antigravity"

    def __init__(self, agent_factory: AgentFactory = Agent, timeout_seconds: float = REVIEW_TIMEOUT_SECONDS):
        self._agent_factory = agent_factory
        self._timeout_seconds = timeout_seconds

    def review(self, request: ReviewRequest) -> ProviderOutput:
        if not _has_credentials():
            raise ProviderError("Set GEMINI_API_KEY, or configure Vertex AI credentials")
        model = request.model or DEFAULT_MODEL
        config = build_config(request, model=model)
        # The harness also looks for instruction files in its working directory.
        with contextlib.chdir(request.workspace):
            try:
                return asyncio.run(asyncio.wait_for(self._run(config, request, model), self._timeout_seconds))
            except TimeoutError as error:
                limit = f"{self._timeout_seconds:g}s"
                raise ProviderError(f"The agent exceeded the {limit} time limit", model=model) from error

    async def _run(self, config: LocalAgentConfig, request: ReviewRequest, model: str) -> ProviderOutput:
        async with self._agent_factory(config) as agent:
            response = await agent.chat(build_prompt(request.bundle))
            data = await response.structured_output()
            usage = _usage(response.usage_metadata)
            stop_reason = response.stop_reason

        if stop_reason is not StopReason.UNSPECIFIED:
            raise ProviderError(f"The agent stopped early: {stop_reason.value}", usage=usage, model=model)
        if data is None:
            raise ProviderError("The agent returned no structured output", usage=usage, model=model)
        try:
            result = ReviewResult.model_validate(data)
        except pydantic.ValidationError as error:
            detail = f"{error.error_count()} validation error(s)"
            raise ProviderError(f"The agent returned invalid findings: {detail}", usage=usage, model=model) from error
        return ProviderOutput(result=result, usage=usage, model=model)
