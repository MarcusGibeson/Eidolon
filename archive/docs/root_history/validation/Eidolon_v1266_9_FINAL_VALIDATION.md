# Eidolon v1266.9 Final Validation

Status: final source and fresh-extraction validation complete.

## Implemented scope

v1266 adds deterministic affected-surface and dependency-aware test selection for sealed v1265 isolated self-candidates. Trusted tests derive from the active source baseline; candidate-created tests are supplemental only; modified/deleted trusted tests block selection. The layer selects but does not execute verification.

## Practical full-tree probe

A disposable candidate-only change to `conscious_agent/isolated_self_modification.py` produced:

- v1265 source-only self inventory: 3,324 files / 41,991,919 bytes at probe time.
- One v1265 provider fixture call to create the candidate.
- v1266 trusted-test inventory: 1,136 tests.
- Affected surfaces: `python_runtime`, `self_modification`.
- Risk band: high.
- 10 selected tests: 7 focused + 3 regressions.
- Regression expansion: v1264 planning checkpoint, v1255 controlled application/rollback checkpoint, v1247 privacy/security checkpoint.
- Active source unchanged.
- v1266 provider calls: 0.
- Tests executed by v1266: 0.

## Final source validation

- v1266.0-v1266.2 foundations: 29/29.
- v1266.3-v1266.5 integration: 12/12.
- v1266.6-v1266.8 reliability: 15/15.
- v1266.9 checkpoint: 8/8.
- Retained v1265.0-v1265.2: 29/29.
- Retained v1265.3-v1265.5: 17/17.
- Retained v1265.6-v1265.8: 19/19.
- Retained v1265.9: 36/36.
- Retained checkpoints v1264.9 through v1254.9: 32/32, 32/32, 26/26, 27/27, 21/21, 39/39, 42/42, 42/42, 40/40, 31/31, 29/29.
- v1250.3 release metadata: 94/94.
- v1250.4 checkpoint registry: 118/118.
- v1247.9 privacy/security: 59/59.
- Python compilation: 2,711/2,711 source files.
- Source-only inventory: 3,328 files / 42,000,399 bytes.
- Root package privacy: 0 forbidden runtime entries, 0 private-content findings.
- Secret scan: 0 confirmed, 0 likely, 10 synthetic test canaries.

One grouped retained regression command reached its wall-clock limit after completing through v1255.9. The remaining v1254.9, metadata, registry, privacy, compilation, and root-package checks were run independently against the same source tree and passed; no assertion failed in the timed-out batch.

## Final package validation

The first sealed package-validation pass established:

- Source-only archive entries: 3,328.
- Exactly one `Eidolon/` root.
- Fresh-extraction parity: 3,328/3,328.
- Missing files: 0.
- Extra files: 0.
- Byte mismatches: 0.
- ZIP forbidden runtime entries: 0.
- ZIP private-content findings: 0.
- Fresh v1266 suites: 29/29, 12/12, 15/15, 8/8.
- Fresh retained v1265.9: 36/36.
- Fresh release metadata: 94/94.
- Fresh checkpoint registry: 118/118.
- Fresh privacy/security: 59/59.
- Fresh Python compilation: 2,711/2,711.
- Fresh extracted-root forbidden runtime entries: 0.
- Fresh extracted-root private-content findings: 0.

The final archive is rebuilt after embedding this report and is then rechecked for exact parity and the same core v1266/metadata/privacy evidence. The SHA-256 is recorded externally in the release receipt to avoid self-referential archive hashing.
