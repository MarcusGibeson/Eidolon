# Eidolon v2502.8 Browser Campaign Ledger

Current source: **v2502.8 Research Intelligence Browser Campaign Consolidation**.

Status: **Browser-complete cumulative source candidate; uninstalled, unpromoted, uncertified.** v2502.9 remains the Desktop engineering and acceptance gate.

## Authoritative input

- Input archive: `Eidolon_v2502_2_research_result_review_citation_quality_candidate_source_only.zip`
- Verified input ZIP SHA-256: `5F2BDFDDBA6A5041BBEAE8285753E399D5D056302B9A430FA23A1BFBAD9D1A56`
- Archive shape: exactly one `Eidolon/` root.
- The campaign prompt supplied source-manifest SHA-256 `f1662fae2cc8bd94c7d8d77827d3eb395c86e06471e475dd0e3f465f958dd6f4`; the hash-verified baseline evaluated under the retained v1265.2 `source_only_manifest` canonical algorithm to `a165a68a849af9eaf260150f51d9e9d59d3d0b48a3e2c14c95ac8224900637fc`. The ZIP hash therefore remained authoritative and the discrepancy was preserved rather than silently rewritten.

## Work ledger

### v2502.3 - Durable research-session history

Added digest-bound terminal research history for completed, cancelled, failed, and interrupted sessions. Public history keeps exact session lineage, timestamps, terminal state, report digest, evidence/source-failure counts, freshness/quality bands, and integrity diagnostics while excluding private objectives, queries, page bodies, credentials, cookies, and private receipts. Reconnect and duplicate terminal persistence are idempotent. The dashboard gains a narrow-width history surface. A retained server-side reconnect/progress renderer placement defect was repaired.

### v2502.4 - Evidence-summary comparison

Added explicit comparison of two completed sessions using content-free evidence structure only. Added, removed, changed, stale, contradictory, duplicate, and unsupported evidence remain distinct; exact report/session digests and source independence are preserved; no winner is inferred automatically. Comparison performs no web request and rejects sessions that are not meaningfully comparable.

### v2502.5 - Bounded cited-report export

Added explicit operator-selected local Markdown export for one completed report. Export binds source session ID, report digest, export schema version, and export digest and includes verified findings, labeled inference, disagreement, evidence gaps, freshness, sanitized citations, and limitations. Private objectives, queries, raw pages, credentials, cookies, provider payloads, stack traces, private paths, and unrelated runtime state are excluded. Repeated execution is idempotent and no upload/transmission authority exists.

### v2502.6 - Research question decomposition

Hardened deterministic decomposition around required facts, comparative criteria, assumptions, unknowns, and stopping conditions using the retained research reasoning owners. Overly broad, ambiguous, unsafe, side-effecting, and budget-impossible objectives fail closed before public research begins. Planning remains provider-neutral and deterministic.

### v2502.7 - Source strategy and adaptive follow-up

Strengthened primary/authoritative preference, source diversity, domain duplication, independence, freshness, relevance, and quality strategy. One privacy-safe follow-up may be admitted for a material contradiction or evidence gap when sufficient budget remains. Evidence, page, time, and source-failure thresholds stop additional work. Access-control evasion, paywall bypass, authentication expansion, and page-directed authority expansion remain prohibited. A regression that initially reserved budget from legacy two-query sessions was repaired; adaptive reservation now requires sufficient query budget. A synthetic privacy fixture was also changed to use fictional rather than operator-private context before release packaging.

### v2502.8 - Synthesis quality and consolidation

Strengthened evidence-weighted conclusions so material conclusions are attributable or explicitly labeled inference. Same-source citation repetition is visible but cannot count as independent confirmation. Minority, contradictory, stale, incomplete, duplicate, and unsupported evidence remain present. The retained dashboard coherently exposes review, history, explicit comparison, and explicit local export. Release metadata and the four authoritative README/roadmap surfaces were advanced coherently to the unpromoted v2502.8 candidate.

## Browser verification ledger summary

- v2501.0-v2501.8 directly affected historical research suites: **9 suites / 112 checks passed / 0 failed**.
- v2502.0-v2502.8 research suites: **9 suites / 240 checks passed / 0 failed**.
- Combined focused regression: **18 suites / 352 checks passed / 0 failed**.
- Changed Python syntax compilation: pass, no source-tree bytecode required.
- Rendered dashboard JavaScript: Node syntax check pass.
- Source immutability around focused testing: pass, zero non-cache added/removed/changed files.
- One quick release-profile invocation ran for 252.336 seconds and correctly blocked on the retained `quick_profile_is_bounded` contract after all six campaign suites were initially placed in the quick set. It reported zero source writes and zero source deletes. The verifier registration was repaired without rerunning the one-shot quick profile: all six suites remain registered once in the canonical verifier inventory, while v2502.7 and v2502.8 replace superseded high-signal research representatives in the 20-stage quick profile. The directly failing v1300.9.1 bounded-profile contract then passed.
- Native network validation was not performed in Browser.

Final archive and canonical source-manifest hashes are generated externally after source-only staging and fresh-extraction verification, because embedding those self-referential release hashes in this source ledger would change the manifest they describe.

## Deferred v2502.9 Desktop ledger

Desktop Codex retains responsibility for native Windows public-web transport and DNS/redirect/connected-peer behavior; configured-provider/live-public-web research where explicitly authorized; process ownership, ports, restart and concurrency behavior; private-runtime history/reconnect restoration; long-session budget/performance and failure behavior; local report-export path/permission behavior; installer, upgrade, rollback and fresh-install checks; and operator-visible Windows UI/accessibility acceptance. No Browser result grants installation, promotion, certification, release, model-management, destructive-operation, secret-access, source-mutation, or standing research authority.
