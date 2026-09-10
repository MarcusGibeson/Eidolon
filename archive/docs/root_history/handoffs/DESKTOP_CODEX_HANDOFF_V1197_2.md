# Windows/Desktop Codex Handoff: v1197.2

## Candidate purpose

Review the source-only v1197.2 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install Foundations candidate.

## Review priorities

1. Confirm the five lifecycle operations remain evidence-only and deterministically ordered.
2. Confirm exact binding of snapshot, context, source and target version, source and target schema, runtime, backup, rollback, manifest, artifact, receipt, sequence, and prior evidence.
3. Confirm original-runtime, backup, rollback, and isolated fresh-install truth cannot be forged without rejection.
4. Confirm Windows paths and encodings do not affect digest or source-discovery behavior.
5. Confirm CLI and API exposure is read-only and POST remains unavailable.
6. Confirm no runtime or source files are created, copied, changed, or removed by the checkpoint.
7. Keep the inherited global-profile debt separate from current v1197 regression status.

## Expected commands

```powershell
python tools/v1197_0_2_runtime_lifecycle_migration_tests.py
python tools/v1196_9_adversarial_privacy_authority_replay_recovery_checkpoint_tests.py
python tools/v1195_9_long_session_multi_day_soak_checkpoint_tests.py
python tools/v1150_1_external_runtime_data_migration_tests.py
python tools/v1150_1_source_only_runtime_boundary_tests.py
```

Set `PYTHONDONTWRITEBYTECODE=1` and direct `EIDOLON_DATA_DIR` to a neutral external path. Run compilation with bytecode outside the source tree.

## Explicit non-goals

Do not apply migration, upgrade, rollback, fresh installation, approval, installation, promotion, certification, publication, release, or autonomous authority. The next Desktop Codex and native-provider decision gate remains v1200.
