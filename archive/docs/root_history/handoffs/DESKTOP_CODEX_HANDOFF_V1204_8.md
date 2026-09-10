# Desktop Codex Handoff: v1204.8

1. Verify the candidate SHA-256 supplied with the archive.
2. Extract beneath exactly one `Eidolon/` root.
3. Run `python tools/v1204_6_8_selected_project_apply_rollback_reliability_tests.py`.
4. Run `python tools/release_verify.py --profile quick --json`.
5. In the dashboard, verify apply recovery and rollback recovery are POST-only and expose no project paths or rollback content.
6. Confirm no release, repair, model-management, or independent authority is granted.

Do not install or promote this development candidate.
