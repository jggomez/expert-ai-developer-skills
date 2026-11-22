# Test matrix — dev-kit-portal

Commands (from `portal/`): `npm test` (vitest), `npm run build && npx playwright test` (E2E on `dist/`),
`npx playwright test -c playwright.live.config.mjs` (same journeys on https://senior-ai-dev-kit.web.app).

| TC | Objective | Steps | Expected result | Automated test |
| :-- | :-- | :-- | :-- | :-- |
| TC-01 | Catalog mirrors the repo | Build catalog from repo root | 10 plugins, 40 skills, 19 agents, 11 rules, 16 workflows, 3 sidecars, 2 tools; unique ids, GitHub source, host | `tests/unit/catalog.test.mjs` |
| TC-02 | Relations and install commands | Read `plugin/senior-dev`, `skill/context-capture` | Agents/skills/hooks linked; `claude plugin install …`, `agy …`, `npx skills add …` | `catalog.test.mjs` |
| TC-03 | Builder works on any root, fails loudly | Fixture repo; broken frontmatter | Counts match fixture; `Invalid frontmatter` thrown | `catalog.test.mjs` |
| TC-04 | Every item is bilingual | Check es/en title, summary, use for every id | No missing or stale translation | `tests/unit/i18n.test.mjs` |
| TC-05 | Pipeline points at real items | Resolve every pipeline id | All ids exist in catalog | `i18n.test.mjs` |
| TC-06 | Language redirect | Open `/` with es-MX and en-US | `/es/` and `/en/` | `tests/e2e/portal.spec.mjs` |
| TC-07 | Search and filters | Kind chip, text search, empty state, clear | 19 hooks; flutter matches; empty message; 120 again | `portal.spec.mjs` |
| TC-08 | Host filter | Select Antigravity | Only items with the antigravity host | `portal.spec.mjs` |
| TC-09 | Pipeline explorer | Click Verify, ArrowRight, open item | Panels switch; Ship selected; item page opens | `portal.spec.mjs` |
| TC-10 | Detail, copy, language switch | `/es/plugin/senior-dev/`, copy, switch | Command in clipboard, "Copiado"; `/en/plugin/senior-dev/` | `portal.spec.mjs` |
| TC-11 | 404 | Open unknown path | HTTP 404, bilingual page | `portal.spec.mjs` |
| TC-12 | Responsive, no console errors | 375/768/1280/1920 on home and detail | No horizontal scroll; screenshots in `evidence/` | `portal.spec.mjs` |
