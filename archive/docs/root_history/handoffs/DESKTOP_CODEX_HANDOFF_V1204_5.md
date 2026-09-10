# Desktop Codex Handoff: v1204.5

1. Verify the candidate SHA-256 supplied with the package.
2. Extract beneath exactly one `Eidolon/` root.
3. Run `python tools/v1204_3_5_selected_project_rollback_recovery_tests.py`.
4. Run `python tools/release_verify.py --profile quick --json` with runtime data outside the source tree.
5. In the dashboard, verify the POST-only apply-recovery, rollback-request, and rollback-authorization endpoints.
6. Confirm rollback requires the exact proposal ID, revision, and rollback-request digest.
7. Confirm no release promotion, automatic repair, model management, or independent authority is granted.
