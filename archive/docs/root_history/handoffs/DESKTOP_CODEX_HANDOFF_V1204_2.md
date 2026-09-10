# Desktop Codex Handoff: v1204.2

1. Verify the candidate SHA-256 supplied with the archive.
2. Extract beneath exactly one `Eidolon/` root.
3. Run `python tools/v1204_0_2_selected_project_apply_foundations_tests.py`.
4. Run `python tools/release_verify.py --profile quick --json` with runtime data outside the source tree.
5. In the dashboard, verify that selected-project apply requires a digest-bound request followed by the exact authorization phrase.
6. Confirm that a stale selected-project snapshot blocks before authorization consumption.
7. Confirm no release, repair, model-management, or independent authority is granted.
