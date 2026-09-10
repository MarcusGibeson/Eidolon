# v2730.9.3 Operator Repair Controls

This patch repairs the independent v2730.9.2 review findings. Architecture consolidation is not included.

Use your configured Python environment from the Eidolon source directory:

    python conscious_agent/main.py --reliability status
    python conscious_agent/main.py --reliability review-policy

Policy review reads the real retrieval outcome history. Insufficient history creates no candidate. Review the returned candidate, then use its exact request_digest:

    python conscious_agent/main.py --reliability execute DIGEST --confirm DIGEST

Rollback requires the apply receipt_id:

    python conscious_agent/main.py --reliability rollback-policy RECEIPT --confirm RECEIPT

For an explicitly selected response, review and repair it without changing conversation history:

    python conscious_agent/main.py --reliability review-response --text "I deleted the file, and the answer is 42."

Review the returned candidate and execute its exact digest as above. This is a local CLI operator workflow, not an automatic conversation rewrite or a new chat command. Selected response text is stored only in private runtime as part of the explicit review request. No provider is contacted. Do not supply secrets. A mixed clause that cannot safely be separated stays blocked.

Optional --runtime-root PATH comes immediately after --reliability, before the subcommand, for disposable trials.

## State and authority

The existing policy filename now holds one versioned envelope containing policy and receipts, atomically replaced together. Flat legacy policies migrate on the first authorized application without changing values merely on read. Old separate receipts are retained but cannot authorize rollback; new receipts apply only to new changes. Malformed state fails closed.

Each candidate binds the reviewed policy baseline and receipt history. Replays and stale baselines are rejected, including after rollback. The bounded ledger fails closed at 1024 receipts rather than discarding replay evidence.

The operator CLI consumes exact request confirmation before execution. An interrupted request is never implicitly retried. Inspect policy/status and receipts before preparing a new request.

Research no longer erases a public subject merely because it is capitalized. Identifier, relationship-name, credential, and path filtering remains; public queries still require the existing exact authorization. Relevance and market demand are not guaranteed by this plumbing repair.

Installation, source promotion, training, provider selection, and model promotion remain separate authorities. Source-only archives must exclude runtime records and environments.

## Tests

### Corrected archive and query privacy

The corrected v2730.9.3 candidate preserves deterministic timestamps and records Unix mode 0755 for .sh/.command files, 0644 for other files. Archive verification rejects incorrect modes. Agent workflow notes live outside the source root and are excluded from source manifests and rejected from archives. The corrected candidate has its own source digest and archive hash; it is not interchangeable with the initial v2730.9.3 ZIP.

Relationship-qualified multi-token names, such as "my wife Sarah Jenkins", are removed together. Bare names such as "Sarah Jenkins" are intentionally retained when supplied as an operator research subject: capitalization alone cannot distinguish people from legitimate named public topics. This is a limited heuristic, not comprehensive personal-data detection. Explicit public-query confirmation remains a required, load-bearing privacy boundary, and operators must not authorize disclosure of private names. No automatic name classification or implicit public-query authorization is introduced. These cases and the actual missing-confirmation denial are tested.

tools/v2730_9_3_review_repairs_tests.py covers parser/planner subjects, privacy, candidate tampering, concurrent application, replay, failed writes, rollback corruption, mixed response clauses, and subprocess CLI paths. Retained v2730.9.2 and coding suites also run. Native gate results and installation evidence are maintained outside source in the repair workspace.
