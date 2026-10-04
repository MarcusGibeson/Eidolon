# G-EXTRACT1 Design Revision Changelog

## Prospective Whole-Answer Canonicalization Amendment

Accepted parent: `6fb3f2af5806760c034006a8561ce08e938c210a`.
Encoding closure only; no checker or blueprint repair and no corpus rescoring.

| Finding / Obligation | Disposition | Repair / Preservation |
| --- | --- | --- |
| Boolean text vs native scalar underdetermined | Resolved prospectively | All canonical values are JSON strings across all seven tags. |
| NUMBER spelling and host types underdetermined | Resolved | Exact rational plain decimal, minimal fractional text, signed zero normalization, int/Decimal/Fraction/text equivalence; no floats or rounding. |
| Schema/tag distinction and field sorting | Intentionally retained | Exact schema identity, uppercase derived tag, unsigned UTF-8 field-name sorting, duplicate-field rejection. |
| Outer JSON contract | Intentionally retained | ensure_ascii=True, compact separators, UTF-8, no newline; non-ASCII and mutation vectors. |
| Historical/new and sensitivity claims | Intentionally retained | Same completed projection on both validated answers; unchanged scopes/full-object byte equality and fixture-name limitation. Historical adapter 106/106 is not a whole-answer campaign. |
| Other encodings / freshness | Intentionally retained | All prior contracts identical; freshness ensure_ascii=False and unrelated numeric conventions unchanged. |
| Corpus, gold, failure evidence and checker preservation | Resolved | Ten-file current snapshot and gold hash; accepted blueprint digest checks; old shared helper AST unchanged. Guards updated to current checkpoint only. |
| Blueprint and checker authority | Intentionally withheld | Independent amendment rereview, separate blueprint rebind/rereview and later checker repair required. |
| Scientific effects / thresholds | None | No equality, threshold, allocation, gate, schedule, seed, model-facing byte or historical-result change. |

Design tests add golden byte vectors, host equivalence, sorting and malformed-byte
mutations. PASS denotes structural/cross-representation consistency only.
Earlier entries retain their historical claims and checkpoint identities.


## Prospective Freshness Canonicalization Amendment

Parent: `01aafde7410a44085999aa4aa39f883618e78799`. This is serialization
closure only, independently rereviewable; not checker repair or corpus approval.
The existing 168-base untracked candidate corpus was constructed before this task
and is immutable here. Earlier statements about zero authored corpus refer only
to their historical checkpoints, not the current preserved authoring attempt.

| Requested issue/control | Resolution |
|---|---|
| INTEGER `0` versus `"0"` | Both freshness row elements MUST be JSON strings. Integer semantic text is minimal base 10; signed zero becomes `"0"`. |
| Schema identity versus semantic tag | First element is exact historical schema spelling/full finite-enum schema. Generic INTEGER/NUMBER/DATE/TIME/ENUM tags cannot replace schema bytes. |
| NUMBER equivalence | Exact rational terminating-decimal rendering; plain notation, no plus/exponent/unnecessary zeros, integral values omit the decimal point, signed zero becomes `"0"`. No float or Decimal-context rounding. |
| Other schemas | Boolean lowercase; date/time exact validated forms; string and enum values preserved exactly without similarity normalization. |
| Scope/order/duplicates | VALUE facts only, source-record order, duplicates preserved; no fields/IDs/outputs/implicit absence. |
| Byte representation | UTF-8, ensure_ascii=false, compact separators, no trailing newline; all values text, independent of host scalar types. |
| Full schema tests | All primitive and blueprint-used finite enum schemas; numeric equivalence, distinct values, exact fractions, large numbers, strings/Unicode and ordered duplicate rows. Test-only noncanonical numeric lexemes do not loosen authoring metadata. |
| Adversarial checks | Native scalars, generic tags, exponent/zero variants, capitalization/reformatting/trimming/ordinal substitution, sorting/deduplication, spacing/ASCII escaping and extra scope all reject. |
| Other encodings | Whole answers, identity atoms, date-number tuples, fingerprints, similarity/views/scaffold residuals/historical projections unchanged. Freshness NUMBER text does not replace their existing encodings. |
| Allocation/science preservation | Parent projection permits only the new contract and review-status paths. Counts, gates, schedules, seeds, budget, output amendment, contamination thresholds and historical rules remain unchanged. |
| Corpus/gold/checkers | Seven pre-edit SHA-256 digests checked; candidate gold remains embedded in byte-identical candidates. Stop/diagnosis evidence and both corpus checkers preserved. No rescoring/regeneration/finalization. |
| Blueprint | Five files checked against accepted 01aafde checkpoint, unchanged. Separate independent amendment rereview and authorized blueprint rebind required. |
| Human/machine equivalence | Exact parsed freshness normative annex equals the new machine object; validator scope remains structural/cross-representation consistency, not scientific validity. |
| Governance | Provider/model calls0, no runtime/execution, no historical rewrite, G-ROUTE4 CLOSED FAILED, belief effects none. Only six design/checking files authorized for commit. |

