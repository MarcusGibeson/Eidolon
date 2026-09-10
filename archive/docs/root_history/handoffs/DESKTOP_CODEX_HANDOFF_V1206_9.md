# Desktop Codex Handoff v1206.9

1. Verify the candidate SHA-256 before extraction.
2. Extract beneath exactly one `Eidolon/` root.
3. Run `python tools/v1206_9_browser_runtime_test_adapter_checkpoint_tests.py`.
4. Run `python tools/v1206_6_8_browser_runtime_reliability_tests.py`.
5. In the dashboard, build an isolated website, run the browser runtime test, and choose **Seal browser runtime checkpoint**.
6. Confirm the checkpoint shows nine bound stages, runtime pass/fail evidence, cleanup state, operator review required, and no repair or apply authority.
7. Confirm duplicate checkpoint requests resume the same digest and stale runtime-result digests are rejected.
8. Run the bounded quick release profile.

Do not install, promote, certify, release-authorize, or declare the candidate final.
