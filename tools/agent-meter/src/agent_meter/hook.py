"""Host hook entry points (ADR §3.10, BR-20, invariant I-4).

``hook_main`` is the fast path the hosts call. It imports the standard library only
(plus ``paths``/``model``/``readers.base``, which are stdlib-only), never ``duckdb``:

* reads at most 64 KiB of stdin and keeps ONLY allowlisted keys;
* spawns ``agent-meter hook-worker`` detached (new session, stdio to ``/dev/null``,
  arguments via argv, never a shell);
* writes nothing to stdout for Claude Code and exactly ``{}`` for Antigravity;
* returns 0 on every path, including bad input, exceptions and the watchdog timeout.

``worker_main`` runs in the detached process: it ingests that one unit, writes
``last-summary.txt`` (never a task label) and notifies according to the policy.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import re
import signal
import subprocess
import sys
import threading
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import FrameType
from typing import BinaryIO, Final, Literal, TextIO

from agent_meter.config import Config, ConfigError, load_config
from agent_meter.model import Host
from agent_meter.paths import AppHome, atomic_write_text
from agent_meter.readers.base import host_from_transcript_path

__all__ = [
    "MAX_STDIN_BYTES",
    "WATCHDOG_S",
    "WORKER_LOCK_TIMEOUT_S",
    "HookPayload",
    "hook_main",
    "parse_payload",
    "worker_main",
]

_LOG = logging.getLogger(__name__)

MAX_STDIN_BYTES: Final = 64 * 1024
WATCHDOG_S: Final = 2.0
WORKER_LOCK_TIMEOUT_S: float = 3.0
NOTIFIED_KEEP: Final = 500
Event = Literal["session-end", "task-end"]
_EVENTS: Final = ("session-end", "task-end")
_SAFE_ID: Final = re.compile(r"^[A-Za-z0-9_.:@-]{1,200}$")
_SAFE_WORD: Final = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_ANTIGRAVITY_HOSTS: Final = (Host.ANTIGRAVITY_CLI, Host.ANTIGRAVITY_IDE, Host.ANTIGRAVITY_APP)


@dataclass(frozen=True, slots=True)
class HookPayload:
    host: Host | None
    event: Event
    session_id: str | None
    transcript_path: str | None
    fully_idle: bool | None
    termination_reason: str | None
    reason: str | None


class _HookTimeout(Exception):
    """Raised by the watchdog when the fast path exceeds its budget."""


# ----------------------------------------------------------------------------- payload


def _text(data: dict[str, object], key: str, pattern: re.Pattern[str]) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and pattern.match(value) else None


def _flag_host(host_flag: str) -> Host | None:
    try:
        return Host(host_flag)
    except ValueError:
        return None


def parse_payload(raw: bytes, *, host_flag: str, event: str) -> HookPayload:
    """Extract ONLY the allowlisted keys (ADR §3.10); anything else is discarded unread."""
    try:
        decoded = json.loads(raw[:MAX_STDIN_BYTES].decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        decoded = None
    data: dict[str, object] = decoded if isinstance(decoded, dict) else {}
    chosen_event: Event = "session-end" if event == "session-end" else "task-end"
    if host_flag.startswith("antigravity"):
        transcript = data.get("transcriptPath")
        transcript_path = transcript if isinstance(transcript, str) and len(transcript) < 4096 else None
        detected = host_from_transcript_path(transcript_path) if transcript_path else None
        host = detected if detected in _ANTIGRAVITY_HOSTS else _flag_host(host_flag)
        idle = data.get("fullyIdle")
        return HookPayload(
            host=host,
            event=chosen_event,
            session_id=_text(data, "conversationId", _SAFE_ID),
            transcript_path=transcript_path,
            fully_idle=idle if isinstance(idle, bool) else None,
            termination_reason=_text(data, "terminationReason", _SAFE_WORD),
            reason=None,
        )
    transcript = data.get("transcript_path")
    return HookPayload(
        host=_flag_host(host_flag),
        event=chosen_event,
        session_id=_text(data, "session_id", _SAFE_ID),
        transcript_path=transcript if isinstance(transcript, str) and len(transcript) < 4096 else None,
        fully_idle=None,
        termination_reason=None,
        reason=_text(data, "reason", _SAFE_WORD),
    )


# ----------------------------------------------------------------------------- fast path


def _parse_hook_args(argv: Sequence[str]) -> tuple[str, str, float]:
    """Tolerant manual parse: unknown or malformed flags fall back to defaults (never exits)."""
    host_flag, event, timeout = "", "task-end", WATCHDOG_S
    items = list(argv)
    for index, item in enumerate(items):
        value = items[index + 1] if index + 1 < len(items) else None
        if value is None:
            continue
        if item == "--host":
            host_flag = value
        elif item == "--event" and value in _EVENTS:
            event = value
        elif item == "--timeout":
            try:
                parsed = float(value)
            except ValueError:
                continue
            if 0 < parsed <= 30:
                timeout = parsed
    return host_flag, event, timeout


@contextlib.contextmanager
def _watchdog(seconds: float) -> Iterator[None]:
    usable = hasattr(signal, "setitimer") and threading.current_thread() is threading.main_thread()
    if not usable:
        yield
        return

    def _expire(_signum: int, _frame: FrameType | None) -> None:
        raise _HookTimeout

    previous = signal.signal(signal.SIGALRM, _expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _worker_argv(payload: HookPayload, host_flag: str) -> list[str]:
    assert payload.session_id is not None
    host = payload.host.value if payload.host is not None else host_flag
    argv = [
        sys.executable, "-m", "agent_meter", "hook-worker",
        "--host", host, "--event", payload.event, "--session-id", payload.session_id,
    ]
    if payload.fully_idle is not None:
        argv += ["--fully-idle", "true" if payload.fully_idle else "false"]
    if payload.termination_reason:
        argv += ["--termination-reason", payload.termination_reason]
    if payload.reason:
        argv += ["--reason", payload.reason]
    return argv


def _spawn_worker(argv: Sequence[str]) -> None:
    subprocess.Popen(
        list(argv),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def _log_failure(stage: str, exc: BaseException) -> None:
    """Record only the exception class (never its message, which could carry paths)."""
    try:
        home = AppHome.resolve()
        logs = home.ensure_dir(home.logs_dir)
        with open(logs / "hook.log", "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now(UTC).isoformat()} {stage} {type(exc).__name__}\n")
    except OSError:
        _LOG.debug("hook log unavailable")


def hook_main(argv: Sequence[str], stdin: BinaryIO, stdout: TextIO) -> int:
    """Host hook fast path; ALWAYS returns 0 (BR-20, I-4)."""
    host_flag, event, timeout = _parse_hook_args(argv)
    try:
        with _watchdog(timeout):
            raw = stdin.read(MAX_STDIN_BYTES)
            payload = parse_payload(raw if isinstance(raw, bytes) else b"", host_flag=host_flag, event=event)
            if payload.session_id is not None and (payload.host is not None or host_flag.startswith("antigravity")):
                _spawn_worker(_worker_argv(payload, host_flag))
    except _HookTimeout as exc:
        _log_failure("timeout", exc)
    except Exception as exc:  # the host must never see a failure (BR-20)
        _log_failure("error", exc)
    finally:
        if host_flag.startswith("antigravity"):
            with contextlib.suppress(OSError, ValueError):
                stdout.write("{}\n")
                stdout.flush()
    return 0


# ----------------------------------------------------------------------------- worker


def _worker_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-meter hook-worker", add_help=False, exit_on_error=False)
    parser.add_argument("--host", required=True)
    parser.add_argument("--event", required=True, choices=_EVENTS)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--fully-idle", choices=("true", "false"))
    parser.add_argument("--termination-reason")
    parser.add_argument("--reason")
    return parser


def _candidate_hosts(host: str) -> tuple[Host, ...]:
    flag = _flag_host(host)
    if flag is not None:
        return (flag,)
    return _ANTIGRAVITY_HOSTS if host.startswith("antigravity") else ()


def _load_notified(home: AppHome) -> list[str]:
    try:
        data = json.loads(home.notified.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [k for k in data if isinstance(k, str)] if isinstance(data, list) else []


def _mark_notified(home: AppHome, key: str) -> bool:
    """``True`` if ``key`` was not notified before (``state/notified.json`` dedupe)."""
    seen = _load_notified(home)
    if key in seen:
        return False
    seen.append(key)
    atomic_write_text(home.notified, json.dumps(seen[-NOTIFIED_KEEP:]))
    return True


@dataclass(frozen=True, slots=True)
class _Located:
    host: Host
    unit_id: str
    is_child: bool


def _locate(cfg: Config, hosts: Sequence[Host], session_id: str) -> _Located | None:
    from agent_meter.collector import reader_roots
    from agent_meter.readers.base import available_readers

    for reader in available_readers(reader_roots(cfg)):
        if reader.host not in hosts:
            continue
        unit = reader.find_unit(session_id)
        if unit is not None:
            return _Located(reader.host, unit.unit_id, unit.unit_id != session_id)
    return None


def worker_main(argv: Sequence[str]) -> int:
    """Detached worker: ingest one unit, write ``last-summary.txt``, notify per policy."""
    try:
        args = _worker_parser().parse_args(list(argv))
    except (argparse.ArgumentError, SystemExit):
        return 2
    home = AppHome.resolve()
    try:
        cfg = load_config(home)
    except ConfigError as exc:
        _log_failure("worker-config", exc)
        return 1
    located = _locate(cfg, _candidate_hosts(args.host), args.session_id)
    if located is None:
        return 0
    try:
        return _run_worker(home, cfg, args, located)
    except Exception as exc:  # detached process: record the class name, never crash noisily
        _log_failure("worker", exc)
        return 1


def _run_worker(home: AppHome, cfg: Config, args: argparse.Namespace, located: _Located) -> int:
    from agent_meter import notify as notifier
    from agent_meter.collector import collect
    from agent_meter.locking import LockTimeout
    from agent_meter.store import Store
    from agent_meter.summary import (
        SummaryError,
        render_session_summary,
        session_summary,
        summary_from_snapshot,
        task_rollups,
    )

    antigravity = located.host in _ANTIGRAVITY_HOSTS
    fully_idle = {"true": True, "false": False}.get(args.fully_idle or "")
    signal_kind: Literal["session-end", "task-end"] | None = None
    if args.event == "session-end":
        signal_kind = "session-end"
    elif not located.is_child and (not antigravity or fully_idle is True):
        signal_kind = "task-end"
    now = datetime.now(UTC)
    result = collect(
        home, cfg, only=(located.host, args.session_id), lock_timeout_s=WORKER_LOCK_TIMEOUT_S, now=now,
        signal=signal_kind,
    )
    if result.status == "locked":
        text = summary_from_snapshot(home.snapshot, located.host, located.unit_id, cfg)
        atomic_write_text(home.last_summary, text + "\n")
        return 0
    try:
        with Store.open(home, read_only=True, lock_timeout_s=WORKER_LOCK_TIMEOUT_S) as store:
            summary = session_summary(store, located.host, located.unit_id, now=now)
            latest = task_rollups(store, session_id=located.unit_id, last=1)
    except (SummaryError, LockTimeout):
        return 0
    text = render_session_summary(summary, cfg)
    atomic_write_text(home.last_summary, text + "\n")
    quiet = located.is_child or (antigravity and fully_idle is False) or cfg.notify == "off"
    if quiet:
        return 0
    task = latest[0] if latest else None
    if args.event == "session-end":
        wanted = cfg.notify in ("auto", "session")
    else:
        long_enough = task is not None and task.wall_clock_ms >= cfg.notify_min_task_s * 1000
        wanted = cfg.notify in ("auto", "long-tasks") and long_enough
    task_key = task.task_id if task is not None else "-"
    if wanted and _mark_notified(home, f"{located.host.value}:{located.unit_id}:{task_key}:{args.event}"):
        lines = text.splitlines()
        notifier.notify(lines[0].removeprefix("[agent-meter] "), "\n".join(line.strip() for line in lines[1:]))
    return 0

