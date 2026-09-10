# Windows/Desktop Codex Handoff: v1197.8

## Candidate purpose

Review v1197.6-v1197.8 Runtime Lifecycle Reliability and Adversarial Hardening before the v1197.9 consolidation checkpoint.

## Review focus

1. Confirm all eight reliability event classes remain content-free and evidence-only.
2. Confirm exact lifecycle, operation, snapshot, context, plan, evidence, assessment, application-review, runtime, backup, rollback, manifest, sequence, and prior-event binding.
3. Confirm stale runtime, backup, rollback, manifest, review, and lineage are rejected.
4. Confirm interruption, integrity failure, rollback failure, contamination, drift, and recovery-reentry evidence cannot trigger real recovery or lifecycle application.
5. Confirm GET-only API and dashboard surfaces expose bounded public summaries only.
6. Confirm Windows execution uses explicit UTF-8 reads and creates no source-tree bytecode or runtime artifacts.
7. Confirm release verification registers v1197.8 exactly once.

## Required commands

Run from a fresh Windows extraction beneath exactly one `Eidolon/` root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = "."
python tools/v1197_6_8_runtime_lifecycle_reliability_adversarial_tests.py
python tools/v1197_3_5_runtime_lifecycle_application_review_tests.py
python tools/v1197_0_2_runtime_lifecycle_migration_tests.py
python tools/v1196_9_adversarial_privacy_authority_replay_recovery_checkpoint_tests.py
python tools/v1150_1_external_runtime_data_migration_tests.py
python tools/v1150_1_source_only_runtime_boundary_tests.py
```

Compile all source Python files with bytecode directed outside the extracted source tree.

## Expected focused results

- v1197.6-v1197.8: 409/409 PASS
- v1197.3-v1197.5: 278/278 PASS
- v1197.0-v1197.2: 177/177 PASS
- v1196.9: 248/248 PASS
- existing external runtime migration: 20/20 PASS
- source-only boundary: 9/9 PASS

## Hard boundaries

Do not read or modify real runtime data. Do not create a backup, migrate, upgrade, roll back, install, recover, retry, contact a provider or model, start a process or thread, create or consume approval, mutate source/runtime state, claim a global profile pass, or grant authority.

The next Desktop Codex and native-provider milestone review remains scheduled for v1200.
