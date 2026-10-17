"""Tasks & agents: cost share by agent type, agent-run timelines, the task table.

Tasks are identified as ``task #<seq>`` only: task labels never reach the page (BR-16).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final

from agent_meter.report.charts import (
    ShareItem,
    TimelineLane,
    duration_scale,
    share_bar,
    timeline,
)
from agent_meter.report.data import (
    TASK_LIMIT,
    AgentRunRow,
    AgentTypeRow,
    ReportData,
    TagRow,
    TaskRow,
    TaskTimeline,
)
from agent_meter.report.fmt import (
    DASH,
    esc,
    format_cost,
    format_duration_ms,
    format_int,
    format_multiplier,
    format_percent,
    host_label,
    unpriced_note,
)
from agent_meter.report.html import (
    card,
    chart_card,
    cost_td,
    muted,
    num_td,
    section,
    table,
    td,
    text_td,
)
from agent_meter.report.series import (
    CATEGORICAL_SLOTS,
    OTHER_LABEL,
    OTHER_TONE,
    assign_tones,
)
from agent_meter.report.values import CostTotal, DisplayCurrency

__all__ = ["render"]

_STATUS_LABELS: Final = {
    "in_progress": "in progress",
    "closed_stale": "closed (stale)",
}
_MAX_LANES: Final = 16
_MS: Final = timedelta(milliseconds=1)


def _ms(delta: timedelta) -> Decimal:
    return Decimal(delta // _MS)


def _share_caption(share: Decimal | None, cost: CostTotal) -> str:
    note = unpriced_note(cost)
    parts = [format_percent(share) if share is not None else DASH, format_cost(cost)]
    return " · ".join(parts) + (f" {note}" if note else "")


# ----------------------------------------------------------- agent cost share


def _fold_agents(
    agents: Sequence[AgentTypeRow], tones: Mapping[str, str]
) -> list[ShareItem]:
    items = []
    other_cost = CostTotal(None)
    other_share = Decimal(0)
    folded = False
    for agent in agents:
        if tones[agent.agent_type] == OTHER_TONE:
            folded = True
            other_cost = other_cost + agent.cost
            other_share += agent.cost_share or Decimal(0)
            continue
        items.append(
            ShareItem(
                label=agent.agent_type,
                tone=tones[agent.agent_type],
                value=agent.cost.cost_usd,
                caption=_share_caption(agent.cost_share, agent.cost),
            )
        )
    if folded:
        items.append(
            ShareItem(
                label=OTHER_LABEL,
                tone=OTHER_TONE,
                value=other_cost.cost_usd,
                caption=_share_caption(other_share, other_cost),
            )
        )
    return items


def _agent_table(agents: Sequence[AgentTypeRow], display: DisplayCurrency | None) -> str:
    rows = [
        "<tr>"
        + text_td(agent.agent_type)
        + num_td(format_int(agent.runs), agent.runs)
        + num_td(format_int(agent.calls), agent.calls)
        + num_td(format_duration_ms(agent.active_ms), agent.active_ms)
        + cost_td(agent.cost, display)
        + num_td(format_percent(agent.cost_share), agent.cost_share)
        + "</tr>"
        for agent in agents
    ]
    return table(["Agent type", "Runs", "Calls", "Active", "Cost", "Share"], rows)


def _cost_share(
    data: ReportData, tones: Mapping[str, str], display: DisplayCurrency | None
) -> str:
    if not data.agent_types:
        return ""
    chart = share_bar(_fold_agents(data.agent_types, tones), title="Cost share by agent type")
    subtitle = (
        f"Top {CATEGORICAL_SLOTS} agent types; the rest folded into Other"
        if len(data.agent_types) > CATEGORICAL_SLOTS
        else "Share of priced cost across every task in scope"
    )
    return chart_card(
        "Cost share by agent type",
        subtitle,
        chart,
        _agent_table(data.agent_types, display),
        wide=True,
    )


# ------------------------------------------------------------------ timelines


def _lane(run: AgentRunRow, origin: datetime, tones: Mapping[str, str]) -> TimelineLane:
    start = _ms(run.started_at - origin)
    end = max(_ms(run.ended_at - origin), start)
    caption = (
        f"{format_duration_ms(end - start)} · {format_cost(run.cost)} · "
        f"starts +{format_duration_ms(start)}"
    )
    return TimelineLane(
        label=run.agent_type,
        depth=run.spawn_depth,
        start_ms=start,
        end_ms=end,
        tone=tones.get(run.agent_type, OTHER_TONE),
        caption=caption,
    )


def _run_table(
    runs: Sequence[AgentRunRow], origin: datetime, display: DisplayCurrency | None
) -> str:
    rows = []
    for run in runs:
        start = _ms(run.started_at - origin)
        duration = max(_ms(run.ended_at - run.started_at), Decimal(0))
        rows.append(
            "<tr>"
            + text_td(run.agent_type)
            + num_td(format_int(run.spawn_depth), run.spawn_depth)
            + num_td(f"+{format_duration_ms(start)}", start)
            + num_td(format_duration_ms(duration), duration)
            + num_td(format_duration_ms(run.active_ms), run.active_ms)
            + num_td(format_int(run.calls), run.calls)
            + cost_td(run.cost, display)
            + "</tr>"
        )
    return table(["Agent", "Depth", "Starts", "Duration", "Active", "Calls", "Cost"], rows)


def _timeline_card(
    item: TaskTimeline, tones: Mapping[str, str], display: DisplayCurrency | None
) -> str:
    task = item.task
    origin = min(run.started_at for run in item.runs)
    finish = max(run.ended_at for run in item.runs)
    lanes = [_lane(run, origin, tones) for run in item.runs[:_MAX_LANES]]
    title = f"task #{task.seq_in_session}"
    chart = timeline(lanes, title=f"{title} agent runs", scale=duration_scale(_ms(finish - origin)))
    hidden = len(item.runs) - len(lanes)
    more = f'<p class="muted">+{hidden:,} more runs in the table view</p>' if hidden > 0 else ""
    subtitle = (
        f"{task.project_label} · {host_label(task.host)} · {task.local_date.isoformat()} · "
        f"{_agents_label(task)} · {format_cost(task.cost)}"
    )
    return chart_card(
        title, subtitle, chart + more, _run_table(item.runs, origin, display)
    )


def _timelines(
    data: ReportData, tones: Mapping[str, str], display: DisplayCurrency | None
) -> str:
    if not data.timelines:
        return card(
            "Agent timelines",
            muted("No task in scope spawned subagents, so there is no timeline to draw."),
        )
    return "".join(_timeline_card(item, tones, display) for item in data.timelines)


# ----------------------------------------------------------------- task table


def _agents_label(task: TaskRow) -> str:
    noun = "agent" if task.agent_runs == 1 else "agents"
    return f"{task.agent_runs} {noun} (max depth {task.max_spawn_depth})"


def _retries_text(task: TaskRow) -> str:
    if task.retries == 0:
        return DASH
    noun = "retry" if task.retries == 1 else "retries"
    summary = f" {task.retry_summary}" if task.retry_summary else ""
    return f"{task.retries} {noun}{summary}"


def _tests_text(runs: int, failures: int) -> str:
    if runs == 0:
        return DASH
    return f"{runs - failures} ✓ · {failures} ✗"


def _agent_breakdown(agents: Sequence[AgentTypeRow], display: DisplayCurrency | None) -> str:
    rows = []
    for agent in agents:
        name = agent.agent_type if agent.runs <= 1 else f"{agent.agent_type} ×{agent.runs}"
        rows.append(
            "<tr>"
            + text_td(name)
            + cost_td(agent.cost, display)
            + num_td(format_int(agent.calls), agent.calls)
            + num_td(format_int(agent.tool_calls), agent.tool_calls)
            + num_td(format_int(agent.files_touched), agent.files_touched)
            + num_td(_tests_text(agent.test_runs, agent.test_failures), agent.test_runs)
            + num_td(format_duration_ms(agent.active_ms), agent.active_ms)
            + num_td(format_percent(agent.cost_share), agent.cost_share)
            + "</tr>"
        )
    head = "".join(
        f'<th scope="col">{esc(h)}</th>'
        for h in ("Agent", "Cost", "Calls", "Tools", "Files", "Tests", "Active", "Share")
    )
    return (
        f'<table class="nested"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}'
        "</tbody></table>"
    )


def _task_row(task: TaskRow, display: DisplayCurrency | None) -> str:
    agents = esc(_agents_label(task))
    if task.agents:
        agents = (
            f"<details><summary>{agents}</summary>"
            f"{_agent_breakdown(task.agents, display)}</details>"
        )
    parallelism = task.parallelism if task.agent_runs > 1 else None
    return (
        f'<tr data-task="{esc(task.task_id)}">'
        + td(esc(task.local_date.isoformat()), sort=task.started_at.isoformat())
        + td(esc(f"task #{task.seq_in_session}"), sort=task.seq_in_session)
        + text_td(task.project_label)
        + text_td(host_label(task.host))
        + text_td(_STATUS_LABELS.get(task.status, task.status))
        + num_td(format_duration_ms(task.wall_clock_ms), task.wall_clock_ms)
        + num_td(format_duration_ms(task.active_ms), task.active_ms)
        + td(agents, sort=task.agent_runs)
        + num_td(format_multiplier(parallelism), parallelism)
        + text_td(_retries_text(task))
        + num_td(_tests_text(task.test_runs, task.test_failures), task.test_runs)
        + num_td(format_int(task.files_touched), task.files_touched)
        + num_td(format_int(task.calls), task.calls)
        + cost_td(task.cost, display)
        + text_td(task.work_item_tag or DASH)
        + "</tr>"
    )


def _task_table(data: ReportData, display: DisplayCurrency | None) -> str:
    headers = [
        "Date",
        "Task",
        "Project",
        "Host",
        "Status",
        "Wall-clock",
        "Active",
        "Agents",
        "Parallelism",
        "Retries",
        "Tests",
        "Files",
        "Calls",
        "Cost",
        "Work item",
    ]
    limit_note = (
        f"Showing the {TASK_LIMIT:,} most recent of {data.task_count:,} tasks."
        if data.task_count > len(data.tasks)
        else f"{data.task_count:,} tasks."
    )
    return card(
        "All tasks",
        muted(
            f"{limit_note} Parallelism = Σ agent active time ÷ task active time, shown "
            "only for tasks with subagents."
        ),
        '<input type="search" id="task-filter" placeholder="Filter tasks" '
        'aria-label="Filter tasks">',
        table(
            headers,
            (_task_row(task, display) for task in data.tasks),
            table_id="tasks-table",
        ),
    )


def _tags_table(tags: Sequence[TagRow], display: DisplayCurrency | None) -> str:
    return card(
        "Work items",
        table(
            ["Work item", "Tasks", "Wall-clock", "Active", "Cost"],
            (
                "<tr>"
                + text_td(tag.tag)
                + num_td(format_int(tag.tasks), tag.tasks)
                + num_td(format_duration_ms(tag.wall_clock_ms), tag.wall_clock_ms)
                + num_td(format_duration_ms(tag.active_ms), tag.active_ms)
                + cost_td(tag.cost, display)
                + "</tr>"
                for tag in tags
            ),
        ),
    )


def render(data: ReportData, display: DisplayCurrency | None) -> str:
    tones = assign_tones([agent.agent_type for agent in data.agent_types])
    charts = _cost_share(data, tones, display) + _timelines(data, tones, display)
    parts = [f'<div class="grid">{charts}</div>', _task_table(data, display)]
    if data.tags:
        parts.append(_tags_table(data.tags, display))
    return section(
        "tasks",
        "Tasks & agents",
        "Where agent time and cost go, and how the most recent multi-agent tasks unfolded.",
        *parts,
    )
