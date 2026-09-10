# Eidolon v1350.9 Desktop Codex Architecture / Windows Review

This is the scheduled ten-arc review for v1341-v1350. It is a source/architecture and portable Windows-oriented review performed on the Linux/container validation host. It does **not** claim native Windows execution or certification.

## Architecture findings

- Phase 5 contains ten implementation-skill modules and has no internal import cycles.
- Dependency direction remains narrow: v1346 cross-platform automation reuses v1345 Windows semantics; v1347 framework adaptation delegates execution to v1341 Python implementation. The v1350 benchmark consumes content-minimized scenario evidence rather than importing and rerunning skills itself.
- The largest Phase 5 module is `python_implementation.py` at 460 lines. No blind line-count split is warranted at this gate.
- Language-specific skills reuse the Phase 4 candidate-workspace/file/Git/process/browser contracts rather than creating alternate authority or execution paths.
- v1348 dependency selection is offline and evidence-only. It cannot contact registries, install packages, or mutate lockfiles.
- v1349 cross-language changes stages one receipt-owned multi-file candidate transaction only after per-file validation and all verification commands pass; failure creates no partial commit.
- v1350 requires six representative evidence paths: Python, web/browser, CLI/cross-platform, mixed-stack, framework adaptation, and dependency selection. Each must prove verification, cleanup/recoverability, selected-source immutability, and authority safety.

## Retained runtime / Windows-oriented evidence

- Retained ordinary-chat command distinction: 138/138, source immutable.
- Post-review critical-path repair: Phase 5 inspection controls are import-lazy for unrelated chat, and `eidolon.py chat` enters the lightweight launcher in-process instead of spawning a second interpreter. The historical v1251/v1253 cold-start budgets were not relaxed.
- Post-repair startup evidence: v1251.3-v1251.5 21/21 and v1253.3-v1253.5 20/20; an independent clean-snapshot reproduction measured v1253.3-v1253.5 cold launch at approximately 3.08 seconds against the unchanged 5.5-second budget.
- v1320.9 project-understanding checkpoint: 4/4, including Windows-pending honesty and governance preservation.
- v1253.9.1 pre-Codex runtime coherence: 81/81.
- v1253.9.2 Windows-oriented source coherence: 19/19.
- v1345 remains the Windows-first automation layer. v1346 adds POSIX behavior by explicit target-platform branching and argument vectors; it does not replace Windows quoting/path/process semantics with POSIX shell-string assumptions.
- Native PowerShell, Windows process-tree, service, installer, and filesystem behavior remain external Windows evidence on this host.

## Review decision

No protected-core authority expansion, release path, provider-management path, package-installation path, destructive recovery path, or unrestricted autonomy was introduced in Phase 5. No architecture blocker was found. v1350 may proceed to the mandatory complete ten-stage segmented verifier and final immutable checkpoint packaging. Native Windows execution remains an external validation requirement.
