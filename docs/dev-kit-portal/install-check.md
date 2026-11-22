# Install check — 2026-11-22

Every install command shown on the portal, run for real in a throwaway `HOME` (Claude Code, Antigravity) or tool dir
(uv), so the developer's own setup was not touched. Source: GitHub `main` at `44d0355`.

| Path | Command | Result |
| :-- | :-- | :-- |
| Claude Code marketplace | `claude plugin marketplace add jggomez/expert-ai-developer-skills` | exit 0 |
| Claude Code plugins (all 10) | `claude plugin install <plugin>@expert-ai-developer-skills` | exit 0 ×10; `python-backend` pulls `senior-dev` as a dependency |
| Claude Code orchestrator | `claude --agent senior-dev:senior-dev-orchestrator` | agent file present in the installed plugin |
| Antigravity plugins (all 10) | `git clone …` then `agy plugin install ./plugins/antigravity/<plugin>` | exit 0 ×10; `agy plugin list` shows all enabled |
| Skills CLI | `npx skills add jggomez/expert-ai-developer-skills --skill python-expert` | exit 0; `.agents/skills/python-expert/SKILL.md` written (asks for confirmation unless `-y`) |
| agent-meter CLI + app | `uv tool install "agent-meter[app] @ git+…#subdirectory=tools/agent-meter"` | **failed**: uv picked the system Python 3.10 (`requires-python >=3.11`) |
| agent-meter CLI + app (fixed) | `uv tool install --python 3.12 "agent-meter[app] @ git+…"` | exit 0; `agent-meter --version` → `agent-meter 0.1.0` |
| agent-meter installers | release `agent-meter-v0.1.0`: `…-mac-arm64.dmg`, `…-windows-x64.exe` | HTTP 200 both |
| pr-reviewer quick start | `git ls-remote …` + `curl … pr-review.yml \| sed "s/<commit-sha>/$SHA/"` | exit 0; SHA pinned, valid YAML |

## Fix applied

All agent-meter install commands now use `uv tool install --python 3.12 …` (tool READMEs EN/ES, root README,
`docs/agent-metrics/`, both plugin READMEs, the `agent-metrics` skill and its copies, the CLI hint in `cli.py`, and
the structure test). The stale `@feature/agent-metrics` example now points to the `agent-meter-v0.1.0` tag.

## Re-run after the merge — GitHub `main` at `116779d`

Same isolated setup, every command copied from the live portal.

| Path | Result |
| :-- | :-- |
| Claude Code marketplace + all 10 plugins | exit 0 ×10; installed `python-backend` has the new deploy-guard matcher and `rules/python-backend-rules.md`; orchestrator agent present |
| Antigravity, all 10 plugins from a fresh clone | exit 0 ×10 |
| Skills CLI (`--skill python-expert -y`) | exit 0; `.agents/skills/python-expert/SKILL.md` written |
| agent-meter `uv tool install --python 3.12 "agent-meter[app] @ git+…"` | exit 0; `agent-meter 0.1.0`; `doctor` and `pricing list` (moved to `cli_commands/`) work; `claude-fable-5-2` priced |
| agent-meter installers (`.dmg`, `.exe`) | HTTP 200 both |
| pr-reviewer quick start | exit 0; pinned to `116779d`, no `<commit-sha>` left, valid YAML |
| CI on `116779d` | agent-meter CI green on Linux, macOS and Windows (UI tests 9/9 on Linux); desktop build and self-test green on Windows and macOS |
