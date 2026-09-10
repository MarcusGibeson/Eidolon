# Desktop Codex Handoff: v1201.8

1. Verify the candidate SHA-256 supplied beside the archive.
2. Extract beneath exactly one `Eidolon/` root in a clean directory.
3. Run `python tools/v1201_6_8_bounded_browser_javascript_validation_tests.py`.
4. Run `python tools/v1201_3_5_isolated_workspace_preview_tests.py`.
5. Run `python tools/v1201_0_2_isolated_workspace_materialization_tests.py`.
6. Run `python tools/release_verify.py --profile quick --json`.
7. Start the dashboard, create and approve a small webpage proposal, generate and materialize it, open the isolated preview, then select **Run bounded validation**.
8. Confirm successful JavaScript reports a digest-only pass and malformed JavaScript reports a digest-only failure without repair or project mutation.
9. Confirm the selected project and Eidolon source remain unchanged and runtime validation records remain outside the source tree.

Do not install, promote, certify, or treat the candidate as final.
