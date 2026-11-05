"""Reviewing groups of files, with real processes and with crashes."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pr_reviewer.application.run_review import ReviewSettings
from pr_reviewer.domain.models import DiffBundle, FileDiff, ReviewReport
from pr_reviewer.entrypoints.parallel_review import (
    ShardJob,
    review_shards,
    share_budget,
)


def job(tmp_path: Path, path: str, budget: str = "1.00") -> ShardJob:
    shard = DiffBundle(base="a" * 40, head="b" * 40, files=[FileDiff(path=path, patch="+a\n")])
    return ShardJob(shard, ReviewSettings(provider="unknown", budget_usd=budget), tmp_path, None)


def test_real_processes_return_a_report_for_each_group(tmp_path: Path):
    # Arrange: an unknown provider fails inside the worker, so no AI is needed to cross the process boundary.
    jobs = [job(tmp_path, "a.py"), job(tmp_path, "b.py")]

    # Act
    reports = review_shards(jobs)

    # Assert
    assert [report.status for report in reports] == ["failed", "failed"]
    assert all("Unknown provider" in report.error for report in reports)


def test_a_crashed_group_is_reported_and_the_other_survives(tmp_path: Path):
    # Arrange
    def worker(item: ShardJob) -> ReviewReport:
        if item.shard.files[0].path == "bad.py":
            raise RuntimeError("worker died")
        return ReviewReport(status="ok", provider="unknown")

    # Act
    reports = review_shards(
        [job(tmp_path, "good.py"), job(tmp_path, "bad.py")],
        worker=worker,
        executor=lambda workers: ThreadPoolExecutor(workers),
    )

    # Assert
    assert [report.status for report in reports] == ["ok", "failed"]
    assert "worker died" in reports[1].error


def test_each_group_receives_a_share_of_the_dollar_budget(tmp_path: Path):
    # Arrange
    seen: list[str] = []

    def worker(item: ShardJob) -> ReviewReport:
        seen.append(item.settings.budget_usd)
        return ReviewReport(status="ok", provider="unknown")

    # Act
    review_shards(
        [job(tmp_path, "a.py"), job(tmp_path, "b.py"), job(tmp_path, "c.py")],
        worker=worker,
        executor=lambda workers: ThreadPoolExecutor(workers),
    )

    # Assert
    assert seen == ["0.33", "0.33", "0.33"]


@pytest.mark.parametrize(("budget", "shards", "expected"), [("1.00", 4, "0.25"), ("0.10", 3, "0.03")])
def test_budget_shares_never_add_up_to_more_than_the_limit(budget: str, shards: int, expected: str):
    # Act / Assert
    assert share_budget(budget, shards) == expected


def test_groups_run_two_at_a_time_to_respect_the_model_quota(tmp_path: Path):
    # Arrange
    workers: list[int] = []

    def executor(count: int) -> ThreadPoolExecutor:
        workers.append(count)
        return ThreadPoolExecutor(count)

    # Act
    review_shards(
        [job(tmp_path, f"{name}.py") for name in "abcd"],
        worker=lambda item: ReviewReport(status="ok", provider="unknown"),
        executor=executor,
    )

    # Assert
    assert workers == [2]
