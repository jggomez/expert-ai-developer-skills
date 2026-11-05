"use strict";

const FALLBACK_REFRESH_MS = 30000;
const BUSY_RETRY_MS = 3000;
const DENSE_DAYS = 60;
const $ = (id) => document.getElementById(id);
let language = "en";
let text = {};
let retry = null;

function t(key, values = {}) {
  return (text[key] ?? key).replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");
}

function localized(formatted) {
  return language === "es" ? formatted.replace(/[.,]/g, (mark) => (mark === "." ? "," : ".")) : formatted;
}

function count(value) {
  return localized(Number(value).toLocaleString("en-US"));
}

function usd(value) {
  if (value === null || value === undefined) return "—";
  const options = { minimumFractionDigits: 2, maximumFractionDigits: 2 };
  return "$" + localized(Number(value).toLocaleString("en-US", options));
}

function compact(value) {
  const number = Number(value);
  if (number >= 1e9) return `${localized((number / 1e9).toFixed(1))} B`;
  return number >= 1e6 ? `${localized((number / 1e6).toFixed(1))} M` : count(number);
}

function dateTime(iso) {
  return iso ? new Date(iso).toLocaleString(language, { dateStyle: "medium", timeStyle: "short" }) : "—";
}

function cell(value) {
  const td = document.createElement("td");
  td.textContent = value;
  return td;
}

function node(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = content;
  return element;
}

function row(...cells) {
  const tr = document.createElement("tr");
  tr.append(...cells.map((item) => (item instanceof Node ? item : cell(item))));
  return tr;
}

function setStatus(message) {
  $("status").textContent = message;
}

function applyText() {
  document.documentElement.lang = language;
  $("language").value = language;
  for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
  for (const element of document.querySelectorAll("[data-i18n-placeholder]")) element.placeholder = t(element.dataset.i18nPlaceholder);
  for (const element of document.querySelectorAll("[data-i18n-aria]")) element.setAttribute("aria-label", t(element.dataset.i18nAria));
}

function ago(minutes) {
  return minutes < 1 ? t("live.just_now") : t("live.minutes_ago", { minutes });
}

function renderBudgets(lines) {
  const box = $("budgets");
  box.replaceChildren();
  if (!lines.length) {
    box.append(node("p", "muted", t("live.no_budgets")));
    return;
  }
  for (const line of lines) {
    const item = node("div", `budget ${line.level}`);
    item.append(node("span", "", `${line.label}, ${line.period}`));
    item.append(node("span", "", t("live.budget_used", { spent: usd(line.spent_usd), limit: usd(line.limit_usd) })));
    item.append(node("span", "badge", t(`level.${line.level}`)));
    const meter = node("progress");
    meter.max = 100;
    meter.value = Math.min(Number(line.percent), 100);
    meter.setAttribute("aria-label", t("live.percent_used", { percent: localized(line.percent) }));
    item.append(meter);
    box.append(item);
  }
}

function renderSessions(sessions) {
  $("sessions").replaceChildren(...sessions.map((s) => row(s.project, s.host, count(s.calls), usd(s.cost_usd),
    s.context_tokens === null ? "—" : t("live.tokens", { count: count(Math.round(s.context_tokens / 1000)) }), ago(s.minutes_ago))));
  $("no-sessions").hidden = sessions.length > 0;
  $("sessions-table").hidden = sessions.length === 0;
}

function settle(data) {
  window.clearTimeout(retry);
  if (data.busy || data.stale) {
    setStatus(t(data.busy ? "status.updating" : "status.updating_saved"));
    retry = window.setTimeout(refreshCurrent, BUSY_RETRY_MS);
    return false;
  }
  setStatus(t("status.updated", { time: new Date().toLocaleTimeString(language) }));
  return true;
}

