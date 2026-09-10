# Eidolon v2731.0.3 Research Admissibility and Runtime Contention Repair

Working source at start of session: **v2730.9.3**
Session date: **2026-09-09 / 2026-09-10**

## Conversation service contention repair

Desktop chat stopped responding: `/api/dashboard-chat/stream` accepted the TCP connection but never
sent response headers, so the shell timed out after 180 s with `acceptance=None`. Four independent
causes, each a long operation on a hot path, three of them holding a process-global lock.

- `conversation_sessions.migrate_legacy_dashboard_chat_turns` derived the archive session identity
  from a digest of `data/dashboard_chat/`, a directory the live chat surface still writes to on every
  turn. Each new turn changed the digest, missed the idempotency guard, and re-imported the whole
  transcript into a fresh session under `_SESSION_LOCK`. Observed: 447 stuck threads, 401 duplicate
  sessions, 125 MB of duplicated transcript. Identity is now stable, only new turns are appended, and
  an unchanged directory is skipped by a cheap count/size/mtime signature.
- `runtime_projection_cache.cached_read_only_projection` ran `builder()` outside the cache lock, so
  every concurrent caller started its own rebuild, and its directory-mtime signature invalidated on
  any unrelated write. `/api/status` costs 15-27 s and is polled every 8 s, so several full rebuilds
  ran concurrently, each taking `_INDEX_LOCK` and `_SESSION_LOCK`. Single-flight added: concurrent
  callers wait on one build and accept a result finished after they asked.
- `dashboard_chat_console._current_action_portal_for_turn` resolved each rendered turn's governed
  action separately, and every resolution re-read and re-parsed the entire chat-actions directory. A
  120-turn window against 121 action files was roughly 14,500 file reads for one snapshot, and each
  call also took `_INDEX_LOCK` and deep-copied the projection. The catalogue is now indexed once per
  render and passed down. `chat_action_router.resolve_chat_action_id` additionally stopped loading
  the catalogue in order to resolve a concrete identifier to itself.
- `api_server` counted memories with `len(load_memories())`, loading and JSON-parsing 2,467 payloads
  under `_INDEX_LOCK` to produce a number. Replaced with `count_memories()` (`SELECT COUNT(*)`).

Measured: `/api/status` 15.6 s to 3.6 s cold; four concurrent callers 26.6 s each to 5.7 s shared;
trial wall time 1105 s to ~200 s; dashboard threads during a full trial went from climbing to 128 to
flat at 5-13. Not fixed: a warm chat-console render still costs ~3.6 s from other work in that path.

## Research evidence admissibility repairs

A bounded research trial could not admit evidence regardless of source quality. The search adapter
emits placeholder metadata, and every placeholder is treated downstream as inadmissible.

- **Freshness.** `search()` returns empty `published_at`/`fetched_at`, so every candidate was
  `freshness: unknown`, and unknown never satisfies a current-evidence claim. The fetched document
  usually declares a date and the parser already extracted it; `observe()` now derives freshness from
  it. Undeclared or unparseable dates still resolve to unknown.
- **Freshness policy.** `create_session` defaulted every session to `current` (30 days) irrespective
  of the question. A durable demand question now resolves to `slow_changing` (730 days) from the
  objective's shape; competition to `versioned`; free-tier feasibility stays `current`. An explicit
  caller policy still wins. `requires_current_evidence` is unchanged.
- **Source kind.** `source_kind: "unknown"` yields empty `supportable_dimensions`, so an unknown-kind
  source can support no claim at all. `observe()` now maps a document's declared JSON-LD `@type` and
  `og:type` to a kind. Bare `Article`/`BlogPosting` is deliberately not promoted, and a promotional
  URL remains unable to establish demand at any kind.
- **Assessment cap.** The synthesis prompt requested four source assessments regardless of corpus
  size, so with seven observed sources three were never assessed and could never support a claim.
  The cap now follows the number of sources offered, bounded at 8, with the output token budget
  scaled to fit. Verified in production: `grounded_assessment_count` moved from a constant 4 to 8.
- **Benign grounding rejections.** Any grounding rejection refused the whole inference, so the model
  repeating one assessment was weighted identically to it quoting text absent from the observed
  excerpt. Grounding already drops the repeat. Rejections are now classified: claiming provenance the
  response does not have still refuses, duplication does not, and unlisted reasons fail closed. A
  live trial failed on exactly one `duplicate_assessment`. Raising the assessment cap made this more
  likely to fire, by asking for more assessments over a small corpus.
- **Stale citations.** A cited source that was merely out of date denied the entire inference, while
  a vendor page or an irrelevant one was simply skipped. Stale citations are now excluded from
  eligibility and recorded on the inference with a limitation naming the exclusion. Two fresh
  independent publishers are still required, a stale source still cannot count as support, and a
  citation that contradicts the claim still refuses the finding outright.

Measured across trials on one objective: citation freshness `unknown: 8` to `fresh: 5, stale: 2`;
`max_quality` 0.30 to 0.82; grounded assessments 4 to 8; supporting assessments 1 to 4.

