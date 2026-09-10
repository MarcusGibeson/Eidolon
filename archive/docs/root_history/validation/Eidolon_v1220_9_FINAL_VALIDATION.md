# Eidolon v1220.9 Final Validation

## Candidate identity

- Baseline: v1219.9 Conversational Supervised Repaired-Candidate Rollback Checkpoint
- Baseline archive SHA-256: `181250C66215954DA4B38EF22B076FE7AFD2BA4EFEE24DB5BC0B54C4AB529E85`
- Working source version: `1220.9`
- Milestone: Operator Repaired-Candidate Rollback Result Review Checkpoint
- State: source-only, uninstalled, unpromoted, uncertified, and release-unauthorized

## Implemented section

v1220 adds one exact, content-free operator review packet for every terminal v1219 rollback result. It preserves rollback, apply, manifest, authorization, workspace, review, and decision digests; distinguishes verified pre-apply restoration from safely restored applied state; and offers only `accept-rollback-result`, `defer`, or `reject-rollback-result`.

The ordinary-chat route accepts only exact digest-bound phrases. Same-decision replay is idempotent, conflicting decisions fail closed, stale or tampered bindings are rejected, and no review action retries rollback or grants provider, test, repair, apply, rollback, installation, promotion, release, model-management, or independent authority.

## Focused verification

- v1220.0-v1220.2 foundations: 16/16 passed
- v1220.3-v1220.5 conversational decisions: 27/27 passed
- v1220.6-v1220.8 reliability and privacy: 7/7 passed
- v1220.9 external checkpoint surface: 13/13 passed
- v1220.9 internal read-only checkpoint audit: 127/127 passed

## Retained adjacent verification

- v1219.0-v1219.2 foundations: 19/19 passed
- v1219.3-v1219.5 execution: 24/24 passed
- v1219.9 checkpoint: 30/30 passed; internal audit 88/88
- v1219.6-v1219.8 reliability: did not complete within the isolated command window; no pass is claimed

## Source integrity and limitations

The source-only tree is cleaned of bytecode and cache directories before packaging. The v1220 checkpoint reads no runtime data and preserves an identical source signature before and after inspection. Browser-dependent historical gates and the full inherited release graph were not rerun during this reconstruction.

## Next bounded unit

`v1221.0-v1221.2 Unified Supervised Development Transaction History Foundations`
