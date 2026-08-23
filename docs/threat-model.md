# Threat Model

## Assets

- Program plans and internal delivery dates
- Team/owner information
- Decision and risk records
- Approval status and generated artifacts

## Primary threats and controls

| Threat | Impact | Control |
|---|---|---|
| Malformed or adversarial input | Misleading plan or runtime failure | Strict JSON contract validation and non-zero failure |
| Fabricated dependency references | False sequencing confidence | Unknown references rejected before generation |
| Cyclic plans | Impossible delivery order | Graph cycle detection |
| Automation bias | Draft treated as approved plan | Human-review marker by default; explicit approval action |
| Sensitive data committed to Git | Information disclosure | Example data is synthetic; future adapters require redaction policy |
| Workflow token overreach | Repository compromise | GitHub Actions use job-specific least-privilege permissions |
| Dependency compromise | Supply-chain exposure | No runtime third-party dependencies in v0.1 |
| Model hallucination in future enrichment | Unsupported claims or dropped risks | Deterministic core remains authoritative; eval and human gates required |

## Out of scope for v0.1

- Authentication and multi-tenant authorization
- Direct Jira/Linear writes
- Handling regulated personal or customer data
- Autonomous execution against production systems

Any deployment adding these capabilities requires a new threat-model review.

