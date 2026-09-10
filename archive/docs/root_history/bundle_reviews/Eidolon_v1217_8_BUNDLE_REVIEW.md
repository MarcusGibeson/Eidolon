# v1217.8 Bundle Review

## Scope

Repaired-Candidate Apply Reliability and Recovery.

## Result

- Added prepared/running/sealed journals, live duplicate blocking, bounded leases, expired recovery, and deterministic replay.
- Preserved third-state operator edits and rejected stale or tampered proposals, candidates, execution records, manifests, receipts, and journals.
- Enforced one attempt and reduced private exceptions and Windows-style paths to type-only digests.

## Authority boundary

Recovery may only seal the already-authorized apply or restore its sealed pre-apply state. Rollback remains separately authorized; installation, promotion, release, model management, and independent authority remain unavailable.

## Focused evidence

`tools/v1217_6_8_supervised_repaired_candidate_apply_reliability_tests.py`: **48/48 passed**.
