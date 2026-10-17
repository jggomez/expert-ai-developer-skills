"""agent-meter: local-first token, cost and latency metrics for AI coding agents."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__: str = version("agent-meter")
except PackageNotFoundError:  # running from a source checkout without installation
    __version__ = "0.0.0+source"
