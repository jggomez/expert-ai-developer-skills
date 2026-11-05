"""The native window. ``pywebview`` is an optional extra, so it is imported only here."""

from __future__ import annotations

from importlib.resources import as_file, files
from typing import Final

from agent_meter.app.services import AppApi
from agent_meter.app.tray import create_tray, tray_text
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

        tray = None

        def refresh() -> None:
            api.collect_now()
            api.run_rules()
            window.evaluate_js("window.agentMeterRefresh && window.agentMeterRefresh()")
            if tray is not None:
                tray.update(*tray_text(api.overview(), api.texts()["language"]))

        def bring_back() -> None:
            window.show()
            window.restore()

        watcher = TranscriptWatcher(watched_folders(), refresh)

        def catch_up() -> None:
            """Sessions that ran while the app was closed, and everything on the very first start."""
            nonlocal tray
            tray = create_tray(bring_back, window.destroy, api.texts()["language"])
            refresh()
            watcher.start()

        try:
            webview.start(catch_up)
        finally:
            watcher.stop()
            if tray is not None:
                tray.stop()
