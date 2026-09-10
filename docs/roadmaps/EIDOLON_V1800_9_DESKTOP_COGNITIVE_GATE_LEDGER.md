# Eidolon v1800.9 Desktop Cognitive Gate Ledger

Status: Desktop-reviewed source-only checkpoint; unpromoted and not installed.

## Input identity

- Candidate ZIP SHA-256: `e1397685fa0ce898995aabffaba383c71b1c8fd8a2f9ed2c0a6b1247cb5b5a4c`
- Candidate source-manifest SHA-256: `d298cb6d4e3fbf35c2f7f6ec94ff6349a3b551123d78a7a8c06b88921856c8cb`
- Archive shape: one `Eidolon/` root; no packaged private runtime data.
- Cumulative diff from v1700.9: 14 added, 11 modified, 0 deleted files before Desktop repairs.

## Windows evidence

- Focused Era 3 suites: 102/102 passed before repair; 104/104 after the two added privacy assertions.
- Affected retained suites: 523/523 passed, plus 84/84 internal requirement assertions.
- Historical v1155.9 suite: 62/66 on both untouched v1700.9 and this candidate, with the same four failures.
- Native Ollama: readiness passed; configuration digest matched; generation, streaming, and embeddings passed; embedding dimensions 768.
- Browser review: desktop composer visible, Enter submitted exactly one turn, no console errors, and 390x844 layout has no document, log, or message overflow after repair.
- Ordinary conversation: correct cold and warm responses committed exactly once; first-visible measurements were approximately 11.5 and 10.4 seconds on a long restored conversation.

## Desktop repairs

1. Public problem-frame projections now expose only IDs, provenance, confidence, reason codes, and text digests. Operator request text stays in the external private record.
2. Problem-frame corrections/cancellation, causal observations, long-plan outcomes/revisions/pause state, and epistemic outcomes now use the existing cross-process metadata mutation lock. Concurrent stale writers fail closed instead of reporting two successes and losing one update.
3. Reusable chat bubbles and the fast first-use shell wrap long identifiers and clip horizontal overflow at narrow widths.

## Remaining limitations

- Native daily-use response latency is still noticeable with the configured 7B model and a long conversation history.
- The v1155.9 historical fixture debt remains inherited and non-regressive.
- This gate is not an installation, promotion, certification, model-management action, or grant of independent authority.

## Next bounded unit

`v1801.0 - Memory Consolidation and Retrieval foundations`
