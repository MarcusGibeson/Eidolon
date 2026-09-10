# Eidolon v1195.2 Final Validation

## Baseline

- Input: `Eidolon_v1194_9_unified_cognitive_developer_experience_checkpoint_source_candidate.zip`
- Verified input SHA-256: `FD8EAD2A9D0123EA43ABAD6118A20492B4D589FD2506DF69F7072F31387D7D4C`
- Input treated as immutable.
- Extraction root: exactly one `Eidolon/` directory.
- Neutral worktree: `<neutral-worktree>/Eidolon`.

## Implemented behavior

- Deterministic long-session and multi-day soak plans.
- Nine exact soak domains: conversation, cognition, action, campaign, queue, cancellation, interruption, restart, and recovery.
- Exact unified snapshot, context, artifact, receipt, sequence, and prior-interval lineage.
- Bounded day, session, interval, elapsed-time, cycle, foreground-latency, token, disk, and memory observations.
- Deadline or no-deadline truth.
- Progress, interruption, restart, provider-outage, and recovery-review evidence.
- Content-free public summaries only.
- No real waiting, scheduling, automatic continuation, execution, cancellation, retry, restart, recovery, provider/model contact, process/thread start, source/runtime mutation, approval creation or consumption, global-profile pass claim, or authority expansion.

## Deterministic verification

- v1195.2 internal checkpoint: 212/212 PASS.
- v1195.0-v1195.2 external focused suite: 170/170 PASS.
- v1194.0-v1194.2: 74/74 PASS.
- v1194.3-v1194.5: 78/78 PASS.
- v1194.6-v1194.8: 83/83 PASS.
- v1194.9 checkpoint: 190/190 PASS.
- v1193.9 checkpoint: 223/223 PASS.
- v1192.9 checkpoint: 383/383 PASS.
- v1191.9 checkpoint: 176/176 PASS.
- v1190.9 checkpoint: 82/82 PASS.
- v1189.9 checkpoint: 72/72 PASS.
- Source-only runtime boundary: 9/9 PASS.
- External Python compilation: 2,131/2,131 PASS.
- Release-verification registration for v1195.2: exactly once.

## Safety and privacy

- Source unchanged during checkpoint execution: PASS.
- Runtime mutation: none.
- Production-source mutation by checkpoint: none.
- Approval creation or consumption: none.
- Actual waiting or automatic continuation: none.
- Work execution, cancellation, restart, or recovery: none.
- Provider/model contact: none.
- Process/thread start: none.
- Authority granted: no.
- Source-root privacy preflight: zero forbidden entries.

## Remaining limitations

- Operator-reviewed soak progression is deferred to v1195.3-v1195.5.
- Reliability and adversarial long-duration hardening is deferred to v1195.6-v1195.8.
- The inherited global quick/full profile was not rerun and no global-profile pass is claimed.
- Historical performance-budget and partial-fixture-overlap debt remains unresolved.
- Desktop Codex and native-provider review remain scheduled for v1200.

## Packaging

The final source-only archive must contain exactly one `Eidolon/` root and exclude runtime, private, cache, settings, compiled, and generated state. Final archive privacy and fresh-extract byte comparison are recorded in the delivery summary after packaging.
