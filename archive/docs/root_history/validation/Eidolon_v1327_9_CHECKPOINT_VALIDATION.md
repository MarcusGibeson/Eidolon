# Eidolon v1327.9 Dynamic Replanning Checkpoint Validation

v1327 revises plans only when evidence materially changes. Completed steps remain preserved as prior evidence, unfinished steps may be rerouted, source-manifest drift and changed evidence are digest-bound, and the resulting record explains why the route changed. No-change evidence retains the prior route instead of creating gratuitous churn.

Focused v1327 suites pass 5 + 4 + 4 + 5 checks after correcting a newly introduced reliability-test fixture that had expected a step to count as completed without supplying it in `completed_step_codes`. The implementation was not weakened. Retained release-metadata consolidation remains 94/94 and checkpoint-registry consolidation remains 118/118.

Replanning rejects authority-bearing plans, cannot repeat completed work in replacement steps, and grants no execution, provider, project-mutation, source-application, installation, release, or unrestricted autonomous authority. Native Windows execution remains external evidence.

Next: v1328 - Stop and Escalation Logic.
