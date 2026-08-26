"""CLI entry point for importing a read-only Jira Cloud program snapshot."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .core import InputError
from .jira import fetch_jira_issues, jira_issues_to_program, load_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="program-ops-jira")
    parser.add_argument("--base-url", default=os.environ.get("JIRA_BASE_URL"))
    parser.add_argument("--email", default=os.environ.get("JIRA_EMAIL"))
    parser.add_argument("--token-env", default="JIRA_API_TOKEN", help="Environment variable containing a Jira API token")
    parser.add_argument("--jql", required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get(args.token_env)
    if not args.base_url or not args.email or not token:
        print(f"error: set --base-url, --email, and {args.token_env}", file=sys.stderr)
        return 2
    try:
        metadata = load_metadata(args.metadata)
        metadata.update({"jira_base_url": args.base_url, "jql": args.jql})
        payload = fetch_jira_issues(args.base_url, args.email, token, args.jql)
        program = jira_issues_to_program(payload, metadata)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(program, indent=2) + "\n", encoding="utf-8")
    except (InputError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "workstreams": len(program["workstreams"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
