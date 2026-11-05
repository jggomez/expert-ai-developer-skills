"""Look for a newer release. Runs only when the user asks, and installs nothing."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Final

__all__ = ["RELEASES_PAGE", "check_for_update", "newest_release"]

RELEASES_API: Final = "https://api.github.com/repos/jggomez/expert-ai-developer-skills/releases?per_page=50"
RELEASES_PAGE: Final = "https://github.com/jggomez/expert-ai-developer-skills/releases/"
TAG_PREFIX: Final = "agent-meter-v"
TIMEOUT_S: Final = 10
_VERSION: Final = re.compile(r"\d+(\.\d+)*\Z")
_LOG = logging.getLogger(__name__)


def _parts(version: str) -> tuple[int, ...] | None:
    return tuple(int(part) for part in version.split(".")) if _VERSION.match(version) else None


def newest_release(releases: list[dict[str, Any]]) -> dict[str, str] | None:
    """Other tools in this repository publish releases too, so only this tool's tags count."""
    found: list[tuple[tuple[int, ...], dict[str, str]]] = []
    for release in releases:
        tag = str(release.get("tag_name", ""))
        url = str(release.get("html_url", ""))
        version = _parts(tag.removeprefix(TAG_PREFIX))
        if tag.startswith(TAG_PREFIX) and version and url.startswith(RELEASES_PAGE) \
                and not release.get("draft") and not release.get("prerelease"):
            found.append((version, {"version": tag.removeprefix(TAG_PREFIX), "url": url}))
    return max(found, key=lambda item: item[0])[1] if found else None


def _fetch() -> list[dict[str, Any]]:
    request = urllib.request.Request(RELEASES_API, headers={"User-Agent": "agent-meter", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:  # fixed https address
        document = json.load(response)
    return document if isinstance(document, list) else []


def check_for_update(current: str, fetch: Callable[[], list[dict[str, Any]]] = _fetch) -> dict[str, Any]:
    try:
        latest = newest_release(fetch())
    except (OSError, ValueError, urllib.error.URLError) as exc:
        _LOG.info("update check failed: %s", type(exc).__name__)
        return {"ok": False}
    installed = _parts(current.split("+", 1)[0])
    if latest is None or installed is None:
        return {"ok": True, "newer": False, "current": current}
    newer = (_parts(latest["version"]) or ()) > installed
    return {"ok": True, "newer": newer, "current": current, "latest": latest["version"], "url": latest["url"]}
