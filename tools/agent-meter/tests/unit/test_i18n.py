"""English and Spanish in the desktop app: catalog, insights, budgets, diagnostics and alerts."""

from __future__ import annotations

import re
from decimal import Decimal
from importlib.resources import files
from pathlib import Path

import pytest

from agent_meter import budgets, i18n
from agent_meter.app.services import AppApi
from agent_meter.budgets import BudgetLine, send_alerts
from agent_meter.config import Config, ConfigError, load_config, save_config, set_key
from agent_meter.paths import AppHome

ASSETS = files("agent_meter.app") / "assets"
ALL_RULES = ("long_session", "stale_cache", "repeated_implementers", "expensive_agent", "outlier_tasks", "model_what_if")


def insight_item(rule: str, evidence: dict[str, object]) -> dict[str, object]:
    return {"rule": rule, "title": "english", "action": "english", "saving_basis": "english", "evidence": evidence}


EVIDENCE: dict[str, dict[str, object]] = {
    "long_session": {"sessions": 3, "cost_usd": "1278.064", "threshold_calls": 1000, "baseline_calls": 500},
    "stale_cache": {"resumes": 32, "cost_usd": "43.961", "idle_hours": "1"},
    "repeated_implementers": {"tasks": 3, "repeats": 4, "cost_usd": "24.54"},
    "expensive_agent": {"agent_type": "code-implementer", "runs": 9, "average_usd": "6.11", "ratio": "2.9"},
    "outlier_tasks": {"tasks": 1477, "top_tasks": 148, "share_pct": "67"},
    "model_what_if": {"source": "claude-opus-5-5", "target": "claude-sonnet-5-5", "calls": 8969,
                      "cost_usd": "740.87", "alternative_usd": "370.43"},
}


def test_every_language_has_the_same_keys() -> None:
    assert set(i18n.UI["en"]) == set(i18n.UI["es"])


def test_placeholders_match_between_languages() -> None:
    fields = re.compile(r"\{(\w+)\}")

    for key, english in i18n.UI["en"].items():
        assert set(fields.findall(english)) == set(fields.findall(i18n.UI["es"][key])), key


def test_every_key_the_page_uses_exists() -> None:
    page = (ASSETS / "index.html").read_text(encoding="utf-8")
    script = (ASSETS / "app.js").read_text(encoding="utf-8")

    used = set(re.findall(r'data-i18n(?:-\w+)?="([\w.]+)"', page)) | set(re.findall(r'\bt\("([\w.]+)"', script))

    assert used
    assert used <= set(i18n.UI["en"])


def test_every_visible_english_word_in_the_page_is_translated() -> None:
    page = (ASSETS / "index.html").read_text(encoding="utf-8")
    body = page[page.index("<body>") :]
    tagged = re.sub(r"<(\w+)[^>]*data-i18n=\"[\w.]+\"[^>]*>[^<]*</\1>", "", body)
    text = re.sub(r"<[^>]+>", " ", tagged)

    assert set(text.split()) <= {"agent-meter", "—", "English", "Español"}


def test_every_insight_rule_has_spanish_text() -> None:
    assert set(EVIDENCE) == set(ALL_RULES)
    assert set(i18n.INSIGHT_TEXT) == set(ALL_RULES)


@pytest.mark.parametrize("rule", ALL_RULES)
def test_spanish_insights_replace_all_english_text(rule: str) -> None:
    (item,) = i18n.localize_insights({"note": "english", "insights": [insight_item(rule, EVIDENCE[rule])]}, "es")["insights"]

    assert "english" not in (item["title"], item["action"], item["saving_basis"])
    assert "{" not in item["title"] + item["action"] + item["saving_basis"]


def test_spanish_insight_keeps_the_measured_figures() -> None:
    document = {"note": "n", "insights": [insight_item("long_session", EVIDENCE["long_session"])]}

    (item,) = i18n.localize_insights(document, "es")["insights"]

    assert item["title"] == "3 sesiones superaron 1.000 llamadas y costaron $1.278,06"
    assert item["evidence"] == EVIDENCE["long_session"]


def test_english_insights_are_left_untouched() -> None:
    document = {"note": "n", "insights": [insight_item("long_session", EVIDENCE["long_session"])]}

    assert i18n.localize_insights(document, "en") == document


