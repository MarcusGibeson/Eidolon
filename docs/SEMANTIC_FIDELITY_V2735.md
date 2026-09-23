# Semantic fidelity — reviewer contract v2735.0

**Status: QUALIFIED for the observed semantic-role preservation failure mode.**
Closed by operator decision after G-SYNTH1-R2, 2026-09-23. Two caveats travel with this closure; they are
recorded below and are part of the qualification, not footnotes to it.

## The failure this repairs

Attempt 5 (`cddac8ff2e222ac0`) was the first complete full-package independent review: 140/140 parts, 911 grounded
observations, every observation represented, nothing silently dropped. Its final synthesis nonetheless reported a
deliberate architectural constraint as a possible model deficiency.

The drift was located exactly, and it was not in the final reasoner:

```
O3    "The architecture specifies that the model does not emit … 'use', 'investigate', 'abstain'."
PS3   "The architecture specifies the model does not emit …"
DS3   "Architecture specifies model does not emit …"
GS154 "Architecture specifies model does not emit …"          ← role intact through four levels
        + GS151 "gates failed unsafe use (3/12) but passed primary (0/42)"
        ↓ merged
GS201 "Gates failed unsafe use (3/12) but passed primary (0/42); model does not emit operational labels…"
        ↓ propagated verbatim through GS242, GS270, GS293, GS311, GS326
final  filed under possible_model_or_reasoning_failures
```

One consolidation merge glued a measured result to a design constraint and dropped the three words carrying the
second one's role. The final layer reasoned correctly from a representation that had already lost the distinction.

A second, separate defect: the fold register described itself as `kind="unknown"` and "unrepresented above", so
preserved evidence was reported as missing while the architecture accounting recorded it as represented.

## What v2735.0 changes

| Commit | Change |
|---|---|
| `37c14d8` | The preservation register describes itself as preservation: `preserved_register` / `preserved_indirectly`, "not directly cited by a synthesis statement; preserved through register lineage". Prompts say preserved evidence is present, not missing. |
| `c81b4cb` | Statements carry semantic role as data: `direct_roles`, `inherited_roles`, `role_lineage`, `proposed_roles`, over a closed ten-role enum. Model proposes, governance decides; an unusable proposal inherits its sources' roles. |
| `f916fcf` | Merge-time fidelity validator. A role that changes interpretation may not fall to inherited-only while the sentence asserts something settled. Prose that kept the framing is promoted; prose that lost it is refused. |
| `09ed8c9` | Conflicts are read from inherited roles as well as direct ones, qualified by relevance: only when the statement directly claims something assertive. |
| `8b03001` | `minority_finding`, `limitation` and `hypothesis` are challenged under a flat `measured_result` or `observation`, not only under a `conclusion`. Lexicon gains `opposite` and the numeral form of a minority. Promotions report the marker that triggered them. |

### The invariant

Traceability and fidelity are not the same thing, and the distinction is the design:

* **traceability** — no role disappears from lineage;
* **fidelity** — a role that materially affects interpretation stays *directly expressed* when its absence would
  change what the sentence means.

Keeping `design_constraint` in an ancestry field while the sentence reads as a deficiency satisfies the first and
fails the second. That is precisely what Attempt 5 did.

Direct and inherited stay separate. No ancestral role is unioned into `direct_roles` to make a check pass; after
nine consolidation rounds that would hand the final layer statements claiming to be six kinds of fact at once.

## G-SYNTH1-R2 — the qualifying run

22 chains of four single-subject inputs each, the planner's own statement budget, real `GROUP_PROMPT`, real
validator, real governance, qwen3.8:27b at `f398196f…`. 15.1 minutes.

```
verdict                               PASS
role_loss                             0
false_promotion                       0     (operator inspection — see below)
preserved_register_misclassification  0     (10 registers created)
refused merges retain inputs          yes
silently dropped observations         none
thresholds / floors                   MIN_REDUCTION 0.80, representation floor 0.5, unchanged
statements                            43
multi-input merges                    34
critical multi-input merges           12    (minimum required 8)
reductions                            0.79–0.80 across 10 rounds
```

Critical merges resolved: **9** claimed the role directly, **2** recovered by deterministic promotion, **1** refused
with all inputs carried forward, **0 demoted and unchallenged**.

Role use, live: the model uses the vocabulary rather than collapsing to `observation` — proposed `measured_result`
25, `procedure` 13, `design_constraint` 9, `observation` 6, `limitation` 5, `uncertainty` 4, `hypothesis` 1. All
four forced-invalid proposals were discarded.

### false_promotion — how it was decided

Both promotions were read by the operator and accepted as genuine:

```
critical-agreement   proposed ['measured_result']              promoted ['minority_finding']
  "29/32 items had identical dispositions; 1 item produced a unique disposition (DS1, DS2)."

critical-conflict    proposed ['measured_result','procedure']  promoted ['contradiction']
  "Records T07-r1 and T07-r2 report opposite relations for the same evidence, while both cited
   two spans and were read in fixed order."
```

**This is external/operator inspection, not deterministic semantic certification.** The marker check reports what
wording it saw; it cannot tell a true sentence from a false one, and it is not treated as if it could.

## Caveats carried by this closure

**1. Marker matching has a semantic ceiling.** A limitation expressed only as a bare quantity still produces a
safe false refusal. The live case:

```
"Correlated error was observed in three items, which were drawn from a pool of
 twelve ambiguous items examined after the primary scoring pass."
   → challenged for `limitation`, refused, all inputs carried forward
```

The sentence conveys the limitation to any reader and matches no defensible marker. No marker was invented for it.
The refusal is conservative — nothing is lost, the inputs carry forward — but it is a real limit of the approach,
not an edge case.

**2. The harness accounting bug must be fixed before the harness is reused.**
`qualifications/g_synth1_r2_harness.py` files a promoted statement as "demoted and accepted", because unlike
`run_unit` it never applies the promotion back to its local `roles` dict. The run therefore reported
`critical_demoted_and_accepted: 2` and `critical_role_recovery_rate: 0.0`; the true figures, reconstructed from the
recorded per-statement evidence, are **0 unchallenged** and **2 recovered**, a rate of **2/3** on a denominator of
3. The harness was not corrected and re-run, because the qualification may not be modified after its output is
seen. The per-statement records were sufficient to reconstruct the correct result; they may not be next time.

## Open, and deliberately not addressed

There is no synthesis-level retry. A refused statement carries its inputs forward unchanged, which is safe and
was adequate here (one refusal in 43 statements). Building a retry loop would change execution semantics, retry
accounting, convergence and checkpoint state; the absence of one is an acknowledged open item, not a defect.

## Frozen and untouched

Attempt 5 (`review.json` `c22728f6…`, `BASELINE.json` beside it), Attempts 1–3, the derived Attempt 3 recovery,
the G-CORROB1 package `eef879f1…`, corpus, gold, scorer, gates, and the frozen baseline reviewer
`experiment_review.py` at `ded43418…` (v2731.8, byte-identical throughout).

## Evidence

* `qualifications/g_synth1_r2_evidence.json` — the full run, per statement, `89a12cfe…`
* `qualifications/g_synth1_r2_harness.py` — the harness as run, `c09e763e…` (see caveat 2 before reuse)
* `qualifications/semantic_fidelity_fixture.json` — the two real Attempt 5 transitions this arc was built from
* `tools/v2735_0_0_preserved_register_tests.py` — 137 checks
* `tools/v2735_1_0_semantic_role_tests.py` — 264 checks, including all three live R2 sentences verbatim
