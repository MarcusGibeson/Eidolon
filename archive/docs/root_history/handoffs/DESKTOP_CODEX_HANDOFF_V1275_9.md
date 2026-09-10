# Desktop Codex Handoff — v1275.9 Dependency and Packaging Management

## Candidate scope

Validate native Windows behavior of v1275 dependency/package management bound to v1274 environment evidence and the existing v1273 ownership/v1272 recovery/v1271 session/v1270 campaign lineage.

## Required native scenarios

1. Create a fresh Windows virtual environment under a normal drive-letter path and verify the disposable clean-install path uses that environment rather than the active Python installation.
2. Repeat under a UNC path and an extended-length `\\?\` path, including a path beyond 260 characters when host policy permits it.
3. Verify requirements `-r`/`-c` includes remain inside the selected source root and path escapes are rejected on Windows separators.
4. Exercise a dependency file held open with restrictive NTFS sharing flags; drift/inspection must fail safely rather than silently reading a different file.
5. Exercise antivirus/indexer contention during deterministic ZIP replacement; the source tree must remain unchanged and a partial ZIP must not be presented as successful.
6. Perform a real clean install from a fresh source extraction with local/offline dependency material. Confirm `--no-index` and `PIP_NO_INDEX=1` prevent registry access.
7. Attempt a package whose dependencies require an unavailable remote distribution. Verify a clean bounded failure receipt without fallback network contact.
8. Exercise conflicting exact pins, contradictory bounds, markers, direct references, and constraints; unproven relationships must remain uncertain rather than be guessed coherent.
9. Modify a requirement/lock/configuration file after exact authorization preparation and verify execution is blocked as stale before pip runs.
10. Build the source-only ZIP twice from the same extracted tree and confirm byte-identical SHA-256 results, one `Eidolon/` root, and no runtime/private entries.
11. Confirm ZIP metadata uses the fixed deterministic timestamp/permission contract and source files are not rewritten to obtain reproducibility.
12. Close/restart dashboard/API/worker state around dependency assessment. No old clean-install authorization may be manufactured, renewed, or inferred from restart.

## Expected boundaries

- dependency inventory and conflict-free status are evidence, not install authority;
- a dependency-change plan does not edit the active source tree;
- clean-install execution requires one exact digest-bound authorization and current dependency/environment evidence;
- generic `go ahead`, `proceed`, or `do it` remains non-authorizing;
- clean-install execution is disposable and offline/no-index by default;
- raw installer output, credentials, provider payloads, and private runtime state are not package evidence;
- source-only package rules continue to exclude runtime `data/`, caches, logs, virtual environments, and private state;
- reproducible package creation is not release/publish authority;
- v1265, v1267, v1269, v1255, and rollback retain their separate exact authority boundaries.

## Handoff state

`v1275_dependency_packaging_management_checkpoint_ready_for_desktop_codex_review`

Next bounded unit after this checkpoint: **v1276 Architecture Boundary Extraction**. v1276 is not part of this handoff and has not been started.
