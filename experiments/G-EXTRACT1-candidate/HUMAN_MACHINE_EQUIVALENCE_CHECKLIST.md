# G-EXTRACT1 v6 Human/Machine Equivalence Checklist

This checklist records reviewer-facing equivalence claims. `validate_design.py` checks the mechanics listed here, but its PASS is structural and cross-representational evidence only; it does not prove scientific validity.

| Normative area | Markdown | JSON | Deterministic check |
|---|---:|---:|---:|
| Design identity and authority flags | yes | yes | yes |
| Historical G-ROUTE4 bindings | yes | yes | digest checked |
| Scope, models, phases, and call counts | yes | yes | yes |
| Periodless SUBJECT and full prompt substitution | yes | yes | full bytes + SHA |
| Placeholder types and canonical literals | yes | yes | render/reject vectors |
| Two-node dependency and operation ordering | yes | yes | render vectors |
| SUM 2/3/4 operands and COUNT removal | yes | yes | behavioral vectors |
| Historical schema token vocabulary | yes | yes | parse/reject vectors |
| Schema-to-semantic/gold/role/tag mapping | yes | yes | exact mapping checks |
| Finite-enum grammar | yes | yes | valid/invalid vectors |
| Operation semantic/domain matrix | yes | yes | valid/invalid fixture vectors |
| Numeric promotion and terminating DIVIDE | yes | yes | exact evaluation vectors |
| Calendar/clock/elapsed policies | yes | yes | rollover/domain vectors |
| Source-reference cardinality | yes | yes | missing/duplicate vectors |
| Output producer/schema compatibility | yes | yes | mismatch vectors |
| Canonical eight-key output-field schema | yes | yes | exact-shape rejects |
| SOURCE_COPY, operation, and absence bindings | yes | yes | role derivation vectors |
| Typed five-key source facts | yes | yes | render/schema rejects |
| Positive factual-atom anti-coaching grammar | yes | yes | positive/negative vectors |
| Metadata-derived family precedence | yes | yes | adversarial family vectors |
| Derived secondary features and C1-C4 | yes | yes | derivation/count checks |
| E7 zero-node graph and explicit absence | yes | yes | valid/invalid vectors |
| Duplicate-aware evaluator vs historical parser | yes | yes | duplicate vectors |
| Explicit-absence outcome precedence | yes | yes | all primary paths |
| Accepted truncation false-clean rule | yes | yes | accepted/rejected vectors |
| Exact-value comparator semantics | yes | yes | contract assertions |
| Similarity normalization/tokenizer/Jaccard | yes | yes | token vectors/constants |
| End-to-end canonical fingerprints | yes | yes | derived byte vectors |
| Topological fingerprint order independence | yes | yes | reversed-node vectors |
| Exact whole-answer/identity/date-number reuse | yes | yes | canonical vectors |
| Six pairwise contamination scopes | yes | yes | exact set check |
| Independent contamination implementations | yes | yes | contract checks |
| 28 family-slot reserves | yes | yes | count/mapping vectors |
| Phase A repeat reduction | yes | yes | Boolean truth table |
| Phase A/B gates and confidence values | yes | yes | arithmetic checks |
| Cell carry-forward and no pooling | yes | yes | state assertions |
| Integrity event catalog | yes | yes | catalog/vector checks |
| Primary verdict precedence | yes | yes | terminal vectors |
| Baseline paths, hashes, and Git blobs | yes | yes | live verification |
| Model blobs and generation configuration | yes | yes | identity checks |
| Seed formula | yes | yes | exact check |
| Gold/adjudication freeze | yes | yes | governance assertions |
| Separate future authorization boundaries | yes | yes | all flags checked |
| Zero provider calls/fixtures/reserves | yes | yes | checked |
| Belief effects none | yes | yes | checked |

## Deliberate representation choices

- `ambiguity_contract` remains a stable JSON container key; its normative construct is explicit partial absence under `g-extract1.explicit-absence-scoring.v4`.
- Machine vector payloads are executable examples of co-normative prose, not additional scientific rules.
- Source-fact `schema_type` is evaluator metadata and is not rendered into the historical prompt.
- Artifact digests and Git blobs are enumerated in JSON and bound normatively in Markdown without duplicating every digest by hand.
- The generated validation report is evidence, not a third normative design representation.

## Blueprint boundary

A later blueprint may allocate IDs, instantiate frozen templates and quotas, define files, create schedules, and prepare implementation checklists. It may not invent schema aliases, source types, operation domains, prompt wording, output bindings, family tags, equivalence semantics, contamination rules, reserve choice, gate reduction, integrity events, or governance authority.
