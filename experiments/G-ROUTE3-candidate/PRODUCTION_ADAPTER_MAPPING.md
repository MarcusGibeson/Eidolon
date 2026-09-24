# Prospective production-adapter mapping

**No production authority is granted by this document or by G-ROUTE3.** This maps what a future adapter
would consume if G-ROUTE3 passed and a separate governed task later authorized one.

| Stage | Input | Output | G-ROUTE3 component that stands in for it |
|---|---|---|---|
| Task classification | the request | one of the six task classes | fixture `task_class` (assigned, not inferred) |
| Risk classification | the request and its consequences | R1–R4 | fixture `consequence_risk` (assigned, not inferred) |
| Qualification lookup | task × risk | qualified tiers in cost order | `routing_lookup` in the frozen `QUALIFICATION_TABLE.json` |
| Tier selection | qualified tiers | cheapest qualified tier, or `no_qualified_model` | `g_route3_routing.route` |
| Generation | request, tier | raw output | provider boundary (zero retries, fresh session) |
| Transport canonicalization | raw output | payload plus provenance | `g_route2_normalization.normalize` |
| Operational validation | payload | `output_accepted` | frozen gold-blind operational validator |
| Conservative triggers | payload, request context | escalation reasons | `g_route3_routing.triggers_for` |
| Stop decision | three verdicts | stop, next qualified tier, or fail closed | `g_route3_routing.verdicts` |
| Terminal outcomes | — | `stopped`, `no_qualified_model`, `escalation_exhausted`, `evidence_only` | same |

## Gaps a production adapter would still have

- **Classification is assumed.** G-ROUTE3 hands the router the correct task and risk class. A real task or
  risk classifier would introduce its own error, and nothing here measures it.
- **The table is pilot scale.** Four observations per cell cannot license production reliance on its own.
- **R4 remains evidence-only.** No adapter may select a model adaptively for R4.
- **Tables age.** A model upgrade, a configuration change or a prompt-profile change invalidates the table. A
  production adapter would need re-qualification bound to exact model digests.
- **Operational acceptance is not correctness.** Qualification reduces the risk of trusting it; it does not
  remove that risk. G-ROUTE3 measures how much risk remains.
