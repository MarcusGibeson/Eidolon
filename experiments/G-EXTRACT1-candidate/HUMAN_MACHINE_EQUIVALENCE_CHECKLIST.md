# G-EXTRACT1 v5 Human/Machine Equivalence Checklist

This checklist records reviewer-facing equivalence claims. `validate_design.py` checks many of them behaviorally, but the checklist and PASS report do not prove scientific validity.

| Normative area | Markdown | JSON | Deterministic check |
|---|---:|---:|---:|
| Design identity and authority flags | yes | yes | yes |
| Historical G-ROUTE4 bindings | yes | yes | digest checked |
| Scope, models, phases, and call counts | yes | yes | yes |
| Periodless SUBJECT and full prompt substitution | yes | yes | full bytes + SHA |
| Placeholder types and canonical literals | yes | yes | render/reject vectors |
| Two-node dependency and operation ordering | yes | yes | render vectors |
| SUM 2/3/4 operands | yes | yes | behavioral vectors |
| COUNT removal | yes | yes | catalog assertion |
| Historical absence instruction | yes | yes | source artifact checked |
| Canonical output-field schema | yes | yes | exact key/role vectors |
| SOURCE_COPY and EXACT_COPY distinction | yes | yes | role derivation vectors |
| Typed source facts and sentence rendering | yes | yes | behavioral vectors |
| String/distractor coaching exclusion | yes | yes | positive/negative vectors |
| Metadata-derived family precedence | yes | yes | adversarial family vectors |
| Derived secondary features | yes | yes | adversarial feature vectors |
| C1-C4 composed rows | yes | yes | shape/count checks |
| E7 zero-node graph restrictions | yes | yes | valid/invalid vectors |
| Explicit-partial-absence outcome precedence | yes | yes | classifier vectors |
| Duplicate-aware evaluator vs historical parser | yes | yes | duplicate vectors |
| Accepted truncation false-clean rule | yes | yes | accepted/rejected vectors |
| Exact-value comparator semantics | yes | yes | contract assertions |
| Similarity normalization/tokenizer/Jaccard | yes | yes | token vectors and constants |
| End-to-end canonical fingerprints | yes | yes | four fixture vectors |
| Exact whole-answer reuse | yes | yes | canonical comparison vectors |
| Entity/identifier reuse | yes | yes | atom intersection vectors |
| Date-number tuple extraction/reuse | yes | yes | fixture extraction + order vectors |
| Six pairwise contamination scopes | yes | yes | exact set check |
| Independent contamination implementations | yes | yes | contract checks |
| 28 family-slot reserves | yes | yes | count/mapping vectors |
| Phase A repeat reduction | yes | yes | complete Boolean truth table |
| Phase A/B gates and confidence values | yes | yes | arithmetic checks |
| Cell carry-forward and no pooling | yes | yes | state assertions |
| Integrity event catalog | yes | yes | catalog/vector checks |
| Primary verdict precedence | yes | yes | terminal vectors |
| Baseline artifacts, paths, hashes, blobs | yes | yes | live file verification |
| Model blobs and generation configuration | yes | yes | identity checks |
| Seed formula | yes | yes | exact string check |
| Gold/adjudication freeze | yes | yes | governance assertions |
| Separate future authorization boundaries | yes | yes | all flags checked |
| Zero provider calls/fixtures/reserves | yes | yes | checked |
| Belief effects none | yes | yes | checked |

## Deliberate representation choices

- `ambiguity_contract` remains the JSON container name for compatibility; its normative ID and construct are `g-extract1.explicit-absence-scoring.v4` and explicit partial absence.
- Machine-only vector payloads are executable examples of prose rules, not extra scientific rules.
- SHA-256 and Git blob bindings are enumerated in JSON and described as normative in Markdown; duplicating every digest in prose is unnecessary and risks transcription drift.
- The validation report is generated evidence and is not co-normative.

## Blueprint boundary

A later blueprint may allocate IDs, instantiate already-frozen templates and quotas, define files, create schedules, and prepare implementation checklists. It may not invent prompt wording, output bindings, family tags, equivalence semantics, contamination rules, reserve choice, gate reduction, integrity events, or governance authority.
