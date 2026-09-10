# v1266.0-v1266.9 Intelligent Test Selection Review

## Scope

v1266 consumes one sealed v1265 isolated self-modification candidate and produces a bounded, reviewable test-selection artifact. It does not execute tests, contact providers, mutate either active source or the disposable candidate, repair code, apply a candidate, install, release, or grant self-update authority.

## v1266.0-v1266.2

- Added a manifest/digest-bound test-selection record linked to the exact v1265 operation, result digest, and candidate manifest.
- Inventories existing trusted tests from the active source baseline while deriving affected source relationships from the disposable candidate.
- Classifies changed paths into architectural surfaces including Python runtime, release control, privacy/security, conversation, coding pipeline, self-modification, planning/inspection, test infrastructure, documentation, and operator surfaces.
- Builds a bounded reverse Python import graph and propagates affected modules two dependency levels.
- Selects focused and regression tiers with content-minimized reason codes and evidence strength.
- Computes bounded risk bands and deterministic selection IDs/digests.
- Selection preparation has no test-execution, repair, application, installation, release, or independent authority.

## v1266.3-v1266.5

- Integrated selection directly with the sealed v1265 self-candidate record and disposable workspace.
- Direct tests importing changed modules are selected as focused evidence.
- Tests of modules transitively dependent on changed modules are expanded as regressions.
- High-risk governance surfaces add retained regression checkpoints even when they are not direct imports.
- A content-minimized explanation summarizes affected surfaces, test tiers, and selection-reason counts without exposing test contents.
- Selection never recontacts the v1265 provider.

## v1266.6-v1266.8

- Added freshness validation against the exact v1265 result digest, candidate manifest, current disposable workspace, active trusted-test inventory, and recomputed selection semantics.
- Resealing altered selection content with recomputed outer digests is insufficient; semantic recomputation still rejects the mismatch.
- Modifying or deleting an existing trusted test in the candidate blocks selection.
- Candidate-created tests are recorded as supplemental/untrusted and cannot count as retained verification.
- Added eight-way concurrent duplicate convergence, long-path coverage, stale-candidate invalidation, read-only health inspection, and a Windows/Desktop handoff.

## v1266.9 checkpoint

The checkpoint is read-only. It verifies the foundations/integration/reliability surfaces, retained v1265 self-modification, privacy tooling, denied test execution and repair authority, and the v1267 boundary.

## Practical full-tree probe

The final v1266 working source was used as the real source baseline. A disposable v1265 candidate changed only `conscious_agent/isolated_self_modification.py` by appending a harmless candidate-only comment. At probe time:

- Source-only self inventory: 3,324 files / 41,991,919 bytes.
- Provider fixture calls: 1, solely to create the disposable v1265 candidate.
- v1266 trusted test inventory: 1,136 files.
- Changed paths: 1.
- Affected surfaces: `python_runtime`, `self_modification`.
- Risk band: high.
- Selected verification: 10 tests, comprising 7 focused and 3 regression tests.
- Focused evidence covered v1265/v1266 direct-import and path-lineage tests.
- Regression evidence added v1264 planning, v1255 controlled application/rollback, and v1247 privacy/security boundaries.
- Active source manifest remained unchanged.
- v1266 executed zero tests and contacted zero providers.

The probe workspace was external and disposable and was removed afterward.

## Authority boundary

Application remains separately governed by v1255. v1266 grants no command execution, test execution, repair, active-source mutation, candidate mutation, installation, promotion, certification, release, permanent approval, or independent self-update authority. v1267 owns bounded execution of selected verification and iterative self-repair.
