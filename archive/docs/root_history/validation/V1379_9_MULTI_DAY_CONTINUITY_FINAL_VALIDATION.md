# Eidolon v1379.9 Multi-Day Continuity Final Validation

This checkpoint extends **Phase 8: Durable Multi-Step Campaigns** with compact project-state continuity across restarts and calendar gaps.

- Capsules retain only exact digests for campaign goal, plan, budget, current step, source/workspace/upstream state, checkpoints, partial results, conflict evidence, and rollback lineage.
- Raw chat, goals, plans, and evidence are not copied into continuity state; chat replay is explicitly unnecessary.
- Atomic generation-linked persistence prevents stale capsule replacement.
- Resume assessment reports calendar gap and blocks silent continuation when source, workspace, or upstream state drifted.
- Long gaps require renewed operator review while ordinary short-gap resumes remain advisory only.
- Tampered/stale capsules and malformed generations fail closed.
- Capsule serialization is bounded to a compact size.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5. Retained release metadata and checkpoint registry verification are required before packaging. No capsule automatically resumes work, mutates project/source state, contacts providers, releases software, or grants independent authority.
