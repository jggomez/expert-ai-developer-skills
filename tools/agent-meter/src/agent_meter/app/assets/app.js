"use strict";

const FALLBACK_REFRESH_MS = 30000;
const LEVELS = { ok: "On track", warn: "Near limit", over: "Over limit" };
const $ = (id) => document.getElementById(id);
const usd = (value) => (value === null || value === undefined ? "—"
  : "$" + Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function ago(minutes) {
  return minutes < 1 ? "Just now" : `${minutes} min ago`;
}

function setStatus(text) {
  $("status").textContent = text;
}

function renderBudgets(lines) {
  const box = $("budgets");
  box.replaceChildren();
  if (!lines.length) {
    box.append(node("p", "muted", "No budgets yet. Add one in Settings."));
    return;
  }
  for (const line of lines) {
    const row = node("div", `budget ${line.level}`);
    row.append(node("span", "", `${line.label}, ${line.period}`));
    row.append(node("span", "", `${usd(line.spent_usd)} of ${usd(line.limit_usd)}`));
    row.append(node("span", "badge", LEVELS[line.level]));
    const meter = node("progress");
    meter.max = 100;
    meter.value = Math.min(Number(line.percent), 100);
    meter.setAttribute("aria-label", `${line.percent}% used`);
    row.append(meter);
    box.append(row);
  }
}

function renderSessions(sessions) {
  const body = $("sessions");
  body.replaceChildren();
  for (const s of sessions) {
    const row = document.createElement("tr");
    row.append(cell(s.project), cell(s.host), cell(Number(s.calls).toLocaleString("en-US")), cell(usd(s.cost_usd)),
      cell(s.context_tokens === null ? "—" : `${Math.round(s.context_tokens / 1000)}k tokens`), cell(ago(s.minutes_ago)));
    body.append(row);
  }
  $("no-sessions").hidden = sessions.length > 0;
  $("sessions-table").hidden = sessions.length === 0;
}

async function refreshLive() {
  const data = await window.pywebview.api.overview();
  if (data.busy) {
    setStatus("Updating data…");
    return;
  }
  $("today").textContent = usd(data.today_usd);
  $("month").textContent = usd(data.month_usd);
  $("forecast").textContent = usd(data.forecast_usd);
  $("plan").textContent = data.plan_value_ratio ? `${data.plan_value_ratio}x` : "Not set";
  renderBudgets(data.budgets);
  renderSessions(data.sessions);
  setStatus(`Updated ${new Date().toLocaleTimeString()}`);
}

function insightCard(item) {
  const card = node("article", "insight");
  card.append(node("h3", "", item.title));
  const saving = item.saving_usd === null ? "No savings estimate" : `About ${usd(item.saving_usd)} (estimate)`;
  card.append(node("p", "saving", saving), node("p", "muted", item.saving_basis), node("p", "", item.action));
  return card;
}

async function refreshInsights() {
  const data = await window.pywebview.api.insights(30);
  if (data.busy) {
    setStatus("Updating data…");
    return;
  }
  $("insights-period").textContent = `${data.from} to ${data.to}. Findings are measured, and savings are estimates.`;
  const list = $("insights-list");
  list.replaceChildren(...data.insights.map(insightCard));
  if (!data.insights.length) list.append(node("p", "muted", "No rule fired in this period."));
  $("insights-note").textContent = data.note;
}

async function refreshSettings() {
  const data = await window.pywebview.api.settings();
  const form = $("settings-form");
  for (const [key, value] of Object.entries(data.values)) form.elements[key].value = value;
  const checks = $("checks");
  checks.replaceChildren();
  for (const check of data.checks) {
    const item = node("li", check.status.toLowerCase());
    item.append(node("span", "badge", check.status), node("span", "", `${check.check}: ${check.message}`));
    checks.append(item);
  }
}

const REFRESH = { live: refreshLive, insights: refreshInsights, settings: refreshSettings };
let current = "live";

function refreshCurrent() {
  return REFRESH[current]().catch((error) => setStatus(`Could not load data: ${error.message || error}`));
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
  message.textContent = "Saved";
}

async function collectNow() {
  const message = $("settings-message");
  message.textContent = "Collecting…";
  const result = await window.pywebview.api.collect_now();
  message.textContent = result.status === "ok" ? `Collected in ${(result.duration_ms / 1000).toFixed(1)} s`
    : result.status === "locked" ? "Busy. Try again in a minute." : result.message || "Collect failed";
  refreshCurrent();
}

function start() {
  for (const button of document.querySelectorAll("nav button")) {
    button.addEventListener("click", () => show(button.dataset.tab));
  }
  $("settings-form").addEventListener("submit", saveSettings);
  $("collect").addEventListener("click", collectNow);
  window.agentMeterRefresh = () => (current === "settings" ? undefined : refreshCurrent());
  window.setInterval(window.agentMeterRefresh, FALLBACK_REFRESH_MS);
  refreshCurrent();
}

if (window.pywebview?.api?.overview) start();
else window.addEventListener("pywebviewready", start, { once: true });
