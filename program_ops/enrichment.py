"""Provider-neutral, review-only LLM enrichment behind the validated contract."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from .core import InputError, validate_program


class EnrichmentProvider(Protocol):
    """Minimal provider contract; transport-specific adapters implement this method."""

    @property
    def identity(self) -> dict[str, str]: ...

    def complete(self, system: str, user: str) -> str: ...


class OpenAICompatibleProvider:
    """Adapter for OpenAI-compatible chat-completions endpoints, including local gateways."""

    def __init__(self, base_url: str, model: str, api_key: str, timeout: float = 30.0):
        allowed_local = base_url.startswith(("http://127.0.0.1", "http://localhost"))
        if not base_url.startswith("https://") and not allowed_local:
            raise InputError("enrichment endpoint must use https:// or localhost")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    @property
    def identity(self) -> dict[str, str]:
        return {"adapter": "openai-compatible", "model": self.model, "base_url": self.base_url}

    def complete(self, system: str, user: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode()
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise InputError("enrichment provider returned an unexpected response") from exc
        except urllib.error.HTTPError as exc:
            raise InputError(f"enrichment provider returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise InputError(f"enrichment provider failed: {exc.reason}") from exc


def enrich_program(data: dict[str, Any], provider: EnrichmentProvider) -> dict[str, Any]:
    """Generate bounded suggestions without mutating the validated source program."""
    validate_program(data)
    system = (
        "You are a program-analysis assistant. Return JSON only with keys executive_narrative "
        "(string), questions (array of strings), and risk_notes (array of strings). Do not change "
        "owners, dates, dependencies, status, approval state, or source facts. State uncertainty."
    )
    user = json.dumps({
        "program": data["program"],
        "objective": data["objective"],
        "target_date": data["target_date"],
        "workstreams": data["workstreams"],
        "risks": data.get("risks", []),
        "decisions": data.get("decisions", []),
    }, separators=(",", ":"))
    raw = provider.complete(system, user)
    try:
        suggestions = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError("enrichment provider did not return valid JSON") from exc
    if not isinstance(suggestions, dict):
        raise InputError("enrichment response root must be an object")
    if not isinstance(suggestions.get("executive_narrative"), str):
        raise InputError("enrichment response missing executive_narrative")
    for field in ("questions", "risk_notes"):
        if not isinstance(suggestions.get(field), list) or not all(isinstance(item, str) for item in suggestions[field]):
            raise InputError(f"enrichment response {field} must be an array of strings")
    return {
        "status": "DRAFT — HUMAN REVIEW REQUIRED",
        "source_program": data["program"],
        "provider": provider.identity,
        "suggestions": suggestions,
        "guardrails": {
            "source_mutated": False,
            "dependency_changes_allowed": False,
            "approval_inferred": False,
        },
    }
