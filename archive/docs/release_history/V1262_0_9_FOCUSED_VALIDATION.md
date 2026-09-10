# v1262.0-v1262.9 Focused Validation

Development Backlog Generation must prove that candidate work is evidence-bound and bounded while remaining separate from prioritization and execution.

## Required checks

- v1261 assessment digest and source-manifest lineage are retained.
- Work items have stable IDs/digests and bounded categories.
- Every work item carries acceptance criteria, dependency fields, risk, uncertainty, and effort evidence.
- Duplicate generation is deterministic and idempotent.
- Explicit contradictory evidence produces an evidence-resolution dependency rather than silent reconciliation.
- Missing tests/docs/configuration are uncertain review candidates, not automatically verified defects.
- Stale source invalidates the backlog for later action.
- Dependency cycles are rejected.
- Tampered item contracts/digests are rejected.
- Deep/Windows-shaped paths remain contained.
- Public output exposes no raw source/evidence/private paths.
- Priority/rank remain unset.
- No proposal, provider, command, test, mutation, application, release, or self-update authority is created.

## Narrow inherited repair

v1261 previously parsed a 64 KiB prefix for Python syntax, allowing a valid large module to appear syntactically broken if the prefix ended mid-expression. The scanner now parses the complete source file within an 8 MiB per-file bound, otherwise recording a parse skip instead of a false failure. The retained v1261 foundation fixture now includes a valid >64 KiB Python module.

## Focused suites

- `tools/v1262_0_2_development_backlog_generation_foundations_tests.py`
- `tools/v1262_3_5_development_backlog_generation_integration_tests.py`
- `tools/v1262_6_8_development_backlog_generation_reliability_tests.py`
- `tools/v1262_9_development_backlog_generation_checkpoint_tests.py`
- retained v1261.0-v1261.9 suites
- retained release metadata/checkpoint registry checks
- v1247.9 privacy/security audit
- whole-source Python compilation
- source-only archive privacy, fresh-extraction parity, and fresh-extraction v1262 reruns
