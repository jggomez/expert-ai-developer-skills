"""Entry point of the packaged app, which has no terminal to print errors to."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import Final

from agent_meter.app.services import AppApi
from agent_meter.paths import AppHome

__all__ = ["SELF_TEST_FLAG", "main", "self_test"]

SELF_TEST_FLAG: Final = "--self-test"
LOG_NAME: Final = "desktop.log"
LOG_BYTES: Final = 1_000_000
_LOG = logging.getLogger(__name__)


def self_test(home: AppHome) -> None:
    """Every read the screens make, so the build fails here and not on someone's machine."""
    api = AppApi(home)
    result = api.collect_now()
    if result["status"] != "ok":
        raise RuntimeError(f"collect failed: {result}")
    for read in (api.overview, api.history, api.insights, api.settings, api.actions, api.changes, api.texts):
        read()


def main() -> int:
    home = AppHome.resolve()
    home.ensure_dir(home.logs_dir)
    handler = logging.handlers.RotatingFileHandler(home.logs_dir / LOG_NAME, maxBytes=LOG_BYTES, backupCount=1, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        if SELF_TEST_FLAG in sys.argv:
            self_test(home)
            import webview  # noqa: F401  # the bundled window layer must load too

            return 0
        from agent_meter.app.window import run_app

        run_app(home)
    except Exception:
        _LOG.exception("the desktop app stopped")
        return 1
    return 0
