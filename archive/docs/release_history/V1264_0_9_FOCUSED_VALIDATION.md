# v1264.0-v1264.9 Focused Validation

## Focused suites

- `tools/v1264_0_2_alternative_planning_foundations_tests.py`
- `tools/v1264_3_5_alternative_planning_integration_tests.py`
- `tools/v1264_6_8_alternative_planning_reliability_tests.py`
- `tools/v1264_9_alternative_planning_checkpoint_tests.py`

## Retained direct dependencies

- v1263 priority selection checkpoint and behavioral suites;
- v1262 backlog checkpoint;
- v1261 evidence-inspection checkpoint;
- v1250.3 release-metadata consolidation;
- v1250.4 checkpoint-registry consolidation;
- v1247.9 privacy/security checkpoint.

## Required evidence

1. All v1264 suites run provider-free and with bytecode disabled.
2. Multiple approaches are generated for one exact selected work item.
3. Failure modes remain `predicted` and carry falsification conditions.
4. Exact approach ties yield no defensible plan.
5. Missing/ambiguous priority selection yields no plan.
6. Plan scoring is semantically recomputed during validation.
7. Resealed score or failure-mode epistemic tampering is rejected.
8. Changed source/backlog/priority lineage invalidates old plans.
9. Duplicate concurrent planning converges deterministically.
10. Planning creates no proposal, command/test execution, provider contact, application, release, or self-update authority.
11. Whole-tree Python parsing/compilation remains clean.
12. Source-only and ZIP privacy scans contain no forbidden runtime/private data.
13. Fresh extraction has exact file-by-file parity.
14. Rerun the four v1264 suites, metadata/registry, privacy/security, and Python validation from the fresh extraction.

## Native Windows Desktop review

Exercise real NTFS case-insensitive paths and junction/reparse containment across the v1261→v1264 chain, restart/concurrent duplicate planning from separate processes, long paths, source changes during planning, tampered/resealed plan records, and preservation of zero execution/application authority.
