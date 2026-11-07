"""Shared test setup."""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest

_POSIX_ONLY = {"st_mode": "Windows has no POSIX file modes", "S_IMODE": "Windows has no POSIX file modes",
               "signal.SIGKILL": "Windows has no SIGKILL"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if os.name != "nt":
        return
    for item in items:
        function = getattr(item, "function", None)
        source = inspect.getsource(function) if function is not None else ""
        for needle, reason in _POSIX_ONLY.items():
            if needle in source:
                item.add_marker(pytest.mark.skip(reason=reason))
                break


@pytest.fixture(autouse=True)
def _isolated_user_home(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point HOME away from the real user so no test writes to the real ~/.agent-meter.

    Tests that need a specific home still set HOME or AGENT_METER_HOME themselves.
    """
    home = tmp_path_factory.mktemp("user-home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("AGENT_METER_HOME", raising=False)
    return home
