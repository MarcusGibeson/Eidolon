# Desktop Codex Handoff v1206.8

1. Verify the candidate SHA-256.
2. Extract beneath one `Eidolon/` root.
3. Run `python tools/v1206_6_8_browser_runtime_reliability_tests.py`.
4. On Windows, verify discovery can classify Chrome or Edge without exposing the executable path publicly.
5. Verify a valid website passes runtime execution, a missing browser fails with digest-only evidence, live journals block duplicate execution, and stale journals recover exactly once.
6. Run the bounded quick release profile.

Do not install, promote, certify, or declare the candidate final.
