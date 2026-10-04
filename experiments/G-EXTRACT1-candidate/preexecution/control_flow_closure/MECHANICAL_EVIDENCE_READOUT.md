# Control-flow closure producer evidence

Implementation commit: 17af89c9c4f279d55d48aac46125c2844d3b4ad5.
Producer evidence commit: 10cc8a978237fa6a403c1bfd72184845200b192e.
Accepted science closure: 6c85b10930cefe410a1965c0924e4fd9f47eb4ef.

These are synthetic implementation checks, not scientific qualification.
Provider/model calls and real Phase A/B calls are zero.

## Scoped transport repair

The generic guarded wrapper is unchanged. Non-Exception BaseException signals
escaping the post-START transport invocation/result-validation boundary retain
SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT before a bare re-raise. The
INVALID incident records the active phase/cell. No receipt or call-journal
record type is invented. The original signal object and arguments propagate.
Current collection is terminal immediately; reconstruction rejects the open
START under the existing omission semantics.

The 102 new CF checks cover KeyboardInterrupt, SystemExit, GeneratorExit,
custom BaseException in A and B, plus receipt-validation control signals.
They prove retention before propagation, append-only disk persistence, no
fabricated completion/receipt, immediate INVALID reporting, external-catch
collection rejection with zero later transport invocations/no second START,
and restart rejection. RuntimeError, ValueError, and OSError preserve the
governed PROVIDER_FAILURE_WITHOUT_RECEIPT regression behavior.

## Complete producer replay

- Total deterministic checks: 2623, all PASS.
- LR1: 137; LR2: 143; LR3: 42.
- I1: 15; I2: 38; I3: 22; I4: 10; I5: 8; I6: 83.
- All ten frozen global precontact blockers: PRE_CONTACT_BLOCKED, six A_BLOCKED
  cells, zero transport. Postcontact INVALID/INCOMPLETE never becomes A_BLOCKED.
- Two clean full pilots: 480 A and 240 B observations each, 720 total each.
- All 64 conditional B subsets; 108 E5 wire audits; 12 elapsed clarifications.
- All 1447 authority-bearing files per pilot match byte-for-byte across both
  clean trees. Complete journals/checkpoints/schedules/final reports retained.
- All 50 protected files and all 25 existing corpus JSON artifacts unchanged.
- No corpus/gold/design/blueprint/threshold/schedule/configuration modification.

Phase A schedule SHA-256:
3c48390307dd683e7ba2f736318d42f4d9fbda6527bbb9d64ee03b4bf97bb4dd

Maximum Phase B schedule SHA-256:
6361e990216be94ca3ad69b75b485adf70fc8a035b2e459e5d309063c8ea164b

## Implementation byte bindings

- tools/g_extract1_runner.py:
  70824534f88a0c08b5f88afde354aba7d83e23ed78560108139a4b85d9a88ef5
- tools/g_extract1_pilot.py:
  35eea1d9e0a823e6d1380bb422425ef308fa3564e5bc755726ddedbaf23e65e2
- tools/g_extract1_control_flow_tests.py:
  9ddf037576aa9f12c425427b7a17dc8719235d60592e40a9cfcc98c472f83177

The candidate also binds unchanged contract/journal/scoring/regression modules,
accepted package/science closure, all protected manifest entries, schedules,
journal/checkpoint schema, LR/CF reports, complete pilot evidence, and E5 audit.

New candidate file SHA-256:
4819d754192df7c49055a825353b9387d2cf51efe9652ef9f64bda8736be62c1

Candidate status: EXECUTION_FREEZE_CANDIDATE_ONLY. Activation false. The three
prior candidates listed in REPAIR_SPEC.md remain blocked/unactivated and
byte-identical. Exactly one independent audit is required; its separate
IMPLEMENTATION_CLOSURE_AUDIT report and PREEXECUTION_STAGE_STATUS record govern
readiness. Producer PASS alone grants no authority. No post-audit repair.

Execution freeze inactive. A/B unauthorized. Autonomy false; belief effects
none. G-ROUTE4 remains CLOSED FAILED and unchanged.
