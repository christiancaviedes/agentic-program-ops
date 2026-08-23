# System Overview

## Design intent

Agentic Program Ops is a contract-first artifact compiler. It transforms a bounded program definition into consistent operating artifacts while keeping sequencing and risk acceptance under human control.

## Components

1. **Input adapter** reads a versionable JSON contract representing PRD intent and Jira-style workstreams.
2. **Validator** enforces required fields, unique workstream IDs, valid dependency references, and acyclic sequencing.
3. **Artifact compiler** produces roadmap, Mermaid dependency graph, RAID log, and executive brief.
4. **Evidence layer** records latency, artifact counts, risk/dependency counts, approval state, model cost, and a trace event.
5. **Human gate** separates generated drafts from approved planning baselines.

## Trust boundaries

- User-supplied JSON is untrusted until validation completes.
- Generated prose is a planning aid, not authorization to ship or spend.
- Approval is explicit and recorded in output; it is not inferred from successful generation.
- CI validates repository behavior but cannot validate business assumptions.

## Extensibility

Future LLM and ticket-system adapters should target the same validated internal contract. They must not write around the validator, suppress the review gate, or mutate source systems without an explicit connector-specific authorization layer.
