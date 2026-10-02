# G-EXTRACT1 Design Revision Changelog

## Candidate v6

Parent candidate: v5 at `1302c49d68b4fd15eab47a92faa687817f59b442`.

Scope: design and deterministic validation artifacts only. No blueprint, scored fixture, reserve, corpus, production implementation, provider call, or experiment execution was created.

### Rereview-5 findings

| Finding | Resolution | Binding location |
|---|---|---|
| Historical schema vocabulary and semantics were incomplete | Resolved. `g-extract1.schema-types.v1` freezes the six primitive tokens, finite-enum grammar, semantic tags, gold forms, source kinds, output roles, producer compatibility, and contamination tags. Aliases and unknown tokens are authoring errors. | design sections 4 and 6; machine `schema_type_contract` |
| Source facts did not carry enough type identity to distinguish integral NUMBER from INTEGER | Resolved prospectively. The canonical source-fact record now includes non-rendered `schema_type`; literal kind and schema must agree. That schema drives source references, SOURCE_COPY, ENTITY_FIELD_BIND, EXACT_COPY, gold, and fingerprints without changing prompt bytes. | design sections 5.1 and 7; five-key fact contract |
| Operations were syntactically but not semantically typed | Resolved. `g-extract1.operation-semantics.v1` freezes operand compatibility, numeric promotion, result schema, exact domain restrictions, source cardinality, two-node compatibility, and deterministic gold for every authorable operation. | design section 5; machine `operation_semantics_contract` |
| Division and temporal edge behavior were implicit | Resolved. DIVIDE requires a nonzero divisor and a terminating reduced decimal; calendar offsets are 0..366; clock offsets are 0..1439 modulo one day; elapsed time is forward with next-day rollover and equality equal to zero. | design sections 5.2-5.3 |
| Source references and producer/output schemas could disagree | Resolved. Ordinary references resolve exactly one non-entity typed VALUE fact; entity facts require ENTITY_FIELD_BIND; every output schema must exactly match the frozen producer semantic result. | design sections 5.1 and 6 |
| Anti-coaching denylist was bypassable | Resolved. Arbitrary prose is unavailable. String/entity facts use a positive factual-atom grammar with bounded ASCII, length, word count, punctuation, finite statuses/codes/labels, plus a reserved-token defense. Required adversarial phrases fail while benign factual labels pass. | design section 7; fact content-safety contract |
| Explicit-absence classifier vectors missed primary paths | Resolved. Behavioral vectors now cover empty bytes, malformed JSON, string and array roots, schema-invalid objects, duplicate accepted objects, exact absence, unsupported values, supported-field errors, and accepted/rejected truncation. | explicit-absence scoring v4; validator |
| Output-field shape checks were incomplete | Resolved. The validator enforces the exact eight keys and rejects missing/extra keys, unknown schemas, and incompatible binding fields in addition to producer/schema mismatches. | canonical output contract; validator |
| Operation validator lacked required invalid-domain cases | Resolved. Behavioral vectors reject zero/nonterminating division, illegal types and offsets, wrong result schemas, missing/duplicate references, and incompatible chains while accepting representative exact arithmetic and temporal cases. | operation semantics v1; validator |
| Fingerprint validation could inherit supplied operation order or injected derivations | Resolved. Fingerprints independently topologically order canonical operation nodes, derive output roles, boundary, temporal pattern, and source layout, and are checked against frozen bytes including reversed-input-order vectors. | contamination v3; validator |
| Exact-answer contamination tags could drift from schema aliases | Resolved. Canonical answers use only schema-types.v1 tags: STRING, NUMBER, INTEGER, BOOLEAN, DATE, TIME, and ENUM. No `date` or `time` aliases remain. | schema-types v1; contamination v3 |
| Human/machine semantic rules could diverge | Resolved. Both normative artifacts now describe the same schema vocabulary, typed source facts, operation domains, source cardinality, result compatibility, positive value grammar, and unchanged governance boundaries. | both co-normative artifacts; equivalence checklist |

### Preserved design

The periodless SUBJECT/full-prompt hashes, unchanged historical suffix, canonical output bindings, E7 zero-operation explicit partial absence, duplicate-aware evaluator, accepted-truncation false-clean rule, COUNT removal, canonical decimal metadata, contamination thresholds, 28 reserve slots, Phase A repeat reductions, gates, integrity events, result precedence, no A/B pooling, and no failed-cell reentry remain unchanged.

### Governance

G-ROUTE4 remains CLOSED FAILED and immutable. Provider/model calls, scored fixtures, and reserve fixtures remain zero. Belief effects remain none. Separate authorization remains required for blueprint, fixture/gold authoring, implementation, pilot, execution freeze, Phase A, and Phase B.
