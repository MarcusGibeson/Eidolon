# Windows / Desktop Codex Handoff: v1195.9

## Review target

Review the source-only v1195.9 Long-Session and Multi-Day Soak checkpoint candidate. Do not treat extraction, installation, promotion, certification, publication, or release as implied by reaching this version.

## Priority checks

1. Confirm the archive has exactly one `Eidolon/` root and no runtime, cache, compiled, private, or settings artifacts.
2. Run `tools/v1195_9_long_session_multi_day_soak_checkpoint_tests.py` with Python 3.11+ and `PYTHONPATH=.`.
3. Confirm the source-discovered registry contains `long-session-multi-day-soak-consolidated-checkpoint` once.
4. Run the CLI command `python eidolon.py long-session-multi-day-soak-consolidated-checkpoint`.
5. Verify GET `/api/cognition/long-session-multi-day-soak-consolidated-checkpoint` and rejection of POST.
6. Inspect the dashboard panel for bounded soak, progression, and reliability truth.
7. Confirm no actual waiting, continuation, pause, resume, cancellation, retry, recovery, execution, provider/model contact, process/thread start, source/runtime mutation, approval consumption, global-profile pass claim, or authority expansion occurs.
8. Retain inherited performance-budget and partial-fixture-overlap debt as unresolved rather than silently passing it.

## Expected focused results

- Internal checkpoint: 204/204 PASS.
- External suite: 236/236 PASS.
- v1195 bundles: 170/170, 232/232, and 133/133 PASS.
- Source-only runtime boundary: 9/9 PASS.
- Python compilation: 2,139/2,139 PASS.

## Windows notes

- Use explicit UTF-8 reads for source and roadmap files.
- Keep bytecode and runtime data outside the source tree.
- Use neutral extraction and verification paths that do not share candidate cleanup prefixes.
- No Desktop Codex or native-provider milestone decision is due until v1200.
