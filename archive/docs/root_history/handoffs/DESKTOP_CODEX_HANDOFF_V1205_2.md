# Desktop Codex handoff: v1205.2

1. Verify the candidate SHA-256 supplied with the archive.
2. Extract beneath exactly one `Eidolon/` root.
3. Run `python tools\v1205_0_2_general_small_project_consolidation_tests.py`.
4. Run `python tools\post_review_development_verify.py --profile quick --json`.
5. Start the dashboard and verify the POST-only `/api/development-campaign/implement-small-project` route for one approved website, JavaScript tool, and Python CLI proposal.
6. Confirm unsupported project kinds return an explicit limitation without provider contact.
7. Confirm no selected project changes, dependency installation, repair authority, release authority, or model management occur.

Do not install, promote, certify, or declare the candidate final.
