# Eidolon v1372.9 Crash-Safe Checkpoints Final Validation

This checkpoint extends **Phase 8: Durable Multi-Step Campaigns** with exact, idempotent recovery checkpoints that prevent duplicate side effects after interruption.

- Per-step campaign checkpoints bind campaign-record digest, step digest, attempt identity, operation/result evidence where applicable, checkpoint state, mutating-side-effect classification, and confirmation state.
- Checkpoint state progression is monotonic across `prepared`, `side_effect_recorded`, and `completed`; identical duplicate writes converge idempotently and stale/regressive writes fail closed.
- A confirmed completed step is skipped during recovery rather than replayed.
- A missing or clean prepared step may resume from that step without implying execution authority.
- An interrupted mutating step with recorded but unconfirmed side effects yields `stop_no_replay` / `recovery_blocked_uncertain_side_effect`; uncertainty is surfaced instead of converting a crash into an assumption that nothing happened.
- Atomic persistence occurs only beneath an explicitly supplied external runtime root; selected source/project state is not mutated by checkpoint persistence.
- Ordinary-chat inspection is read-only and import-lazy.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5. Retained release metadata passes 94/94 and checkpoint registry passes 118/118; v1372.9 is classified as `durable_campaign_arc`. No checkpoint or recovery recommendation grants replay, execution, source/project mutation, provider/network, installation, promotion, release, or independent authority.
