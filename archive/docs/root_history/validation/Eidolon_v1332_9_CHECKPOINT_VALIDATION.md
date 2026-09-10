# Eidolon v1332.9 Tool Preconditions Checkpoint Validation

This checkpoint continues Phase 4 from the immutable v1331.9 Tool Capability Registry checkpoint.

## Completed behavior

- Evaluates evidence-bound preconditions for a declared tool capability before future execution is considered.
- Checks registered capability, evidence-backed availability, workspace identity, cwd containment, clean boundaries, compatible workspace mode, dependencies, permissions, and expected artifact contracts.
- Side-effecting tools require an owned or candidate workspace; risk plans that require disposable/isolated execution require candidate-workspace evidence.
- Missing, unknown, contradictory, or unsupported evidence blocks the affected precondition rather than being silently treated as success.
- The evaluator consumes supplied evidence only: it performs no environment probe, invokes no tool, starts no process, mutates no project, and contacts no provider.
- Satisfying every precondition produces `tool_preconditions_satisfied_but_unauthorized`; preconditions are never authority.
- Ordinary chat can inspect the current supplied precondition state without converting inspection into execution.

## Focused deterministic evidence

- v1332.0-v1332.2 foundations: 5/5
- v1332.3-v1332.5 integration: 4/4
- v1332.6-v1332.8 reliability/adversarial: 5/5
- v1332.9 checkpoint: 5/5
- retained v1250.3 release metadata: 94/94
- retained v1250.4 checkpoint registry: 118/118

Tampered sealed records are rejected. Availability without evidence, dirty workspace boundaries, missing dependencies, unknown permission state, and missing expected-artifact contracts fail closed.

## Authority and platform boundary

No tool, command, test, project mutation, source mutation, installation, release, approval, or independent authority is granted. Native Windows execution remains external evidence and is not claimed by this Linux/container host.
