# G-ROUTE1 Activity and Checkpoint Contract

One shared Activity represents one benchmark run. Allowed live data is limited to state, stage, completed calls, total calls, provider-contact count, structural-failure count, checkpoint position, active elapsed time, and the current fixture/task/tier identity. Prompts, fixture contents, model outputs, expected values, semantic judgments, qualification results, and routing outcomes are prohibited during collection.

States are `preparing`, `running`, `paused`, and terminal `complete`, `incomplete`, `failed`, or `cancelled`. Checkpoints bind the run identity, next schedule position, completed schedule position, persisted-call count, dependency digest, state, and checkpoint digest. Resume fails closed on any disagreement.

Successful scientific finalization is ordered and fail-closed: seal the score, append the terminal receipt, mark the run manifest complete, mark Activity complete, then seal the checkpoint. A complete checkpoint requires exactly 216 persisted calls, `completed_position = 216`, `next_position = 217`, a valid score record, and agreement among the result receipt, terminal receipt, run manifest, Activity, and checkpoint. Once terminal, the checkpoint is immutable and cannot be resumed. Repeating the same terminal seal is idempotent; conflicting terminal finalization is rejected. Paused checkpoints remain resumable, while failed or incomplete runs cannot be represented as complete.

Activity observation grants no authority and cannot change prompts, order, persisted outputs, validation, scoring, or the terminal verdict.
