# v1191.9 Responsiveness and Background Work Checkpoint Review

## Scope

Built from the immutable v1191.8 source-only candidate with verified SHA-256 `4A1668B7CB1107001F5B1BCA03C117A0EB8141D446AC77B131FADE042C6DDBCC`.

The checkpoint consolidates v1191.0-v1191.8 and repairs four findings inherited from the v1190.9 Desktop review.

## Completed repairs

1. Web-page sample requests now route correctly.
   - `Make me a web page ...` is classified as an action request.
   - `Build me a web page ...` remains an action request.
   - Both ground to the registered `software_development` capability.
   - The capability is proposal-only, medium-risk, and never execution-eligible from conversation.

2. The supervised development campaign is visible in ordinary chat.
   - Non-streaming and streaming conversation paths receive the same content-free campaign projection.
   - The projection exposes the governed inspect, specify, plan, review, sandbox implementation, test, diagnosis/repair, result presentation, and bounded-learning stages.
   - No proposal is persisted, approval created, campaign started, work executed, or authority granted.

3. Windows CRLF sandbox repair materialization is supported.
   - Reviewed UTF-8 text is compared using canonical newline bytes.
   - Raw physical sandbox bytes are preserved in the rollback artifact.
   - Canonical reviewed digests and physical rollback digests remain separate and explicit.
   - True content drift is still rejected.

4. Current v1190 Windows encoding failures are repaired.
   - The v1190.3-v1190.5 navigation suite uses explicit UTF-8 reads.
   - The v1190.6-v1190.8 reliability suite uses explicit UTF-8 reads.

## Severity review

- Critical: none found.
- High: the two reported v1190.9 high-severity findings are repaired and covered by deterministic tests.
- Medium: the two reported Windows compatibility findings are repaired and covered by deterministic tests.
- Remaining medium debt: inherited quick/full verifier ownership, historical fixture overlap, cleanup-prefix behavior, and performance-budget reconciliation remain for v1193 and later hardening.
- Low: chat campaign integration remains proposal-only and content-free; it intentionally does not persist or execute campaign work.

## Boundaries preserved

No queued work, development campaign, provider, model, thread, process, shell command, approval consumption, cancellation, recovery, source mutation, runtime mutation, installation, promotion, certification, publication, release, or autonomous authority expansion occurs.

## Next bounded unit

v1192.0-v1192.2 Bounded Evidence Compaction Foundations.
