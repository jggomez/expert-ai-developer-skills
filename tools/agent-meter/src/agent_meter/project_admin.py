"""Project details shared by the CLI and the desktop app."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Final

from agent_meter.project_resolver import (
    ProjectOverride,
    ProjectsConfig,
    load_projects_config,
    save_projects_config,
)

__all__ = ["PROJECT_LIST_SQL", "save_project_override"]

# Hides orphan identities, such as a pre-move path id after its sessions were relocated.
PROJECT_LIST_SQL: Final = """
SELECT p.project_id, p.display_name, p.kind, p.remote_url, p.client, p.billing_model,
       p.hourly_rate, p.fixed_price, p.rate_currency,
       (SELECT COUNT(*) FROM v_sessions s WHERE s.project_id = p.project_id) AS sessions,
       (SELECT SUM(d.cost_usd) FROM v_daily_project_cost d WHERE d.project_id = p.project_id) AS cost_usd,
       (SELECT COALESCE(SUM(d.unpriced_calls), 0) FROM v_daily_project_cost d
         WHERE d.project_id = p.project_id) AS unpriced_calls
FROM projects p
WHERE p.project_id = '(unassigned)' OR p.client IS NOT NULL OR p.billing_model IS NOT NULL
   OR EXISTS (SELECT 1 FROM sessions s WHERE s.project_id = p.project_id)
   OR EXISTS (SELECT 1 FROM llm_calls c WHERE c.project_id = p.project_id)
   OR EXISTS (SELECT 1 FROM dev_hours_manual h WHERE h.project_id = p.project_id)
ORDER BY p.display_name, p.project_id
"""


def save_project_override(path: Path, project_id: str, changes: dict[str, Any]) -> None:
    config = load_projects_config(path)
    updated = replace(config.projects.get(project_id, ProjectOverride()), **changes)
    save_projects_config(
        ProjectsConfig(
            projects={**config.projects, project_id: updated}, path_aliases=config.path_aliases,
            ignore=config.ignore, merges=config.merges,
        ),
        path,
    )
