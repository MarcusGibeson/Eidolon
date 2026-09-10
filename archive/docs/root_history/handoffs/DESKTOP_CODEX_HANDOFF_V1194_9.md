# Windows / Desktop Codex Handoff: v1194.9

## Candidate purpose

Review the v1194.9 Unified Cognitive and Developer Experience read-only checkpoint as the final consolidated v1194 source state before v1195 long-session and multi-day soak hardening.

## Review priorities

1. Confirm all nine governed domains remain separate and content-free.
2. Confirm approve/reject/defer navigation changes presentation focus only.
3. Confirm foreground responsiveness cannot be blocked or replaced by background work.
4. Confirm compacted evidence remains exactly expandable and original evidence remains preserved.
5. Confirm interruption, restart, stale focus/context/snapshot, provider outage, latency, privacy, and tamper cases remain evidence-only.
6. Confirm current regressions remain separate from inherited verifier debt and no global profile pass is claimed.
7. Confirm no approval creation/consumption, execution, recovery, provider/model contact, process/thread start, runtime mutation, installation, promotion, certification, publication, release, or authority grant occurs.
8. Recheck Windows UTF-8 and CRLF repairs retained from v1191.9.
9. Review inherited performance-budget and partial-fixture-overlap debt separately from current v1194.9 behavior.

## Suggested Windows commands

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = "."
python tools/v1194_9_unified_cognitive_developer_checkpoint_tests.py
python tools/v1194_6_8_unified_experience_reliability_integration_tests.py
python tools/v1194_3_5_operator_coordination_navigation_tests.py
python tools/v1194_0_2_unified_cognitive_developer_experience_tests.py
python tools/v1193_9_verifier_historical_debt_checkpoint_tests.py
python tools/v1192_9_evidence_compaction_checkpoint_tests.py
python tools/v1191_9_responsiveness_background_work_checkpoint_tests.py
python tools/v1190_9_unified_experience_checkpoint_tests.py
python tools/v1150_1_source_only_runtime_boundary_tests.py
```

Use neutral runtime, bytecode, profile-output, and extraction paths that do not share the candidate-version cleanup prefix.

## Expected bounded results

- v1194.9 external: 190/190 PASS.
- v1194.9 internal: 181/181 PASS.
- v1194.8: 83/83 PASS.
- v1194.5: 78/78 PASS.
- v1194.2: 74/74 PASS.
- v1193.9: 223/223 PASS.
- v1192.9: 383/383 PASS.
- v1191.9: 176/176 PASS.
- v1190.9: 82/82 PASS.
- Source-only boundary: 9/9 PASS.

## Bounded next step

Proceed only to v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations after accepting this checkpoint. The next Desktop Codex and native-provider decision review remains scheduled for v1200.
