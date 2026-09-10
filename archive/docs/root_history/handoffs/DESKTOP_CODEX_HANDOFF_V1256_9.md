# Desktop Codex Handoff: Eidolon v1256.9

## Candidate purpose

Review the v1256 Persistent Development Sessions checkpoint on native Windows. The source candidate should remain uninstalled and must not replace the active Eidolon installation during review.

## Highest-value native checks

1. Start a real bounded development session, close/restart the Eidolon process, and confirm the same deterministic session reconstructs requirements, plan, attempts, test evidence, blocker/completion state, and the correct next control.
2. Confirm a restart/resume never calls the provider or runs commands/tests until the already-existing exact v1254/v1255 authorization is explicitly supplied.
3. Exercise concurrent resumes from separate processes/tabs and confirm exactly one content-minimized progress event is committed for one observed generation/state.
4. Exercise actual NTFS long paths and junction/reparse boundaries beneath the runtime/session storage roots.
5. Change the selected project after restart and before execution authorization; stale source must block resurfacing unsafe execution authority.
6. Interrupt during an isolated-execution or controlled-application lease, expire the lease, restart, and confirm recovery projects the original exact authorization rather than minting a new one or duplicating provider work.
7. Corrupt session index, session record, and progress-event metadata independently. Verify quarantine/reconstruction from sealed v1254/v1255 lineage and verify private/raw provider/test content is not synthesized into recovery metadata.
8. Carry a session through successful controlled application, duplicate replay, rollback preparation, process restart, and separately authorized rollback. Confirm provider-call count and authority-consumption counts do not increase during observational resume.

## Expected retained evidence

- v1256.0-.2: 49/49.
- v1256.3-.5: 42/42, provider calls exactly 2 in the end-to-end fixture.
- v1256.6-.8: 36/36.
- v1256.9: 40/40.
- v1255.0-.2: 44/44; v1255.3-.5: 43/43; v1255.6-.8: 50/50.
- v1250.3 metadata: 94/94; v1250.4 registry: 118/118.

## Authority boundary

The review must not infer authority from continuity. Automatic resume, duplicate execution, provider contact, project mutation, application, rollback, installation, promotion, certification, release, permanent approval, and independent authority remain denied unless the pre-existing exact governed action separately authorizes them.

## Next arc

v1257 Diagnostic and Repair Reasoning is not part of this candidate and must not be started or inferred during the review.
