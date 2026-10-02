# G-EXTRACT1 Design Revision Changelog

This record maps the third adversarial rereview of commit `196958184bd2f3aacc4e2ee4798c5811aed0a342` to design candidate v4. All changes are prospective design/checking changes. No blueprint, fixture, reserve, runner, scorer, provider call, or experiment run was created.

## Third-rereview findings

| Finding | Disposition | Candidate v4 repair |
|---|---|---|
| SUBJECT placeholder bytes were underdefined | Resolved | Operation contract v2 adds typed placeholders, exact identifier/literal/string rendering, connected graph rule, SUM bounds/punctuation, per-operation allowed kinds, and nine executable rendering vectors. |
| Family and secondary-feature metadata were not fully derived | Resolved | Family contract v2 defines the canonical fixture/fact representation, exact derivation of every family field and secondary tag, wrapped-numeric E3 behavior, output roles, and five adversarial family vectors. |
| C3 aggregation-to-binding was ambiguous | Resolved | C3 is exactly a numeric node followed by `EXACT_COPY` of that derived target; E3 explicitly recognizes this wrapped-numeric graph. |
| Duplicate keys could receive ambiguity credit | Resolved | Ambiguity contract v3 separates unchanged operational parsing from duplicate-aware semantic parsing. Duplicate-key operational acceptance is false-clean and can never be `exact_valid_not_provided`; five vectors exercise it. |
| Fingerprint inputs depended on prose interpretation | Resolved | Typed fact records render one sentence each; fact roles, entity indices, output roles, operand kinds, and source layout are finite derivations with layout/rejection vectors. |
| Post-contact gold defect lacked its own event | Resolved | Added `POST_CONTACT_GOLD_DEFECT_DISCOVERED`, distinct from `POST_CONTACT_GOLD_MUTATION`, both invalid. |
| Interruption/checkpoint failure states were prose-only | Resolved | Added corrupt, missing, and unverifiable checkpoint/journal events plus provider-failure-without-receipt and classification vectors. |
| Reserve count contradicted one-to-one language | Resolved | Reserve contract v3 is explicitly one slot per phase x round x family: 28 total. It freezes slot IDs, ordered primaries, one profile, single-claim activation, and stop behavior. |
| Independent contamination implementations were vague | Resolved | Requires separately authored modules with no shared normative helpers; only contract/data and standard-library primitives may be shared; byte disagreement blocks freeze. |
| Tokenizer handled dates as signed fragments | Resolved | Tokenizer precedence is date, time, context-valid number, identifier. Frozen vectors cover dates, times, negatives, subtraction, exponent, currency, underscore, and hyphen. |
| Validator checked presence more than behavior | Resolved | Validator v3 renders operation vectors, derives family/features, classifies duplicate outputs, tokenizes vectors, classifies layouts/reserves/events/verdicts, and retains its non-scientific claim boundary. |

## Preserved design

- Seven families; 35 fixtures per round; 30 determinate plus five E7.
- Phase A two repeats and 420 calls; Phase B one observation and at most 210 calls; maximum 630.
- Gates remain 29/30 semantic, 29/30 structural, 27/30 useful acceptance, zero false-clean, E7 A 10/10, E7 B 5/5, malformed at most one.
- Historical `not_provided` behavior, system/template bindings, models/configuration, no prompt repair, no A/B pooling, and no failed-cell reentry remain unchanged.
- G-ROUTE4 remains closed failed and immutable; belief effects remain none.

## Deferred under separate authority

- Authorability and scientific representativeness require separately authorized blueprint and corpus review.
- Production scorer/comparator/runner remain unimplemented.
- Provider option honoring remains unattested internally by Ollama.
- Deterministic validation does not establish scientific validity or replace adversarial rereview.