async function refreshLive() {
  const data = await window.pywebview.api.overview();
  settle(data);
  if (data.busy) return;
  $("today").textContent = usd(data.today_usd);
  $("month").textContent = usd(data.month_usd);
  $("forecast").textContent = usd(data.forecast_usd);
  $("plan").textContent = data.plan_value_ratio ? `${localized(data.plan_value_ratio)}x` : t("live.not_set");
  renderBudgets(data.budgets);
  renderSessions(data.sessions);
}

function dayDetail(day) {
  return t("history.day_detail", { date: day.date, cost: usd(day.cost_usd), calls: count(day.calls), sessions: count(day.sessions) });
}

function renderChart(days) {
  const chart = $("history-chart");
  const top = Math.max(...days.map((day) => Number(day.cost_usd)), 0);
  chart.classList.toggle("dense", days.length > DENSE_DAYS);
  chart.setAttribute("aria-label", t("history.chart_label"));
  chart.replaceChildren(...days.map((day) => {
    const column = node("div", "column");
    const bar = node("div", "day-bar");
    bar.style.height = top ? `${(Number(day.cost_usd) / top) * 100}%` : "0";
    column.append(bar);
    column.addEventListener("mouseenter", () => { $("history-hover").textContent = dayDetail(day); });
    return column;
  }));
  $("history-max").textContent = usd(top);
  $("history-first").textContent = days[0]?.date ?? "";
  $("history-last").textContent = days[days.length - 1]?.date ?? "";
  $("history-hover").textContent = t("history.hover_hint");
  const used = days.filter((day) => day.calls > 0).reverse();
  $("history-days-table").replaceChildren(...used.map((day) =>
    row(day.date, usd(day.cost_usd), count(day.calls), count(day.sessions), count(day.tasks))));
}

function chooseProject(projectId) {
  $("history-project").value = projectId;
  refreshCurrent();
}

function renderProjectOptions(projects, selected) {
  const select = $("history-project");
  const everything = new Option(t("history.all_projects"), "");
  select.replaceChildren(everything, ...projects.map((project) => new Option(project.name, project.project_id)));
  select.value = projects.some((project) => project.project_id === selected) ? selected : "";
}

function projectLink(project) {
  const td = document.createElement("td");
  const button = node("button", "link", project.name);
  button.type = "button";
  button.addEventListener("click", () => chooseProject(project.project_id));
  td.append(button);
  return td;
}

function renderHistory(data) {
  $("history-cost").textContent = usd(data.totals.cost_usd);
  $("history-estimated").textContent = Number(data.totals.estimated_usd) > 0
    ? t("history.estimated", { amount: usd(data.totals.estimated_usd) }) : "";
  $("history-calls").textContent = count(data.totals.calls);
  $("history-sessions").textContent = count(data.totals.sessions);
  $("history-tasks").textContent = count(data.totals.tasks);
  renderChart(data.by_day);
  renderProjectOptions(data.projects, data.project_id ?? "");
  $("history-months").replaceChildren(...data.by_month.map((m) =>
    row(m.month, usd(m.cost_usd), count(m.calls), count(m.sessions), count(m.tasks))));
  $("history-projects").replaceChildren(...data.projects.map((p) => row(projectLink(p), usd(p.cost_usd),
    `${localized(p.share_pct)} %`, count(p.calls), count(p.sessions), count(p.tasks), compact(p.tokens))));
  $("history-session-rows").replaceChildren(...data.sessions.map((s) => row(dateTime(s.ended_at), dateTime(s.started_at),
    s.project, s.host, count(s.calls), count(s.tasks), usd(s.cost_usd))));
  const shown = data.sessions.length;
  const total = data.totals.sessions;
  $("history-shown").textContent = !total ? t("history.empty")
    : shown < total ? t("history.shown", { shown: count(shown), total: count(total) }) : "";
}

async function refreshHistory() {
  const data = await window.pywebview.api.history(Number($("history-days").value), $("history-project").value || null);
  settle(data);
  if (!data.busy) renderHistory(data);
}

