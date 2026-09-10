# Desktop Codex Handoff — v1277.9 Development Observability

## Candidate focus

Validate v1277 observability on native Windows against the real v1270-v1274 development lineage. The Python fixture suite is evidence, not a substitute for native process/filesystem behavior.

## Native checks

1. Run a multi-hour development campaign and verify bounded event growth while aggregate counts continue increasing.
2. Close and reopen the dashboard/API process and confirm current phase, next authorization, timing, failure/retry/recovery counts, and durable lineage are reconstructed without provider/test replay.
3. Force-kill a worker before and after v1272 recovery-journal writes and verify observability follows the durable outcome rather than inventing success.
4. Exercise provider outage/return and confirm only content-free status/reason codes are retained.
5. Exercise v1273 ownership contention/lease transfer and confirm ownership signals remain diagnostic only.
6. Verify NTFS sharing violations and filesystem-lock waits are diagnosable without raw path leakage.
7. Test drive-letter, UNC, `\\?\` extended-length, and >260-character source/runtime paths.
8. Split a verification harness that exceeds its phase budget and confirm v1277 records `budget_split_required` without raising a global timeout.
9. Interrupt shutdown during observability-record replacement and verify atomic recovery/quarantine behavior.
10. Verify no prompt, response, provider payload, command output, raw test output, secret value, or private runtime content appears in observability records or source-only packaging.

## Known limitations

- Retained events are bounded and are not a complete forensic event log.
- Timings are wall-clock phase observations, not CPU/process-profiler attribution.
- Provider payloads, prompts, responses, and raw test output are intentionally excluded even when they would make debugging easier.
- v1277 does not grant retry, execution, provider, test, update, application, rollback, installation, promotion, certification, or release authority.
- v1278 Security and Privacy Hardening has not been started.
