"""Read-only Jira Cloud adapter for the validated program contract."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .core import InputError, validate_program


def fetch_jira_issues(
    base_url: str,
    email: str,
    api_token: str,
    jql: str,
    *,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Fetch Jira issues with least-privilege GET access and a bounded field set."""
    if not base_url.startswith("https://"):
        raise InputError("Jira base URL must use https://")
    query = urllib.parse.urlencode({
        "jql": jql,
        "maxResults": 100,
        "fields": "summary,assignee,project,status,duedate,issuelinks,labels,description",
    })
    url = f"{base_url.rstrip('/')}/rest/api/3/search?{query}"
    credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Basic {credentials}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise InputError(f"Jira request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise InputError(f"Jira request failed: {exc.reason}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("issues"), list):
        raise InputError("Jira response did not contain an issues array")
    return payload


def jira_issues_to_program(payload: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Map Jira Cloud search results into the compiler's internal contract."""
    issues = payload.get("issues", [])
    if not issues:
        raise InputError("Jira query returned no issues")
    issue_keys = {issue.get("key") for issue in issues}
    workstreams = []
    for issue in issues:
        key = issue.get("key")
        fields = issue.get("fields") or {}
        if not key:
            raise InputError("Jira issue missing key")
        assignee = fields.get("assignee") or {}
        project = fields.get("project") or {}
        status = fields.get("status") or {}
        dependencies = []
        for link in fields.get("issuelinks") or []:
            link_type = link.get("type") or {}
            inward = link.get("inwardIssue") or {}
            if link_type.get("name", "").casefold() == "blocks" and inward.get("key") in issue_keys:
                dependencies.append(inward["key"])
        workstreams.append({
            "id": key,
            "title": fields.get("summary") or key,
            "owner": assignee.get("displayName") or "Unassigned",
            "team": project.get("name") or project.get("key") or "Jira",
            "window": fields.get("duedate") or "TBD",
            "status": (status.get("name") or "planned").casefold(),
            "depends_on": sorted(set(dependencies)),
            "deliverables": [f"Resolve {key} against acceptance criteria"],
            "source_url": f"{metadata.get('jira_base_url', '').rstrip('/')}/browse/{key}",
            "labels": fields.get("labels") or [],
        })
    program = {
        "program": metadata.get("program"),
        "objective": metadata.get("objective"),
        "target_date": metadata.get("target_date"),
        "executive_owner": metadata.get("executive_owner", "TBD"),
        "assumptions": metadata.get("assumptions", []),
        "decisions": metadata.get("decisions", []),
        "risks": metadata.get("risks", []),
        "source": {"type": "jira-cloud", "jql": metadata.get("jql", "")},
        "workstreams": workstreams,
    }
    validate_program(program)
    return program


def load_metadata(path: Path) -> dict[str, Any]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid metadata JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(metadata, dict):
        raise InputError("Metadata root must be an object")
    return metadata
