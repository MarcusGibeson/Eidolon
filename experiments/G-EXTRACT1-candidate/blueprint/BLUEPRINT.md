# G-EXTRACT1 Authoring Blueprint

Status: READY_FOR_G_EXTRACT1_BLUEPRINT_CONTAMINATION_REREVIEW. Mechanical rebind only.

## Authority And Scope

Scientific basis: V10 commit `394d24121309ec9dce80e725b50dbe5eb60f6d2a`, plus the
accepted output-field amendment `aef3e0900cba41481904c8a451c4ca28b9d46c53`, and
accepted contamination repair `62c783bd8be708a86c82a9e00c80b0fa6fb5b459`.
The six design artifacts are byte-bound to the repair commit in BLUEPRINT.json
and remain unchanged. Prior accepted blueprint `28fb6bbd3fb668265e4cc50cda0da0f9afdf3ce5`
is lineage only: its allocations are preserved exactly. Original lineage is
`99707b4f13abd6533f1d09313bdb066793996be9`.
BLUEPRINT.json is the complete value-free enumeration; its scientific_traceability
maps every scientific dimension to the accepted JSON contract. The machine artifact
is authoritative for enumerated IDs, schemas, allocations and schedule positions;
this document describes it without adding semantic rules.

No source values, source prose, operand literals, entity source values, answer
objects, final prompts or request bytes are authored. Frozen design expectation
classes (E4 Boolean, enum position and E7 Boolean allocation) are copied constraints,
not newly authored gold answers. Ranges, schema tokens, selector indices and
identifier templates are blueprint metadata, not scored content.

## Canonical Output Fields

Every planned output materializes exactly eight keys: `name`, `schema_type`,
`required`, `binding_kind`, `source_field`, `producer_target`, `label_removal`,
`absence_capable`. Globally required=true and label_removal=false, including all
families, schemas, roles, scored/reserve bases and E5 CF1/CF2 members. No optional
output or label-stripping tolerance exists in G-EXTRACT1. The general historical
comparator capability remains unchanged; this experiment does not exercise it.

SOURCE_COPY: name/source_field equal the generated ordinary non-entity VALUE
fact identifier, exact source schema, producer_target=null, absence_capable=false.
OPERATION_TARGET: name/producer_target equal the generated operation target,
exact producer result schema, source_field=null, absence_capable=false.
EXPLICIT_ABSENCE: name/source_field equal the generated absence fact identifier,
schema provided|not_provided, producer_target=null, absence_capable=true. No gold
is authored here; the existing E7 gold derivation remains for future corpus work.

Output roles stay in separate output_field_metadata, never a ninth canonical key.
Each of the eight fields traces to the accepted amendment's binding construction;
lexical/schema/role derivations retain the existing V10 contracts. Rendered rows
inherit the canonical output array from their scientific_metadata_source base.
Thus CF1/CF2 output objects are identical, even though their future gold differs.

There are 220 logical output definitions: 144 non-E7 one-output bases plus 76 E7
outputs. E7 primaries have 4 contexts x (3+3+3+3+4)=64 outputs; four subtype01
reserves add 12. The 24 E5 CF2 members add 24 output instances: 244 rendered output
instances total, 204 scored and 40 reserve. This is not a new fixture/observation
denominator, and it changes no previous architecture/call/gate count.

## Enumeration

140 scored logical bases plus 28 subtype-01-only logical reserves = 168 bases.
20 scored and 4 reserve E5 bases are pairs: exactly CF1 then CF2. Others are SINGLE.
160 scored plus 32 reserve rendered variants = 192 objects. Ordinals are 1..168,
following the frozen A primaries/A reserves/B primaries/B reserves formulas.
Each position carries subtype, lexical generator, typed graph/operand-reference
shape, schema/output binding plan, value-shape constraints, composed/secondary
features, E4 allocation, E5 population/selector transition, E7 presentation,
recurrence membership, gate membership and authoring-contract references.

Per phase/round: 35 logical bases, 30 determinate plus 5 E7, 40 rendered variants.
Each model/round cell has 80 observations in A, 40 in B. E5 contributes 5 logical
pairs, 20 A observations or 10 B observations, requiring 5/5 semantic pair success.
General denominators remain 30 determinate logical bases, never rendered variants.
E7 remains 10/10 observations in A and 5/5 in B. Positive E5 reductions require all
four A or both B observations; adverse reductions use any observation. All other
gates are referenced/copied exactly from V10; no threshold is changed.

## Schedules

