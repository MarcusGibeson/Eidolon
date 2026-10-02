# G-EXTRACT1 Design Revision Changelog

## Candidate v5

Parent candidate: v4 at `b966e789f4b489f0634ab8f2fcb1e3290f1acb4a`.

Scope: design and deterministic validation artifacts only. No blueprint, scored fixture, reserve, runtime implementation, provider call, or experiment execution was created.

### Rereview-4 findings

| Finding | Resolution | Binding location |
|---|---|---|
| Full prompt assembled as `SUBJECT.. Copy` | Resolved. SUBJECT is periodless; fragments join with `. `; the unchanged historical template supplies the one terminal period. Five complete prompt vectors bind final bytes and SHA-256. | operation v3; baseline v3 |
| Output binding and role vocabularies conflicted | Resolved. One eight-key output-field schema and three binding kinds drive corpus, gold, roles, E7, fingerprints, reserves, and vectors. `source_copy` is the role; EXACT_COPY is a producer/feature. | family assignment v3 |
| Exact-answer, identity, and date-number reuse were not derived | Resolved. Canonical bytes, comparison unit, atom derivation, ordering, duplicate behavior, six pair scopes, vectors, and fixture-level tuple extraction are frozen. | contamination v3 exact-reuse contract |
| E7 could depend on unresolved temporal/comparison values | Resolved. E7 has zero operation nodes, exactly one explicit absence, and at least two SOURCE_COPY outputs. Any operation or unresolved dependency is an authoring error. | family assignment v3 E7 graph contract |
| Phase A family floor lacked repeat reduction | Resolved. Positive properties require both repeats; adverse properties are affected by either repeat; family floor requires both repeats correct; four truth rows are frozen. | phase-A fixture reduction v1 |
| Decimal metadata policy conflicted with validation | Resolved. Metadata must already be canonical. `5.0`, `0.5`, `-0.5` pass; `5.00`, `0.50`, `-0.50`, `-0.0`, and exponent metadata fail. Provider number equivalence remains evaluator-only. | operation v3 and exact-value v1 |
| Distractor strings could carry coaching | Resolved. A conservative normalized token/phrase denylist applies to all authored string/entity values, with positive and negative vectors. | fact-record content-safety contract |
| COUNT lacked collection fact semantics | Resolved by removal. COUNT is absent from catalog, families, composed rows, and validation. | operation v3 |
| E7 was named as broad ambiguity | Resolved. Normative name is `explicit partial absence / not-provided handling`; the contract disclaims broad ambiguity measurement. Legacy container key remains only as a stable document field. | explicit-absence scoring v4 |
| Truncated accepted output could escape false-clean | Resolved. Truncation remains the primary outcome; accepted truncation is false-clean and unsafe, rejected truncation is contained but gets no semantic credit. | explicit-absence scoring v4 |
| Human/machine vocabulary drift | Resolved. Markdown and JSON use the same operation, output binding, role, decimal, E7, gate, integrity, baseline, and governance contracts. | both normative artifacts |
| Validator needed behavioral v5 coverage | Resolved. It renders full prompts, derives output roles and fingerprints from canonical fixtures, checks E7 graph legality, duplicate/truncation behavior, exact reuse, tuple extraction, decimal rejection, coaching rejection, COUNT removal, and repeat truth tables. | `validate_design.py` |

### Preserved design

Seven families, 35 fixtures per round, 30 determinate plus five E7, 420 Phase A calls, at most 210 Phase B calls, all gate values, 28 family-slot reserves, historical operational validator behavior, duplicate-aware evaluator distinction, contamination thresholds, integrity-event principles, verdict precedence, no A/B pooling, and no failed-cell reentry remain unchanged.

### Governance

G-ROUTE4 remains CLOSED FAILED and immutable. Provider/model calls remain zero. Scored and reserve fixture counts remain zero. Belief effects remain none. Separate authorization remains required for every later phase.
