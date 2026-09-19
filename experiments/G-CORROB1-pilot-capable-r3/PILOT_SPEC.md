# G-CORROB1 live mechanical-pilot specification

This specification creates a separately governed, pilot-only path. It does not
amend or reinterpret the frozen G-CORROB1-R2 experiment.

## Three distinct layers

### A. Deterministic structural tests

Offline fixtures exercise request construction, parsing, validation, governance,
pairing, persistence, Activity, and both scorer boundaries. They contact no
provider and carry no execution authority.

### B. Authorized two-call live mechanical pilot

One dedicated synthetic item (`PX01`) produces exactly one blind A/B pair and two
generation calls. The calls use the production prompt builder, provider adapter,
parser, structural validator, individual governance, paired comparator,
persistence primitive, and shared Activity subsystem. A pilot-only verifier
checks lineage and mechanical completeness without gold or semantic correctness.

The live path requires an exact operator authorization bound to the pilot-capable
freeze candidate digest. It is unable to authorize the full experiment.

### C. Full G-CORROB1 execution

The production runner remains unchanged: 32 items, three repeats, two roles, 192
calls, 96 pairs, and the production scorer's fixed denominators. A pilot receipt
is not an experiment result and cannot satisfy this path.

## Pilot pass boundary

The pilot may establish only live mechanics: model/config binding, submitted
seeds/options, fresh request sessions, response preservation, parsing,
validation, governance/comparator plumbing, pilot persistence, Activity, and
terminal lineage. It must not interpret semantic correctness, agreement,
disagreement, disposition, utility, or safety.

The pilot fails closed on provider/configuration mismatch, fallback, malformed or
truncated output, binding/assessor errors, duplicates, missing roles, stale data,
digest or persistence failure, namespace crossover, or lineage failure. There is
no retry and no model-based repair.

## Authority

The checked-in freeze candidate has `pilot_authorized=false` and
`experiment_authorized=false`. A later one-shot authorization wrapper may enable
only the two-call pilot. Full experiment authority remains a separate contract.

The failed first attempt remains preserved at
`experiments/G-CORROB1-candidate-r2/MECHANICAL_PILOT_ATTEMPT_1_BLOCKER.md`.
