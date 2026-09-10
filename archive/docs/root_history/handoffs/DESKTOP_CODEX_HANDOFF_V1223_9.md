# Desktop Codex Handoff — v1223.9

Review the v1223.9 source-only candidate from a fresh Windows extraction.

Confirm that Eidolon can derive one privacy-safe queue across multiple supervised-development transactions without replacing proposal, history, or resumption receipts.

Verify that:

- transactions are grouped only through digest-bound project identity and no project name or path appears publicly;
- active, awaiting approval, resumable, blocked, deferred, abandoned, and closed states are deterministic;
- exactly one current transaction is selected per project;
- multiple open transactions for the same project are blocked as a conflict rather than granted parallel authority;
- exact ordinary-chat queue, filter, project-state, focus, defer, close, and reopen controls remain distinct from wishes, quotations, and casual conversation;
- focus changes conversation context only and grants no authority;
- defer and close are durable queue dispositions and do not mutate the selected project;
- reopen prepares only a new digest-bound approval-gated proposal with approval unconsumed and continuation unexecuted;
- queue, focus, and item controls survive restart through append-only generations and deterministic replay;
- stale queue digests, missing items, malformed records, tampered controls, cross-project evidence, and conflicting open work fail closed;
- pagination is bounded to 50 items and total queue discovery is bounded to 500 proposals;
- no request, path, project name, file name, generated content, provider output, test output, rollback content, or runtime location is exposed;
- no queue operation contacts a provider, runs commands/tests, continues work, repairs, applies, rolls back, installs, promotes, certifies, releases, manages models, changes project/source bytes, or grants authority.

Run the four focused v1223 suites, retained v1222 suites, checkpoint CLI and GET API, registry discovery, privacy inventory, source immutability checks, and quick/full release profiles where the environment permits. Treat unavailable dependencies and timed-out inherited gates as limitations rather than passes.

Next bounded unit: v1224.0-v1224.2 Operator-Governed Work Prioritization and Scheduling Foundations.
