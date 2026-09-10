# Windows / Desktop Codex Handoff: v1189.9

## Candidate identity

- Candidate: `Eidolon_v1189_9_persistent_supervised_developer_alpha_hardening_checkpoint_source_candidate.zip`
- Source milestone: v1189.9 Persistent Supervised Developer Alpha Hardening Checkpoint
- Authoritative input: v1189.8 source-only candidate
- Input SHA-256: `9DA7DEB0D8126D84A9EDBE5850A0488DD4E63A84E215BA1F9D6C969F02403861`
- The final candidate SHA-256 is supplied beside the archive.

## What to verify on Windows

1. Verify the candidate SHA-256 before extraction.
2. Extract beneath exactly one `Eidolon/` root.
3. Keep runtime data, bytecode, caches, reports, and private state outside the source tree.
4. Run `tools/v1189_9_persistent_supervised_developer_alpha_hardening_checkpoint_tests.py` with `PYTHONPATH` set to the extracted root.
5. Confirm registry discovery for `persistent-supervised-developer-alpha-hardening-checkpoint`.
6. Run the explicit CLI command with the same checkpoint identifier.
7. Verify GET-only API access at `/api/cognition/persistent-supervised-developer-alpha-hardening-checkpoint`.
8. Confirm the dashboard panel loads without JavaScript syntax errors.
9. Run the retained v1189.2, v1189.5, and v1189.8 suites.
10. Run source-only privacy and source-tree immutability checks.

## Expected current results

- Internal checkpoint: 344/344 PASS.
- External checkpoint suite: 72/72 PASS.
- Retained v1189 suites: 30/30, 27/27, and 28/28 PASS.
- No source writes, sandbox writes, provider/model contact, automatic retry/resume/recovery, or authority expansion.

## Known blocked profile debt

The quick release profile is not a global pass. It retains 24 inherited historical blocked groups and exceeds the 420-second quick-performance budget. Current v1189 steps pass and must remain distinguished from inherited debt.

## Next bounded work

Begin only v1190.0-v1190.2 Unified Experience Foundations:

- Unify chat, reasoning, planning, action, campaign approval, evidence, and results into one coherent operator-facing state model.
- Preserve explicit authority boundaries and existing source-discovered checkpoint ownership.
- Do not collapse review, execution, learning, promotion, certification, or release into one implicit state.
- Do not continue into v1190 Bundle B without a separate operator request.

The next Desktop Codex and native-provider decision gate remains scheduled for v1200. Reaching v1190 or v1200 source does not install, promote, certify, publish, or grant independent authority.
