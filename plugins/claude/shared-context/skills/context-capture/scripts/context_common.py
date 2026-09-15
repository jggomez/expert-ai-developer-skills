#!/usr/bin/env python3
"""Shared helpers for the shared-context plugin's capture/pack/rollup scripts.

Stdlib only, host-neutral: the same code runs whether invoked by Claude Code
(`Bash`) or Antigravity CLI (`run_command`). Every script keeps a session's
`manifest.json`, `summary.md` and `decisions.md` loose (fast to browse and
diff in a PR); the heavier detail is packed into `detail.tar.xz`.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

DEFAULT_CONFIG = {
    "autosave": {"everyNToolCalls": 25, "everyMinutes": 10, "onStop": True},
    "compression": {"format": "tar.xz", "keepUncompressedSessions": 5},
    "retention": {"maxSessions": 100, "maxAgeDays": 90},
    "capture": {"includeGitDiff": True, "maxDiffLines": 400, "redactSecrets": True},
    "restore": {"askBeforeLoad": True, "autoLoadPreferences": False},
}

# Stays loose in every session dir (the "what / why").
LOOSE_FILES = ("manifest.json", "summary.md", "decisions.md")
# Packed into detail.tar.xz (the "how / detail").
DETAIL_MEMBERS = ("flows.md", "topics.md", "files-touched.json", "git-context.md", "artifacts")
DETAIL_ARCHIVE = "detail.tar.xz"
FULL_ARCHIVE = "full.tar.xz"

_SECRET_PATTERNS = [
    ("stripe-key", r"sk_live_[0-9a-zA-Z]{24}"),
    ("aws-akid", r"AKIA[0-9A-Z]{16}"),
    ("aws-secret", r"(?i)aws_secret_access_key\s*[:=]\s*['\"][0-9a-zA-Z/+=]{40}['\"]"),
    ("openai-key", r"sk-[0-9a-zA-Z]{48}"),
    ("google-api-key", r"AIza[0-9A-Za-z\-_]{35}"),
    ("private-key-block", r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    ("slack-webhook", r"https://hooks\.slack\.com/services/T[0-9A-Za-z_]+/B[0-9A-Za-z_]+/[0-9A-Za-z_]+"),
    ("bearer-token", r"(?i)bearer\s+[0-9a-zA-Z._\-]{20,}"),
    ("generic-secret",
     r"(?i)(api[_-]?key|secret|passwd|password|token|credential)s?\s*[:=]\s*['\"][0-9a-zA-Z_\-./+=]{16,}['\"]"),
]
_SECRET_RE = [(name, re.compile(pat)) for name, pat in _SECRET_PATTERNS]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def eprint(*args):
    print(*args, file=sys.stderr)


def resolve_context_dir(arg=None):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("SHARED_CONTEXT_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.path.join(os.getcwd(), "context"))


def detect_host(explicit=None):
    if explicit and explicit != "auto":
        return explicit
    for var in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "CLAUDECODE"):
        if os.environ.get(var):
            return "claude-code"
    for var in ("ANTIGRAVITY", "AGY_PLUGIN_ROOT", "GEMINI_CLI"):
        if os.environ.get(var):
            return "antigravity"
    return "unknown"


def current_user():
    for var in ("SHARED_CONTEXT_USER", "USER", "USERNAME", "LOGNAME"):
        v = os.environ.get(var)
        if v:
            return re.sub(r"[^0-9A-Za-z._-]", "", v) or "agent"
    try:
        import getpass
        return re.sub(r"[^0-9A-Za-z._-]", "", getpass.getuser()) or "agent"
    except Exception:
        return "agent"


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config(context_dir, create=True):
    path = os.path.join(context_dir, ".contextrc.json")
    user_cfg = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                user_cfg = json.load(f) or {}
        except (OSError, ValueError):
            user_cfg = {}
    elif create:
        os.makedirs(context_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
            f.write("\n")
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_CONFIG.items()}
    for k, v in user_cfg.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


def redact_text(text):
    """Returns (redacted_text, [finding_type, ...])."""
    findings = []

    def _repl(match, name):
        findings.append(name)
        return f"«REDACTED:{name}»"

    for name, rx in _SECRET_RE:
        text = rx.sub(lambda m, n=name: _repl(m, n), text)
    return text, findings


def ensure_scaffold(context_dir):
    """Creates context/, .contextrc.json, .gitattributes and the .gitignore
    entry for .session-state.json. Idempotent."""
    os.makedirs(context_dir, exist_ok=True)
    load_config(context_dir, create=True)

    ga = os.path.join(context_dir, ".gitattributes")
    if not os.path.exists(ga):
        with open(ga, "w", encoding="utf-8") as f:
            f.write("*.tar.xz binary -diff\n*.md text\n*.json text\n")

    gi = os.path.join(context_dir, ".gitignore")
    lines = []
    if os.path.exists(gi):
        with open(gi, encoding="utf-8") as f:
            lines = f.read().splitlines()
    changed = False
    for entry in (".session-state.json", "*.tmp"):
        if entry not in lines:
            lines.append(entry)
            changed = True
    if changed:
        with open(gi, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def git_output(args, repo):
    try:
        res = subprocess.run(["git", "-C", repo] + args,
                             capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return res.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def collect_git(repo, max_diff_lines):
    branch = git_output(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    head = git_output(["rev-parse", "--short", "HEAD"], repo)
    diffstat = git_output(["diff", "--stat"], repo).splitlines()
    truncated = len(diffstat) > max_diff_lines
    if truncated:
        diffstat = diffstat[:max_diff_lines]
    return {
        "branch": branch or None,
        "head": head or None,
        "diffstat": "\n".join(diffstat),
        "diffstatTruncated": truncated,
        "recentCommits": git_output(["log", "--oneline", "-10"], repo),
    }


def iter_session_dirs(context_dir):
    """Yields (date_str, session_id, path) for every session dir, ascending."""
    if not os.path.isdir(context_dir):
        return
    for date_name in sorted(os.listdir(context_dir)):
        date_path = os.path.join(context_dir, date_name)
        if not os.path.isdir(date_path) or not _DATE_RE.match(date_name):
            continue
        for sess in sorted(os.listdir(date_path)):
            sp = os.path.join(date_path, sess)
            if os.path.isdir(sp):
                yield date_name, sess, sp


def read_manifest(session_path):
    mp = os.path.join(session_path, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def dir_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except OSError:
                pass
    return total


def human_size(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{int(n)}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{int(n)}B"


def regenerate_index(context_dir):
    """(Re)writes context/INDEX.md from every session's manifest.json."""
    rows = []
    for date_name, sess, sp in iter_session_dirs(context_dir):
        m = read_manifest(sp)
        started = m.get("started", "")
        rows.append({
            "date": date_name,
            "session": sess,
            "time": started[11:16] if len(started) >= 16 else sess[:5],
            "host": m.get("host", "?"),
            "agent": m.get("agent", "?"),
            "model": m.get("model", "?"),
            "status": m.get("status", "?"),
            "task": (m.get("task") or "").replace("\n", " ").strip(),
            "archived": os.path.exists(os.path.join(sp, FULL_ARCHIVE)),
        })
    rows.sort(key=lambda r: (r["date"], r["session"]), reverse=True)

    lines = [
        "# Shared Context Index",
        "",
        f"_{len(rows)} session(s). Regenerated {iso(now_utc())}. Newest first._",
        "",
        "| Date | Session | Host | Agent | Model | Status | Task |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for r in rows:
        task = r["task"][:80] + ("…" if len(r["task"]) > 80 else "")
        flag = " _(archived)_" if r["archived"] else ""
        lines.append(
            f"| {r['date']} | `{r['session']}` | {r['host']} | {r['agent']} | "
            f"{r['model']} | {r['status']} | {task}{flag} |"
        )
    has_pref = os.path.exists(os.path.join(context_dir, "preferences.md"))
    has_arch = os.path.exists(os.path.join(context_dir, "architecture.md"))
    lines += [
        "",
        "## Long-lived files",
        "",
        f"- `preferences.md` — {'present' if has_pref else 'not yet created'}",
        f"- `architecture.md` — {'present' if has_arch else 'not yet created'}",
        "",
    ]
    with open(os.path.join(context_dir, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(rows)