function insightCard(item) {
  const card = node("article", "insight");
  card.append(node("h3", "", item.title));
  const saving = item.saving_usd === null ? t("insights.no_saving") : t("insights.saving", { amount: usd(item.saving_usd) });
  card.append(node("p", "saving", saving), node("p", "muted", item.saving_basis), node("p", "", item.action));
  if (item.suggestion) {
    const button = node("button", "", t("changes.prepare"));
    button.type = "button";
    button.addEventListener("click", () => prepareChange(...item.suggestion));
    card.append(button);
  }
  return card;
}

async function refreshInsights() {
  const data = await window.pywebview.api.insights(30);
  settle(data);
  if (data.busy) return;
  $("insights-period").textContent = t("insights.period", { from: data.from, to: data.to });
  const list = $("insights-list");
  list.replaceChildren(...data.insights.map(insightCard));
  if (!data.insights.length) list.append(node("p", "muted", t("insights.none")));
  $("insights-note").textContent = data.note;
}

async function refreshSettings() {
  const data = await window.pywebview.api.settings();
  const form = $("settings-form");
  for (const [key, value] of Object.entries(data.values)) form.elements[key].value = value;
  setStatus(data.busy ? t("status.updating") : "");
  const checks = $("checks");
  checks.replaceChildren();
  for (const check of data.checks) {
    const item = node("li", check.status.toLowerCase());
    item.append(node("span", "badge", t(`check.${check.status.toLowerCase()}`)), node("span", "", `${check.check}: ${check.message}`));
    checks.append(item);
  }
}

let pending = null;

function actionCard(action) {
  const card = node("article", "action");
  card.dataset.action = action.id;
  card.append(node("h3", "", t(`action.${action.id}`)));
  card.append(node("p", "muted", action.current === null ? t("changes.unset") : t("changes.current", { value: action.current })));
  card.append(node("p", "muted", t(`action.${action.id}.note`)));
  const row = node("div", "actions");
  const select = document.createElement("select");
  select.setAttribute("aria-label", t(`action.${action.id}`));
  select.replaceChildren(...action.options.map((option) => new Option(option, option)));
  if (action.options.includes(action.current)) select.value = action.current;
  const button = node("button", "", t("changes.preview"));
  button.type = "button";
  button.disabled = action.options.length === 0;
  button.addEventListener("click", () => previewChange(action.id, select.value));
  row.append(select, button);
  card.append(row);
  return card;
}

function hideChangePreview() {
  pending = null;
  $("change-preview").hidden = true;
}

function showChangeMessage(message) {
  $("change-message").textContent = message;
}

async function previewChange(actionId, value) {
  hideChangePreview();
  const plan = await window.pywebview.api.preview(actionId, value);
  if (!plan.ok) {
    showChangeMessage(t(`error.${plan.code}`));
    return;
  }
  if (!plan.changed) {
    showChangeMessage(t("changes.same"));
    return;
  }
  showChangeMessage("");
  pending = plan;
  $("change-diff").textContent = plan.diff;
  $("change-preview").hidden = false;
  $("change-preview").scrollIntoView({ block: "nearest" });
}

async function confirmChange() {
  if (!pending) return;
  const plan = pending;
  hideChangePreview();
  const result = await window.pywebview.api.apply_action(plan.action, plan.new_value, plan.before_sha256);
  showChangeMessage(result.ok ? t("changes.applied") : t(`error.${result.code}`));
  refreshCurrent();
}

async function undoChange(changeId) {
  const result = await window.pywebview.api.undo_action(changeId);
  showChangeMessage(result.ok ? t("changes.undone") : t(`error.${result.code}`));
  refreshCurrent();
}