All earlier sections below are checkpoint history; the current amendment changes
no scientific rule and grants no later-phase authority.

## Prospective Contamination-Feasibility Repair

Parent: `28fb6bbd3fb668265e4cc50cda0da0f9afdf3ce5`. Design/checking only;
no source values, gold, scored/reserve content or blueprint files authored.

| Requested finding/control | Resolution |
|---|---|
| Do not repair only E5-01/E5-02 | Complete symbolic 14,028 logical / 18,312 rendered cross-base audit; all ten E5 pairs, all families/cross-family pairs and 24 separate same-base scopes covered. |
| Impossible-class inventory/minima/forced grams | 14 exact classes, 234 logical / 906 rendered comparisons; exact contexts, scopes, fingerprint agreement, rational minima, shape/content and grams frozen in co-normative annex and report. |
| Distinguish mandatory scaffold from genuine replay | Per-class fixed-window proof; all mutable literals excluded from the removable set. E1 fixed zero/366 boundary issue separately named, not cross-subtype identity. |
| Smallest prospective bounded repair | Only the 234 enumerated position pairs; ordinary five-gram set minus exact class invariant intersection, strict residual <0.12, nonempty residuals. No family-wide or author-selectable waiver. |
| Ledger and actual eligibility | Actual subtype/value/lexical/schema/operation/gold/output and exact planned fingerprints mandatory; E5 pair audit; distinct full fingerprints for different subtypes. |
| Preserve freshness / detect copying | All raw sequence/answer/identity/tuple/payload/generated-identity/A-B protections unchanged; adversarial replay and copied-residual tests reject. |
| No shape-only exception / empty content | Report all views; shape is not permission; old empty finite content is NOT_APPLICABLE, residual empty is authoring error, all other requirements still mandatory. |
| Global/historical protection | Original threshold and historical section objects unchanged; 106/106 adaptation rechecked; no historical edits. |
| Pair-local E5 versus cross-base | Same-base exception unchanged; new groups contain only distinct logical bases and never use pair-local sharing to admit cross-base data. |
| Recurrence membership | All 168 positions /192 variants, 51 classes,35 subtype groups, profiles/gates/seeds/budget/authority remain unchanged; scaffold groups are separate. |
| Full post-repair proof | All old infeasible pairs covered and nonempty residual lower bound zero; every other pair passes its unchanged lower-bound rule. Pairwise feasibility only, not concrete corpus success. |
| Blueprint status | Five accepted blueprint files unchanged against 28fb6bbd; checker guard now pins that accepted checkpoint instead of older 99707b4f. Separate future blueprint rebind after rereview. |
| Human/machine equivalence | Exact parsed scaffold contract annex; preservation projection back to parent catches any unrelated machine alteration. |
| Governance | All authority false; model/provider calls0; corpus/gold/reserve content0; G-ROUTE4 CLOSED FAILED unchanged; belief effects none. |

Earlier amendments below are preserved historical checkpoint records. Their
checkpoint-specific status and blueprint references do not override this amendment.

## Narrow prospective output-field amendment to accepted V10

Accepted design parent: `394d24121309ec9dce80e725b50dbe5eb60f6d2a`. Reviewed blueprint: `99707b4f13abd6533f1d09313bdb066793996be9`. Marcus authorized only this design/checking amendment; the blueprint remains byte-unchanged and still needs its separate repair/review.

