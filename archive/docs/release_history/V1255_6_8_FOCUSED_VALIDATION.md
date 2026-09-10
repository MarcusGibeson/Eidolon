# v1255.6-v1255.8 Focused Validation

Bundle C hardens controlled application and rollback for Windows-style path semantics, interruption, partial transactions, and operator review.

## Implemented

- Windows casefold collision rejection and link/reparse containment checks for affected paths.
- Candidate workspace tamper detection before authority consumption or backup capture.
- Expired application-lease recovery from known baseline/candidate partial states under the same consumed authority, with no provider recontact.
- Concurrent duplicate application calls fail closed while one owner is active; late replay restores the one sealed result.
- Verification-failure automatic rollback preserves unrelated operator edits.
- Backup-tamper detection and rollback blocking.
- Interrupted rollback recovery from known candidate/baseline mixtures without overwriting unknown third states.
- Read-only application health inspection and content-minimized operator handoff.

## Deterministic focused evidence

`tools/v1255_6_8_controlled_application_reliability_tests.py`: **50/50 passed**.

Reliability fixtures use sealed deterministic v1254 lineage so the suite isolates v1255 transaction/recovery behavior. The real provider-backed lineage remains covered by the v1255.3-v1255.5 integration suite.

Native NTFS junction/reparse behavior, case-insensitive filesystem behavior, and atomic replacement semantics still require the Desktop Codex Windows review rather than being inferred from a non-Windows host.
