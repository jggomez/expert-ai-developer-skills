"""Spending history for the app: one query at the finest grain, rolled up by day, month, project and session."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from agent_meter.store import Store

__all__ = ["HISTORY_SQL", "SESSIONS_SHOWN", "build_history", "load_history"]

SESSIONS_SHOWN: Final = 100
ZERO: Final = Decimal(0)
Row = Mapping[str, object]

HISTORY_SQL: Final = """
SELECT c.local_date, c.local_month, c.project_id, COALESCE(p.display_name, c.project_id) AS display_name,
       c.host, c.session_id, c.task_id, COUNT(*) AS calls, SUM(c.cost_usd) AS cost_usd,
       SUM(c.cost_usd) FILTER (WHERE c.estimated) AS estimated_usd,
       COUNT(*) FILTER (WHERE c.unpriced) AS unpriced_calls,
       SUM(c.prompt_tokens + COALESCE(c.output_tokens, 0)) AS tokens, MIN(c.ts) AS first_ts, MAX(c.ts) AS last_ts
FROM v_calls c LEFT JOIN projects p ON p.project_id = c.project_id
GROUP BY c.local_date, c.local_month, c.project_id, p.display_name, c.host, c.session_id, c.task_id
"""


MODEL_LATENCY_SQL: Final = """
SELECT host, COALESCE(priced_model, model_label, model) AS model, (host = 'claude-code') AS estimated, COUNT(*) AS calls,
       quantile_cont(latency_ms, 0.5) AS p50_ms, quantile_cont(latency_ms, 0.95) AS p95_ms
FROM v_calls
WHERE latency_ms IS NOT NULL AND local_date >= ? AND (? IS NULL OR project_id = ?)
GROUP BY 1, 2, 3 ORDER BY calls DESC, model LIMIT 12
"""


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _cost(value: object) -> Decimal:
    return ZERO if value is None else Decimal(str(value))


def _int(value: object) -> int:
    return int(str(value or 0))


@dataclass(slots=True)
class _Tally:
    """Totals for one group of rows, whatever the group is."""

    cost: Decimal = ZERO
    estimated: Decimal = ZERO
    calls: int = 0
    unpriced: int = 0
    tokens: int = 0
    sessions: set[tuple[str, str]] = field(default_factory=set)
    tasks: set[str] = field(default_factory=set)
    first: datetime | None = None
    last: datetime | None = None

    def add(self, row: Row) -> None:
        self.cost += _cost(row["cost_usd"])
        self.estimated += _cost(row["estimated_usd"])
        self.calls += _int(row["calls"])
        self.unpriced += _int(row["unpriced_calls"])
        self.tokens += _int(row["tokens"])
        self.sessions.add((str(row["host"]), str(row["session_id"])))
        if row["task_id"] is not None:
            self.tasks.add(str(row["task_id"]))
        first, last = row["first_ts"], row["last_ts"]
        assert isinstance(first, datetime) and isinstance(last, datetime)
        self.first = first if self.first is None else min(self.first, first)
        self.last = last if self.last is None else max(self.last, last)

    def figures(self) -> dict[str, Any]:
        return {"cost_usd": _money(self.cost), "calls": self.calls, "sessions": len(self.sessions),
                "tasks": len(self.tasks), "tokens": self.tokens}


def _tally_by(rows: Iterable[Row], *columns: str) -> dict[tuple[object, ...], _Tally]:
    groups: dict[tuple[object, ...], _Tally] = {}
    for row in rows:
        groups.setdefault(tuple(row[c] for c in columns), _Tally()).add(row)
    return groups


def _days(rows: Sequence[Row], first: date, last: date) -> list[dict[str, Any]]:
    """Every day in the window, so that a day without use shows as a gap and the time axis stays true."""
    groups = _tally_by(rows, "local_date")
    found = []
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        found.append({"date": day.isoformat(), **groups.get((day,), _Tally()).figures()})
    return found


def _projects(rows: Sequence[Row]) -> list[dict[str, Any]]:
    groups = _tally_by(rows, "project_id", "display_name")
    total = sum((tally.cost for tally in groups.values()), ZERO)
    found = [
        {"project_id": str(project), "name": str(name), **tally.figures(),
         "share_pct": str((tally.cost * 100 / total).quantize(Decimal("0.1"))) if total else "0.0"}
        for (project, name), tally in groups.items()
    ]
    return sorted(found, key=lambda p: (-Decimal(p["cost_usd"]), p["name"]))


def _session_list(rows: Sequence[Row]) -> list[dict[str, Any]]:
    groups = sorted(_tally_by(rows, "host", "session_id", "display_name").items(),
                    key=lambda item: (item[1].last, item[0][1]), reverse=True)
    return [
        {"host": str(host), "project": str(name), "started_at": t.first.isoformat() if t.first else None,
         "ended_at": t.last.isoformat() if t.last else None, **t.figures()}
        for (host, _session, name), t in groups[:SESSIONS_SHOWN]
    ]


def build_history(rows: Sequence[Row], *, as_of: date, days: int = 0, project_id: str | None = None) -> dict[str, Any]:
    """``days`` of 0 means all history. The project list ignores ``project_id`` so it can stay a filter."""
    start = as_of - timedelta(days=days - 1) if days > 0 else None
    window = [r for r in rows if start is None or r["local_date"] >= start]  # type: ignore[operator]
    chosen = [r for r in window if project_id is None or r["project_id"] == project_id]
    totals = _Tally()
    for row in chosen:
        totals.add(row)
    dated: list[date] = [r["local_date"] for r in chosen]  # type: ignore[misc]
    first = start or min(dated, default=as_of)
    months = sorted(_tally_by(chosen, "local_month").items(), key=lambda item: str(item[0][0]), reverse=True)
    return {
        "from": first.isoformat(), "to": as_of.isoformat(), "days": days, "project_id": project_id,
        "totals": {**totals.figures(), "estimated_usd": _money(totals.estimated), "unpriced_calls": totals.unpriced},
        "by_day": _days(chosen, first, as_of),
        "by_month": [{"month": str(key[0]), **tally.figures()} for key, tally in months],
        "projects": _projects(window),
        "sessions": _session_list(chosen),
    }


def load_history(store: Store, *, as_of: date, days: int = 0, project_id: str | None = None) -> dict[str, Any]:
    document = build_history(store.query(HISTORY_SQL), as_of=as_of, days=days, project_id=project_id)
    start = as_of - timedelta(days=days - 1) if days > 0 else date.min
    document["model_latency"] = [
        {"host": str(row["host"]), "model": str(row["model"]), "estimated": bool(row["estimated"]), "calls": row["calls"],
         "p50_ms": round(float(str(row["p50_ms"]))), "p95_ms": round(float(str(row["p95_ms"])))}
        for row in store.query(MODEL_LATENCY_SQL, [start, project_id, project_id])
    ]
    return document