| Blueprint rereview finding | Disposition and prospective repair |
|---|---|
| `label_removal` remains an author-selected scoring flag | Resolved in design: constant false for every output/schema/role, primary/reserve and E5 member. Generated values need no stripping tolerance. General historical comparator capability is retained, but G-EXTRACT1 does not exercise it. |
| Complete eight-key output construction is not bound | Resolved in design: required is always true; binding-specific ordered templates freeze names, exact schemas, source/producer nullability and absence capability. Existing identifier/type/role derivations remain unchanged; roles stay separate metadata. |
| Validators can share the omission | Resolved for design checking: all 168 symbolic bases and 192 variants derive full eight-key outputs; flags, missing/extra keys and binding corruption are mutation-tested. The exact amended human annex is compared with JSON. No blueprint validator or blueprint artifact is changed. |
| Old design directory inventory rejects the previously authorized blueprint | Checking compatibility only: allow exactly the five existing blueprint files, byte-bound to the reviewed commit. No wildcard, new content, rewrite or authority extension. |

All other V10 machine rules are compared structurally against the accepted commit with an exact amendment-path allowlist. Historical prompt/comparator capabilities, subtype/value allocations, recurrence, contamination, reserves, schedules/seeds, gates and governance are unchanged. Historical adaptation remains 106/106. This is not scientific approval or corpus/gold authorization. Provider/model calls and corpus/gold/reserve content authoring are zero; G-ROUTE4 remains CLOSED FAILED; belief effects none.

## Candidate v10: authorized counterfactual correction

Reviewed parent: `500f29dbfc157cd4a024976694da47e8f3e2e5b7`. The original unrestricted selector-blind allocation request was blocked with no edits. Marcus explicitly authorized counterfactual selector controls instead. Design/checking only; no corpus, reserve or blueprint authoring.

| Rereview-9 / blocked-V10 finding | Disposition and prospective repair |
|---|---|
| Schema x record-type can recover R2 anchor selection | Resolved by paired complete requests: only requested selector bytes differ; record type/schema identical within each pair. A notice/B event retained, not independent of phase. |
| Precision/rank associations permit selector-blind answers | Resolved by invariant population/precision/value order within each pair and distinct gold. V9 anchor difficulty remains; CF2 rank derives from the other selector. |
| Actual qualification is model x round, not pooled | Resolved: pair gates independently apply to each model x round x phase; both A and B must pass. |
| 513 marginal policies omit conditional/identifier lookup | Intentionally retained as secondary bounded CF1 diagnostics only. No universal protection claim; exact pair-invariant keys require conflicting answers for any deterministic selector-blind function. |
| Arbitrary unique-ID lookup defeats finite counterbalancing | Resolved: CF1/CF2 share one logical ordinal and every non-selector request byte, including seed. Variant identity is metadata-only. No cognitive inference. |
| Provider settings could differ between variants | Resolved: same model/configuration/seed within each repeat; exact canonical full-request bytes and masked equality audited. Bound historical builder definitions cross-checked offline. |
| Pair scoring / repeats / family floor unclear | Resolved: A all four, B both; adverse any observation; strict5/5 E5 pairs added without weakening general29/30,27/30 or4/5 gates. |
| Contamination and exact reuse normally reject deliberate sharing | Resolved: exception confined to CF1/CF2 of one frozen validated E5 pair. Every cross-base variant retains all v9 controls. Fingerprints intentionally ignore selector choice. |
| Reserve must not substitute one variant | Resolved: four E5 reserves are complete pairs, matching ordered transitions and v9 actual-validated anchor profiles. All28 logical slots remain01-only; no pools/member substitution. |
| Old168 objects/630 calls no longer accurate | Resolved:168 logical bases,192 rendered variants,480 A +240 max B =720;14.285714% increase vs630,48.387097% reduction vs1395. |
| Recurrence and comparison scope affected | Resolved: base ledger168/51/35/14,028 preserved and rederived; expanded192 entries/18,336 pairs,24 exact within-pair scopes,18,312 cross-base checks. |
| Human/machine and validator scope | Resolved: exact co-normative pair/accounting/gate/seed objects compared; behavioral mutations, all pair reductions, shared seeds and bound full requests tested. PASS is structural/cross-representation consistency only. |
| Historical adapter/governance | Retained unchanged:106/106 adaptations, historical digests, no providers/models, zero corpus/reserve items, no future authorization. |

