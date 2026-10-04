# G-EXTRACT1 Pre-Execution Implementation

Status: implementation and no-provider mechanical pilot only. The execution
freeze is a candidate, not an activation. Phase A and Phase B remain unauthorized.

## Immutable Inputs

Package commit: `81dc9d05f49e9c1310bb38676bfd7cf6a8620cf7`.
Independent closure audit: `6c85b10930cefe410a1965c0924e4fd9f47eb4ef`.
Manifest SHA-256:
`aad9f460edd373f5ce3a0b5469449e4b6df918081c956ca819c1b515f8ca1042`.
The loader verifies the accepted manifest, audit, every manifest final artifact,
the design/blueprint bindings and the historical baseline artifacts before use.
Neither corpus nor gold is rewritten. Original untracked authoring/failure files
remain outside this stage's Git staging list.

## Implementation Map

| File | Responsibility |
|---|---|
| `tools/g_extract1_contract.py` | Frozen package verification, identity receipts, schedule construction, exact wire bytes, E5 selector-span invariance |
| `tools/g_extract1_scoring.py` | Duplicate-aware lexical parser, exact comparator, frozen normalizer/operational integration, E7 outcomes, logical reductions, gates, transitions and first-match verdicts |
| `tools/g_extract1_journal.py` | Exclusive-create hash-chain records, flush/fsync, sealed checkpoints and prefix verification |
| `tools/g_extract1_runner.py` | Collection lifecycle, append-only starts/completions/failures, replay, conditional B eligibility, synthetic-only reserve checks and final packaging |
| `tools/g_extract1_pilot.py` | No-network synthetic tests, full two-pass mechanical replay, interruption/resume, candidate construction |

## Requests and Schedule

Phase A has 480 scheduled calls; the maximum conditional Phase B has 240.
The 720-call maximum contains no discovery, validation, retry or repair calls.
The harness independently reconstructs and compares the frozen blueprint
skeletons. Conditional B is a stable filter of the maximum template by the exact
sorted set of A-qualified cells, followed only by schedule-position renumbering.
Original template positions, call IDs and seeds remain bound.

Wire bodies have exactly the historical six keys. Input is the already accepted
corpus request; no scientific rendering changes are made. The historical system
text, common suffix, 12 elapsed-time clarifications and generation options remain
unchanged. `min_p` is not added: omission is part of the bound historical request.
Within each E5 model/base/repeat pair, only the designated escaped selector span
may differ. No timestamps, variant labels or session metadata enter wire bytes.

## Evaluation

Raw output is preserved. The bound transport normalizer removes only permitted
wrappers, retaining lexical numeric tokens and duplicate evidence. The unchanged
operational wrapper and the new exact comparator are reported separately.
Operational acceptance plus semantic failure is false-clean, including duplicate
keys and accepted truncation. E7 is explicit partial absence, not general
ambiguity; malformed containment earns no semantic recognition credit.

Positive logical properties require all repeats and all E5 variants. Adverse
properties affect a logical fixture if any observation is affected. Correlated
false-clean requires both repeats of the same rendered variant and is inapplicable
in B. E5 requires all five logical pairs correct, independently of the redundant
4/5 family floor. A and B reports are never pooled.

## Journal and Resume

Each START binds the complete scheduled call and exact wire digest. Each
COMPLETE preserves raw response, truncation evidence and deterministic evaluation.
Each FAILURE binds a call-specific receipt and its frozen integrity event. There
is no overwrite or silent retry. An unreceipted in-flight call is inadmissible.

Checkpoint authority excludes timestamps. It binds run, frozen inputs, source
hashes, schedule, journal prefix, next position, all cell reports and eligibility.
Replay rechecks call order, duplicates, request bytes, scoring and B eligibility
before verifying the checkpoint. A sealed interruption can resume; missing,
corrupt or inconsistent evidence fails closed. Historical interrupted evidence
is retained, not rewritten.

## Reserves and Activity

No actual reserve is activated. Synthetic tests cover only the 28 accepted
subtype01 backups, complete E5 pair replacement and pre-contact refreeze
requirements. Actual fixture semantics are revalidated by the pinned design
validator before canonical reserve profile comparison; caller-declared profile
equality is not evidence. Real activation requires a separate accepted refreeze.

Activity integration is not required by the accepted isolated experiment
architecture. No production runtime, router, persistence or Activity subsystem is
changed. Journal telemetry is operational only, with no private reasoning content.

## Authority Boundaries

The only CLI is the no-provider pilot. A socket tripwire forbids network access
throughout certification. Its transport and all evidence are explicitly synthetic.
Pilot reports use `synthetic_primary_verdict`, never real qualification. No run,
apply, release or execution-freeze activation pointer is written.

Future live collection requires a separately approved active execution freeze,
an explicit per-phase operator authorization bound to this run and implementation,
and a non-synthetic byte transport. This stage does not supply any such grant or
instantiate a provider adapter. Model/provider receipt tests are synthetic and do
not attest installed identities or internal provider option honoring.

G-ROUTE4 remains CLOSED FAILED. No historical rewrite, autonomy, production
routing update or belief effect occurs. One local-model research job at a time
remains required. Independent implementation audit follows pilot completion; a
blocker stops progression rather than starting a nested review sequence.
