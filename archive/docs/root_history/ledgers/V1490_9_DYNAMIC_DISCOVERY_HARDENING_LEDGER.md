# v1490.9 Dynamic Discovery Hardening Ledger

Status: **unpromoted development checkpoint**.

- Repairs the Desktop Codex stale-cache finding by binding discovery-cache admission and per-file structural analysis caches to current raw-byte SHA-256 digests. Path/size/mtime metadata is never sufficient to reuse discovery evidence.
- Deterministic regressions cover same-length source and test replacements with restored timestamps, LF/CRLF/mixed trees, real byte mutation, added/deleted files, protected compound identifiers, module-aware test attribution, and cache invalidation.
- v1490.3-v1490.9 adds deterministic duplicate/exact-overlap exclusion, partial-overlap visibility for later comparison, confidence/uncertainty evidence, completed-lineage exclusion, and protected-boundary hardening.
- Dynamic discovery remains provider-free, read-only, non-selecting, non-authorizing, and source-immutable.
- No installation, promotion, model management, workspace preparation, or autonomous authority is granted.
