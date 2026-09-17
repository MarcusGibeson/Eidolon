# Hierarchical reviewer v2732.0 — bounded intermediate synthesis

**Status: deterministically qualified to 64 parts; real-model validated at 19 parts. NOT installed as the active
reviewer for any experiment.**

This record is separate from the v2731.8 validation and from
[the capacity qualification](REVIEWER_CAPACITY_QUALIFICATION.md) that motivated it.

## 1. Identity

| | |
|---|---|
| contract | `v2732.0` |
| module | `conscious_agent/experiment_review_hierarchical.py` |
| digest (working copy, CRLF) | `07054cacc0f05fd8fc26594cf9a15c6c5cd7f6cddb3f61b4f7e25904ef00cdd3` |
| digest (git blob, LF) | `ca3211798afa07e01010603aba4dcd9853383a97` (sha1) |
| baseline | `v2731.8`, **byte-for-byte unchanged**, imported not modified |

The baseline supplies package loading, chunking, observation grounding, statement validation, part and document
planning, the mutation guard, the ledger and the final prompts. No baseline limit was raised.

**G-EVID1 was not used** for implementation, tuning, debugging or validation, and was not read semantically.

## 2. Architecture

```
part review
  -> document-level synthesis
    -> bounded intermediate synthesis   (new)
      -> final synthesis
        -> mechanical verification
```

The intermediate level is a **bounded fan-in reduction tree**. Inputs are partitioned in stable order into groups of
at most `GROUP_MAX_INPUTS`; each group emits at most `GROUP_MAX_STATEMENTS`; uncited inputs carry forward unchanged
and re-enter the next round. Rounds repeat until the surviving count is at most `FINAL_MAX_INPUTS`.

### The convergence problem, and the honest fix

Carry-forward alone **does not converge**. The first build of this module stalled at a fixed point above the cap: a
model that cites a fraction of its inputs leaves the rest verbatim every round, and the surviving count asymptotes.
Measured: `74 → 56 → 47 → 42 → 40 → 40` at 34 parts. Simply adding rounds does not help.

So each round has a floor. It must shrink to at most `MIN_REDUCTION` of its input count, and when it would not, the
**minimum number** of uncited inputs needed to make progress is folded into one deterministic **register** for that
round. A register keeps the folded inputs' identifiers and their full observation lineage, and the artifact lists
every one of them. What stops travelling onward is only their prose.

Which inputs are folded is decided by how many rounds they have already gone uncited, then by stable position —
never by what they say. An earlier attempt that ranked by lineage size performed *worse*, because coverage is a set
union and a few overlapping high-lineage inputs cover fewer distinct observations than several diverse small ones.
That attempt was reverted rather than kept.

### Bounded is not the same as meaningful

A register keeps an observation accounted for, but the final synthesis cannot reason about prose it never sees. An
early version of this design satisfied every bound while collapsing to **2 final inputs** — a technically valid,
substantively empty review. So `MIN_SYNTHESISED_REPRESENTATION` requires at least half the evidence to reach the
final as actual statements; below that the review fails closed with `final_representation_below_floor`.

**This is stricter than the baseline**, which would carry such a review through to a final object. The difference is
deliberate. See §6.

## 3. The mathematical bound

```
FINAL_INPUT_BOUND_CHARS = FINAL_MAX_INPUTS x (MAX_STATEMENT_CHARS + FINAL_LINE_OVERHEAD_CHARS + 1)
                        = 32 x (200 + 40 + 1)
                        = 7,712 characters
```

independent of part count, against:

| | chars |
|---|---:|
| **v2732.0 structural bound** | **7,712** |
| v2731.8 configured budget | 12,000 |
| hard context ceiling, `final:second_half`, 8,192-token window | 13,488 |

The bound sits at 64% of the configured budget and 57% of the hard context ceiling, leaving headroom for prompt
overhead and output reserve at both final stages.

Both limits requirement 10 asks for are explicit: group size (`GROUP_MAX_INPUTS = 12`) and round width
(`MAX_GROUPS_PER_ROUND = 32`). Worst-case rounds from `N` surviving inputs is
`ceil(log(FINAL_MAX_INPUTS / N) / log(MIN_REDUCTION))` = 11 rounds from 320 inputs at `MIN_REDUCTION = 0.80`, which
is the document-level input count of a 64-part package. `MAX_ROUNDS = 12` covers the envelope with one round spare;
beyond it the review fails closed.

