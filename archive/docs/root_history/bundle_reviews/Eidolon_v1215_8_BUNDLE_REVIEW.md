# v1215.6-v1215.8 Bundle Review

## Scope

Supervised Repair Execution Reliability and Privacy.

## Result

- Added prepared/running/sealed journals, bounded leases, live duplicate blocking, expired-lease recovery, and deterministic sealed replay.
- Enforced one repair attempt and rejected stale proposal digests, changed lineage, tampered proposals, forged authority, and modified execution records.
- Reduced private provider failures to content-free evidence and kept requests, paths, prompts, code, provider output, test output, and runtime records out of public projections.
- Verified that v1215 delegates through the retained v1210 executor instead of duplicating build-coordinator or test-adapter logic.

## Authority boundary

Repair results require operator review. Apply, rollback, installation, promotion, release, model management, and independent action remain unavailable.

## Focused evidence

`tools/v1215_6_8_supervised_repair_execution_reliability_tests.py`: **31/31 passed**.