Prior candidate sections below record earlier dispositions, not renewed universal claims. The v10 pair extension supersedes their E5 single-variant interpretations only. No gate is loosened and no historical artifact is rewritten.

## Candidate v9

Reviewed parent: `9ac3db265a1ae2ed6936ff4890b8eb001f0ab266`. Design/checking only; no blueprint or corpus authoring.

| Rereview-8 finding | Disposition and prospective repair |
|---|---|
| Four E7 reserves have unavoidable identical fingerprints | Resolved: full value-free 168-position ledger, 51 exact classes/35 subtype groups, exact member maxima and all collision scopes. All 45 recurring classes are preregistered, not an E7-only exception. |
| Ordinalized names mask similarity | Resolved: NEW text/schema ordinal-neutralization, historical text unchanged; ordinary/shape/content views and adversarial probes. Ordinal masking alone still gives the demonstrated fresh-value replay 0.0; undeclared layout and shape replay checks catch it. |
| E5 schema/subtype predicts entity | Resolved: exact four-context index matrix; all 243 schema, 243 subtype and 27 selector-role mappings evaluated. None passes both phases of a round; one-context schema/subtype maxima can still be 5/5 and are disclosed. |
| Value difficulty is author-selectable | Resolved: 35 profiles with exact context expansion for magnitude, precision, signs, carry/borrow, three-operand SUM, exact quotient/denominator complexity, conversion, comparison/temporal gaps, entity ranks/separation and zero distractors. Actual value validation precedes reserve profile derivation. |
| Cross-round/unmapped reserve collisions implicit | Resolved: all pair scopes explicit; same-subtype ledger compatibility never grants replacement rights. Slot01-only activation preserved. |
| E7 B overinterpreted as freshness-only | Resolved: explicitly fresh-fixture validation under prospectively shifted order, not IID/freshness-only. |
| Whole-answer control overclaim | Intentionally retained as exact-object replay only; ordinal names limit sensitivity. Complementary controls and limits disclosed. |
| Historical adapter after comparison change | Retained: all106 read-only adaptations, unchanged projection/digest and historical thresholds; only NEW similarity side masked. |

### Necessary prospective consistency corrections

1. Fixed-template ordinary similarity cannot universally satisfy <0.20 after ordinal masking (E7 probe 0.272727, generated-only copy 1.0). Exact preregistered same-subtype positions instead require content five-gram Jaccard <0.12 plus raw typed VALUE freshness and every exact-reuse check. Both-empty content sets are NOT_APPLICABLE, restricted to fixed generated labels/enums. This scoped contamination exception is explicit and requires scientific rereview; no qualification gate changes.
2. Required E4 rotations/E7 order shifts are planned 5/6 variants. Exact ledger variants may recur; different fully validated subtypes retain the original ordinary near-replay test. Shape replay adds evidence for undeclared variants, which are authoring errors regardless score. No post-authoring layout exceptions.
3. E1-05 uses a source offset and E2-05 a literal end to distinguish otherwise unavoidable unrelated-subtype fingerprints. Other catalog/system/common-suffix bytes and full prompt checking hashes are preserved.
4. E4-02 positive INTEGER-minus-fractional-NUMBER always borrows at a fractional column. Its profile is borrow=true rather than an impossible rotated no-borrow case. E3-02 absolute-difference borrow remains counterbalanced.
5. The reserve profile appends its validated value_shape_profile. Old isolated mechanics are not v9 corpus-valid evidence; enforce_v9=True checks actual subtype/value/wiring before full reserve-profile comparison.
6. Finite enum/Boolean catalog tokens are not scalable freshness evidence in the declared content view (but remain in ordinary/shape views). Their exact allocation/scoring remains required; E7-05 Boolean support is true/false/false/true. Both-empty content is disclosed as NOT_APPLICABLE, not a low-similarity claim.
7. Entity-bound source/selector contamination atoms resolve the selected entity's complete facts, rather than the ordinary non-entity reference path. Twenty typed entity checking vectors exercise this existing binding semantic explicitly. Actual E4/E5/E7 profiles and exact DIVIDE complexity are now behaviorally exercised, not only declared.

