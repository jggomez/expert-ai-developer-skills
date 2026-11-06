"""Today's spending next to the clock: the macOS menu bar, or the Windows notification area.

A tray that cannot start must never stop the app, so ``create_tray`` returns ``None`` on any failure.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Final, Protocol

from agent_meter import i18n

__all__ = ["Tray", "create_tray", "tray_text"]

_LOG = logging.getLogger(__name__)
ICON_SIZE: Final = 64


class Tray(Protocol):
    def update(self, title: str, lines: list[str]) -> None: ...

    def stop(self) -> None: ...


def tray_text(overview: dict[str, Any], language: str) -> tuple[str, list[str]]:
    """The short figure for the bar, then the menu lines. Empty while there is nothing to show."""
    if "today_usd" not in overview:
        return "", []
    words = i18n.UI[language]
    title = i18n.money(Decimal(str(overview["today_usd"])), language)
    lines = [
        f"{words['live.today']}: {title}",
        f"{words['live.month']}: {i18n.money(Decimal(str(overview['month_usd'])), language)}",
    ]
    lines += [
        f"{words['level.' + line['level']]}: {line['label']}, {line['period']}"
        for line in overview.get("budgets", []) if line["level"] != "ok"
    ]
    return title, lines


class _MacTray:
    def __init__(self, show: Callable[[], None], quit_app: Callable[[], None], labels: dict[str, str]) -> None:
        import AppKit
        from PyObjCTools import AppHelper

        self._appkit = AppKit
        self._helper = AppHelper
        self._labels = labels

        class Target(AppKit.NSObject):  # type: ignore[misc]
            def openWindow_(self, _sender: Any) -> None:
                show()

            def quitApp_(self, _sender: Any) -> None:
                quit_app()

        self._target = Target.alloc().init()
        self._item: Any = None
        AppHelper.callAfter(self._create)

    def _create(self) -> None:
        self._item = self._appkit.NSStatusBar.systemStatusBar().statusItemWithLength_(self._appkit.NSVariableStatusItemLength)
        self._item.button().setTitle_("agent-meter")
        self._set_menu([])

    def _set_menu(self, lines: list[str]) -> None:
        menu = self._appkit.NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        for line in lines:
            entry = self._appkit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(line, None, "")
            entry.setEnabled_(False)
            menu.addItem_(entry)
        if lines:
            menu.addItem_(self._appkit.NSMenuItem.separatorItem())
        for label, selector in ((self._labels["show"], "openWindow:"), (self._labels["quit"], "quitApp:")):
            entry = self._appkit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(label, selector, "")
            entry.setTarget_(self._target)
            menu.addItem_(entry)
        self._item.setMenu_(menu)

    def update(self, title: str, lines: list[str]) -> None:
        def apply() -> None:
            if self._item is not None:
                self._item.button().setTitle_(title or "agent-meter")
                self._set_menu(lines)

        self._helper.callAfter(apply)

    def stop(self) -> None:
        if self._item is not None:
            self._appkit.NSStatusBar.systemStatusBar().removeStatusItem_(self._item)


class _WindowsTray:
    def __init__(self, show: Callable[[], None], quit_app: Callable[[], None], labels: dict[str, str]) -> None:
        import pystray
        from PIL import Image, ImageDraw

        self._pystray = pystray
        self._show = show
        self._quit = quit_app
        self._labels = labels
        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((4, 4, ICON_SIZE - 4, ICON_SIZE - 4), fill=(37, 99, 235, 255))
        self._icon = pystray.Icon("agent-meter", image, "agent-meter", self._menu([]))
        self._icon.run_detached()

    def _menu(self, lines: list[str]) -> Any:
        item = self._pystray.MenuItem
        entries = [item(line, None, enabled=False) for line in lines]
        if lines:
            entries.append(self._pystray.Menu.SEPARATOR)
        entries += [item(self._labels["show"], lambda: self._show(), default=True), item(self._labels["quit"], lambda: self._quit())]
        return self._pystray.Menu(*entries)

    def update(self, title: str, lines: list[str]) -> None:
        self._icon.title = (lines[0] if lines else title or "agent-meter")[:127]
        self._icon.menu = self._menu(lines)
        self._icon.update_menu()

    def stop(self) -> None:
        self._icon.stop()


def create_tray(show: Callable[[], None], quit_app: Callable[[], None], language: str) -> Tray | None:
    words = i18n.UI[language]
    labels = {"show": words["tray.show"], "quit": words["tray.quit"]}
    try:
        if sys.platform == "darwin":
            return _MacTray(show, quit_app, labels)
        if sys.platform == "win32":
            return _WindowsTray(show, quit_app, labels)
    except Exception:
        _LOG.exception("the tray icon could not start")
    return None
