"""Shared test setup."""

from __future__ import annotations

import inspect
import os

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