Validator PASS means deterministic structural/cross-representation consistency only. The 168-object proof is symbolic structural feasibility, not proof that future content/gold/contamination will pass. Scientific validity and blueprint readiness remain for independent v9 rereview. G-ROUTE4 remains immutable CLOSED FAILED; model/provider calls, scored fixtures and reserve authoring are zero. All later authorizations remain separate.

## Candidate v8

Reviewed parent: 6eef00a09a90fb8a50a6e18ff9cdcc90ae712d6e. Prospective design/checking only.

| Rereview-7 finding | Disposition |
|---|---|
| Historical fingerprint gap | Resolved: 106-input surface projection with separate rules, no invented metadata. |
| All E4 true | Resolved: rotating matrices each 3 true/2 false; both constants fail. |
| Entity discrimination | Resolved: semantic pairwise distinctness/wrong-selection tests; Boolean excluded; three-option enum. |
| Enum positions | Resolved: fixed E5/E7 context index/permutation. |
| Reserve contradiction | Resolved: 01-only activation, explicit 02..05/multiple stops. |
| Legacy atom shape | Resolved: two-element comparison atoms. |
| Lexical wording | Resolved: exact inclusion/exclusion and association, no causal claim. |
| Whole-answer limitation | Intentionally retained exact-object rule with complementary controls. |
| Unproven profile domains | Resolved: actual semantic/subtype validation first. |
| E7 integration | Resolved: exact mix/order/context/placement. |
| New/new refinement | Intentionally retained, discrimination change documented separately. |

G-ROUTE4 stays CLOSED FAILED; gates unchanged. No blueprint, fixtures/reserves, production code, provider contact or execution. Scientific approval unresolved until v8 rereview. Validator scope remains structural/cross-representation only.

## Candidate v7

Reviewed parent: v6 at `1ba43663d0c646b0dc743c65424019782bd2f696`.

Only the six design/checking artifacts change. G-ROUTE4 remains CLOSED FAILED. No blueprint, corpus, scored fixture, reserve, production implementation, provider contact or experiment execution is authorized or created.

| Rereview-6 finding | Disposition and repair | Binding |
|---|---|---|
| Identifiers, record types, enum options and Title Case labels permit covert coaching | Resolved. Two disjoint seven-word record catalogs, generated fixture/source/node ordinals, opaque enum prefixes, generated entity labels and string atoms replace author-selected semantics. Every primary/reserve has one immutable lexical ordinal. Record types occur five times per phase/round. | lexical-neutrality.v1; rendering v4; human section 7 and annex |
| ENTITY_FIELD_BIND lacks a complete population | Resolved. Exactly two or three entities; one selector and source VALUE fact for every entity; exact schema identity across the population; unique metadata/fact selectors; no unknown, incomplete, extra or non-entity duplicate entity facts. Source/output schema identity is preserved. | entity-population.v1; operation-semantics.v2 |
| Reserve profiles omit canonical type/domain dimensions | Resolved. Exact ordered compact JSON profile includes source/output schemas, result tags, promotion classes, conversion IDs, comparison types/boundary, temporal domain, entity count/role, output roles, counts and exact subtype/domain allocation. Only byte-identical profiles may replace. Fresh values/ordinals are excluded. The one reserve covers subtype slot 01 only; other defects stop authoring. | reserve-equivalence.v1; reserve-activation.v4 |
| Family/composed quotas leave subtype selection to the blueprint | Resolved. Exact five-slot rows per family freeze calendar, clock/elapsed, ADD/SUBTRACT/SUM/DIVIDE/unit, comparisons, entity populations, copy types and E7 support mix. Four composed rows name eight distinct slots. Numeric promotions, operators, boundaries and domains are fixed for both phases. | subtype-allocation.v1 |
| Source date-number atoms use literal syntax rather than schema semantics | Resolved. Source tags come from source schema; field arguments resolve source schemas; derived arguments resolve producer tags; gold uses output schema. NUMBER 5.0 and INTEGER 5 have distinct bytes. Exact rational serialization prevents rounding. | contamination.v4; co-normative atom contract |
| Enum binding can widen, narrow or reorder the schema | Resolved. SOURCE_COPY, ENTITY_FIELD_BIND and EXACT_COPY preserve historical schema bytes, including option order. Behavioral entity/copy vectors cover identical, wider, reordered and narrower schemas. | operation-semantics.v2; validator |
| E7 shape checks are not integrated | Resolved. Canonical fixture tests enforce zero nodes, exactly one missing provided/not_provided field with not_provided gold, complete supported source copies, and every source/gold binding. Wrong schema/gold/count/graph/binding/source data is rejected. | explicit-absence-scoring.v4 integrated shape; validator |
| Domain boundaries and large terminating division need tests | Resolved. Calendar 0/366 and rejected -1/367; clock 0/1439 and rejected -1/1440; elapsed ordinary/rollover/equal/max; leap boundaries; exact terminating/nonterminating divisions including an 81-digit numerator. Fraction and integer scale arithmetic eliminate Decimal-context rounding. | operation-semantics.v2; validator |
| New lexical pools must be reflected in contamination | Resolved. Generated identifiers, strings and entity values remain in payload comparisons. Neutral field names are not identity values; generated id_ values are. Historical identity detection retains its historical adapter. Record type exclusion remains the existing prompt-boilerplate rule, with its allocation independently audited. | lexical-neutrality.v1; contamination.v4 |
| Validator must execute new mechanics rather than just find strings | Resolved. It executes lexical membership/generation, population mutations, exact enum schemas, reserve byte profiles and type/conversion differentials, allocation counts, E7 fixture shape, atom resolution, exact domains, reversed graph ordering and fingerprint bytes. Parsed normative JSON embedded in the human design is compared against the machine objects. | validate_design.py; validation report |

