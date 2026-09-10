# Desktop Codex Handoff: v1201.9

1. Verify the candidate SHA-256 supplied with the archive.
2. Extract beneath exactly one `Eidolon/` root and confirm no packaged `data/`, caches, credentials, conversations, provider payloads, or private paths exist.
3. Run `python tools/v1201_9_small_website_implementation_checkpoint_tests.py`.
4. Run `python tools/v1201_6_8_bounded_browser_javascript_validation_tests.py` and the inherited focused suites if desired.
5. Run `python tools/release_verify.py --profile quick --json` from a clean external runtime configuration.
6. Start the dashboard, create a plain-chat request such as “Build me a to-do webpage,” approve the exact proposal revision, and use **Build isolated website**.
7. Confirm the dashboard shows a seven-stage small website checkpoint, exact-change counts, passing bounded validation, an opaque preview URL, and operator review still required.
8. Confirm no selected-project or Eidolon-source files changed and no apply, repair, model, promotion, certification, or release authority was granted.

This candidate is for review only. Do not install, promote, certify, or declare it final from this handoff.
