# Windows/Desktop Codex and Native-Provider Handoff: v1199.9

## Review target

Review the v1199.9 Final Source-Only Candidate checkpoint as the final source candidate before the separate v1200 Cognitive Beta and Autonomous Developer Alpha decision gate.

## Required Windows/Desktop checks

1. Extract beneath exactly one clean `Eidolon/` root.
2. Confirm the supplied archive SHA-256 before extraction.
3. Run the v1199.9 external checkpoint suite.
4. Run the retained v1199.2, v1199.5, and v1199.8 suites.
5. Run current checkpoint verification through v1189.9 and the source-only boundary suite.
6. Compile all Python source with bytecode redirected outside the source tree.
7. Confirm zero runtime, settings, cache, compiled, private, provider-payload, conversation, memory, prompt, raw-patch, stdout, stderr, or credential artifacts in the archive.
8. Confirm GET-only checkpoint API behavior and POST rejection.
9. Confirm dashboard rendering remains content-free and presentation-only.
10. Review inherited quick/full performance-budget debt and partial fixture overlap separately from current regressions.

## Native-provider review boundary

Native-provider review may inspect provider readiness and compatibility only through the established supervised review process. It must not install, pull, delete, or switch models; expose provider payloads; consume approval; mutate runtime state; continue automatically; or grant provider, release, or autonomous authority.

## v1200 decision gate evidence

The v1200 gate must include:

- Desktop Codex review.
- Native-provider review.
- Complete current verification.
- Historical-debt accounting.
- Privacy and authority review.
- Upgrade, backup, rollback, and fresh-install evidence.
- Long-session and multi-day soak evidence.
- Responsiveness, background-work separation, queue, and cancellation evidence.
- The complete governed inspect -> plan -> approve -> implement -> test -> diagnose/repair -> present -> learn loop.
- An explicit operator decision.

Reaching v1200 source does not itself install, promote, certify, publish, release, or grant independent authority.
