"""CLI entry point for optional, provider-neutral program enrichment."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .core import InputError, load_program
from .enrichment import OpenAICompatibleProvider, enrich_program


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="program-ops-enrich")
    parser.add_argument("input", type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--token-env", default="LLM_API_KEY")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    api_key = os.environ.get(args.token_env)
    if not api_key:
        print(f"error: set {args.token_env}", file=sys.stderr)
        return 2
    try:
        provider = OpenAICompatibleProvider(args.base_url, args.model, api_key)
        result = enrich_program(load_program(args.input), provider)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (InputError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "status": result["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
