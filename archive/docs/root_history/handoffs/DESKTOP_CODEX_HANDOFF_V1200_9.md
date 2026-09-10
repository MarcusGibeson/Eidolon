# Desktop Codex Handoff: v1200.9 Development Candidate

1. Verify the candidate SHA-256 before extraction.
2. Extract beneath exactly one `Eidolon/` root beside, not over, the installed v1200.0 baseline.
3. Run `python tools/v1200_7_9_structured_generation_tests.py`.
4. Run `python tools/release_verify.py --profile quick --json > v1200_9_quick.json`.
5. Start the dashboard and verify that an approved, grounded proposal can invoke `/api/development-campaign/generate` with exact proposal revision, revision digest, and planning digest.
6. Confirm malformed paths, stale digests, unplanned files, oversized output, and invalid syntax return a blocked digest-only result.
7. Confirm no generated files appear in the selected project, source tree, or an implementation workspace.
8. Confirm raw provider prompts and output exist only under the external runtime root.

Do not install, promote, certify, or replace the Desktop-verified v1200.0 baseline from this handoff.
