# Eidolon v1377.9 Conflict Reconciliation Final Validation

This checkpoint extends **Phase 8: Durable Multi-Step Campaigns** with deterministic, content-free pre-apply conflict detection.

- Exact campaign/candidate/source/workspace/upstream/session digests bind every assessment to reviewed evidence.
- Operator edits, upstream drift, unexplained stale worktrees, unknown changes, and competing sessions block the original candidate from silent application.
- Campaign-owned changes are distinguished from external changes so ordinary progress does not create false conflicts.
- Reconciliation dispositions are exact-assessment-bound and operator-reviewed, but remain non-executing plans only.
- Raw paths and file content are never persisted by the public conflict record.
- Tampered/stale assessments and malformed change/session evidence fail closed.
- Ordinary-chat inspection exposes only content-free reconciliation evidence.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5. Retained release metadata and checkpoint registry verification are required before packaging. No conflict record grants application, rebase/worktree mutation, project/source mutation, release, or independent authority.
