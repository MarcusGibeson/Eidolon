# Eidolon v1371.9 Campaign Records Final Validation

This checkpoint begins **Phase 8: Durable Multi-Step Campaigns** with chat-independent, content-minimized campaign records.

- Campaign records bind source, workspace, standing-session grant, goal, plan, budget, current step, progress, evidence-set, state, recovery state, and generation lineage by digest.
- Records persist atomically only beneath an explicitly supplied external runtime root; no selected source or project mutation occurs.
- Loading a campaign requires the exact expected record digest and never reads chat history.
- Duplicate persistence converges idempotently; later generations require exact prior-record lineage; stale or tampered records fail closed.
- Inactive standing-session context, invalid source/workspace/goal/plan/budget lineage, impossible progress, and malformed evidence are rejected.
- Ordinary-chat inspection is read-only and import-lazy.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 8/8; checkpoint 5/5. Release authority and checkpoint registry remain coherent. No campaign record grants work execution, source/project mutation, provider/network, installation, promotion, release, or independent authority.
