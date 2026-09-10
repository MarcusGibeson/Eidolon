# Eidolon v1253.9 Final Validation

Status: Runtime Efficiency Beta checkpoint implementation complete. Final package evidence is external, digest-bound, and must be produced from the exact source-only candidate after this document is frozen.

## Scope completed

- v1253.0 critical-path cognition split
- v1253.1 bounded internal maintenance queue
- v1253.2 turn-local work coalescing
- v1253.3 import-graph and lazy chat-path cleanup
- v1253.4 second self-maintenance decomposition slice
- v1253.5 fast dashboard health and API dependency isolation
- v1253.6 explicit median/p95 performance budgets
- v1253.7 machine-readable performance regression receipts
- v1253.8 integrated real-use runtime benchmark
- v1253.9 read-only Runtime Efficiency Beta checkpoint

## Performance-gate policy

Hardware-independent invariants remain hard release-verification gates: prompt projection size, warm pre-provider critical-path latency, trusted action acknowledgement, indexed persistent-state reads, dashboard fast-status behavior, authority preservation, source immutability, and bounded deferred work.

Cold terminal startup and module-import timings are hardware-sensitive. They retain explicit targets and safety ceilings, but they are not treated as portable universal release gates after unrelated retained suites have already loaded the host. Native measurements remain reportable evidence and may be compared with same-host baselines. A single host-sensitive outlier cannot authorize or revoke release, rollback, installation, promotion, or certification.

## Representative pre-freeze measurements

On the development host during focused validation:

- immediate terminal chat readiness was approximately 1.1-1.9 seconds across isolated runs;
- conversation-runtime subprocess import was approximately 0.8-1.2 seconds;
- ordinary warm fake-provider pre-provider work remained well below the 50 ms median budget;
- deferred ordinary goal/planning completion was approximately 2 ms after generation;
- compact model-facing synthetic projections remained below 1,000 estimated tokens and complete ordinary test prompts remained below 3,000 estimated tokens;
- medium persistent-state indexed reads remained in the low-single-digit millisecond range;
- the retained v1252.9 20,000-memory / 1,000-session / 20,000-action checkpoint remained within its bounded latency budgets.

These measurements are evidence, not authority. Exact final-tree and fresh-extraction verifier receipts, package audit, performance receipt, archive digest, and SHA-256 are external artifacts produced after the candidate is frozen.

## Required final package gates

The exact packaged candidate must demonstrate:

1. all v1253 focused suites pass;
2. retained cleanup, response-time, persistent-state, and hardening checkpoints pass;
3. all Python source parses successfully;
4. the complete ten-stage segmented verifier passes with zero failed stages;
5. source remains unchanged during read-only verification;
6. verifier runtime cleanup succeeds;
7. the archive contains exactly one `Eidolon/` root and excludes runtime/private/cache/VCS material;
8. a fresh extraction reproduces focused checkpoint parity and the complete segmented verifier;
9. no installation, promotion, certification, release, provider-contact, project-mutation, source-mutation, approval, or independent authority is granted.

When those external gates pass, the exact v1253.9 source-only archive is the candidate for the postponed Desktop Codex review. The checkpoint itself does not authorize that review to mutate or install anything.