## Collection recovery

- The observation loop iterated a candidate list frozen before observation, and an unreadable source
  was dropped with no replacement, shrinking the evidence pool by exactly the number of failures while
  most of the query budget went unused. A failure now triggers one targeted replacement search that
  excludes the failed host, capped at 3 per run and bounded by every existing budget.
- A consent-gated or JS-rendered domain yields nothing for any of its pages, and several such pages
  sat in the queue together, each spending its own failure. Later pages from a host that already
  failed are now skipped. A live run that spent 3 failures on one domain now spends 1.
- Promotional pages are sorted last when the objective requires a specific evidence dimension.
- `passage_options` only offered text in 30-600 character sentence-bounded segments, so a page that
  is one unbroken paragraph produced none and was dropped from the prompt entirely. It now works in
  offsets: overlong runs are cut at whitespace, consecutive short fragments joined across their
  original separators. Every option remains an exact slice of the observed excerpt.

## Observability

Diagnostics existed but were not persisted, so failures were invisible in the stored receipt. Added
to the content-free projection: `model_assessment_status`, `model_assessment_denial_reason`,
`grounded_assessment_count`, `assessment_stance_counts`, `assessment_evidence_kind_counts`,
`rejected_assessment_counts`, `assessment_selector_diagnostics`, `assessment_admission_blockers`,
`omitted_passage_source_count`, `skipped_unreadable_host_count`, `readable_content_failure_count`.
Counts and fixed reason codes only; no claim text, quote, or URL.

`model_assessed_conclusion` returned a bare `model_assessment_not_admitted` from nineteen distinct
sites, so every refusal read the same. Each now returns its own reason code. This is what identified
the duplicate-assessment defect; three separate predictions about the cause had been wrong first.

The terminal-failure path built a minimal report that omitted these, leaving the runs most in need of
a post-mortem blind. It now carries them, initialised before collection so a run that dies early
cannot raise a second error while describing the first.

## Version control

The repository contained an empty `.git` directory, so no work was recoverable. Version control was
established mid-session: source only, 5,972 files / 53.6 MB. The runtime data root is excluded
wholesale — a naive add would have taken 188,347 files and 1.9 GB, including 113 MB of private
conversation transcripts that `conversation_sessions.py` states must never be packaged as source.

## Regression coverage

New suites totalling **179 checks**, each verified to fail when its fix is reverted:

- `tools/v2730_9_5_research_source_metadata_tests.py` (39)
- `tools/v2730_9_6_legacy_dashboard_chat_import_tests.py` (16)
- `tools/v2730_9_7_observation_replacement_tests.py` (17)
- `tools/v2730_9_8_projection_cache_single_flight_tests.py` (14)
- `tools/v2730_9_9_passage_extraction_tests.py` (20, incl. 400 fuzz cases on the verbatim invariant)
- `tools/v2731_0_0_source_assessment_cap_tests.py` (9)
- `tools/v2731_0_1_unreadable_host_skip_tests.py` (16)
- `tools/v2731_0_2_model_assessment_denial_reason_tests.py` (32)
- `tools/v2731_0_3_transcript_action_lookup_tests.py` (16)

Pre-existing failures, confirmed unrelated by re-running against reverted code: `v2501_1`, `v2502_7`,
`v2503_0`, `v2503_2_quick_verifier_parallel_core`, `v2503_2_quick_verifier_profile_optimization`.

## Not established

- No trial produced a supported finding or a labelled inference. Denials walked through four rules in
  sequence: `grounding_rejected_some_assessments` (a defect, fixed), `cited_source_stale_or_conflicting`
  (a defect, fixed), and `insufficient_distinct_publishers` (correct behaviour). The remaining
  constraint is evidence supply, not a defect: a source must be cited, assessed as supporting,
  classified as survey/customer-experience/usage-measurement, fresh, and from a distinct publisher.
  Runs on this objective yield one such source, against a requirement of two. All four fresh hosts in
  the final run resolved to distinct non-empty publisher digests and none was role-excluded, so the
  independence machinery is working.
- Reddit is not recoverable within the adapter's constraints. Both `www.` and `old.` return a consent
  gate, not a JS shell: `<title>Welcome to Reddit`, post content absent. Passing it requires cookies,
  which the read-only contract forbids. This costs the whole `community_experience` source class,
  which is admissible for demand and would be the natural second publisher.
- The search backend rate-limited after roughly a dozen trials in a few hours, degrading from 11-13
  candidates per run to 3. It recovered after about two hours.

## Authority

This repair grants no provider, tool, source mutation, installation, promotion, or independent
authority. No evidence gate was weakened in substance: undated sources still cannot satisfy a
current-evidence claim, promotional sources still cannot establish demand, `requires_current_evidence`
is unchanged, two fresh independent publishers are still required, a contradicting citation still
refuses a finding, and model stance remains advisory and non-verifying.
