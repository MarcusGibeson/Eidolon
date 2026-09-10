# Desktop Codex Handoff — Eidolon v1261.9

## Review target

Review the source-only v1261.9 Evidence-Based Project Inspection candidate on native Windows. The implementation is intentionally read-only and must not be interpreted as backlog, execution, self-modification, installation, or release authority.

## Native Windows checks

1. Inspect a representative project containing real NTFS junctions and reparse points. Confirm linked targets are rejected and not scanned.
2. Exercise case-insensitive aliases/collisions that differ only by filename case.
3. Exercise deep/long paths under the operator's actual Windows configuration.
4. Modify a source file after assessment and confirm the freshness check returns `inspection_source_stale`.
5. Attempt a source change during a long inspection and confirm the resulting assessment is rejected by a later freshness check before downstream use.
6. Supply explicit minimized runtime-health, test-result, operator-feedback, and development-session evidence; confirm raw payloads/private paths do not enter public projections.
7. Supply contradictory evidence for the same claim; confirm it remains unresolved rather than being silently reconciled.
8. Run repeated/concurrent read-only assessments from separate processes/tabs and compare deterministic assessment digests when the source/evidence inputs are unchanged.
9. Confirm no inspection result creates a v1262 backlog item, development proposal, provider call, command, test execution, selected-project mutation, application authorization, or self-update authority.

## Expected source contracts

- `conscious_agent/evidence_based_project_inspection_foundations.py`
- `conscious_agent/evidence_based_project_inspection.py`
- `conscious_agent/evidence_based_project_inspection_reliability.py`
- `conscious_agent/evidence_based_project_inspection_checkpoint.py`
- `tools/v1261_0_2_evidence_based_project_inspection_foundations_tests.py`
- `tools/v1261_3_5_evidence_based_project_inspection_integration_tests.py`
- `tools/v1261_6_8_evidence_based_project_inspection_reliability_tests.py`
- `tools/v1261_9_evidence_based_project_inspection_checkpoint_tests.py`

## Known limitation

The current structural inventory can prove that tests/config/docs and source patterns exist; it does not claim that unexecuted tests pass, that documentation is semantically correct, or that runtime health is healthy unless separately supplied evidence says so. Those states remain explicitly unknown.

## Next arc boundary

v1262 Development Backlog Generation may consume v1261 findings, but v1261 itself must not auto-create work. Do not treat this handoff as authorization to begin v1262, install a candidate, or modify the active Eidolon installation.
