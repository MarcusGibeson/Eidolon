# Governed failed-unit recovery

`failed-unit-recovery.v1` — `conscious_agent/review_recovery.py`

## Why it exists

The G-CORROB1-R2 independent review, attempt 3 (`b6e64bc963efc2b9`), observed 139 of 140 required parts over
9 h 44 m and then failed closed on `observe:D13:63`. Failing closed was correct: a review that cannot ground one
required part has not reviewed the package, and it must not synthesise over partial evidence.

What was not a decision anyone made is that the other 139 units — 708 grounded observations, nine and a half hours
of provider work — had no way to continue. The only path forward was to run the whole review again.

Recovery executes **only the units that failed**, and writes a **new derived artifact**.

## What it is not

|  | Pause / resume | Failed-unit recovery |
|---|---|---|
| Source state | live work, sealed checkpoint | a review that already terminated incomplete |
| Identity | same review, same job | new derived review, explicit lineage to the source |
| Scope | continue wherever it stopped | only the named failed units |
| Trigger | operator play/pause | separate governed operation, explicit confirmation |

Ordinary pause/resume must never be used to resurrect a terminal incomplete review. They answer different
questions and carry different guarantees.

## What recovery may not change

Recovery is review-execution repair, never scientific outcome repair. It does not touch the review package, the
corpus, gold, scorer results, experiment gates, the canonical experiment, or the source artifact. It does not relax
grounding, identifier support or quote allowances, and it grants no mutation authority. Belief effects remain none
and the derived artifact remains non-authoritative.

If the missing unit still grounds nothing, the derived review is incomplete, synthesis stays withheld, and the
failure is recorded — exactly as the original did.

## Compatibility

A unit may only be re-executed under the conditions the source review ran under. All nine of these must match
exactly, and any difference refuses the recovery outright — there is no override:

| Binding | Covers |
|---|---|
| `package_manifest_sha256` | the package as a whole |
| `package_documents` | every document, by digest |
| `reviewer_contract` | observation and synthesis semantics |
| `baseline_contract`, `baseline_module_sha256` | the frozen validator: chunking, grounding, identifier support, quote location |
| `prompt_templates_sha256` | the exact observation prompt and retry preface |
| `limits` | observation, quote and retry allowances |
| `model` | model, provider, context size, resolved configuration |
| `review_id_vocabulary` | which identifier classes exist |

### The one binding treated separately

`reviewer_module_sha256` is the reviewer module's **whole-file** digest. It covers synthesis, reporting and
accounting as well as observation, so any unrelated repair — fixing a wrong retry total, say — would otherwise make
every earlier incomplete review permanently unrecoverable.

A difference there never passes silently. It produces the verdict `execution_equivalent`, recovery refuses until it
is acknowledged **by exact digest**, and the acknowledgement is recorded in the derived artifact's lineage. The nine
execution bindings above must still match exactly, so an acknowledgement can never carry a change to how an
observation is produced or validated.

This scoping applies to recovery only. It does **not** change the whole-tree mutation guard, which answers a
different question — *did the protected source tree change during the review?* — and stays strict. It also does not
authorise concurrent source edits during scientific execution.

## Lineage

The derived artifact declares its own origin in `provenance.lineage`, and the same record is written beside it as
`recovery_lineage.json`:

- the source review id and the **digest** of the exact source artifact continued
- which units were re-executed
- how many observations were inherited, and the index above which every observation is recovered
- the full compatibility verdict, including any acknowledged module change

No hidden splicing: inherited observations are carried across byte-for-byte with their original identifiers, and
recovered observations are appended with their own provider-call and grounding provenance.

## Refusals

Recovery refuses, before writing anything or making any provider call, when: it is not explicitly confirmed; the
source review is complete; the source has gaps execution cannot fill (such as an absent required role); there are no
missing required units; a named unit was already observed successfully; a named unit was not missing in the source;
any execution binding differs; a reviewer-module change is unacknowledged or acknowledged with the wrong digest; or
a derived review already exists for that source.

## Invocation

Operator-invoked only. Nothing imports `review_recovery` — it is not reachable from the conversational adapter, the
job runner or the research UI, so a recovery cannot be triggered by Eidolon or by a UI click.

## Tests

`tools/v2734_1_0_failed_unit_recovery_tests.py` — 61 deterministic and adversarial checks, including a real
incomplete review produced by genuine grounding failure, byte-identity of the source across every operation,
per-binding refusals, acknowledgement handling, and fail-closed behaviour when recovery itself grounds nothing.
