# v1195.9 Long-Session and Multi-Day Soak Checkpoint Review

## Scope

This read-only checkpoint consolidates:

- v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations.
- v1195.3-v1195.5 Operator-Reviewed Soak Progression.
- v1195.6-v1195.8 Soak Reliability and Adversarial Hardening.

It remains content-free, evidence-only, and non-mutating.

## Consolidated behavior

- Two explicit soak modes: `long_session` and `multi_day`.
- Nine governed evidence domains.
- Approve, reject, and defer operator decisions.
- Nine progression actions with exact multi-session transition lineage.
- Four terminal interval dispositions.
- Eight reliability and adversarial event classes.
- Foreground responsiveness, latency budgets, resource budgets, progress truth, original-evidence preservation, and inherited-debt visibility.
- Source-discovered registry, CLI, GET-only API, dashboard, release metadata, documentation, and release-verification integration.

## Preserved boundaries

The checkpoint does not wait, continue, pause, resume, cancel, retry, recover, execute, contact a provider or model, start a process or thread, mutate source or runtime state, create or consume approval, claim a global quick/full-profile pass, or grant authority.

## Severity review

- Critical: none found.
- High: none found.
- Medium: inherited quick/full performance-budget debt and partial fixture overlap remain unresolved.
- Low: soak continuation, pause/resume, cancellation, retry, restart, and recovery remain deliberately evidence-only and non-mutating.

## Verification summary

- Internal v1195.9 checkpoint: 204/204 PASS.
- External v1195.9 suite: 236/236 PASS.
- v1195.6-v1195.8: 133/133 PASS.
- v1195.3-v1195.5: 232/232 PASS.
- v1195.0-v1195.2: 170/170 PASS.
- v1194.9: 190/190 PASS.
- v1193.9: 223/223 PASS.
- v1192.9: 383/383 PASS.
- v1191.9: 176/176 PASS.
- v1190.9: 82/82 PASS.
- v1189.9: 72/72 PASS.
- Source-only runtime boundary: 9/9 PASS.
- Python compilation: 2,139/2,139 PASS.

The inherited global quick/full profile was not rerun. No global-profile pass is claimed.
