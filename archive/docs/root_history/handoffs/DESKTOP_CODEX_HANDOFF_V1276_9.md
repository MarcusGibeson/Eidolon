# Desktop Codex Handoff — v1276.9 Architecture Boundary Extraction

Candidate source authority: v1276.9. Previous authoritative archive: v1275.9 SHA-256 `B5176256C1F74EF6EBC9890D3CDA2E0042566E8689F2F179458073CD9D5EC1CE`.

## Native Windows checks

1. Launch dashboard and API from a clean extraction and verify imports of `dashboard_development_campaign_panel`, `api_request_boundary`, and `release_evidence_boundary` do not alter startup ownership or route behavior.
2. Repeat import/startup after dashboard/API closure, abrupt process termination, and ordinary restart; no runtime migration should be required.
3. Exercise simultaneous read/import activity while Windows Defender/indexing is active and inspect NTFS sharing-violation behavior. Import errors must remain visible rather than silently bypassed.
4. Exercise drive-letter, UNC, and `\\?\` extended-length source roots, including a root whose selected extracted-module path exceeds 260 characters.
5. Confirm `api_server.py` still owns GET/POST route dispatch and HTTP server lifecycle, `dashboard.py` still owns dashboard request/action handling, and `self_maintenance.py` still owns release/governance mutation boundaries.
6. Confirm source-only packaging excludes runtime `data/`, private state, caches, logs, provider payloads, virtual environments, conversations, memories, prompts/responses, and generated credentials.
7. Inspect shutdown and filesystem locking around the extracted modules. No architecture extraction requires a write to those modules at runtime.

## Boundaries

Architecture evidence and a clean native run grant no provider, command, test, install, source-mutation, application, rollback, update, promotion, certification, release, permanent, or autonomous authority. v1277 has not been started.
