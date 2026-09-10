# v1254.6-v1254.8 Bundle C Review

## Scope

Bundle C hardens isolated coding execution for Windows portability, interruption/restart recovery, stale-source races, transactional workspace behavior, cancellation, and operator review.

## Implemented

- Rejects Windows reserved device names, trailing-dot/space and invalid portable path forms, and case-insensitive path collisions during inspection.
- Keeps long valid relative paths intact rather than imposing the legacy 260-character MAX_PATH limit in the platform-neutral contract.
- Revalidates disposable workspace integrity before execution, including unexpected links/reparse-like entries, private/generated material, special files, and casefold collisions.
- Rejects provider attempts to modify or delete existing project-owned tests.
- Preflights every generated file operation before writing any of them, preventing a later conflict from leaving earlier files partially applied.
- Rechecks selected-source freshness after provider generation and before workspace application, blocking operator/source races.
- Persists generation attempts before application. An expired execution lease may recover with the same exact authorization and reuses the sealed attempt instead of contacting the provider twice.
- Deterministic cancellation removes the disposable workspace and prevents later execution/provider contact.
- Added read-only execution health inspection with lineage, attempt/review digest, workspace-integrity, source-freshness, lease/recovery, and authority-boundary evidence.
- Added exact ordinary-chat review control and operator handoff containing diff, verification evidence, source freshness, limitations, and explicit v1255 application-stage separation.

## Evidence

`tools/v1254_6_8_isolated_coding_execution_reliability_tests.py`: **86/86 passed**.

The suite covers casefold collisions, Windows reserved names, long paths, injected private files, symlink escapes, project-test tampering, transactional multi-file conflicts, expired-lease recovery without duplicate provider calls, cancellation cleanup, operator review, and a selected-source change occurring during provider generation.

## Native Windows limitation

The source implements Windows-aware reparse/link containment and deterministic fixtures exercise the contract, but this Linux-side development environment cannot create and validate a real Windows junction/reparse point. Native Windows junction behavior remains an explicit Desktop Codex handoff item.

## Authority boundary

Application, installation, release, permanent approval, unrestricted dependency/shell authority, and independent self-update remain denied.
