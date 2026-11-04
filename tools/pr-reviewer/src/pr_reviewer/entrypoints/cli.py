"""Command line used by the GitHub Action, one subcommand per step."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import cast, get_args

from pr_reviewer.adapters.filesystem.clean_workspace import build_clean_workspace
from pr_reviewer.adapters.git.diff_reader import GitDiffReader
from pr_reviewer.application.ports import DEFAULT_BUDGET_USD, DEFAULT_MAX_TOKENS
from pr_reviewer.application.prepare_diff import prepare_diff
from pr_reviewer.application.publish_review import publish_review
from pr_reviewer.application.run_review import ReviewSettings, run_review
from pr_reviewer.domain.file_selection import DEFAULT_MAX_CHARS
from pr_reviewer.domain.findings import PublishOptions
from pr_reviewer.domain.models import DiffBundle, ReviewReport, Severity
from pr_reviewer.domain.triggers import ReviewContext, resolve_context
from pr_reviewer.entrypoints.composition import (
    github_client,
    load_provider,
    pull_request_gateway,
    setup_claude,
)


def _write_output(context: ReviewContext) -> None:
    values = {
        "should_run": str(context.should_run).lower(),
        "repo": context.repo,
        "pr_number": str(context.pr_number),
        "base_sha": context.base_sha,
        "head_sha": context.head_sha,
    }
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def run_context(_: argparse.Namespace) -> int:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))

    def fetch_pr(repo: str, number: int) -> dict[str, object]:
        return github_client().pull_request(repo, number)

    context = resolve_context(os.environ["GITHUB_EVENT_NAME"], event, fetch_pr)
    if not context.should_run:
        print(f"::notice title=pr-reviewer skipped::{context.reason}")
    _write_output(context)
    return 0


def run_diff(args: argparse.Namespace) -> int:
    patterns = [p.strip() for p in args.exclude.replace(",", "\n").splitlines() if p.strip()]
    bundle = prepare_diff(
        GitDiffReader(args.repo),
        base=args.base,
        head=args.head,
        exclude=patterns,
        max_chars=args.max_chars,
    )
    args.output.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(f"Reviewing {len(bundle.files)} file(s), omitting {len(bundle.omitted)}")
    return 0


def run_review_command(args: argparse.Namespace) -> int:
    bundle = DiffBundle.model_validate_json(args.bundle.read_text(encoding="utf-8"))
    report = run_review(
        bundle,
        ReviewSettings(
            provider=args.provider,
            model=args.model or None,
            max_tokens=args.max_tokens,
            budget_usd=args.budget_usd,
        ),
        load_provider=lambda: load_provider(args.provider, args.fake_findings),
        build_workspace=lambda: build_clean_workspace(args.repo, args.workspace),
    )
    args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(f"Review {report.status}: {len(report.findings)} finding(s)")
    return 0


def run_publish(args: argparse.Namespace) -> int:
    bundle = DiffBundle.model_validate_json(args.bundle.read_text(encoding="utf-8"))
    report = ReviewReport.model_validate_json(args.report.read_text(encoding="utf-8"))
    options = PublishOptions(max_findings=args.max_findings, min_severity=cast(Severity, args.min_severity))
    result = publish_review(pull_request_gateway(args.repo_name, args.pr), report, bundle, options)
    print(f"Posted {result.inline_posted} inline comment(s); {result.already_posted} already posted")
    return 0


def run_setup_claude(_: argparse.Namespace) -> int:
    agent_id, environment_id = setup_claude()
    print("Save these as repository variables:")
    print(f"CLAUDE_AGENT_ID={agent_id}")
    print(f"CLAUDE_ENVIRONMENT_ID={environment_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr-reviewer", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    context = commands.add_parser("context", help="decide from the GitHub event whether to review")
    context.set_defaults(func=run_context)

    diff = commands.add_parser("diff", help="compute the diff to review")
    diff.add_argument("--repo", type=Path, required=True)
    diff.add_argument("--base", required=True)
    diff.add_argument("--head", required=True)
    diff.add_argument("--output", type=Path, required=True)
    diff.add_argument("--exclude", default="", help="extra patterns, separated by commas or new lines")
    diff.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    diff.set_defaults(func=run_diff)

    review = commands.add_parser("review", help="run the provider and write a report")
    review.add_argument("--provider", required=True, choices=["antigravity", "claude", "fake"])
    review.add_argument("--repo", type=Path, required=True)
    review.add_argument("--bundle", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    review.add_argument("--workspace", type=Path, required=True, help="where to create the clean copy")
    review.add_argument("--model", default="")
    review.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    review.add_argument("--budget-usd", default=DEFAULT_BUDGET_USD, help="spend limit for providers that enforce one")
    review.add_argument("--fake-findings", type=Path)
    review.set_defaults(func=run_review_command)

    setup = commands.add_parser("setup-claude", help="create the Claude agent and environment, once")
    setup.set_defaults(func=run_setup_claude)

    post = commands.add_parser("publish", help="post the report to the pull request")
    post.add_argument("--bundle", type=Path, required=True)
    post.add_argument("--report", type=Path, required=True)
    post.add_argument("--repo-name", required=True)
    post.add_argument("--pr", type=int, required=True)
    post.add_argument("--max-findings", type=int, default=10)
    post.add_argument("--min-severity", choices=get_args(Severity), default="low")
    post.set_defaults(func=run_publish)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    try:
        code: int = args.func(args)
    except Exception as error:  # The review only comments, so it must never block a merge.
        traceback.print_exc()
        print(f"::warning title=pr-reviewer::{args.command} failed: {type(error).__name__}")
        return 0
    return code


if __name__ == "__main__":
    sys.exit(main())
