# Independent control-flow closure

Verdict: PASS / READY_FOR_EXECUTION_FREEZE_REVIEW_ONLY.

Exactly one fresh independent read-only audit completed the required scope.
There were no P1/P2 findings, product assertion failures, or scientific gaps.
The full auditor-authored report, scripts, failed accounting assertion,
partial setup report, raw assertions, and synthetic evidence are preserved
unchanged in independent_audit_evidence. All 24713 copied files match their
original bytes; 24712 non-manifest members match the sealed evidence manifest.

The auditor first directly reproduced KeyboardInterrupt and SystemExit at
Run.perform after transport observed START, followed by GeneratorExit and a
custom BaseException. The original signal object/arguments propagated only
after the scoped INVALID omission incident was persisted. External catch
permitted zero later transport calls and no second START; disk reconstruction
rejected the omitted call. A/B signal scope, ordinary exceptions, malformed
outcomes, and complete LR1-LR3/I1-I6 suites were then exercised afresh.

The reviewer executed the actual 480-call synthetic A path, checked all 64 B
subsets, 108 E5 wire audits, 12 elapsed clarifications, scorers/reserves, all 50
protected files, and full journal/checkpoint/state lineage. Both producer
720-observation pilots were independently replayed and their complete 1447-file
trees compared byte-for-byte. Candidate and eight committed source bindings,
accepted package/science closure, and all three old blocked candidates matched.

There are 5758 recorded audit assertions: 5757 PASS and one disclosed auditor
accounting error (all untracked files counted instead of corpus-only files),
corrected and preserved. A missing temp-helper parent was also corrected before
that test. Neither required repository/product repair or represented a blocker.
No assertion failure or earlier evidence was erased. No post-audit repair and
no second audit occurred.

Implementation: 17af89c9c4f279d55d48aac46125c2844d3b4ad5.
Producer evidence: 10cc8a978237fa6a403c1bfd72184845200b192e.
Candidate: 4819d754192df7c49055a825353b9387d2cf51efe9652ef9f64bda8736be62c1.

The candidate remains EXECUTION_FREEZE_CANDIDATE_ONLY, unactivated. The three
superseded candidates remain blocked/unactivated. Readiness is only for a
separate execution-freeze review; separate activation and A/conditional B
authorization remain required. No live provider identity attestation or
scientific/model qualification is claimed.

Provider/model calls and real A/B calls: zero. Accepted corpus, gold, design,
blueprint, thresholds, schedules, and provider configuration unchanged. No
autonomy; belief effects none. G-ROUTE4 remains CLOSED FAILED.
