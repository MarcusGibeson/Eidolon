# Windows/Desktop Codex Handoff: v1198.9

## Candidate purpose

Review the source-only v1198.9 Feature Freeze and Architecture Consolidation checkpoint before beginning v1199 final-candidate preparation.

## Desktop review focus

1. Extract beneath exactly one clean `Eidolon/` root and confirm the supplied candidate SHA-256.
2. Run `python tools/v1198_9_feature_freeze_architecture_consolidation_checkpoint_tests.py` with UTF-8 text handling and an external `EIDOLON_DATA_DIR`.
3. Run the three retained v1198 suites and the v1197.9 through v1189.9 checkpoint stack.
4. Run `python tools/v1150_1_source_only_runtime_boundary_tests.py` with `PYTHONPATH=.`.
5. Compile all source Python files into a neutral external bytecode directory.
6. Confirm the dashboard JavaScript parses on Windows and the new API remains GET-only.
7. Confirm no CRLF conversion changes source digests or retained UTF-8 roadmap text.
8. Confirm archive privacy and exactly one top-level `Eidolon/` root.

## Expected checkpoint facts

- Contract version: v1198.9.
- Architecture areas: 12.
- Consolidation kinds: 4.
- Review actions: 5.
- Decisions: 3.
- Review outcomes: 15.
- Hardening evidence classes: 8.
- Inherited debt count: 1.
- Global quick/full-profile pass: not claimed.
- Source/runtime mutation: none.
- Authority state: separate and not granted.

## Remaining risk ledger

- Inherited quick/full performance-budget debt.
- Partial fixture overlap still deferred.
- Consolidation and profiling remain evidence-only rather than applied.
- Desktop Codex and native-provider decision review remains scheduled for v1200.
