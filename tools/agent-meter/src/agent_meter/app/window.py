"""The native window. ``pywebview`` is an optional extra, so it is imported only here."""

from __future__ import annotations

from importlib.resources import as_file, files
from typing import Final

from agent_meter.app.services import AppApi
from agent_meter.app.watcher import TranscriptWatcher, watched_folders
from agent_meter.paths import AppHome

__all__ = ["run_app"]

TITLE: Final = "agent-meter"


def run_app(home: AppHome) -> None:
    import webview

    api = AppApi(home)
    with as_file(files("agent_meter.app") / "assets" / "index.html") as page:
        window = webview.create_window(TITLE, url=page.as_uri(), js_api=api, width=1100, height=760, min_size=(720, 520))
        assert window is not None

        def refresh() -> None:
            api.collect_now()
            window.evaluate_js("window.agentMeterRefresh && window.agentMeterRefresh()")

        watcher = TranscriptWatcher(watched_folders(), refresh)
        watcher.start()
        try:
            webview.start()
        finally:
            watcher.stop()
