# Desktop Codex Handoff: v1203.5

1. Verify the candidate SHA-256 supplied with the archive.
2. Extract beneath exactly one `Eidolon/` root.
3. Run `python tools/v1203_3_5_project_owned_python_tests.py`.
4. Run `python tools/v1203_0_2_python_cli_implementation_foundations_tests.py`.
5. Run `python tools/release_verify.py --profile quick --json` with runtime storage outside the source tree.
6. In the dashboard, create and approve a Python CLI proposal and POST the exact proposal ID, revision, and revision digest to `/api/development-campaign/implement-python-cli-with-tests`.
7. Confirm the result reports seven stages, project-test counts, digest-only evidence, operator review required, and no apply or repair authority.

Do not install, promote, certify, or apply the candidate during this review.
