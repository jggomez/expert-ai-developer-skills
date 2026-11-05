"""English and Spanish for the desktop app and its alerts. The CLI and the HTML report stay in English.

English is the source text, so it is returned untouched. Spanish insights are written from each
insight's measured evidence, which means translation can never change a figure. Other backend
messages go through a phrase table: text it does not know stays in English instead of breaking.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Final

__all__ = ["DEFAULT_LANGUAGE", "INSIGHT_TEXT", "LANGUAGES", "UI", "localize_budget_line", "localize_insights",
           "money", "translate"]

DEFAULT_LANGUAGE: Final = "en"
LANGUAGES: Final = ("en", "es")
_SPANISH: Final = "es"

UI: Final[Mapping[str, Mapping[str, str]]] = {
    "en": {
        "nav.label": "Screens", "nav.live": "Live", "nav.history": "History", "nav.insights": "Insights",
        "nav.settings": "Settings", "language.label": "Language",
        "status.loading": "Loading…", "status.updating": "Updating data…",
        "status.updating_saved": "Updating data. Showing the last saved figures.",
        "status.updated": "Updated {time}", "status.error": "Could not load data: {message}",
        "level.ok": "On track", "level.warn": "Near limit", "level.over": "Over limit",
        "check.ok": "OK", "check.warn": "WARN", "check.fail": "FAIL",
        "live.today": "Today", "live.month": "This month", "live.forecast": "Month-end forecast",
        "live.forecast_note": "Estimate from the last 7 days", "live.plan": "Plan value",
        "live.plan_note": "List-price usage against your plan", "live.budgets": "Budgets",
        "live.sessions": "Active sessions", "live.no_sessions": "No session has been active in the last 15 minutes.",
        "live.not_set": "Not set", "live.no_budgets": "No budgets yet. Add one in Settings.",
        "live.budget_used": "{spent} of {limit}", "live.percent_used": "{percent}% used",
        "live.tokens": "{count}k tokens", "live.just_now": "Just now", "live.minutes_ago": "{minutes} min ago",
        "common.project": "Project", "common.host": "Host", "common.calls": "Calls", "common.cost": "Cost",
        "common.context": "Context", "common.last_activity": "Last activity", "common.sessions": "Sessions",
        "common.tasks": "Tasks", "common.tokens": "Tokens", "common.share": "Share", "common.date": "Date",
        "common.month": "Month", "common.started": "Started",
        "common.list_price_note": "Costs use API list prices. They are not what your plan charges.",
        "history.title": "History", "history.period": "Period", "history.all_time": "All time",
        "history.last_7": "Last 7 days", "history.last_30": "Last 30 days", "history.last_90": "Last 90 days",
        "history.all_projects": "All projects", "history.spent": "Spent",
        "history.estimated": "{amount} estimated", "history.by_day": "By day", "history.by_month": "By month",
        "history.by_project": "By project", "history.as_table": "View as a table",
        "history.chart_label": "Cost per day", "history.hover_hint": "Hover over a day to see its figures.",
        "history.day_detail": "{date}: {cost}, {calls} calls, {sessions} sessions",
        "history.shown": "Showing the latest {shown} of {total} sessions.", "history.empty": "No activity in this period.",
        "insights.title": "Where to cut", "insights.period": "{from} to {to}. Findings are measured, and savings are estimates.",
        "insights.saving": "About {amount} (estimate)", "insights.no_saving": "No savings estimate",
        "insights.none": "No rule fired in this period.",
        "settings.budgets": "Budgets and alerts", "settings.daily": "Daily budget (USD)",
        "settings.monthly": "Monthly budget (USD)", "settings.plan": "Plan price per month (USD)",
        "settings.no_limit": "No limit", "settings.notifications": "Notifications",
        "settings.notify_auto": "Sessions and long tasks", "settings.notify_session": "Sessions only",
        "settings.notify_long": "Long tasks only", "settings.notify_off": "Off", "settings.save": "Save",
        "settings.collect": "Collect now", "settings.diagnostics": "Diagnostics", "settings.saved": "Saved",
        "settings.collecting": "Collecting…", "settings.collected": "Collected in {seconds} s",
        "settings.collect_busy": "Busy. Try again in a minute.", "settings.collect_failed": "Collect failed",
    },
    "es": {
        "nav.label": "Pantallas", "nav.live": "En vivo", "nav.history": "Historial", "nav.insights": "Insights",
        "nav.settings": "Ajustes", "language.label": "Idioma",
        "status.loading": "Cargando…", "status.updating": "Actualizando datos…",
        "status.updating_saved": "Actualizando datos. Se muestran las últimas cifras guardadas.",
        "status.updated": "Actualizado {time}", "status.error": "No se pudieron cargar los datos: {message}",
        "level.ok": "En orden", "level.warn": "Cerca del límite", "level.over": "Límite superado",
        "check.ok": "OK", "check.warn": "AVISO", "check.fail": "FALLO",
        "live.today": "Hoy", "live.month": "Este mes", "live.forecast": "Previsión de fin de mes",
        "live.forecast_note": "Estimación según los últimos 7 días", "live.plan": "Valor del plan",
        "live.plan_note": "Uso a precio de lista frente a tu plan", "live.budgets": "Presupuestos",
        "live.sessions": "Sesiones activas", "live.no_sessions": "Ninguna sesión ha tenido actividad en los últimos 15 minutos.",
        "live.not_set": "Sin definir", "live.no_budgets": "Aún no hay presupuestos. Añade uno en Ajustes.",
        "live.budget_used": "{spent} de {limit}", "live.percent_used": "{percent} % usado",
        "live.tokens": "{count}k tokens", "live.just_now": "Ahora mismo", "live.minutes_ago": "Hace {minutes} min",
        "common.project": "Proyecto", "common.host": "Host", "common.calls": "Llamadas", "common.cost": "Coste",
        "common.context": "Contexto", "common.last_activity": "Última actividad", "common.sessions": "Sesiones",
        "common.tasks": "Tareas", "common.tokens": "Tokens", "common.share": "Parte", "common.date": "Fecha",
        "common.month": "Mes", "common.started": "Inicio",
        "common.list_price_note": "Los costes usan precios de lista de la API. No es lo que cobra tu plan.",
        "history.title": "Historial", "history.period": "Periodo", "history.all_time": "Todo",
        "history.last_7": "Últimos 7 días", "history.last_30": "Últimos 30 días", "history.last_90": "Últimos 90 días",
        "history.all_projects": "Todos los proyectos", "history.spent": "Gastado",
        "history.estimated": "{amount} estimados", "history.by_day": "Por día", "history.by_month": "Por mes",
        "history.by_project": "Por proyecto", "history.as_table": "Ver como tabla",
        "history.chart_label": "Coste por día", "history.hover_hint": "Pasa el cursor por un día para ver sus cifras.",
        "history.day_detail": "{date}: {cost}, {calls} llamadas, {sessions} sesiones",
        "history.shown": "Se muestran las {shown} sesiones más recientes de {total}.", "history.empty": "Sin actividad en este periodo.",
        "insights.title": "Dónde recortar", "insights.period": "Del {from} al {to}. Los hallazgos son medidos y los ahorros, estimaciones.",
        "insights.saving": "Unos {amount} (estimación)", "insights.no_saving": "Sin estimación de ahorro",
        "insights.none": "Ninguna regla se activó en este periodo.",
        "settings.budgets": "Presupuestos y avisos", "settings.daily": "Presupuesto diario (USD)",
        "settings.monthly": "Presupuesto mensual (USD)", "settings.plan": "Precio del plan al mes (USD)",
        "settings.no_limit": "Sin límite", "settings.notifications": "Notificaciones",
        "settings.notify_auto": "Sesiones y tareas largas", "settings.notify_session": "Solo sesiones",
        "settings.notify_long": "Solo tareas largas", "settings.notify_off": "Desactivadas", "settings.save": "Guardar",
        "settings.collect": "Recolectar ahora", "settings.diagnostics": "Diagnóstico", "settings.saved": "Guardado",
        "settings.collecting": "Recolectando…", "settings.collected": "Recolectado en {seconds} s",
        "settings.collect_busy": "Ocupado. Inténtalo de nuevo en un minuto.", "settings.collect_failed": "Falló la recolección",
    },
}

# title, action and saving basis, for each rule in agent_meter.insights
INSIGHT_TEXT: Final[Mapping[str, tuple[str, str, str]]] = {
    "long_session": (
        "{sessions} sesiones superaron {threshold} llamadas y costaron {cost}",
        "Empieza una sesión nueva para cada tarea y guarda las decisiones compartidas en las notas del proyecto.",
        "Cada llamada después de las primeras {baseline} se valora al promedio de esas primeras llamadas.",
    ),
    "stale_cache": (
        "{resumes} reanudaciones tras más de {hours} h de inactividad costaron {cost}",
        "Tras una pausa larga, empieza una sesión nueva o ejecuta /compact antes de seguir.",
        "Cada reanudación se valora al coste promedio de una llamada sin esa pausa.",
    ),
    "repeated_implementers": (
        "{tasks} tareas volvieron a ejecutar un implementador después de que terminara, por {cost}",
        "Revisa si esas tareas tenían especificaciones o criterios de aceptación poco claros. "
        "Las fases planificadas no son retrabajo.",
        "El coste completo de cada repetición secuencial. Es un máximo, porque algunas pueden ser fases planificadas.",
    ),
    "expensive_agent": (
        "{agent} cuesta {average} por ejecución, {ratio} veces lo que cuestan los demás",
        "Revisa las instrucciones, el modelo y el alcance que recibe {agent}.",
        "Cada ejecución se valora a la mediana de los promedios de los demás tipos de agente.",
    ),
    "outlier_tasks": (
        "{top} de {tasks} tareas concentraron el {share} % del coste",
        "Abre las tareas más caras y divide el trabajo similar en tareas más pequeñas.",
        "Sin estimación: esto muestra dónde está el coste, no cuánto se puede evitar.",
    ),
    "model_what_if": (
        "{calls} llamadas a {source} costaron {cost}; con {target} serían {alternative} a precio de lista",
        "Prueba {target} en trabajo rutinario. Esto compara solo el precio, no la calidad.",
        "Los mismos tokens al precio de lista del modelo destino. La calidad y el retrabajo pueden cambiar.",
    ),
}
_SINGULAR_TITLES: Final[Mapping[str, tuple[str, str]]] = {
    "long_session": ("sessions", "1 sesión superó {threshold} llamadas y costó {cost}"),
    "stale_cache": ("resumes", "1 reanudación tras más de {hours} h de inactividad costó {cost}"),
    "repeated_implementers": ("tasks", "1 tarea volvió a ejecutar un implementador después de que terminara, por {cost}"),
    "outlier_tasks": ("top_tasks", "1 de {tasks} tareas concentró el {share} % del coste"),
}
_OVERLAP_NOTE: Final = "Los ahorros son estimaciones y las reglas pueden solaparse, así que no los sumes."
_MONEY_FIELDS: Final = (("cost", "cost_usd"), ("alternative", "alternative_usd"), ("average", "average_usd"))
_COUNT_FIELDS: Final = (("sessions", "sessions"), ("threshold", "threshold_calls"), ("baseline", "baseline_calls"),
                        ("resumes", "resumes"), ("tasks", "tasks"), ("top", "top_tasks"), ("calls", "calls"))
_NUMBER_FIELDS: Final = (("hours", "idle_hours"), ("ratio", "ratio"), ("share", "share_pct"))
_TEXT_FIELDS: Final = (("agent", "agent_type"), ("source", "source"), ("target", "target"))

# Whole messages: short identifiers would be unsafe to replace inside longer text.
_EXACT: Final[Mapping[str, str]] = {
    "config": "configuración", "secret": "secreto", "store": "base de datos", "pricing": "precios",
    "scheduler": "programador", "hosts": "hosts", "All projects": "Todos los proyectos", "today": "hoy",
    "this month": "este mes",
}
_PHRASES: Final[Mapping[str, str]] = {
    "timezone ": "zona horaria ", " · notify ": " · avisos ", "hook registered": "hook registrado",
    "(scheduler-only)": "(solo programador)", "last ingest": "última ingesta", " units": " unidades",
    "earliest transcript": "transcript más antiguo", "format changed: ": "formato cambiado: ",
    "unknown host format(s)": "formato(s) de host desconocido(s)",
    "file(s) skipped or corrupt in 7 days": "archivo(s) omitidos o corruptos en 7 días",
    "no Claude Code or Antigravity data found": "no se encontraron datos de Claude Code ni de Antigravity",
    "pricing.local.yaml invalid: ": "pricing.local.yaml no es válido: ",
    "(previous table in use)": "(se usa la tabla anterior)", "unpriced model: ": "modelo sin precio: ",
    " calls)": " llamadas)", " · fix: ": " · solución: ",
    "models priced · every call priced": "modelos con precio · todas las llamadas tienen precio",
    "not created yet (created on first collect)": "aún no creado (se crea en la primera recolección)",
    "present · mode 0600": "presente · modo 0600", "schema v": "esquema v", "last collect": "última recolección",
    "no data yet — run 'agent-meter collect'": "aún no hay datos: ejecuta 'agent-meter collect'",
    "conversations untracked": "conversaciones sin seguimiento",
    "not loaded (hooks/manual collect only)": "sin cargar (solo hooks o recolección manual)",
    "no supported scheduler on this platform": "este sistema no tiene un programador compatible",
    "loaded, but no scheduled collect has succeeded yet":
        "cargado, pero ninguna recolección programada ha terminado bien todavía",
    "loaded, but the last scheduled collect succeeded": "cargado, pero la última recolección programada terminó bien",
    "loaded (every 15 min)": "cargado (cada 15 min)", "last scheduled collect": "última recolección programada",
    "last sync": "última sincronización", "is not a decimal number": "no es un número decimal",
    "must be a positive decimal, got": "debe ser un decimal positivo, recibido", "must be one of": "debe ser uno de",
    "just now": "ahora mismo", "never": "nunca",
}
_PHRASE_ORDER: Final = tuple(sorted(_PHRASES, key=len, reverse=True))
_AGE: Final = re.compile(r"\b(\d+) (min|h|days) ago\b")
_UNIT: Final[Mapping[str, str]] = {"min": "min", "h": "h", "days": "días"}


def _swap_separators(text: str) -> str:
    return text.translate(str.maketrans(",.", ".,"))


def money(value: Decimal, language: str) -> str:
    text = f"{value.quantize(Decimal('0.01')):,}"
    return f"${_swap_separators(text) if language == _SPANISH else text}"


def _insight_values(evidence: Mapping[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, key in _MONEY_FIELDS:
        if key in evidence:
            values[name] = money(Decimal(str(evidence[key])), _SPANISH)
    for name, key in _COUNT_FIELDS:
        if key in evidence:
            values[name] = _swap_separators(f"{int(evidence[key]):,}")
    for name, key in _NUMBER_FIELDS:
        if key in evidence:
            values[name] = _swap_separators(str(evidence[key]))
    for name, key in _TEXT_FIELDS:
        if key in evidence:
            values[name] = str(evidence[key])
    return values


def _spanish_insight(item: Mapping[str, Any]) -> dict[str, Any]:
    rule = str(item["rule"])
    title, action, basis = INSIGHT_TEXT[rule]
    evidence = item["evidence"]
    if rule in _SINGULAR_TITLES and evidence.get(_SINGULAR_TITLES[rule][0]) == 1:
        title = _SINGULAR_TITLES[rule][1]
    values = _insight_values(evidence)
    return {**item, "title": title.format_map(values), "action": action.format_map(values),
            "saving_basis": basis.format_map(values)}


def localize_insights(document: dict[str, Any], language: str) -> dict[str, Any]:
    if language != _SPANISH:
        return document
    return {**document, "note": _OVERLAP_NOTE, "insights": [_spanish_insight(i) for i in document["insights"]]}


def translate(text: str, language: str) -> str:
    """Spanish for a known backend message. Unknown text is returned as it is."""
    if language != _SPANISH:
        return text
    if text in _EXACT:
        return _EXACT[text]
    for phrase in _PHRASE_ORDER:
        text = text.replace(phrase, _PHRASES[phrase])
    return _AGE.sub(lambda m: f"hace {m[1]} {_UNIT[m[2]]}", text)


def localize_budget_line(line: dict[str, Any], language: str) -> dict[str, Any]:
    return {**line, "label": translate(str(line["label"]), language), "period": translate(str(line["period"]), language)}