def test_singular_and_plural_read_correctly_in_spanish() -> None:
    evidence = {**EVIDENCE["long_session"], "sessions": 1}

    (item,) = i18n.localize_insights({"note": "n", "insights": [insight_item("long_session", evidence)]}, "es")["insights"]

    assert item["title"].startswith("1 sesión superó ")


@pytest.mark.parametrize(
    ("rule", "fragment"),
    [("expensive_agent", "2,9 veces"), ("outlier_tasks", "67 %"), ("stale_cache", "$43,96")],
)
def test_spanish_numbers_use_spanish_separators(rule: str, fragment: str) -> None:
    (item,) = i18n.localize_insights({"note": "n", "insights": [insight_item(rule, EVIDENCE[rule])]}, "es")["insights"]

    assert fragment in item["title"]


def test_insight_evidence_carries_what_the_templates_need() -> None:
    fields = re.compile(r"\{(\w+)\}")
    known = {"cost", "alternative", "average", "threshold", "baseline", "hours", "calls", "share", "ratio", "count",
             "tasks", "top", "agent", "source", "target", "sessions", "resumes", "repeats"}

    for texts in i18n.INSIGHT_TEXT.values():
        for template in texts:
            assert set(fields.findall(template)) <= known


@pytest.mark.parametrize(
    ("english", "spanish"),
    [
        ("scheduler", "programador"),
        ("loaded (every 15 min) · last scheduled collect 2 min ago",
         "cargado (cada 15 min) · última recolección programada hace 2 min"),
        ("loaded, but no scheduled collect has succeeded yet",
         "cargado, pero ninguna recolección programada ha terminado bien todavía"),
        ("not loaded (hooks/manual collect only)", "sin cargar (solo hooks o recolección manual)"),
        ("hook registered · last ingest 3 days ago · 12 units",
         "hook registrado · última ingesta hace 3 días · 12 unidades"),
        ("3450 file(s) skipped or corrupt in 7 days", "3450 archivo(s) omitidos o corruptos en 7 días"),
        ("budget.daily_usd: 'abc' is not a decimal number", "budget.daily_usd: 'abc' no es un número decimal"),
    ],
)
def test_spanish_phrases_translate_diagnostics(english: str, spanish: str) -> None:
    assert i18n.translate(english, "es") == spanish


def test_unknown_text_stays_as_it_is() -> None:
    assert i18n.translate("something new", "es") == "something new"


def test_translation_is_off_in_english() -> None:
    assert i18n.translate("hook registered", "en") == "hook registered"


def test_alerts_follow_the_chosen_language(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(budgets.notifier, "notify", lambda title, body: sent.append((title, body)))
    line = BudgetLine("month:all", "All projects", "this month", Decimal(1000), Decimal("1250.50"))

    send_alerts((line,), Config(timezone="UTC", language="es"))

    assert sent == [("agent-meter: presupuesto superado",
                     "Todos los proyectos: $1.250,50 de $1.000,00 este mes (costo a precio de lista)")]


def test_language_defaults_to_english_and_survives_a_save(tmp_path: Path) -> None:
    home = AppHome.resolve(str(tmp_path / "h"))
    assert load_config(home).language == "en"

    save_config(set_key(load_config(home), "language", "es"), home)

    assert load_config(home).language == "es"


def test_unsupported_language_is_rejected() -> None:
    with pytest.raises(ConfigError):
        set_key(Config(timezone="UTC"), "language", "fr")


def test_texts_returns_the_saved_language(tmp_path: Path) -> None:
    api = AppApi(AppHome.resolve(str(tmp_path / "h")))

    result = api.set_language("es")

    assert result["language"] == "es"
    assert result["text"] == i18n.UI["es"]
    assert api.texts()["language"] == "es"


def test_set_language_refuses_an_unsupported_value(tmp_path: Path) -> None:
    api = AppApi(AppHome.resolve(str(tmp_path / "h")))

    result = api.set_language("fr")

    assert result["language"] == "en"
    assert result["error"]


def test_spanish_budget_lines_in_the_document() -> None:
    line = {"label": "All projects", "period": "this month"}

    assert i18n.localize_budget_line(line, "es") == {"label": "Todos los proyectos", "period": "este mes"}


