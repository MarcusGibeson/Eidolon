# Desktop Codex Handoff: v1204.9

1. Verify the candidate ZIP SHA-256 supplied with the handoff.
2. Extract beneath exactly one `Eidolon\` root in a clean Windows directory.
3. Run:

```powershell
python tools\v1204_9_selected_project_apply_rollback_checkpoint_tests.py
python tools\v1204_6_8_selected_project_apply_rollback_reliability_tests.py
python tools\v1204_3_5_selected_project_rollback_recovery_tests.py
python tools\v1204_0_2_selected_project_apply_foundations_tests.py
python tools\release_verify.py --profile quick --json
```

4. Open the dashboard development-campaign page and verify that a completed selected-project apply shows an eight-stage checkpoint. After an explicitly authorized rollback, verify that the same proposal shows a thirteen-stage `rolled_back` checkpoint.
5. Confirm the checkpoint API is POST-only:

```text
/api/development-campaign/finalize-selected-project-apply-rollback-checkpoint
```

6. Confirm no selected-project path, filename, source content, rollback bytes, authorization phrase, runtime receipt, conversation, memory, provider payload, credential, or `projects.json` appears in the source-only archive.
7. Do not install, promote, certify, or declare the candidate final.
