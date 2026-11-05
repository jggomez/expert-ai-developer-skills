"""Review with the Google Antigravity SDK.

The agent can only read the clean workspace. It has no shell, network, write
or subagent tools, so text in the diff cannot make it act on the outside world.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

import pydantic
from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig, LocalAgentConfig
from google.antigravity.hooks import policy
from google.antigravity.types import BudgetConfig, StopReason, UsageMetadata

from pr_reviewer.application.ports import ProviderError, ProviderOutput, ReviewRequest
from pr_reviewer.application.prompt import build_prompt, system_instructions
from pr_reviewer.domain.models import ReviewResult, ReviewUsage

DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_FALLBACK_MODEL = "gemini-3.8-flash"
MAX_MODEL_CALLS = 20
MAX_TOOL_CALLS = 40
REVIEW_TIMEOUT_SECONDS = 600.0
RETRY_DELAYS_SECONDS = (10.0, 30.0)
CANCEL_GRACE_SECONDS = 30.0
_SYSTEM_ERROR = re.compile(r"^System step error \(HTTP (\d+)\)")
_OVERLOAD_CODES = {"429", "500", "502", "503", "504"}

READ_ONLY_TOOLS = (
    BuiltinTools.VIEW_FILE,
    BuiltinTools.LIST_DIR,
    BuiltinTools.SEARCH_DIR,
    BuiltinTools.FIND_FILE,
    BuiltinTools.FINISH,
)

AgentFactory = Callable[[LocalAgentConfig], Any]
Sleep = Callable[[float], Awaitable[None]]

logger = logging.getLogger(__name__)


def build_config(request: ReviewRequest, *, model: str) -> LocalAgentConfig:
    """Configuration of a read-only agent with a hard token budget."""
    return LocalAgentConfig(
        model=model,
        api_key=os.environ.get("GEMINI_API_KEY"),
        system_instructions=system_instructions(request.rubric),
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


def is_overload(record: logging.LogRecord) -> bool:
    match = _SYSTEM_ERROR.match(record.getMessage())
    return match is not None and match[1] in _OVERLOAD_CODES


class _OverloadWatch(logging.Handler):
    """Signal a model overload.

    After a 503 the SDK logs a warning and the turn never ends, so this log line
    is the only sign that the attempt will not finish.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, overloaded: asyncio.Event, errors: list[str]):
        super().__init__(level=logging.WARNING)
        self._loop = loop
        self._overloaded = overloaded
        self._errors = errors

    def emit(self, record: logging.LogRecord) -> None:
        if _SYSTEM_ERROR.match(record.getMessage()):
            self._errors.append(record.getMessage())
        if is_overload(record):
            self._loop.call_soon_threadsafe(self._overloaded.set)


def _add_usage(total: ReviewUsage, spent: ReviewUsage) -> ReviewUsage:
    return ReviewUsage(
        input_tokens=total.input_tokens + spent.input_tokens,
        cached_input_tokens=total.cached_input_tokens + spent.cached_input_tokens,
        output_tokens=total.output_tokens + spent.output_tokens,
    )


def _has_credentials() -> bool:
    vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1")
    return bool(os.environ.get("GEMINI_API_KEY")) or vertex


class AntigravityProvider:
    name = "antigravity"

    def __init__(
        self,
        agent_factory: AgentFactory = Agent,
        timeout_seconds: float = REVIEW_TIMEOUT_SECONDS,
        sleep: Sleep = asyncio.sleep,
    ):
        self._agent_factory = agent_factory
        self._timeout_seconds = timeout_seconds
        self._sleep = sleep

    def review(self, request: ReviewRequest) -> ProviderOutput:
        if not _has_credentials():
            raise ProviderError("Set GEMINI_API_KEY, or configure Vertex AI credentials")
        model = request.model or DEFAULT_MODEL
        # The harness also looks for instruction files in its working directory.
        with contextlib.chdir(request.workspace):
            try:
                return asyncio.run(asyncio.wait_for(self._run(request, model), self._timeout_seconds))
            except TimeoutError as error:
                limit = f"{self._timeout_seconds:g}s"
                raise ProviderError(f"The agent exceeded the {limit} time limit", model=model) from error

    async def _chat(self, config: LocalAgentConfig, request: ReviewRequest) -> tuple[Any, ReviewUsage, StopReason]:
        async with self._agent_factory(config) as agent:
            response = await agent.chat(build_prompt(request.bundle))
            data = await response.structured_output()
            return data, _usage(response.usage_metadata), response.stop_reason

    async def _attempt(
        self, config: LocalAgentConfig, request: ReviewRequest, errors: list[str]
    ) -> tuple[Any, ReviewUsage, StopReason] | None:
        """Run one agent, or return None as soon as the model reports it is overloaded."""
        overloaded = asyncio.Event()
        watch = _OverloadWatch(asyncio.get_running_loop(), overloaded, errors)
        root = logging.getLogger()
        root.addHandler(watch)
        chat = asyncio.create_task(self._chat(config, request))
        signal = asyncio.create_task(overloaded.wait())
        try:
            await asyncio.wait({chat, signal}, return_when=asyncio.FIRST_COMPLETED)
            if chat.done():
                return chat.result()
            chat.cancel()
            await asyncio.wait({chat}, timeout=CANCEL_GRACE_SECONDS)
            return None
        finally:
            root.removeHandler(watch)
            signal.cancel()
            chat.cancel()

    async def _run(self, request: ReviewRequest, model: str) -> ProviderOutput:
        usage = ReviewUsage()
        errors: list[str] = []
        models = (model, model, request.fallback_model or DEFAULT_FALLBACK_MODEL)
        for attempt, current in enumerate(models):
            if attempt:
                delay = RETRY_DELAYS_SECONDS[attempt - 1]
                logger.warning("No answer from %s. Retrying with %s in %gs", model, current, delay)
                await self._sleep(delay)
            model = current
            outcome = await self._attempt(build_config(request, model=model), request, errors)
            if outcome is None:
                continue
            data, spent, stop_reason = outcome
            usage = _add_usage(usage, spent)
            if stop_reason is not StopReason.UNSPECIFIED:
                raise ProviderError(f"The agent stopped early: {stop_reason.value}", usage=usage, model=model)
            if data is not None:
                break
        else:
            detail = errors[-1] if errors else "The model may be overloaded"
            message = f"No structured output after {len(models)} attempts. {detail}"
            raise ProviderError(message, usage=usage, model=model)
        try:
            result = ReviewResult.model_validate(data)
        except pydantic.ValidationError as error:
            detail = f"{error.error_count()} validation error(s)"
            raise ProviderError(f"The agent returned invalid findings: {detail}", usage=usage, model=model) from error
        return ProviderOutput(result=result, usage=usage, model=model)
