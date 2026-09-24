# G-ROUTE1 Activity and Checkpoint Contract

One shared Activity represents one benchmark run. Allowed live data is limited to state, stage, completed calls, total calls, provider-contact count, structural-failure count, checkpoint position, active elapsed time, and the current fixture/task/tier identity. Prompts, fixture contents, model outputs, expected values, semantic judgments, qualification results, and routing outcomes are prohibited during collection.

States are `preparing`, `running`, `paused`, and terminal `complete`, `incomplete`, `failed`, or `cancelled`. Checkpoints bind the run identity, next schedule position, persisted-call count, dependency digest, state, and checkpoint digest. Resume fails closed on any disagreement. Activity observation grants no authority and cannot change prompts, order, persisted outputs, validation, scoring, or the terminal verdict.