| limit | value |
|---|---:|
| `GROUP_MAX_INPUTS` | 12 |
| `GROUP_MAX_STATEMENTS` | 4 |
| `GROUP_INPUT_BUDGET_CHARS` | 6,000 |
| `MAX_GROUPS_PER_ROUND` | 32 |
| `FINAL_MAX_INPUTS` | 32 |
| `MAX_ROUNDS` | 12 |
| `MIN_REDUCTION` | 0.80 |
| `MIN_SYNTHESISED_REPRESENTATION` | 0.50 |

## 4. Deterministic qualification

Synthetic `Q-CAP` packages, deterministic stub calibrated to the measured G-INVAR review (0.45 statements per input,
~150 characters per rendered final input line), across an optimistic/nominal/pessimistic band. Evidence:
`experiments/Q-CAP/hierarchical_sweep.json`.

| band | 19 | 27 | 34 | 48 | 64 |
|---|---|---|---|---|---|
| optimistic | complete | complete | complete | complete | complete |
| **nominal** | **complete** | **complete** | **complete** | **complete** | **complete** |
| pessimistic | floor | floor | floor | floor | floor |

Nominal band detail:

| parts | rounds | final inputs | final chars | % of bound | observations | silent loss | model calls |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 19 | 1 | 26 | 3,939 | 51.1% | 95 | 0 | 51 |
| 27 | 2 | 24 | 3,606 | 46.8% | 135 | 0 | 73 |
| 34 | 2 | 31 | 4,645 | 60.2% | 170 | 0 | 90 |
| 48 | 3 | 29 | 4,266 | 55.3% | 240 | 0 | 130 |
| 64 | 4 | 26 | 3,819 | 49.5% | 320 | 0 | 177 |

**The final block does not grow with part count.** 19 parts → 3,939 chars; 64 parts → 3,819 chars. Compare v2731.8,
where the same quantity grew roughly 376 characters per part and hit 98.9% of budget at 34.

At every nominal scale: part coverage 1.00, zero silently dropped observations, uncaptured accounting balancing
exactly, every quote relocating byte-exactly inside its own part, all identifiers valid, every intermediate group and
both final halves accepted, mutation guard intact, no truncation or schema rejection.

## 5. Adversarial tests

`tools/v2732_0_0_hierarchical_reviewer_tests.py` — **49 checks, all passing**, covering: deterministic and
content-blind grouping, ordering preservation, the stated bound, no growth with part count, explicit downstream state
for every observation, register lineage integrity, disagreement-kind survival, fabricated intermediate citations,
a failed intermediate stage never being bypassed, a bounded-but-vacuous review being refused, mutation guard
integrity, and end-to-end determinism.

`tools/v2731_13_0_reviewer_capacity_tests.py` — 33 checks, still passing, and asserts the baseline's limits are
unchanged.

One bug this suite caught in the harness itself: the stub's input-id pattern did not match `GS`/`U` identifiers, so
from round two the stub saw no citable inputs and everything fell through to folding. The consolidation numbers
measured before that fix understated the architecture and were discarded.

## 6. Historical fixture comparison

Both reviewers run over the same installed fixture packages with an identical deterministic stub, so any difference
is architectural rather than model variance. G-EVID1 excluded.

| fixture | parts | reviewer | status | coverage | observations | silent loss | final inputs | final chars | calls |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| G-INVAR | 19 | v2731.8 | complete | 1.00 | 95 | 0 | 38 | 5,774 | 50 |
| G-INVAR | 19 | **v2732.0** | complete | 1.00 | 95 | 0 | 26 | **3,917** | 54 |
| G-REL-fixtures | 27 | v2731.8 | complete | 1.00 | 135 | 0 | 54 | 8,224 | 66 |
| G-REL-fixtures | 27 | **v2732.0** | complete | 1.00 | 135 | 0 | 24 | **3,580** | 74 |
| G-CAND2-refx | 26 | v2731.8 | complete | 1.00 | 130 | 0 | 52 | 7,880 | 64 |
| G-CAND2-refx | 26 | **v2732.0** | complete | 1.00 | 130 | 0 | 24 | **3,458** | 72 |

**No coverage, grounding or loss difference on any fixture.** The final input block falls 32–57%; model calls rise
8–12%, which is the cost of the consolidation rounds.

### Behavioural differences to declare

1. **v2732.0 refuses reviews v2731.8 would complete.** Under the pessimistic band — a model citing ~25% of its
   inputs — the baseline emits a final object at every scale; v2732.0 fails closed on the representation floor,
   including at 19 parts, which the baseline has historically passed. This is a deliberate tightening, not a
   regression, but it means the two reviewers are not interchangeable on thin model behaviour.
