# v1490.2 Dynamic Improvement Discovery Foundations Ledger — Revised Desktop Repair

Status: revised unpromoted v1490.2 repair candidate; native Windows/Desktop Codex re-review remains required before Bundle B.

## Review correction

The earlier browser candidate reported the focused discovery suite as 36/36 pass. Desktop Codex subsequently reproduced concrete Windows/product defects despite that browser result: newline-normalized module digests made byte-level source immutability fail on CRLF files, compound protected-authority identifiers could lose their protected meaning during tokenization, bare same-name symbols in unrelated tests were incorrectly counted as test evidence, and first discovery was materially too slow on Windows. The prior 36/36 result is retained as historical browser evidence only and is not treated as proof that the candidate passed Desktop review.

## Revised scope

- v1490.0: deterministic AST module/top-level-symbol inventory with raw-byte source digests and module-aware test attribution.
- v1490.1: provider-free cohesive-family discovery with corrected protected-authority detection and explicit exclusion/rejection reasons.
- v1490.2 repair: read-only content-safe indexing/cache invalidation, source-immutability repair, performance reduction, truthful focus-module eligibility, and strengthened deterministic verification.

## Authority boundary

Discovery remains read-only. It does not rank or select candidates, create or persist proposals, prepare workspaces, request or consume approvals, contact providers, run implementations, mutate source/private runtime data, install candidates, promote releases, manage models, or broaden autonomous authority.

## Desktop findings repaired

- Source immutability now hashes inventory modules and verification with raw file bytes. LF, CRLF, mixed trees, and genuine byte mutation are tested separately.
- Protected authority detection preserves compound names including `source_apply`, `live_apply`, `release_apply`, `model_install`, `approval_execute`, `provider_switch`, and `rollback_apply`, and also inspects called dependency names. Harmless standalone `source` or `apply` does not become protected solely from that word.
- Test-reference evidence is attributable to a source module through conservative import/qualified-reference evidence. Bare same-name references are not confirmed coverage.
- Module analysis and test-reference indexing use process-local structural caches only. No source/test bodies or AST nodes are persisted in those caches. Changed, added, and deleted source/test files invalidate the discovery result.
- Current `conscious_agent/self_maintenance.py` no longer reports eligible focus candidates merely from unrelated same-name test references. Its insufficiently attributable families are rejected honestly while repository-wide discovery remains non-ranking/non-selecting.

## Current verification ledger

- Revised v1490.0-v1490.2 focused discovery suite: 64/64 pass in the current browser/container environment.
- v1489 product capability integration: 43/43 pass.
- v1489 symbol-level refactoring: 21/21 pass.
- v1489 generic self-development execution: 24/24 pass.
- v1489 supervised self-development Bundle 16: 13/13 pass.
- v1489 security/privacy/authority Bundle 17: 16/16 pass.
- v1489 ordinary conversation repair: 23/23 pass.
- v1457.9 privacy checkpoint: 7/7 pass.
- Source-only compilation, final source immutability, fresh-extract parity, ZIP SHA-256, and source-manifest SHA-256 are recorded in the final handoff after packaging.

## Content-free performance evidence

On the current verification host, a clean real-source discovery measured approximately 16.022 seconds cold and 0.071 seconds warm. The pre-repair candidate measured approximately 25.69 seconds cold on the same host. Desktop Codex previously observed approximately 197 seconds cold on native Windows; revised native Windows timing remains an external review requirement and is not inferred from browser/container timing.
