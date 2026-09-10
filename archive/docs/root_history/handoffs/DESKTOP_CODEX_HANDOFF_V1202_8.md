# Desktop Codex handoff: v1202.8

1. Verify the candidate SHA-256 supplied beside the archive.
2. Extract beneath exactly one `Eidolon/` root into a clean Windows worktree.
3. Run `python tools/v1202_6_8_javascript_tool_result_disposition_tests.py`.
4. Run `python tools/v1202_3_5_project_owned_javascript_tests.py`.
5. Run `python -m compileall -q conscious_agent tools` with bytecode directed outside the source tree where practical.
6. Run `python tools/release_verify.py --profile quick --json` using external runtime storage.
7. In the dashboard, complete a JavaScript-tool checkpoint, create its review packet, and verify retain/revise/reject/discard controls.
8. Confirm discard removes only the isolated external workspace and does not modify the selected project.
9. Confirm duplicate disposition submissions consume the exact review decision once and conflicting submissions are rejected.
10. Do not install, promote, certify, or apply the candidate during review.