2. **Statement identifiers differ.** v2732.0 mints `GS` (group) and `U` (register) identifiers the baseline never
   produces. Downstream consumers that pattern-match identifier prefixes need updating before this reviewer is
   installed anywhere.
3. **Model calls increase** 8–12% on fixture-scale packages, more at larger scales.

## 7. Real-model validation

One bounded run with the production model: `qwen3.8:27b`, ollama, context 8,192, resolved config
`f398196f63e0eb56d8bc34e7e8c55f212b851145dd067aa3f8ed081297168a62` — the same configuration G-EVID1 ran on. 19 parts
is the smallest synthetic scale that still exercises a consolidation round, so it is the cheapest run that
demonstrates the hierarchy works with a real model rather than only with a stub.

**Status: `complete`. 1 h 58 m (7,079 s), 53 model calls, 70,727 prompt + 29,420 output tokens.**

| measure | result |
|---|---|
| part coverage | 19/19 = **1.00** |
| grounded observations | **141** |
| silent loss | **0** |
| uncaptured accounting | balances |
| quote relocatability | **298/298 byte-exact**, all inside their own part |
| identifier validity | valid — 236 known, 236 cited, no unknown or dropped references |
| intermediate synthesis | 1 round, 4 groups, all accepted, converged |
| reduction | 43 → 26 inputs (**×0.605**) |
| final input | 26 inputs, **3,582 chars** = 46.4% of the 7,712 bound, 29.9% of the 12,000 budget |
| final synthesis | both halves accepted |
| disagreement preserved | **24 non-finding statements** of 95: 8 disagreement, 9 unresolved_relationship, 5 minority, 2 uncertainty |
| degradation | 1 truncation at the output limit, recovered on retry; no stage left without an accepted reply |
| mechanical verification | `missing: []` |

Two results matter beyond the pass:

- **The real model compresses harder than the nominal stub.** Its natural round reduction was ×0.605, comfortably
  inside `MIN_REDUCTION = 0.80`, so **no folding was needed at all** and no register was created. Where the stub
  required folding to converge, the production model converged on its own. The nominal band is therefore
  conservative relative to this model, not optimistic.
- **The real model grounds more observations per part** — 141 over 19 parts (7.4/part) against the stub's 95
  (5.0/part). More upstream evidence means more document-level inputs at scale. Extrapolating both measured real
  rates together (7.4 observations/part, ×0.605 per round), a 64-part package reaches ~145 document-level inputs and
  converges in 3 rounds, well inside `MAX_ROUNDS = 12`. The two effects offset; the higher observation count does
  not threaten the bound.

**Not covered by this run:** no real-model run was performed at 34, 48 or 64 parts. The 64-part envelope is
deterministically qualified and real-model *consistent* by extrapolation from measured rates, but it has not been
directly demonstrated with the production model. At this host's measured rate a 34-part real run is ≈3.4 hours and a
64-part run ≈6.7 hours.

One process note: the measurement harness computed `identifier_validity` as false in the raw run output. That was a
stale import — the run began before the harness was taught to recognise the new `GS` and `U` identifiers.
Recomputed against the same saved artifact with the corrected function it is valid, as the table records. The
reviewer's own `unknown_references` and `dropped_references` were empty throughout.

## 8. Limitations

- **The representation floor is a policy choice, not a measurement.** 0.5 is defensible but not derived; a package
  whose model behaviour sits near it will be sensitive to the exact value.
- **Register folding loses prose at the final level.** Lineage and identifiers are preserved and the artifact lists
  every folded input, but the final synthesis cannot reason about the content of folded evidence. At 64 parts a
  meaningful share of evidence reaches the final only as a register pointer.
- **Model calls grow with scale**: ~177 at 64 parts nominal, against ~80 for the baseline architecture at 34.
  At this host's measured rate that is a multi-hour review.
- **The pessimistic band does not qualify at any scale.** A model that cites very little cannot be reviewed at
  length by this architecture; it fails closed rather than producing a thin review.
- **Detached-job reliability** has not been exercised at all for this reviewer. `tools/run_review_job.py` calls
  the baseline directly, and pointing it at v2732.0 is installation work, which requirement 18 excludes.
- **Real-model validation covers 19 parts only.** 34/48/64 are deterministic plus extrapolation from measured
  real rates, not direct demonstration.

## 9. Reproducing

```bash
python tools/reviewer_capacity_qualification.py --reviewer v2732.0 --out experiments/Q-CAP/hierarchical_sweep.json
```

```bash
python tools/v2732_0_0_hierarchical_reviewer_tests.py
```
