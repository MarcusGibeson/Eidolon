# Eidolon v1380.9 Durable-Campaign Final Validation

This checkpoint completes **Phase 8: Durable Multi-Step Campaigns** by consolidating the v1371-v1379 evidence chain around a staged multi-hour campaign timeline.

- Exact digests bind campaign records, step checkpoints, dependency scheduling, parallel planning, heartbeat evidence, retained partial work, continuity state, conflict assessment, reconciliation disposition, and final result.
- The checkpoint requires an ordered multi-hour timeline containing interruption, restart, external file change, reconciliation, and final completion.
- Operator changes must be explicitly preserved and duplicate mutating side effects are forbidden.
- Compact project-state continuity is required; private chat replay is explicitly rejected.
- Tampered lineage, short/invalid timelines, incomplete scenario evidence, duplicate side effects, and chat replay fail closed.
- The checkpoint remains content-free and read-only.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5. Retained release metadata and checkpoint registry verification are required before packaging. This evidence gate grants no work execution, automatic resume, project/source mutation, provider contact, release, or independent authority.
