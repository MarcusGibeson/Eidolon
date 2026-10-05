# G-CAL1 Prospective Calendar Diagnostic

The co-normative machine contract is `DESIGN.json`. This new experiment does not
reopen G-EXTRACT1 (closed, valid, negative qualification result) or G-ROUTE4
(closed failed). It tests fresh calendar cases, not the cause of earlier errors.

## Task And Baseline

Only qwen3.8:27b on frozen Ollama 0.34.3 is in scope. The complete historical
G-EXTRACT1 system text and structured-extraction template are bound by actual
file hash and reused without editing. The SUBJECT joins `Extract the record
record` and `{target} is {date_field} plus {offset} calendar days` with exactly
`. `; it has no terminal period. The historical template supplies that period.
Negative offsets are signed integer literals in the same operation template.
No examples, reasoning requests, boundary labels or historical failures enter
the request. Configuration is temperature 0.45, top_p 0.9, top_k 40,
repeat_penalty 1.1, num_ctx 8192, num_predict 350, stream/think/fallback false,
retry/repair zero, fresh session true. Provider option honoring remains
unattested, not silently verified.

G-CAL1 independently defines signed, nonzero offsets -367..367 inclusive.
Source is day zero; negative means subtract calendar days. Gregorian leap rules
include the 100/400-year exceptions. Valid dates are zero-padded YYYY-MM-DD,
years 0001..9999, with no timezone. Out-of-range results are authoring errors.
This does not amend G-EXTRACT1's nonnegative domain.

## Allocation And Freshness

There are 40 logical fixtures, ten per C1-C4, and two repeats (80 calls maximum).
C1 stays within one month; C2 crosses December/January in both directions;
C3 covers leap/common February, Feb28/29/Mar1, and 100/400-century rules;
C4 covers signed 364/365/366/367 offsets with and without traversing Feb29.
Each stratum has five positive and five negative offsets. Exact slot offsets,
month and century pools and C4 leap-path allocation are frozen in DESIGN.json.
Ordinary years are 2051..2099. Candidate search is deterministic, rejects
unacceptable candidates, and retains rejection evidence before any contact.

IDs are G-CAL1-C1-01 through G-CAL1-C4-10. Field ordinal is
`4*(slot-1)+stratum_index`, not stratum-major. Every input contains the DATE
fact followed by one quoted neutral `code_{ordinal}_99` STRING fact; only the
date result is requested. Identifiers are f{ordinal}_01/f{ordinal}_02 and
d{ordinal}_01. The code is a uniform ignored fact with no answer content.
It prospectively differentiates the historical-compatible source-layout
projection from old one-fact calendar templates; its possible difficulty
effect limits comparison to G-EXTRACT1. We do not claim exact fixture-layout
equivalence or causal isolation of lexical effects.

Isolated offsets, including 365/366, may recur, as explicitly clarified before
corpus authoring. Source dates, applicable DATE gold, signed date/offset pairs,
complete cases, input payloads, requests and eligible typed date-number tuples
must be fresh. Sources and answers are also disjoint within this corpus.
All G-EXTRACT1 scored/reserve variants (including unexecuted B) and actual
G-ROUTE1/3/4 extraction corpora are screened. Historical duplicate inputs stay
distinct comparisons. Date lexemes in historical source text and prompts are
conservatively excluded. Gold comes from datetime arithmetic and a separate
manual Gregorian day-step implementation, agreeing before freeze.

## Contamination Applicability

Reuse the accepted normalization, ordinal masking, tokenizer, typed freshness,
whole-answer and typed tuple representations. Similarity includes input.text
and schema, not system/SUBJECT/record type/instructions. Historical comparisons
always require ordinary Jaccard <0.20; full 3-component projection collision
is prohibited; two matching components require Jaccard <0.12. G-ROUTE4 and
G-EXTRACT1 use the frozen suffix adapter. Older G-ROUTE1/3 use only their
observable schema/token kinds/instruction surface; subject ends at `. Copy
names` if present, otherwise the full prompt. No semantic graphs are invented.
Legacy typed-tuple provenance is unavailable: report NOT_APPLICABLE, never a
pass. G-EXTRACT1 typed tuples are applicable.

G-ROUTE1/3 historical finite enums include case-sensitive currency tokens such
as EUR|USD|GBP. Their schema bytes and selected option are preserved, not
retrospectively subjected to G-EXTRACT1's lowercase new-authoring grammar.
Projection uses ENUM and exact option count. Older JSON numeric gold is parsed
with Decimal, not host binary floats. Whole-answer representation retains the
accepted name/schema/tag/text shape and UTF-8 name order.

All new pairs share a preregistered two-fact source scaffold. Explicitly freeze
its structural recurrence ledger. Use the accepted declared-scaffold residual
control, never declare high ordinary similarity a pass: remove only invariant
five-grams under symbolic replacement of the DATE, require nonempty residuals
and residual Jaccard <0.12. No DATE-containing gram is removed. Report ordinary,
shape and content views. Exact case/answer/tuple controls still apply to all
pairs. No historical pair receives a scaffold exemption. This is necessary
to distinguish fixed formatting from repeated calendar content, not to hide
reuse of values or waive a failed historical check.

## Schedule And Metrics

Repeat 1 precedes repeat 2. Each block sorts by SHA256 of
`G-CAL1/order/<repeat>/<fixture_id>` (ID tie-break). Seed is
820000+10*ordinal+repeat, so every fixture has two distinct deterministic seeds.
Wire bodies bind model, exact system/prompt/input, stream/think false and the
six frozen options plus seed. Gold and difficulty labels never enter wire data.

Each stratum reports 10 fixtures and 20 observations, both-repeat correctness,
observation correctness/structural validity, false-clean observations/fixtures,
correlated false-clean pairs, malformed and repeat disagreement. Positive
fixture properties require both repeats; adverse properties require either;
correlated false-clean requires both. Report control-minus-pooled-boundary
fixture accuracy and boundary-minus-control false-clean rates as exact rational
contrasts; always report each boundary stratum separately.

Interpretation is DESCRIPTIVE_ONLY, label DESCRIPTIVE_CALENDAR_DIAGNOSTIC.
No defensible validated cutoff exists for ten deliberately selected cases per
stratum, so no categorical replication or qualification threshold is invented.
Patterns cannot prove internal reasoning or cause. Taxonomy is nonexclusive:
off-by-one, year/month mismatch, unchanged date, exact opposite-sign answer,
365/366 alternate-offset answer, leap omission/insertion-compatible patterns,
malformed/schema-invalid, truncation, other mismatch. Exact executable rules
are in DESIGN.json and the bound diagnostic implementation. The deterministic
reference never repairs outputs or adds a production calendar tool.

## Laboratory And Authority

Reuse unchanged generic hash verification, exact response evaluator,
write-once/fsync journal and checkpoint schema, failure receipts and integrity
catalog. Do not reuse scientific qualification gates, six cells or A/B schedule.
The new CAL runner requires a separate future G-CAL1 activation and CAL grant,
run ID and binding, and prohibits synthetic evidence in live mode. The empty
checkpoint `qualified` list is storage compatibility only. Two complete
synthetic pilots must have identical evidence trees. One independent audit
must pass before readiness; any blocker stops without post-audit repair.

No provider/model calls, activation, real execution, Phase B, autonomy or belief
effects are authorized here. G-EXTRACT1 and G-ROUTE4 bytes and verdicts remain
immutable. A future operand-extraction/deterministic-executor hybrid experiment
is recorded as a question only.