Phase A skeleton: 480 calls, 160 per model. B maximum template: 240 calls, 80 per
model. Maximum total: 720. Schedules are source-only metadata, not run journals.
Bases ascend by ordinal. For each base, rotate the frozen model list cyclically
by (zero-based active within-round ordinal rank + round offset) modulo3, with
offsets R2=0 and R3=35, to instantiate balanced model ordering. Within each model,
repeats ascend, and E5 members are CF1 then CF2. This is an operational allocation
under the design's balanced-order obligation, not a new scientific rule.
Each model occupies each list position 23 or 24 times among a phase's 70 bases,
and 11 or 12 times among a round's 35 bases, including reserve substitutions.
B is a stable filtered template for the sorted unique A-qualified model/round
cell set; all 64 subsets are mechanically checked. This does not create a result
or authorize B. Existing template position, call identity and seed are retained;
active schedule positions are renumbered after filtering.
Seeds use phase_base+(logical_ordinal-1)*10+repeat. Only CF1/CF2 of one model/base/
repeat intentionally collide. Reserve activation replaces the whole covered unit,
retains the primary qualification slot for denominator accounting, sorts the
active bases by actual ordinal and regenerates model rotation, seeds, call IDs
and positions. It requires balance/collision/schedule revalidation and refreeze
pre-contact. It is never a
post-output retry or optional model call.

## Contamination And Reserves

The logical recurrence ledger has 51 fingerprint classes, 35 subtype groups and
14,028 unordered base comparisons. The rendered comparison iterator has 18,336
pairs: exactly 24 eligible same-base E5 sharing scopes and 18,312 cross-base pairs.
Historical scope: 106 historical extraction entries times 192 variants = 20,352.
The comparison iterators and source rule references are frozen, but content
acceptance is deferred because no corpus exists. Ordinary ordinal-neutral,
declared-template content/shape, fingerprints, projection and exact-reuse checks
apply through the accepted comparison decision table, not a blanket similarity
threshold. Pair masks never alter contamination inputs. Sharing exemptions
require future byte/gold-validity audit and never extend across bases.
All 28 reserve mappings cover subtype01 only. Uncovered, multiple or mismatched
defects stop authoring. E5 replacement unit is the entire CF1/CF2 pair.
Profile fields retain the exact accepted key order and derivation references.
Final profiles must derive from actual validated content, not merely blueprint
declarations. Value-dependent dimensions remain unauthored until corpus work.

## Request And Gold Boundary

The request template references the exact bound historical system/suffix/provider
configuration and V10 complete-body serializer. Final selector spans, old/new
selector bytes, both request hashes and masked hash are required for every model/
repeat before contact, but cannot be filled before corpus authoring. CF1 retains
anchor checks; CF2 changes only requested selector and mechanically derived gold,
not the population or anchor allocation. No actual requests are rendered here.
Gold derivation is referenced to the frozen typed operation evaluator contract.
No expected answer is selected or computed from authored source values.

## Validation And Governance

Run `python -B experiments/G-EXTRACT1-candidate/blueprint/validate_blueprint.py`.
`--write` deterministically regenerates blueprint documents/report only. Default
mode validates existing bytes without writes. Checks independently count IDs,
ordinals, variants, gates, schedules, seeds, reserve mappings, comparison scopes,
all qualified-cell subsets and traceability; mutation probes reject mismatches.
The report claims structural/design equivalence only, not scientific validity,
future content feasibility, transport correctness or execution readiness.
The accepted repair's design checker pins the prior accepted blueprint as historical
checkpoint evidence. That guard is not rebound: no mutable design-side digest of
this later blueprint is required. All six design artifacts remain exact
accepted bytes. This checker loads only their value-free derivation helpers; it
does not invoke the old checkpoint inventory guard on updated blueprint files.
Instead it checks the repair binding, exact scaffold membership, canonical outputs,
and exact preservation of both prior and original allocations. No design-side changes
or circular design/blueprint digest binding are introduced.

G-ROUTE4 remains CLOSED FAILED. Provider/model calls, scored/reserve content and
gold answers authored are zero; belief effects none; no autonomy or runtime work.
Separate authorization remains required for corpus/gold authoring, implementation,
mechanical pilot, execution freeze, Phase A and conditional Phase B. Blueprint
review must occur first; corpus authoring cannot resume before rebind rereview.
This status does not self-authorize any later stage.

## Accepted Bounded Scaffold Rebind


Mandatory grammar made specific old ordinary/content tests infeasible even with fresh values. The accepted repair, not this blueprint, defines the bounded remedy.

Exactly 14 classes cover 234 logical unordered pairs and 906 cross-base rendered pairs. Twelve subtype-pair summaries split into two E1-05 classes (R2 zero/R3 366), ten E5 classes, and two E7-02/E7-04 presentation classes (A/B).

BLUEPRINT.json comparison_scope.scaffold_overlap contains every exact logical/rendered pair, accepted class ID, invariant gram, old branch/minimum, context/reserve scope, and exact design path. There are no subtype wildcards.

Use existing ordinary normalized/tokenized five-gram sets A/B. Subtract the frozen invariant set I separately: RA=A\I; RB=B\I. Never rewrite tokens, create adjacency, recompute I from values, or apply subtraction historically. Require nonempty RA and RB and strict 25*intersection < 3*union (Jaccard <0.12). Either empty produces AUTHORING_ERROR_EMPTY_RESIDUAL.

