# Eidolon v1265.9 Final Validation

Status: **source and fresh-extraction validation complete**.

## Source-side behavioral results

- v1265.0-v1265.2 foundations: **29/29**
- v1265.3-v1265.5 integration: **17/17**
- v1265.6-v1265.8 reliability: **19/19**
- v1265.9 checkpoint: **36/36**
- retained v1264.0-v1264.2: **56/56**
- retained v1264.3-v1264.5: **54/54**
- retained v1264.6-v1264.8: **48/48**
- retained v1264.9: **32/32**
- retained v1263.9: **32/32**
- retained v1262.9: **26/26**
- retained v1261.9: **27/27**
- v1250.3 release metadata: **94/94**
- v1250.4 checkpoint registry: **118/118**
- v1247.9 privacy/security: **59/59**
- Python static parsing: **2,703/2,703** at pre-package source pass
- source-only privacy summary: **0 forbidden runtime entries / 0 private-content findings**
- secret audit: **0 confirmed or likely secrets; 10 synthetic test canaries**

## Practical full-tree probe

The active source-only manifest was copied to an external disposable workspace. One exact authorization produced one candidate-only probe file with one deterministic provider fixture call. The active manifest remained unchanged, candidate validation passed, no application/self-update authority was granted, and cleanup removed the external workspace.

## Package validation

Initial source-only package validation established the final archive shape before the validation report was sealed:

- source-only entries: **3,316**
- archive roots: **exactly one `Eidolon/`**
- forbidden runtime entries: **0**
- private-content findings: **0**
- fresh extraction parity: **3,316/3,316 files**
- missing files: **0**
- extra files: **0**
- byte mismatches: **0**

The fresh extraction independently repeated:

- v1265.0-v1265.2: **29/29**
- v1265.3-v1265.5: **17/17**
- v1265.6-v1265.8: **19/19**
- v1265.9: **36/36**
- v1250.3 metadata: **94/94**
- v1250.4 registry: **118/118**
- v1247.9 privacy/security: **59/59**
- Python static parsing: **2,703/2,703**

The validation report itself contains no archive hash, avoiding a circular package-hash dependency. The final ZIP SHA-256 is recorded in the external release receipt.
