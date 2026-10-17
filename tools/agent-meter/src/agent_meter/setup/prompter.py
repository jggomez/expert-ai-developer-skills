"""Injectable question/answer layer for the setup wizard.

``ConsolePrompter`` asks on a terminal (blank answer = default). ``AutoPrompter`` implements
``--yes``: it answers every question with its default and echoes the decision, so consent
questions default to yes and privacy questions keep their conservative defaults.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TextIO

__all__ = ["AutoPrompter", "ConsolePrompter", "Prompter", "WizardAborted"]


class WizardAborted(Exception):
    """The user closed the input stream (Ctrl-D) or interrupted the wizard."""


class Prompter(Protocol):
    @property
    def interactive(self) -> bool: ...

    def info(self, text: str) -> None: ...

    def confirm(self, question: str, *, default: bool) -> bool: ...

    def choose(self, question: str, options: Sequence[str], *, default: str) -> str: ...

    def ask(self, question: str, *, default: str = "") -> str: ...


class ConsolePrompter:
    def __init__(self, stdin: TextIO, stdout: TextIO) -> None:
        self._stdin = stdin
        self._stdout = stdout

    @property
    def interactive(self) -> bool:
        return True

    def info(self, text: str) -> None:
        self._stdout.write(f"{text}\n")
        self._stdout.flush()

    def _read(self, prompt: str) -> str:
        self._stdout.write(prompt)
        self._stdout.flush()
        line = self._stdin.readline()
        if not line:
            raise WizardAborted("setup cancelled (end of input)")
        return line.strip()

    def confirm(self, question: str, *, default: bool) -> bool:
        hint = "[Y/n]" if default else "[y/N]"
        while True:
            answer = self._read(f"{question} {hint} ").lower()
            if not answer:
                return default
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            self.info("please answer y or n")

    def choose(self, question: str, options: Sequence[str], *, default: str) -> str:
        while True:
            answer = self._read(f"{question} ({'/'.join(options)}) [{default}] ")
            if not answer:
                return default
            if answer in options:
                return answer
            self.info(f"choose one of: {', '.join(options)}")

    def ask(self, question: str, *, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        return self._read(f"{question}{suffix} ") or default


class AutoPrompter:
    def __init__(self, stdout: TextIO) -> None:
        self._stdout = stdout

    @property
    def interactive(self) -> bool:
        return False

    def info(self, text: str) -> None:
        self._stdout.write(f"{text}\n")
        self._stdout.flush()

    def confirm(self, question: str, *, default: bool) -> bool:
        self.info(f"{question} {'yes' if default else 'no'} (--yes)")
        return default

    def choose(self, question: str, options: Sequence[str], *, default: str) -> str:
        self.info(f"{question} {default} (--yes)")
        return default

    def ask(self, question: str, *, default: str = "") -> str:
        self.info(f"{question} {default} (--yes)")
        return default
