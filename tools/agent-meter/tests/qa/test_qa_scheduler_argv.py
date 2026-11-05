"""DEF-QA1-01 regression: the command line the scheduler installs must actually parse and run.

``scheduler._base.COLLECT_ARGS`` = ``("collect", "--scheduled", "--quiet")`` is written verbatim into
the launchd plist ``ProgramArguments``, the systemd ``ExecStart`` and the crontab line. ``--quiet``
used to be a top-level option only, so argparse exited 2 on every scheduled cycle (PF-05, scenario
3). ``collect`` now accepts it too, which also repairs jobs installed by older versions.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_meter.scheduler._base import scheduled_argv
from tests.qa.conftest import QAWorld, agent_meter_argv


def test_scheduler_installed_argv_runs_and_collects(qa_world: QAWorld) -> None:
    exe = agent_meter_argv()
    argv = scheduled_argv(Path(exe[-1]) if len(exe) == 1 else Path("/unused"))
    command = [*exe, *argv[1:]]

    done = subprocess.run(command, capture_output=True, env=qa_world.env(), timeout=120, check=False)

    assert done.returncode == 0, done.stderr.decode()
    assert done.stdout == b""
    assert qa_world.meter.db.exists()


def test_parseable_order_works_as_reference(qa_world: QAWorld) -> None:
    done = subprocess.run([*agent_meter_argv(), "--quiet", "collect", "--scheduled"], capture_output=True,
                          env=qa_world.env(), timeout=120, check=False)

    assert done.returncode == 0, done.stderr.decode()
    assert done.stdout == b""
    assert qa_world.meter.db.exists()
