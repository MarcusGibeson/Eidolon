# v1255.9 Controlled Application and Rollback Checkpoint Validation

v1255.9 is a read-only checkpoint. Its builder inspects source and structured release/checkpoint metadata only. It does not read private development runtime state, apply or roll back a project, create a backup, execute tests/commands, contact a provider, or grant authority.

## Checkpoint evidence

- `tools/v1255_9_controlled_application_rollback_checkpoint_tests.py`: **35/35 passed**.
- `tools/v1255_0_2_controlled_application_foundations_tests.py`: **44/44 passed**.
- `tools/v1255_3_5_controlled_application_integration_tests.py`: **43/43 passed**.
- `tools/v1255_6_8_controlled_application_reliability_tests.py`: **50/50 passed**.
- Retained v1254.9 isolated-coding checkpoint: **33/33 passed** after historical-current-version compatibility repair.

The checkpoint preserves exact, separate application and rollback authorization and leaves installation, promotion, certification, release, permanent approval, unrestricted shell/dependency authority, and independent self-update authority denied.

Next bounded unit after Desktop review: **v1256 Persistent Development Sessions**. v1256 has not been started.