## Prospective integration corrections

1. Output names equal their generated source/producer binding identifiers. A separate opaque output alias would leave the unchanged model-facing prompt unable to identify its binding. The eight-key representation and historical suffix remain unchanged.
2. Fixture-specific neutral ordinals avoid unavoidable whole-answer collisions from repeated Boolean results. Naming depends only on frozen authoring position, never on gold or observed behavior. Full-prompt mechanical vectors and hashes are updated for these new fixture-content identifiers; historical system/template/artifact hashes remain unchanged.
3. Matched E7 support shapes with empty graphs necessarily collide under the earlier coarse fingerprint. The sixth component now retains its existing layout enum plus the ordered typed fact-role sequence. A/B/reserve E7 source order is frozen as absence-first/absence-last/absence-between-supports. All six components, Jaccard and near-replay thresholds remain; the new bytes are a prospective consistency correction, not a historical rescore.
4. Historical schema parsing remains generic, while new fixture authoring applies the opaque enum lexical overlay. This preserves comparison against historical schemas without permitting semantic enum labels in new prompts.
5. Reserve source/output schema sequences use canonical schema/role sorting with duplicates retained. This preserves exact type multiplicities while allowing the frozen presentation-order variation needed for independent fingerprints. Operation operand semantic-type arrays preserve argument-position typing. The validator proves matching E7 profiles and distinct fingerprints for canonical order variants.

These corrections are explicit design changes and require independent rereview. Validator PASS is deterministic structural/cross-representation evidence only and does not prove scientific validity.

## Preserved boundaries

Seven families; 35 fixtures/round; 30 determinate plus five E7; 420 A calls, at most 210 B calls, 630 maximum; 29/30 semantic and structural, 27/30 useful, zero false-clean, malformed at most one; E7 A=10/10 and B=5/5; Phase A repeat reduction; 28 family-slot reserves; baseline provider/models; exact arithmetic/temporal semantics; no prompt repair, A/B pooling, failed-cell reentry, post-contact edits, threshold relaxation or historical rewrite. Belief effects remain none.

Separate authorization remains required for blueprint, fixture/gold authoring, implementation, mechanical pilot, execution freeze, Phase A and Phase B. Unresolved approval: independent v7 adversarial rereview. No claimed scientific validity or later-phase authority is implied.

## Historical Tuple Scope Correction
Resolved historical provenance impossibility with an explicit NOT_APPLICABLE status only for historical/new date-number. Preserved all NEW/NEW semantics and other historical controls; no candidate outcome drove this correction. Blueprint mechanically binds the same annex.