function effectText(effect) {
  if (!effect) return "—";
  if (!effect.enough) return t("changes.effect_wait", { tasks: effect.tasks_after });
  return t("changes.effect_figures", { before: usd(effect.before.cost_per_task), after: usd(effect.after.cost_per_task),
    retries_before: localized(effect.before.retries_per_task), retries_after: localized(effect.after.retries_per_task) });
}

function changeRow(change) {
  let last = change.undone_at ? t("changes.undone_label") : node("button", "", t("changes.undo"));
  if (last instanceof Node) {
    last.type = "button";
    last.addEventListener("click", () => undoChange(change.id));
    const td = document.createElement("td");
    td.append(last);
    last = td;
  }
  return row(dateTime(change.applied_at), t(`action.${change.action}`), `${change.old_value ?? "—"} → ${change.new_value}`,
    effectText(change.effect), last);
}

async function refreshChanges() {
  const [available, history] = await Promise.all([window.pywebview.api.actions(), window.pywebview.api.changes()]);
  $("action-list").replaceChildren(...available.actions.map(actionCard));
  $("change-rows").replaceChildren(...history.changes.map(changeRow));
  $("change-none").hidden = history.changes.length > 0;
  $("change-table").hidden = history.changes.length === 0;
  setStatus("");
}

async function prepareChange(actionId, value) {
  show("changes");
  await previewChange(actionId, value);
}

const REFRESH = { live: refreshLive, history: refreshHistory, insights: refreshInsights, changes: refreshChanges, settings: refreshSettings };
let current = "live";

function refreshCurrent() {
  return REFRESH[current]().catch((error) => setStatus(t("status.error", { message: error.message || error })));
}

function show(tab) {
  current = tab;
  for (const section of document.querySelectorAll("main > section")) section.hidden = section.id !== tab;
  for (const button of document.querySelectorAll("nav button")) {
    if (button.dataset.tab === tab) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
  refreshCurrent();
}

async function saveSettings(event) {
  event.preventDefault();
  const form = event.target;
  const message = $("settings-message");
  for (const key of ["budget.daily_usd", "budget.monthly_usd", "budget.plan_monthly_usd", "notify"]) {
    const result = await window.pywebview.api.save_setting(key, form.elements[key].value.trim());
    if (!result.ok) {
      message.textContent = result.error;
      return;
    }
  }
  message.textContent = t("settings.saved");
}

async function collectNow() {
  const message = $("settings-message");
  message.textContent = t("settings.collecting");
  const result = await window.pywebview.api.collect_now();
  message.textContent = result.status === "ok" ? t("settings.collected", { seconds: localized((result.duration_ms / 1000).toFixed(1)) })
    : result.status === "locked" ? t("settings.collect_busy") : result.message || t("settings.collect_failed");
  refreshCurrent();
}

function useTexts(result) {
  language = result.language;
  text = result.text;
  applyText();
}

async function changeLanguage(event) {
  useTexts(await window.pywebview.api.set_language(event.target.value));
  $("settings-message").textContent = "";
  refreshCurrent();
}

async function start() {
  useTexts(await window.pywebview.api.texts());
  renderProjectOptions([], "");
  for (const button of document.querySelectorAll("nav button")) {
    button.addEventListener("click", () => show(button.dataset.tab));
  }
  $("settings-form").addEventListener("submit", saveSettings);
  $("collect").addEventListener("click", collectNow);
  $("language").addEventListener("change", changeLanguage);
  $("history-days").addEventListener("change", refreshCurrent);
  $("history-project").addEventListener("change", refreshCurrent);
  $("change-confirm").addEventListener("click", confirmChange);
  $("change-cancel").addEventListener("click", hideChangePreview);
  window.agentMeterRefresh = () => (current === "settings" || current === "changes" ? undefined : refreshCurrent());
  window.setInterval(window.agentMeterRefresh, FALLBACK_REFRESH_MS);
  refreshCurrent();
}

if (window.pywebview?.api?.overview) start();
else window.addEventListener("pywebviewready", start, { once: true });
