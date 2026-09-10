# Desktop Codex Handoff: v1203.9

1. Verify the candidate SHA-256 supplied with the release artifact.
2. Extract beneath exactly one `Eidolon/` root on Windows.
3. Run `python tools/v1203_9_python_cli_implementation_checkpoint_tests.py`.
4. Run `python tools/release_verify.py --profile quick --json`.
5. Open the dashboard and confirm a disposed Python CLI result can recover its final nine-stage checkpoint through the POST-only recovery action.
6. Confirm no selected project is changed and retain/revise/reject preserve the external workspace while discard removes only that workspace.
7. Do not install, promote, certify, or declare the candidate final from this handoff alone.
