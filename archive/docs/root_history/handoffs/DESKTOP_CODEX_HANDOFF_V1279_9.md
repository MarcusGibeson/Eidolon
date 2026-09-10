# Desktop Codex Handoff — v1279.9 Operator Experience

Validate the v1279 operator experience on native Windows against real v1268-v1278 campaign state.

## Native checks

1. Open the dashboard across multiple tabs and confirm all tabs converge on the same durable session state after pause/resume/cancel.
2. Close/restart dashboard and API processes and confirm operator projections reconstruct from durable lineage without provider/test replay.
3. Force-kill a worker during a recoverable stage and confirm recovery reconciliation is readable and does not create authority.
4. Exercise locked runtime records and NTFS sharing violations; failures must be readable and fail closed.
5. Exercise drive-letter, UNC, `\\?\` and >260-character runtime/source paths.
6. Verify keyboard navigation, focus order, labels, details disclosure, and screen-reader text for plans, tests, changes, uncertainty, review, controls, and authorization guidance.
7. Confirm passive GET views expose no exact authorization phrase, prompt/response, provider payload, raw test output, secret, or private runtime content.
8. Confirm generic “go ahead”, navigation, readiness, and v1268 review approval cannot authorize candidate mutation, repair/testing, update, application, or rollback.
9. Confirm rollback appears only as separately governed after a verified update.
10. Confirm dashboard close/reopen never changes campaign/session/update authority state.

## Known limitations

v1279 improves presentation and runtime controls; it is not a new authorization layer and does not replace native Windows process/filesystem validation. v1280 Reliability Checkpoint has not been started.
