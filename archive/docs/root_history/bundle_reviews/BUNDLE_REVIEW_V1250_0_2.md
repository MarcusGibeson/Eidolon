# Eidolon v1250.0-v1250.2 Bundle A Review

## Scope

Bundle A establishes the verification foundation required before architecture cleanup or a postponed Desktop Codex review.

Authoritative input:

- `Eidolon_v1249_9_feature_freeze_final_hardening_checkpoint_final_candidate_source_only(1).zip`
- SHA-256: `84031088BC659F7AC082FF9FECF1AA8132B216BA8FC05DF323EB8707E3E2289C`

The input archive was treated as immutable. Work occurred in a clean extracted tree beneath one `Eidolon/` root.

## v1250.0 Authoritative Cleanup Baseline

Implemented `conscious_agent/release_authority.py` as the structured authority for:

- working source version;
- previous working source version;
- current milestone;
- next bounded unit;
- postponed Codex-review state;
- the v1200-v1250 checkpoint index;
- immutable hashes of the pre-v1250 public documents.

The active public documents now present one current source and one current roadmap. The exact pre-v1250 documents remain byte-for-byte beneath `docs/legacy/`. Historical prose needed by retained substring-based verifiers is isolated in collapsed compatibility appendices instead of being presented as current guidance.

## v1250.1 Segmented Broad Verifier

Implemented `conscious_agent/segmented_release_verifier.py` and `tools/segmented_release_verify.py`.

The verifier defines ten independently runnable stages:

1. source-only packaging and privacy;
2. authority and approval boundaries;
3. conversation and command distinction;
4. build, test, diagnosis, and repair;
5. apply and rollback;
6. queue, execution, intervention, and recovery;
7. cognition and revisable lessons;
8. provider governance and project understanding;
9. dashboard and public-interface stability;
10. representative retained checkpoints.

Each stage has:

- a stable stage identifier;
- explicit suite membership;
- explicit input selectors;
- a stage-manifest digest;
- an input digest;
- a combined stage-state digest;
- a bounded stage budget;
- digest-only subprocess evidence;
- a partial receipt written after every transition;
- exact resume eligibility;
- stale-receipt rejection.

A passing receipt remains verification evidence only. It does not authorize installation, promotion, certification, release, project mutation, provider contact, or independent action.

## v1250.2 Hermetic Verification Runtime

Implemented `conscious_agent/hermetic_verification_runtime.py`.

Verification now has reusable primitives for:

- clean external source snapshots;
- exclusion of runtime data, VCS state, caches, and bytecode;
- `PYTHONDONTWRITEBYTECODE=1` enforcement;
- external `PYTHONPYCACHEPREFIX`, data, home, and temporary paths;
- argument-array subprocess execution with `shell=False`;
- bounded process-group termination on timeout;
- digest-only stdout and stderr evidence;
- external atomic receipt writes;
- forbidden runtime-debris detection;
- authoritative source signatures before and after execution.

The new contract does not use repository file-count or Python-file-count thresholds as evidence of correctness.

## Retained verifier performance correction

Repeated v1249 hardening-report construction reparsed the complete Python tree several times in one process and could degrade into an apparent hang. The report now uses a bounded cache keyed by a source stat signature and returns defensive copies. The retained v1249.3-v1249.5 suite also exits with the already established authoritative result instead of waiting on unrelated process-finalization hooks.

This is a verification correction permitted by the v1249 feature freeze. It does not change product authority or add a product capability.

## Verification evidence

Focused suites:

- v1250.0 authoritative cleanup baseline: 92/92 passed.
- v1250.1 segmented broad verifier: 101/101 passed.
- v1250.2 hermetic verification runtime: 98/98 passed.

Retained v1249 regression suites:

- v1249.0-v1249.2 foundations: 195/195 passed.
- v1249.3-v1249.5 review and interface stability: 266/266 passed.
- v1249.6-v1249.8 adversarial reliability: 183/183 passed.
- v1249.9 checkpoint: 53/53 passed.

Additional evidence:

- all-source verification compile passed without source mutation or source-tree bytecode;
- the real `source-privacy` segmented stage completed using a clean external snapshot;
- both suites in that stage passed;
- the authoritative source signature remained unchanged;
- runtime cleanup completed;
- a second invocation reused the exact passed stage without execution;
- source-only and privacy checks passed;
- no files from the v1249.9 baseline were removed.

## Explicit non-claims

Bundle A does not claim:

- a complete ten-stage broad-profile pass;
- installation readiness;
- release readiness;
- certification;
- Desktop Codex approval;
- provider or native-runtime review;
- architecture cleanup completion;
- elimination of retained comment-token compatibility debt.

The complete segmented broad run belongs to the later cleanup checkpoint after Bundles B and C have changed the remaining shared infrastructure.

## Next bounded unit

`v1250.3-v1250.5 Release Metadata, Checkpoint, and Compatibility Consolidation`
