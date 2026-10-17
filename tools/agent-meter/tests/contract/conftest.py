"""Contract-test configuration: registers the ``contract`` marker and forbids network access."""

from __future__ import annotations

import socket
from collections.abc import Iterator

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "contract: host format contract tests (L2)")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def refuse(*_args: object, **_kwargs: object) -> socket.socket:
        raise RuntimeError("network access is not allowed in contract tests")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    yield
