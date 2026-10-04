# G-EXTRACT1 Bounded Lifecycle Repair

Scope: implementation only, following the blocked audit at
`d331a265c2bfa9abe8b9824930fff19a2f98e746`. Accepted scientific design,
blueprint, corpus, gold, thresholds and historical evidence are immutable.

## I1: Resume Lock

Construction with `resume=True` reconstructs evidence read-only, but cannot
perform, enter B, create a checkpoint or finalize until `resume(checkpoint)`
verifies the authoritative checkpoint marker, sealed prefix, schedule, next
position, frozen binding and reconstructed state. Failed verification is retained
and blocks further operations. No replacement checkpoint is created.

## I2: Retained Terminal Integrity

The shared guarded lifecycle path records integrity exceptions in a separate
write-once hash-chain incident journal. Catching an exception cannot clear its
event, invoke another transport or admit a phase transition. Reconstruction
loads incidents after reconstructing earlier legitimate call evidence. Receipted
failures retain the accepted INCOMPLETE event; unreceipted failure is INVALID.

Successful sealed resume adds a `RESUME_VERIFIED` record retaining
`MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT`. Remaining observations in the same
phase may be preserved, but the INCOMPLETE verdict is never cleared. Interrupted
A cannot qualify into B. The two complete qualification rehearsals are clean,
uninterrupted synthetic runs; interruption tests are isolated and retain failure.

## I3: Integrated State

A eligibility derives from actual completed gate reports and lifecycle scopes,
not from a cache populated by `enter_b()`. Before B entry, completed passing A
cells are A_QUALIFIED_FOR_B, failed A cells have B_NOT_ELIGIBLE, and the report is
nonterminal when B remains available. Receipted failures and sealed interruption
produce A_INCOMPLETE/B_INCOMPLETE, never a successful qualification state.
INVALID events dominate the frozen primary verdict precedence.

## I4: Semantic Replay

FAILURE replay reconstructs the event from failure kind, receipt presence,
call ID and exact request digest, then compares the stored event and category.
Checks remain effective against an attacker who recomputes journal hash chains.
Checkpoint markers bind the pre-marker prefix and full seal. Every START binds
the authoritative lineage then in force. RESUME_VERIFIED must immediately follow
the matching marker; unsealed tails and fabricated lineage fail closed.

## I5: Phase Authorization

Resumed phase is reconstructed before checking the phase grant. B resume needs
B authorization, not A authorization. A grants cannot authorize B and B grants
cannot authorize A. Candidate or inactive freezes authorize neither. Boundary
tests exercise this logic with an explicitly mechanical-only flag and synthetic
transport. They create no actual activation pointer or operator phase grant.

## I6: Complete Protected Inputs

All four manifest digest maps and five scalar file bindings are enumerated and
their actual bytes hashed. Unknown digest groups reject rather than disappearing
from coverage. The candidate source file is hashed; the separately bound gold
projection is recomputed from accepted candidate gold using the original exact
serialization. Streaming hashing preserves exact digest semantics for large
historical evidence. Isolated actual-byte mutations cover newly included checker,
source/supplement and preserved-report artifacts before and after contact.

## Evidence And Authority

The old pilot, audit and blocked candidate remain unchanged. The new candidate
explicitly supersedes blocked SHA-256
`14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f`.
It remains EXECUTION_FREEZE_CANDIDATE_ONLY and unactivated. Separate freeze review,
activation, Phase A and conditional Phase B authorization remain necessary.
Both complete synthetic evidence trees are retained and compared file-for-file.
Exactly one independent read-only audit follows successful targeted tests and
both complete pilots. Any P1/P2 finding stops this task without another repair or
nested review cycle.

Provider/model calls: 0. Real A/B calls: 0. Corpus/gold/design/blueprint changes: 0.
G-ROUTE4 remains CLOSED FAILED. Autonomy: false. Belief effects: none.
