# Desktop Codex Handoff: v1201.5

1. Verify the candidate SHA-256 against the supplied digest.
2. Extract beneath exactly one `Eidolon/` root and confirm no packaged `data/`, caches, conversations, provider payloads, credentials, or private paths exist.
3. Run `python tools/v1201_3_5_isolated_workspace_preview_tests.py`.
4. Run `python tools/v1201_0_2_isolated_workspace_materialization_tests.py` and the retained calculator regression.
5. Start the dashboard using the normal Windows installation procedure.
6. Complete an approved small webpage campaign through materialization, open Development Proposals, and select **Open isolated preview**.
7. Confirm the preview opens through `/development-preview/<opaque-token>/`, assets load, refresh is repeatable, and the selected project remains unchanged.
8. Confirm traversal attempts and unknown tokens return a content-free failure, and inspect response headers for `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and the restrictive content-security policy.

Do not install, promote, certify, apply to a selected project, or infer browser-test success from structural preview evidence.
