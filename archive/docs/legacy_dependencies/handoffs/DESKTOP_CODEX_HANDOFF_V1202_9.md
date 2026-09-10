# Desktop Codex Handoff: v1202.9 JavaScript Tool Implementation Checkpoint Candidate

## Candidate status

Development checkpoint candidate only. Do not treat it as installed, promoted, certified, or final.

## Windows verification

1. Verify the candidate ZIP SHA-256 against the supplied checksum.
2. Extract beneath exactly one `Eidolon\` root into a clean directory.
3. Confirm no `data\`, `__pycache__\`, `.pytest_cache\`, provider payloads, generated project files, credentials, conversations, memories, or private paths are packaged.
4. Run:

```powershell
python -m compileall -q conscious_agent tools
python tools\v1202_9_javascript_tool_implementation_checkpoint_tests.py
python tools\v1202_6_8_javascript_tool_result_disposition_tests.py
python tools\v1202_3_5_project_owned_javascript_tests.py
python tools\release_verify.py --profile quick --json
```

5. In the dashboard, verify a completed JavaScript-tool campaign displays:
   - the seven-stage tested result;
   - the operator review packet;
   - retain, revise, reject, and discard controls;
   - a final nine-stage JavaScript implementation checkpoint after disposition;
   - no apply or repair authority.
6. Simulate interruption recovery by preserving a disposition record while removing only its final checkpoint record, then resubmit the same disposition or use the POST-only checkpoint recovery endpoint. Confirm disposition consumption remains one.
7. Confirm discard removes only the isolated external workspace and retains digest-bound evidence.

## Authority boundary

Do not install, promote, certify, apply generated files, modify Eidolon source through the campaign, manage models, or infer release authority from a passing checkpoint.
