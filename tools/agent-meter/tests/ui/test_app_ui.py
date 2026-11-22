"""Desktop app UI in a real browser: app.js and index.html driven by the real Python ``AppApi``.

pywebview is replaced by a bridge: every ``window.pywebview.api.<name>(...)`` call in the page runs the same
method on an ``AppApi`` over a small test store, so the JavaScript sees exactly what the desktop app sends.
Needs the ``ui`` extra and Chromium: ``uv sync --extra dev --extra ui && uv run playwright install chromium``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

sync_api = pytest.importorskip("playwright.sync_api", reason="install the ui extra to run the app UI tests")

from agent_meter.app.services import AppApi  # noqa: E402
from agent_meter.paths import AppHome  # noqa: E402
from agent_meter.pricing import load_pricing  # noqa: E402
from agent_meter.project_resolver import ProjectsConfig  # noqa: E402
from agent_meter.store import Store  # noqa: E402
from tests.fixtures.records import make_batch, make_project, ts  # noqa: E402

ASSETS = Path(__file__).resolve().parents[2] / "src" / "agent_meter" / "app" / "assets"
NOW = ts(600) + timedelta(minutes=5)
# Playwright finds its browsers under the real home; the fixtures point HOME at a temp folder.
REAL_HOME = os.environ.get("HOME", "")
TABS = ("live", "history", "insights", "changes", "projects", "settings")

BRIDGE = """
window.pywebview = {
  api: new Proxy({}, {
    get: (_target, name) => async (...args) => JSON.parse(await window.__agentMeterApi(String(name), JSON.stringify(args))),
  }),
};
"""


@pytest.fixture()
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppApi:
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    home = AppHome.resolve(str(tmp_path / "meter"))
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as store:
        store.migrate()
        store.load_reference_data(
            pricing=load_pricing(None), host_defaults={},
            projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={}),
            project_refs=[make_project()], settings={"timezone": "UTC"},
        )
        store.apply_batches([make_batch()])
    return AppApi(home, clock=lambda: NOW)


@pytest.fixture()
def page(api: AppApi, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    def call(name: str, args_json: str) -> str:
        if name.startswith("_") or not callable(getattr(api, name, None)):
            raise AttributeError(f"AppApi has no public method {name!r}")
        return json.dumps(getattr(api, name)(*json.loads(args_json)))

    with monkeypatch.context() as patch:
        patch.setenv("HOME", REAL_HOME)
        manager = sync_api.sync_playwright()
        playwright = manager.start()
    try:
        try:
            browser = playwright.chromium.launch()
        except sync_api.Error as exc:  # browser binary missing
            pytest.skip(f"Chromium is not installed for Playwright: {exc.message.splitlines()[0]}")
        context = browser.new_context(viewport={"width": 1100, "height": 800})
        context.expose_function("__agentMeterApi", call)
        context.add_init_script(BRIDGE)
        tab = context.new_page()
        errors: list[str] = []
        tab.on("pageerror", lambda exc: errors.append(str(exc)))
        tab.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        tab.errors = errors
        tab.goto((ASSETS / "index.html").as_uri())
        yield tab
        browser.close()
    finally:
        playwright.stop()


def test_live_screen_shows_spend_and_the_running_session(page: Any) -> None:
    # Act: the page starts by itself once the bridge is in place
    page.wait_for_function("document.getElementById('today').textContent.includes('$')")
    # Assert
    assert page.locator("#sessions tr").count() == 1
    assert page.locator("#sessions-table").is_visible()
    assert page.locator("#status").inner_text() != "Loading…"
    assert page.errors == []


@pytest.mark.parametrize("tab", TABS)
def test_every_screen_opens_without_errors(page: Any, tab: str) -> None:
    # Arrange
    page.wait_for_function("document.getElementById('today').textContent !== '—'")
    # Act
    page.click(f"nav button[data-tab='{tab}']")
    page.wait_for_timeout(300)
    # Assert: only the chosen screen shows, it is marked current, and nothing failed
    assert page.locator(f"main > section#{tab}").is_visible()
    assert page.locator("main > section:visible").count() == 1
    assert page.locator(f"nav button[data-tab='{tab}']").get_attribute("aria-current") == "page"
    assert "Error" not in page.locator("#status").inner_text()
    assert page.errors == []


def test_history_lists_the_project_and_its_spend(page: Any) -> None:
    page.click("nav button[data-tab='history']")
    page.wait_for_function("document.getElementById('history-cost').textContent.includes('$')")

    assert page.locator("#history-projects tr").count() >= 1
    assert page.locator("#history-calls").inner_text().strip() not in ("", "—", "0")
    assert page.errors == []


def test_switching_to_spanish_translates_the_app_and_is_saved(page: Any, api: AppApi) -> None:
    page.wait_for_function("document.getElementById('today').textContent !== '—'")

    page.select_option("#language", "es")
    page.wait_for_function("document.querySelector(\"nav button[data-tab='live']\").textContent === 'En vivo'")

    assert page.locator("nav button[data-tab='settings']").inner_text() == "Ajustes"
    assert api.texts()["language"] == "es"
    assert page.errors == []
