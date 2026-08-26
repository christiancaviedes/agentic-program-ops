from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """Raised when program input cannot produce trustworthy artifacts."""


@dataclass(frozen=True)
class RunResult:
    output_dir: Path
    files: tuple[Path, ...]
    metrics: dict[str, Any]


def load_program(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise InputError("Input root must be a JSON object")
    validate_program(data)
    return data


def validate_program(data: dict[str, Any]) -> None:
    for field in ("program", "objective", "target_date", "workstreams"):
        if not data.get(field):
            raise InputError(f"Missing required field: {field}")
    workstreams = data["workstreams"]
    if not isinstance(workstreams, list) or not workstreams:
        raise InputError("workstreams must be a non-empty array")

    ids: list[str] = []
    for index, item in enumerate(workstreams):
        if not isinstance(item, dict):
            raise InputError(f"workstreams[{index}] must be an object")
        for field in ("id", "title", "owner", "team"):
            if not item.get(field):
                raise InputError(f"workstreams[{index}] missing {field}")
        ids.append(item["id"])
    if len(ids) != len(set(ids)):
        raise InputError("workstream ids must be unique")

    known = set(ids)
    graph: dict[str, list[str]] = {}
    for item in workstreams:
        dependencies = item.get("depends_on", [])
        if not isinstance(dependencies, list):
            raise InputError(f"{item['id']}.depends_on must be an array")
        unknown = set(dependencies) - known
        if unknown:
            raise InputError(f"{item['id']} has unknown dependencies: {', '.join(sorted(unknown))}")
        graph[item["id"]] = dependencies
    _reject_cycles(graph)


def _reject_cycles(graph: dict[str, list[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise InputError(f"Dependency cycle detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def generate_artifacts(data: dict[str, Any], output_dir: Path, approved: bool = False) -> RunResult:
    started = time.perf_counter()
    started_ns = time.time_ns()
    output_dir.mkdir(parents=True, exist_ok=True)
    review_status = "APPROVED FOR PLANNING" if approved else "DRAFT — HUMAN REVIEW REQUIRED"
    workstreams = data["workstreams"]
    risks = _all_risks(data)
    blocked = [item for item in workstreams if item.get("status", "planned").lower() == "blocked"]

    artifacts = {
        "roadmap.md": _roadmap(data, review_status),
        "dependencies.mmd": _dependencies(data),
        "raid-log.md": _raid_log(data, review_status),
        "executive-brief.md": _executive_brief(data, review_status, blocked, risks),
    }
    paths: list[Path] = []
    for name, content in artifacts.items():
        path = output_dir / name
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        paths.append(path)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    metrics = {
        "workstreams": len(workstreams),
        "dependencies": sum(len(item.get("depends_on", [])) for item in workstreams),
        "blocked_workstreams": len(blocked),
        "open_risks": len(risks),
        "human_review": not approved,
        "latency_ms": elapsed_ms,
        "estimated_model_cost_usd": 0,
    }
    metrics_path = output_dir / "run-metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    paths.append(metrics_path)

    trace = {
        "schema": "opentelemetry-span-v1",
        "trace_id": secrets.token_hex(16),
        "span_id": secrets.token_hex(8),
        "name": "program_ops.compile",
        "kind": "INTERNAL",
        "start_time_unix_nano": started_ns,
        "end_time_unix_nano": time.time_ns(),
        "status": {"code": "OK"},
        "resource": {"service.name": "agentic-program-ops", "service.version": "0.3.0"},
        "attributes": {
            "program.name": data["program"],
            "artifact.count": len(artifacts),
            "workstream.count": len(workstreams),
            "dependency.count": metrics["dependencies"],
            "risk.count": metrics["open_risks"],
            "human_review.required": not approved,
            "model.cost.usd": 0,
        },
        "events": [{
            "time_unix_nano": time.time_ns(),
            "name": "artifact_generation_completed",
            "attributes": {"review.status": review_status},
        }],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    trace_path = output_dir / "trace.jsonl"
    trace_path.write_text(json.dumps(trace) + "\n", encoding="utf-8")
    paths.append(trace_path)
    return RunResult(output_dir=output_dir, files=tuple(paths), metrics=metrics)


def _all_risks(data: dict[str, Any]) -> list[dict[str, str]]:
    risks = list(data.get("risks", []))
    for workstream in data["workstreams"]:
        for risk in workstream.get("risks", []):
            risks.append({
                "risk": risk if isinstance(risk, str) else risk.get("risk", "Unspecified risk"),
                "owner": workstream["owner"],
                "severity": "medium",
                "mitigation": "Owner to define mitigation before execution.",
            })
    return risks


def _roadmap(data: dict[str, Any], status: str) -> str:
    rows = []
    for item in data["workstreams"]:
        dependencies = ", ".join(item.get("depends_on", [])) or "None"
        deliverables = "; ".join(item.get("deliverables", [])) or "TBD"
        rows.append(
            f"| {item['id']} | {item['title']} | {item['owner']} / {item['team']} | "
            f"{item.get('window', 'TBD')} | {dependencies} | {item.get('status', 'planned')} | {deliverables} |"
        )
    return f"""# Roadmap: {data['program']}

> **{status}**

**Objective:** {data['objective']}  
**Target date:** {data['target_date']}  
**Executive owner:** {data.get('executive_owner', 'TBD')}

| ID | Workstream | Owner / team | Window | Depends on | Status | Exit criteria |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Operating cadence

- Weekly dependency and RAID review
- Biweekly executive decision review
- Launch-readiness gate before production exposure
- Human approval required for scope, sequencing, and risk acceptance
"""


def _dependencies(data: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for item in data["workstreams"]:
        label = item["title"].replace('"', "'")
        lines.append(f'  {item["id"]}["{item["id"]}: {label}"]')
    for item in data["workstreams"]:
        for dependency in item.get("depends_on", []):
            lines.append(f"  {dependency} --> {item['id']}")
    return "\n".join(lines)


def _raid_log(data: dict[str, Any], status: str) -> str:
    risks = _all_risks(data)
    risk_rows = [
        f"| R{index:02d} | {risk.get('risk', 'Unspecified')} | {risk.get('severity', 'medium')} | "
        f"{risk.get('owner', 'TBD')} | {risk.get('mitigation', 'TBD')} | Open |"
        for index, risk in enumerate(risks, 1)
    ] or ["| — | No risks supplied; validate in review | — | Program lead | Run risk workshop | Open |"]
    assumptions = data.get("assumptions", ["Resourcing remains available through target date."])
    decisions = data.get("decisions", [])
    assumption_rows = [f"| A{index:02d} | {text} | Program lead | Validate |" for index, text in enumerate(assumptions, 1)]
    decision_rows = [
        f"| D{index:02d} | {item.get('decision', 'TBD')} | {item.get('owner', 'TBD')} | {item.get('due', 'TBD')} | Open |"
        for index, item in enumerate(decisions, 1)
    ] or ["| D01 | Approve roadmap and risk posture | Executive owner | Before kickoff | Open |"]
    return f"""# RAID Log: {data['program']}

> **{status}**

## Risks

| ID | Risk | Severity | Owner | Mitigation | Status |
|---|---|---|---|---|---|
{chr(10).join(risk_rows)}

## Assumptions

| ID | Assumption | Owner | Validation |
|---|---|---|---|
{chr(10).join(assumption_rows)}

## Decisions

| ID | Decision | Owner | Due | Status |
|---|---|---|---|---|
{chr(10).join(decision_rows)}
"""


def _executive_brief(
    data: dict[str, Any], status: str, blocked: list[dict[str, Any]], risks: list[dict[str, str]]
) -> str:
    blocked_names = ", ".join(item["title"] for item in blocked) or "None"
    decision_text = "; ".join(item.get("decision", "TBD") for item in data.get("decisions", [])) or "Approve scope and risk posture."
    return f"""# Executive Brief: {data['program']}

> **{status}**

## Outcome

{data['objective']}

## Delivery posture

- Target: **{data['target_date']}**
- Workstreams: **{len(data['workstreams'])}**
- Blocked: **{len(blocked)}** ({blocked_names})
- Open risks: **{len(risks)}**

## Decisions needed

{decision_text}

## Leadership ask

Confirm sequencing, named owners, and risk acceptance before the plan is used for execution.
"""
