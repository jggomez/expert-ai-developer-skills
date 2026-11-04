"""Command line used by the GitHub Action, one subcommand per step."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import cast, get_args

from pr_reviewer.context import ReviewContext, resolve_context
from pr_reviewer.diff import DEFAULT_MAX_CHARS, build_bundle, git_diff
from pr_reviewer.github import GitHubClient
from pr_reviewer.models import DiffBundle, ReviewReport, Severity
from pr_reviewer.providers.base import (
    DEFAULT_MAX_TOKENS,
    ProviderError,
    ReviewProvider,
    ReviewRequest,
)
from pr_reviewer.publish import PublishOptions, publish
from pr_reviewer.workspace import build_clean_workspace

MAX_ERROR_CHARS = 300


def _load_provider(name: str, fake_findings: Path | None) -> ReviewProvider:
    """Import lazily: each provider's SDK is an optional dependency."""
    if name == "fake":
        from pr_reviewer.providers.fake import FakeProvider

        return FakeProvider(fake_findings)
    if name == "antigravity":
        from pr_reviewer.providers.antigravity import AntigravityProvider

        return AntigravityProvider()
    raise ValueError(f"Unknown provider {name!r}")


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


def _github_client() -> GitHubClient:
    return GitHubClient(os.environ["GITHUB_TOKEN"])


def run_context(_: argparse.Namespace) -> int:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))

    def fetch_pr(repo: str, number: int) -> dict[str, object]:
        return _github_client().pull_request(repo, number)

    context = resolve_context(os.environ["GITHUB_EVENT_NAME"], event, fetch_pr)
    if not context.should_run:
        print(f"::notice title=pr-reviewer skipped::{context.reason}")
    _write_output(context)
    return 0


def run_diff(args: argparse.Namespace) -> int:
    text = git_diff(args.repo, args.base, args.head)
    patterns = [p.strip() for p in args.exclude.replace(",", "\n").splitlines() if p.strip()]
    bundle = build_bundle(text, base=args.base, head=args.head, exclude=patterns, max_chars=args.max_chars)
    args.output.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(f"Reviewing {len(bundle.files)} file(s), omitting {len(bundle.omitted)}")
    return 0


def _review(args: argparse.Namespace, bundle: DiffBundle) -> ReviewReport:
    if not bundle.files:
        return ReviewReport(status="ok", provider=args.provider)
    try:
        provider = _load_provider(args.provider, args.fake_findings)
        workspace = build_clean_workspace(args.repo, args.workspace)
        request = ReviewRequest(bundle=bundle, workspace=workspace, model=args.model or None, max_tokens=args.max_tokens)
        output = provider.review(request)
    except ProviderError as error:
        traceback.print_exc()
        return ReviewReport(
            status="failed",
            provider=args.provider,
            model=error.model,
            usage=error.usage,
            error=str(error)[:MAX_ERROR_CHARS],
        )
    except Exception as error:  # A failed review must never block the pull request.
        traceback.print_exc()
        return ReviewReport(
            status="failed",
            provider=args.provider,
            error=f"{type(error).__name__}: {error}"[:MAX_ERROR_CHARS],
        )
    return ReviewReport(
        status="ok",
        provider=args.provider,
        model=output.model,
        findings=output.result.findings,
        usage=output.usage,
    )


def run_review(args: argparse.Namespace) -> int:
    bundle = DiffBundle.model_validate_json(args.bundle.read_text(encoding="utf-8"))
    report = _review(args, bundle)
    args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(f"Review {report.status}: {len(report.findings)} finding(s)")
    return 0


def run_publish(args: argparse.Namespace) -> int:
    bundle = DiffBundle.model_validate_json(args.bundle.read_text(encoding="utf-8"))
    report = ReviewReport.model_validate_json(args.report.read_text(encoding="utf-8"))
    options = PublishOptions(max_findings=args.max_findings, min_severity=cast(Severity, args.min_severity))
    result = publish(_github_client(), args.repo_name, args.pr, report, bundle, options)
    print(f"Posted {result.inline_posted} inline comment(s); {result.already_posted} already posted")
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
    review.add_argument("--provider", required=True, choices=["antigravity", "fake"])
    review.add_argument("--repo", type=Path, required=True)
    review.add_argument("--bundle", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    review.add_argument("--workspace", type=Path, required=True, help="where to create the clean copy")
    review.add_argument("--model", default="")
    review.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    review.add_argument("--fake-findings", type=Path)
    review.set_defaults(func=run_review)

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
