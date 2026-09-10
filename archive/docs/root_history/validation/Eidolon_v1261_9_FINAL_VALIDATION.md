# Eidolon v1261.9 Final Validation

The authoritative baseline for this arc is the finalized v1260.9 Coding Alpha source-only candidate with SHA-256 `3CA795356E40EDC040A5AEF1F1D736B070F44888B5E935C05FFE5720118C7253`.

## Core v1261 evidence

- v1261.0-v1261.2 foundations: **43/43**.
- v1261.3-v1261.5 integration: **36/36**.
- v1261.6-v1261.8 reliability: **34/34**.
- v1261.9 read-only checkpoint: **28/28**.

## Retained evidence

- v1260.0-v1260.2 Coding Alpha foundations: **35/35**.
- v1260.3-v1260.5 canonical Coding Alpha campaign: **33/33**.
- v1260.6-v1260.8 Coding Alpha reliability: **17/17**.
- v1260.9 retained checkpoint: **21/21** under later-source compatibility.
- v1259.9 retained checkpoint: **39/39**.
- v1258.9 retained checkpoint: **42/42**.
- v1257.9 retained checkpoint: **42/42**.
- v1256.9 retained checkpoint: **40/40**.
- v1255.9 retained checkpoint: **31/31**.
- v1254.9 retained checkpoint: **29/29**.
- v1253.9.2 Windows coherence contract: **19/19**.
- v1238.9 broader project/language adapters: **27/27**.
- v1250.3 release metadata consolidation: **94/94**.
- v1250.4 checkpoint registry consolidation: **118/118**.
- v1247.9 privacy/security audit: **59/59**, with **0 confirmed/likely secrets** and 10 deliberate synthetic canaries.

## Static and privacy validation

- Python source compilation before final packaging: **2,671/2,671**.
- Source-only root privacy inventory before packaging: **0 forbidden runtime entries** and **0 private-content findings**.
- Generated runtime `data/settings.json` and bytecode caches are excluded/purged before packaging.

## Limitations

v1261 supplies evidence-based inspection, not semantic proof of every project property. Presence of a test file does not prove the test passes. Documentation presence does not prove correctness. Runtime health, operator feedback, executed-test outcome, and development-session history remain unknown unless explicit bounded evidence is supplied. Native NTFS junction/reparse behavior and true multi-process Windows concurrency remain Desktop review items.

Final archive SHA-256, fresh-extraction parity, archive privacy, and fresh-extraction reruns are recorded in the external release receipt generated after the final ZIP is sealed.
