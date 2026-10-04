# Post-START control-flow closure

Scope: implementation-only repair of LR2_CONTROL_FLOW_EXCEPTION. Accepted
corpus, gold, design, blueprint, scientific gates, schedules, provider/model
configuration, and G-ROUTE4 historical closure are unchanged.

The generic guarded wrapper still catches Exception, not BaseException.
At the boundary after START and before transport-result validation returns,
ordinary Exception retains the existing unreceipted-provider-failure behavior.
Any escaping non-Exception BaseException first retains the existing INVALID
event SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT, scoped to the active
phase/cell, in memory and in the append-only owned integrity journal. The
original exception object is then re-raised with a bare raise.

No provider receipt or journal record type is fabricated. The open START is
historical evidence of an omitted scheduled call. Current-run terminality is
established before external catch; disk reconstruction rejects the open call
under the same frozen omission semantics. No subsequent START or transport
invocation is allowed.

Producer evidence includes actual A/B signal paths, original-object identity,
retained incident scope/category, post-catch collection rejection, restart
rejection, RuntimeError/ValueError/OSError regressions, malformed outcome and
checkpoint regressions, all ten precontact blockers, I1-I6, and two complete
720-observation synthetic pilots with byte-for-byte evidence comparison.
Exactly one fresh independent read-only closure audit follows the producer
evidence. No repair is permitted after that audit in this task.

The new freeze candidate is EXECUTION_FREEZE_CANDIDATE_ONLY and unactivated.
It supersedes but does not retroactively validate these blocked candidates:

- 14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f
- 6e7295b3c79ee95930fee7231265e342905b7848d261ae716d1ef1546ca785ab
- 687a9a50d9bbbe480f3e74e103f5b75c621a46a9ffdcc8e80dab65f6b2915a35

Provider/model calls and real Phase A/B calls are zero. Execution freeze is
inactive; Phase A/B are unauthorized. No autonomy; belief effects none.
