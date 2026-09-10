# v1270.0-v1270.9 Focused Validation

## Direct v1270 suites

- `tools/v1270_0_2_self_development_alpha_foundations_tests.py`
- `tools/v1270_3_5_self_development_alpha_integration_tests.py`
- `tools/v1270_6_8_self_development_alpha_reliability_tests.py`
- `tools/v1270_9_self_development_alpha_checkpoint_tests.py`

The direct suites cover deterministic campaign preparation, evidence-backed priority and plan lineage, exact candidate and repair authorization, trusted selected-test execution, one bounded repair, v1268 review generation, non-authorizing review disposition, concurrent duplicate convergence, stale source, resealed lineage tamper, cancellation/cleanup, long paths, and checkpoint read-only behavior.

## Retained evidence

Retain the v1261-v1269 checkpoint chain, v1250.3 release metadata consolidation, v1250.4 checkpoint registry consolidation, v1247.9 privacy/security audit, source-only package scanning, and whole-tree Python compilation.

## Full-source milestone probe

Run v1270 against the real Eidolon source with an explicit bounded probe signal. The probe may modify only a disposable v1265 source copy, must use v1266-selected trusted verification, must stop at a v1268 review packet, and must leave the active source manifest unchanged.

## Packaging gates

1. Remove runtime data, caches, bytecode, logs, archives, and disposable workspaces from the source candidate.
2. Build from the source-only package inventory.
3. Verify exactly one `Eidolon/` archive root.
4. Run root and ZIP privacy checks.
5. Fresh-extract and compare every packaged file by digest.
6. Rerun all four v1270 suites, release metadata, checkpoint registry, privacy/security, and Python compilation from the exact final extraction.