Both actual fixtures must pass position, lexical, schema, operation/gold, subtype, value-shape, output and planned-fingerprint checks; E5 also requires its full request/pair audit. Raw typed VALUE freshness, whole-answer/identity/date-number reuse, raw payload inequality, generated identities and independent A/B checks remain mandatory. Residual success alone never permits a pair.

Precedence: historical rules first; actual structural/profile invalidity errors; validated same-base E5 pair-local sharing; cross-base freshness/reuse rejection; exact scaffold membership; remaining declared same-subtype content/shape rules; remaining ordinary rules. Pair-local sharing precedes cross-base freshness intentionally. The 24 same-base E5 scopes are separate and excluded from scaffold membership. All four cross-base E5 CF combinations inherit only their exact base-pair membership.

Historical/new remains unchanged: ordinary>=0.20, projection3/3, or projection>=2/3 and ordinary>=0.12 reject; 106/106 historical adaptations and 20,352 comparisons remain required. No historical scaffold handling.

Scaffold classes are not recurrence groups. Remaining same-subtype content rules, different-subtype ordinary rules, 51 fingerprint classes, 35 subtype groups, reserves, schedules, seeds and gates are unchanged. The report partitions all 18,312 cross-base rendered pairs; 906 are included within that domain, not additional comparisons.

This materializes frozen pairwise-feasibility rules only. Simultaneous concrete corpus feasibility, actual independence, corpus acceptance and scientific validity are not proven. No concrete content exists here.

Cross-base partition: 906 scaffold + 518 remaining same-subtype + 16888 ordinary = 18,312. All 24 pair-local scopes remain separate.


| Accepted Class ID | Subtypes | Logical | Rendered | Old Branch / Minimum |
|---|---|---:|---:|---|
| 42a73611bf4015e5e6660a484163279be47e669a9142e29a5f9c45a953215d8a | E1-05/E1-05 | 1 | 1 | NEW_DECLARED_SAME_SUBTYPE / 1/3 |
| 839f9b8efab9396637b185050b5adb5d461c76ae5f86eafdc209553f3b29d301 | E5-01/E5-02 | 32 | 128 | NEW_DECLARED_DIFFERENT_SUBTYPE / 1/2 |
| 000493591dc3359274ddce07832b9527b5df642873848b38c49ae38063a80099 | E5-01/E5-03 | 32 | 128 | NEW_DECLARED_DIFFERENT_SUBTYPE / 2/7 |
| 8b4f0f34c6f47bb712ba5afb894caec7998e0637d5d278c37b46dc705ac86a9d | E5-01/E5-04 | 32 | 128 | NEW_DECLARED_DIFFERENT_SUBTYPE / 8/17 |
| 46bec20fffafd9a0b7a224c7bfe4c4175a3a17e3d2e2665ea4bbd96d065d32d1 | E5-01/E5-05 | 32 | 128 | NEW_DECLARED_DIFFERENT_SUBTYPE / 7/24 |
| 3a0b2e80685aaebe1ec03bf465ffdfb3cde01d06ef5467fb03809af97bed8578 | E5-02/E5-03 | 16 | 64 | NEW_DECLARED_DIFFERENT_SUBTYPE / 2/7 |
| 57fa1e57285b183452b784b072ed2c8a3dc4e72b9a396328226febfbc7ad6ba3 | E5-02/E5-04 | 16 | 64 | NEW_DECLARED_DIFFERENT_SUBTYPE / 8/17 |
| 787c48ccfca24e44d0a1544f1e8c5e49a892ee42da600f82c0a3a0591b2cb6e6 | E5-02/E5-05 | 16 | 64 | NEW_DECLARED_DIFFERENT_SUBTYPE / 7/24 |
| 533f0712dd6ad2a00754210b933849183df02c7ead279d8e62f096657aaabd0d | E5-03/E5-04 | 16 | 64 | NEW_DECLARED_DIFFERENT_SUBTYPE / 14/51 |
| 20c578c99255e84bd743ffde88da47c6c8e1aa677f7cb77a779ec4c7512b2bc9 | E5-03/E5-05 | 16 | 64 | NEW_DECLARED_DIFFERENT_SUBTYPE / 24/53 |
| 6a4e7fd29c8ceb1ae492233135ff85baf094bbcc3f888a3a16faef7336cf4227 | E5-04/E5-05 | 16 | 64 | NEW_DECLARED_DIFFERENT_SUBTYPE / 7/25 |
| 06622d78bd0b1b0df361c77e579c8b484a8f1d6b04bc0b30a67ae85920e1cbc7 | E7-02/E7-04 | 4 | 4 | NEW_DECLARED_DIFFERENT_SUBTYPE / 5/22 |
| b7b568f3bb31af95ff56f9c4ede78aa1e9370c9b410eae69dc750bcc07273c34 | E1-05/E1-05 | 1 | 1 | NEW_DECLARED_SAME_SUBTYPE / 1/3 |
| 2000cecb91fc194e961885dc681b22ab9cf460c1f30b44556a4b5f0e7f7f5903 | E7-02/E7-04 | 4 | 4 | NEW_DECLARED_DIFFERENT_SUBTYPE / 5/22 |
