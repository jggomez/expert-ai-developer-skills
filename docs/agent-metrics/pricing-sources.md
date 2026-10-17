# agent-meter — Pricing Sources (fetched 2026-10-16)

> Seed data for `tools/agent-meter/src/agent_meter/pricing.yaml`. All prices are **USD per 1M tokens**, standard (non-batch, non-priority, global routing) first-party API rates.
> These values were fetched from the official pages on 2026-10-16 by the orchestrator. They must never be "corrected" from memory; refresh by re-fetching the source URLs.
> agent-meter reports **API-equivalent cost** (PRD OQ-2): subscription users (Claude Max, Google AI plans) do not actually pay these amounts.

## 1. Anthropic — https://platform.claude.com/docs/en/about-claude/pricing
| Model id (as seen in transcripts) | Input | Cache write 5m | Cache write 1h | Cache read | Output | Notes |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `claude-opus-5-5` | 4.00 | 5.00 | 8.00 | 0.20 | 20.00 | cache read = 0.05x input |
| `claude-sonnet-5-5` | 2.00 | 2.50 | 4.00 | 0.10 | 10.00 | cache read = 0.05x input |
| `claude-sonnet-5` | 2.00 | 2.50 | 4.00 | 0.20 | 10.00 | introductory $2/$10 became the standard price; the planned 2026-09-01 increase did not happen |
| `claude-opus-5` | 5.00 | 6.25 | 10.00 | 0.50 | 25.00 | |
| `claude-opus-4-8` | 5.00 | 6.25 | 10.00 | 0.50 | 25.00 | |
| `claude-sonnet-4-6` | 3.00 | 3.75 | 6.00 | 0.30 | 15.00 | also used inside Antigravity |
| `claude-haiku-4-5` / `claude-haiku-4-5-20251001` | 1.00 | 1.25 | 2.00 | 0.10 | 5.00 | dated id seen in Claude Code transcripts → alias to `claude-haiku-4-5` |
| `claude-haiku-5-5` (prompt ≤ 100K tokens) | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 | tiered by **prompt length incl. cache reads/writes**, per request |
| `claude-haiku-5-5` (prompt > 100K tokens) | 0.50 | 0.625 | 1.00 | 0.05 | 2.50 | |
| `claude-fable-5-1` | 10.00 | 12.50 | 20.00 | 0.25 | 50.00 | |

Rules from the page that affect computation:
- Claude 4.6+ (except Haiku 5.5): full 1M context at standard price (no long-context tier).
- `inference_geo` US-only: 1.1x on all token categories for 4.6+ (`usage.inference_geo` is in transcripts; v1 may ignore and document, or apply when present).
- Fast mode (Opus 5.5: $8 / $40) — premium pricing when `usage.speed == "fast"`; treat as a separate price row if observed.
- Batch: 50% off (not applicable to interactive coding agents).
- `<synthetic>` model entries are not billable.

## 2. Google Gemini API — https://ai.google.dev/gemini-api/docs/pricing (paid tier, Standard)
| Model id | Input | Cache read | Output | effective window |
| :--- | ---: | ---: | ---: | :--- |
| `gemini-3.8-flash` | 0.75 | 0.075 | 3.75 | through 2026-12-31 |
| `gemini-3.8-flash` | 1.50 | 0.15 | 7.50 | from 2027-01-01 |
| `gemini-3.6-flash` | 0.75 | 0.075 | 3.75 | through 2026-12-31 |
| `gemini-3.6-flash` | 1.50 | 0.15 | 7.50 | from 2027-01-01 |
| `gemini-4-argon` | 2.00 | 0.10 | 10.00 | through 2026-11-30 |
| `gemini-4-argon` | 4.00 | 0.20 | 20.00 | from 2026-12-01 |
| `gemini-3.1-pro-preview` (prompt ≤ 200K) | 2.00 | 0.20 | 12.00 | |
| `gemini-3.1-pro-preview` (prompt > 200K) | 4.00 | 0.40 | 18.00 | |
| `gemini-3-flash-preview` (text) | 0.50 | 0.05 | 3.00 | |
| `gemini-3.5-flash-lite` | 0.30 | 0.03 | 2.50 | |

Notes:
- Output price includes thinking tokens.
- Gemini context caching also bills **storage per token-hour**; it cannot be derived from agent logs → excluded and documented as a known under-estimate.
- Antigravity does not report cache writes; there is no write premium on Gemini (cache creation is billed as input).
- These dated price changes are exactly what `effective_from` in `pricing.yaml` is for (one row per window).

## 3. Antigravity internal model ids → pricing alias proposal
Antigravity logs internal ids (from `gen_metadata` field `1.19`). Proposal for ADR-001 (architect to ratify):

| Internal id (observed) | Proposed mapping | Flag |
| :--- | :--- | :--- |
| `gemini-3.8-flash` | `gemini-3.8-flash` | exact |
| `gemini-3.6-flash` | `gemini-3.6-flash` | exact |
| `gemini-4-argon` | `gemini-4-argon` | exact |
| `claude-sonnet-4-6` | `claude-sonnet-4-6` | exact |
| `gemini-3.8-flash-n` | `gemini-3.8-flash` | `estimated` (variant suffix) |
| `gemini-flash-3.6-high-control` | `gemini-3.6-flash` | `estimated` (variant) |
| `gemini-3.7-flash`, `gemini-3.7-flash-control` | none on public page | `unpriced` unless the user sets an alias |
| `gemini-pro-default`, `gemini-default`, `agy-demo-high`, `agy-demo-medium` | unknown routing aliases | `unpriced` unless the user sets an alias |
| display names like `Gemini 3.1 Pro (High)`, `Gemini 3.5 Flash (Medium)` (field `1.21`) | may disambiguate defaults: `Gemini 3.1 Pro` → `gemini-3.1-pro-preview`; `Gemini 3.5 Flash` not on page | `estimated` when used |

Display rule (PRD BR-02): estimated → value shown with `*`; unpriced → total shown as `≥ $X (N calls unpriced)`, never `$0`. Users can add aliases in `~/.agent-meter/pricing.local.yaml` (merged over the shipped table).
