# Eidolon v2731.0.1 Research Admissibility and Runtime Contention Repair

Working source at start of session: **v2730.9.3**
Session date: **2026-09-09 / 2026-09-10**

## Conversation service contention repair

Desktop chat stopped responding: `/api/dashboard-chat/stream` accepted the TCP connection but never
sent response headers, so the shell timed out after 180 s with `acceptance=None`. Two independent
causes, both a long operation holding a process-global lock on a hot path.

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
- `api_server` counted memories with `len(load_memories())`, loading and JSON-parsing 2,467 payloads
  under `_INDEX_LOCK` to produce a number. Replaced with `count_memories()` (`SELECT COUNT(*)`).

Measured: `/api/status` 15.6 s to 3.6 s cold; four concurrent callers 26.6 s each to 5.7 s shared;
threads during a trial fell from a climb to 87 down to 21 to 5; trial wall time 1105 s to 180 s.

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
  scaled to fit.

Measured across trials on one objective: citation freshness went `unknown: 8` to `fresh: 5, stale: 2`;
`max_quality` 0.30 to 0.82; grounded assessments began returning `supports` rather than only `unclear`.

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
to the content-free projection: `model_assessment_status`, `grounded_assessment_count`,
`assessment_stance_counts`, `assessment_evidence_kind_counts`, `rejected_assessment_counts`,
`assessment_selector_diagnostics`, `assessment_admission_blockers`, `omitted_passage_source_count`,
`skipped_unreadable_host_count`, `readable_content_failure_count`. Counts and fixed reason codes only;
no claim text, quote, or URL.

The terminal-failure path built a minimal report that omitted these, leaving the runs most in need of
a post-mortem blind. It now carries them, initialised before collection so a run that dies early
cannot raise a second error while describing the first.

## Regression coverage

New suites, each verified to fail when its fix is reverted:

- `tools/v2730_9_5_research_source_metadata_tests.py` (39)
- `tools/v2730_9_6_legacy_dashboard_chat_import_tests.py` (16)
- `tools/v2730_9_7_observation_replacement_tests.py` (17)
- `tools/v2730_9_8_projection_cache_single_flight_tests.py` (14)
- `tools/v2730_9_9_passage_extraction_tests.py` (20, incl. 400 fuzz cases on the verbatim invariant)
- `tools/v2731_0_0_source_assessment_cap_tests.py` (9)
- `tools/v2731_0_1_unreadable_host_skip_tests.py` (16)

Pre-existing failures, confirmed unrelated by re-running against reverted code: `v2501_1`, `v2502_7`,
`v2503_0`, `v2503_2_quick_verifier_parallel_core`, `v2503_2_quick_verifier_profile_optimization`.

## Not established

- The assessment cap change is **unverified in production**. Collection failed before synthesis on
  every attempt after it landed, because the search backend began returning 3 candidates where
  earlier runs returned 11-13. This is consistent with rate limiting after roughly a dozen trials.
- No trial in this session produced a supported finding or a labelled inference. The nearest run
  reached two independent supporting survey sources and was still rejected by
  `model_assessed_conclusion`, which requires every citation in the finding to be eligible rather
  than admitting the eligible subset. Whether that rule is over-strict is undecided.
- Reddit is not recoverable within the adapter's constraints. Both `www.` and `old.` return a consent
  gate, not a JS shell: `<title>Welcome to Reddit`, post content absent. Passing it requires cookies,
  which the read-only contract forbids.
- The repository `.git` directory is empty, so none of this session's work was recoverable through
  version control.

## Authority

This repair grants no provider, tool, source mutation, installation, promotion, or independent
authority. No evidence gate was weakened: undated sources still cannot satisfy a current-evidence
claim, promotional sources still cannot establish demand, `requires_current_evidence` is unchanged,
and model stance remains advisory and non-verifying.
