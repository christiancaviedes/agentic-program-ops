from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import InputError, generate_artifacts, load_program


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="program-ops",
        description="Generate a roadmap, dependency graph, RAID log, and executive brief from program input.",
    )
    parser.add_argument("input", type=Path, help="PRD/Jira-style program input as JSON")
    parser.add_argument("--output", "-o", type=Path, default=Path("build/program-plan"))
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Mark outputs approved for planning. Without this flag they require human review.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        program = load_program(args.input)
        result = generate_artifacts(program, args.output, approved=args.approve)
    except (InputError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(result.output_dir), "metrics": result.metrics}, indent=2))
    return 0

