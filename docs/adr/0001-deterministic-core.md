# ADR 0001: Start with a deterministic artifact compiler

- **Status:** Accepted
- **Date:** 2026-08-23

## Context

The portfolio prototype described multiple agents but could not be executed, tested, or evaluated. Adding an LLM first would create impressive prose without proving the correctness of dependency handling, approval state, or operational failure behavior.

## Decision

Version 0.1 uses a dependency-free Python core that validates structured program input and deterministically compiles operating artifacts. Model-backed enrichment is deferred behind the same contract.

## Consequences

### Positive

- Fast, repeatable, offline execution
- Zero provider cost and no credential requirement
- Exact regression tests for critical program logic
- Clear seam for future provider-neutral enrichment

### Negative

- Input must already be structured JSON
- Prose synthesis is intentionally bounded
- It does not infer missing workstreams or stakeholder intent

## Revisit trigger

Add optional model enrichment only after there is an eval dataset for faithfulness, risk preservation, and unsupported-claim detection.

