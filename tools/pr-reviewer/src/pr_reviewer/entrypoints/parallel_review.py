"""Review each group in its own process.

Processes, not threads: the agent runs from its workspace directory and watches
the root logger for overloads, and both are global to a process.
"""

from __future__ import annotations

import logging
import multiprocessing
from collections.abc import Callable
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass, replace
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

from pr_reviewer.application.run_review import ReviewSettings, run_review
from pr_reviewer.domain.models import DiffBundle, ReviewReport
from pr_reviewer.entrypoints.composition import load_provider


@dataclass(frozen=True)
class ShardJob:
    shard: DiffBundle
    settings: ReviewSettings
    workspace: Path
    rubric: str | None


def review_shard(job: ShardJob) -> ReviewReport:
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
    return run_review(
        job.shard,
        job.settings,
        load_provider=lambda: load_provider(job.settings.provider),
        build_workspace=lambda: job.workspace,
        load_rubric=lambda: job.rubric,
    )


def share_budget(budget_usd: str, shards: int) -> str:
    """The dollar limit covers the whole review, so each group gets its share."""
    return str((Decimal(budget_usd) / shards).quantize(Decimal("0.01"), rounding=ROUND_DOWN))


# Two at a time: more than this exhausted the per-minute quota of a Gemini key in a real run.
MAX_PARALLEL_GROUPS = 2


def _process_pool(workers: int) -> Executor:
    # Spawn, because the agent SDK starts threads and subprocesses that do not survive a fork.
    return ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))


def review_shards(
    jobs: list[ShardJob],
    *,
    worker: Callable[[ShardJob], ReviewReport] = review_shard,
    executor: Callable[[int], Executor] = _process_pool,
) -> list[ReviewReport]:
    """A group that crashes becomes a failed report, so the other groups still count."""
    jobs = [replace(job, settings=replace(job.settings, budget_usd=share_budget(job.settings.budget_usd, len(jobs)))) for job in jobs]
    reports = []
    with executor(min(len(jobs), MAX_PARALLEL_GROUPS)) as pool:
        futures = [pool.submit(worker, job) for job in jobs]
        for job, future in zip(jobs, futures, strict=True):
            try:
                reports.append(future.result())
            except Exception as error:
                logging.getLogger(__name__).exception("A review group crashed")
                reports.append(
                    ReviewReport(status="failed", provider=job.settings.provider, error=f"{type(error).__name__}: {error}"[:300])
                )
    return reports
