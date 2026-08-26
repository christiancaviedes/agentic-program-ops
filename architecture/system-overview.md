# System Overview

## Design intent

Agentic Program Ops is a contract-first artifact compiler. It transforms a bounded program definition into consistent operating artifacts while keeping sequencing and risk acceptance under human control.

## Components

1. **Input adapter** reads a versionable JSON contract representing PRD intent and Jira-style workstreams.
2. **Validator** enforces required fields, unique workstream IDs, valid dependency references, and acyclic sequencing.
3. **Artifact compiler** produces roadmap, Mermaid dependency graph, RAID log, and executive brief.
4. **Evidence layer** records latency, artifact counts, risk/dependency counts, approval state, model cost, and an OpenTelemetry-compatible span record with trace/span IDs and semantic attributes.
5. **Human gate** separates generated drafts from approved planning baselines.
6. **Optional enrichment boundary** accepts a provider protocol only after validation and writes a separate, review-only suggestion artifact that cannot alter source facts.

## Trust boundaries

- User-supplied JSON is untrusted until validation completes.
- Generated prose is a planning aid, not authorization to ship or spend.
- Approval is explicit and recorded in output; it is not inferred from successful generation.
- CI validates repository behavior but cannot validate business assumptions.

## Extensibility

The read-only Jira Cloud adapter targets the same validated internal contract and never mutates Jira. The provider-neutral LLM enrichment protocol sits after validation, preserves the deterministic fallback, and cannot suppress the review gate or rewrite source artifacts.
