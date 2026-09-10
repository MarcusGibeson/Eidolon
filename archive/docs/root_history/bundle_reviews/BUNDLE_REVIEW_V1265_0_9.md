# v1265.0-v1265.9 Isolated Self-Modification Review

## Scope

v1265 implements only isolated self-modification. It consumes a validated, uniquely selected v1264 plan, creates a source-only clean copy of Eidolon in external runtime storage, allows one exact digest-bound provider-backed mutation of that disposable copy, and exposes content-minimized candidate evidence. It does not apply the candidate to the active source tree.

## v1265.0-v1265.2

- Added a source-only self inventory capped at 6,000 files / 128 MiB.
- Reuses the current package privacy boundary: all `data/`, runtime, cache, bytecode, log, archive, symlink, and Windows reparse/junction-like entries are excluded or rejected.
- Requires Eidolon source identity markers and a valid v1264 plan/priority/backlog lineage.
- Read-only evidence-acquisition and evidence-resolution plans cannot be promoted into mutation work.
- Creates a deterministic external-runtime `selfmod_*` operation and clean `Eidolon/` workspace with exact manifest parity.
- Seals source, workspace, plan, selection, backlog, selected approach, and authorization digests.
- Preparation is idempotent and grants no provider, command, test, active-source mutation, application, install, release, or self-update authority.

## v1265.3-v1265.5

- Added exact digest-bound isolated self-modification authorization.
- Vague authorization is rejected before provider contact.
- Provider output is a bounded structured change set: at most 32 files, 2 MiB per file, 8 MiB total.
- All changed paths pass relative-path, private/runtime-path, link, and casefold checks.
- Changes are staged transactionally and replace only the disposable workspace.
- Changed Python files receive bounded AST syntax validation; project tests are intentionally not selected or executed yet.
- Candidate review evidence contains paths, before/after digests, added/removed line counts, candidate manifest, and diff digest without exposing source contents.
- Replaying the exact authorization restores the sealed result and does not contact the provider again.

## v1265.6-v1265.8

- Active-source stale changes block before provider contact.
- Workspace/candidate tampering invalidates the sealed candidate.
- Provider attempts to create private/runtime paths fail closed.
- Cancellation and workspace cleanup are deterministic and cleanup is idempotent.
- Interrupted `running` records never auto-retry the provider; they close into operator-reprepare state.
- Four concurrent duplicate exact authorizations converge on one provider call and one sealed candidate in deterministic testing.
- Long external runtime paths are supported.
- Symlink/reparse-like source entries are rejected before clean-copy creation.
- Added read-only health and Desktop operator handoff surfaces.

## v1265.9 checkpoint

The checkpoint is read-only and content-minimized. It verifies presence of the v1265 foundations/integration/reliability surfaces, retained v1264 planning, package privacy, denied active-source/application/self-update authority, and the v1266 boundary.

## Practical full-tree probe

The final v1265 source was used as its own inspection/planning target. v1263 selected the maintenance/limitation candidate via bounded priority context and v1264 selected `bounded_targeted_investigation`. v1265 then copied 3,312 source-only files (41,927,212 bytes at probe time) to external runtime storage. One exact authorization made one harmless candidate-only probe source file with one provider fixture call. The active source manifest remained identical, the candidate manifest changed, candidate validation passed, no application/self-update authority existed, and cleanup removed the disposable workspace. The probe file was never written into the active source tree.

## Boundaries retained

- Active source mutation: denied.
- Selected-project mutation: denied by v1265.
- Application/rollback: remains separately governed by v1255.
- Test selection: deferred to v1266.
- Automatic repair: deferred to v1267.
- Operator review handoff: expanded later by v1268.
- Governed self-update: deferred to v1269.
- Release/promotion/certification/permanent approval/independent authority: denied.
