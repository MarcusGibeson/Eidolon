# Windows/Desktop Codex Handoff v1195.2

## Candidate role

Bounded source-only candidate for v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations. This is not an installation, promotion, certification, publication, release, or authority decision.

## Review focus

1. Verify the candidate archive SHA-256 before extraction.
2. Extract beneath exactly one clean `Eidolon/` root.
3. Use neutral external runtime and bytecode paths that do not share the candidate-version cleanup prefix.
4. Confirm both `long_session` and `multi_day` evidence paths remain synthetic and do not wait, sleep, schedule, or continue automatically.
5. Confirm exact interval ID, sequence, snapshot, context, artifact, receipt, and prior-interval lineage.
6. Confirm day, session, cycle, elapsed-time, foreground-latency, token, disk, and memory budgets reject malformed or excessive evidence.
7. Confirm interruption, restart, outage, cancellation, and recovery remain content-free evidence states only.
8. Confirm duplicate IDs/sequences, overlapping cycles, stale snapshot/context, malformed digests, stalled progress, private fields, hidden execution, automatic continuation, runtime mutation, provider contact, process/thread start, global-pass claims, and authority expansion are blocked.
9. Confirm CLI and GET-only API are read-only and POST is unavailable.
10. Confirm the dashboard exposes bounded summaries only.

## Suggested Windows commands

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:EIDOLON_DATA_DIR = Join-Path $env:TEMP "eidolon-v1195-2-runtime"
python tools/v1195_0_2_long_session_multi_day_soak_tests.py
python tools/v1194_9_unified_cognitive_developer_checkpoint_tests.py
python tools/v1193_9_verifier_historical_debt_checkpoint_tests.py
python tools/v1192_9_evidence_compaction_checkpoint_tests.py
python tools/v1191_9_responsiveness_background_work_checkpoint_tests.py
python tools/v1190_9_unified_experience_checkpoint_tests.py
python tools/v1189_9_persistent_supervised_developer_alpha_hardening_checkpoint_tests.py
$env:PYTHONPATH = "."
python tools/v1150_1_source_only_runtime_boundary_tests.py
```

Compile all Python files using an external bytecode root. Do not permit `__pycache__`, `.pyc`, runtime data, private records, settings, or generated reports inside the source-only candidate.

## Expected retained results

- v1195.0-v1195.2: 170/170 PASS.
- v1194.9: 190/190 PASS.
- v1193.9: 223/223 PASS.
- v1192.9: 383/383 PASS.
- v1191.9: 176/176 PASS.
- v1190.9: 82/82 PASS.
- v1189.9: 72/72 PASS.
- Source-only runtime boundary: 9/9 PASS.

## Boundaries

Do not execute real multi-day work, start a background process, contact a provider or model, consume approval, cancel or recover live work, mutate production/runtime state, install, promote, certify, publish, release, or grant authority. The next Desktop Codex and native-provider milestone review remains v1200.
