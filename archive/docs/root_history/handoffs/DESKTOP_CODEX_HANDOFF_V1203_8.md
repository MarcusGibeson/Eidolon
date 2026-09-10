# Desktop Codex handoff: v1203.8

1. Verify the candidate SHA-256 supplied with the archive.
2. Extract beneath exactly one `Eidolon/` root in a clean location.
3. Run `python tools/v1203_6_8_python_cli_result_disposition_tests.py`.
4. Run `python tools/v1203_3_5_project_owned_python_tests.py`.
5. Start the dashboard and confirm a completed Python CLI result exposes Review, then retain/revise/reject/discard controls.
6. Confirm discard removes only the external isolated workspace; no disposition changes the selected project.
7. Confirm release, repair, and apply authority remain false.

This is a development candidate, not an installation or promotion instruction.
