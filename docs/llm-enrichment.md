# Optional LLM Enrichment

The deterministic compiler remains the source of truth. `program-ops-enrich` adds a bounded,
review-only layer for executive narrative, unresolved questions, and risk notes after the
program contract validates.

The core depends on an `EnrichmentProvider` protocol rather than a model vendor. The included
adapter targets OpenAI-compatible chat-completions endpoints, including local gateways.

```bash
export LLM_API_KEY="..."

program-ops-enrich examples/launch-input.json \
  --base-url https://api.example.com \
  --model provider-model-name \
  --output build/enrichment.json
```

## Guardrails

- The API credential is read from an environment variable, not a command argument.
- Input must pass the deterministic validator before any provider call.
- Output is separate from source artifacts and always marked for human review.
- The provider is instructed not to change owners, dates, dependencies, status, or approval.
- The response must match a bounded JSON shape.
- Output records adapter/model/base URL, but never the credential.
- Provider failure does not prevent the deterministic compiler from running.

No live provider benchmark is committed because this repository does not have or require a
provider credential. Unit tests use a fake provider to exercise the boundary without making
network calls.
