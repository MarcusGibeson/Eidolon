# Eidolon v1378.9 Campaign Rollback Final Validation

This checkpoint extends **Phase 8: Durable Multi-Step Campaigns** with exact-authorized rollback of campaign-owned workspace mutations.

- Private transaction records bind each owned relative path to its exact before/after state while public projections expose only path/content digests.
- Rollback preparation verifies every owned path still matches the campaign-produced after-state; operator or competing-session edits block rollback instead of being overwritten.
- Exact authorization is bound to the prepared rollback-plan digest and transaction digest.
- Created files are removed; modified/deleted files are restored from digest-verified private before images.
- Safe-path containment and symlink rejection prevent rollback escape from the selected external workspace.
- Unrelated files are never enumerated for mutation and remain untouched.
- Tampered/stale transactions, before images, plans, paths, and authorization fail closed.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5. Retained release metadata and checkpoint registry verification are required before packaging. Rollback grants no Eidolon-source mutation, release, or independent authority.
