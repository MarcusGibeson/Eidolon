# Windows / Desktop Codex Handoff: v1191.9

## Candidate purpose

Review the v1191 Responsiveness and Background Work checkpoint and the bounded repairs to four v1190.9 findings.

## Windows checks requested

1. Run `python tools/v1191_9_responsiveness_background_work_checkpoint_tests.py`.
2. Run both current v1190 suites on Windows without forcing a UTF-8 process locale:
   - `python tools/v1190_3_5_unified_experience_navigation_tests.py`
   - `python tools/v1190_6_8_unified_experience_reliability_tests.py`
3. Confirm a CRLF sandbox target materializes successfully and its rollback artifact preserves CRLF bytes.
4. Confirm a genuinely changed CRLF target is still rejected as `stale_sandbox_target_or_drift`.
5. Inspect ordinary chat projections for:
   - `Make me a web page for my dog.`
   - `Build me a web page for my dog.`
   - `Can you make me a web page for my dog?`
6. Confirm each request reaches the proposal-only `software_development` campaign surface and does not execute or create approval.
7. Confirm streaming and non-streaming conversation paths expose equivalent content-free campaign projections.

## Authority boundary

Do not interpret routing or proposal visibility as permission to inspect private source, create an approval, begin a campaign, implement code, run tests, contact a provider/model, or modify runtime state.

## Known inherited debt

The global quick/full profile is still BLOCKED by inherited historical fixture/checkpoint debt and prior performance-budget behavior. No global pass is claimed here.

## Next roadmap unit

v1192.0-v1192.2 Bounded Evidence Compaction Foundations. The next full Desktop Codex and native-provider decision gate remains v1200.
