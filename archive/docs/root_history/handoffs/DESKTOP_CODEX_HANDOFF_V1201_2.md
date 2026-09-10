# Desktop Codex Handoff: v1201.2 Development Candidate

1. Verify the candidate SHA-256 supplied with the archive.
2. Extract beneath exactly one `Eidolon/` root and keep runtime data external.
3. Run `python tools/v1201_0_2_isolated_workspace_materialization_tests.py`.
4. Run `python tools/v1200_7_9_structured_generation_tests.py` and `python tools/v1200_0_cognitive_beta_autonomous_developer_alpha_tests.py`.
5. Start the dashboard and POST exact proposal, planning, and generation bindings to `/api/development-campaign/materialize`.
6. Confirm the response exposes only digests and counts, the external workspace contains the generated files, and the selected project remains byte-for-byte unchanged.
7. Do not install, promote, certify, or apply the workspace to the selected project.
