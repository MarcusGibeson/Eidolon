# Private review runtime — infrastructure repair and verification

**Scope: infrastructure only.** This record is deliberately separate from the coworking-validation evidence. It
changes nothing about the qualified reviewer, its prompts, its thresholds or any review's findings, and it does not
re-open, rescore or reinterpret any earlier review.

Approved by Marcus, 2026-09-16. Implemented outside the frozen reviewer.

## The failure this repairs

Job `job_955f1d999e07f538` (G-INVAR) was confirmed from chat, ran 2h 05m detached, reached 19/19 parts, 100% package
coverage and 100 grounded observations, and then failed its mutation guard on 20 changes — every one of them ordinary
live application state (`cognition/`, `conversation_runtime/`, `conversation_policy_state/`, `conversation_sessions/`,
`chroma/`, `dashboard_chat/`). It is preserved as an incomplete infrastructure trial at the mutation-guard layer.

The cause was structural. `experiment_review.py:899` builds its guarded set as `[root, *protected_roots]`, where
`root` is the reviewer's runtime root, included unconditionally. The detached job pointed that root at the **live**
data directory, so every ordinary write during a multi-hour review counted as a mutation, while the adapter's whole
premise is that Eidolon stays usable while a review runs.

## What changed

Only `tools/run_review_job.py`, the detached job/runtime preparation layer.

`conscious_agent/experiment_review.py` is **byte-identical** to the qualified v2731.8 baseline:
`d158e253dd88febca8f22ed050beccde2724fd9b604138fa579c5201228b21c8`, the digest of the file as stored (a Windows
checkout rewrites line endings, so the working copy must be newline-normalised before hashing).

Each detached review now receives a private runtime root at
`<data>/research_review_runtimes/<job_id>/`, created for that job and written to by nothing else. The reviewer's
unconditional root guard therefore watches a directory that is genuinely quiescent. The artifact is copied into the
live review area **after** the guarded window closes, so listing, status and receipts are unchanged.

## What is guarded, before and after

| | live G-INVAR run | after this repair |
|---|---|---|
| Eidolon source tree | **not guarded at all** | **guarded** (`git` HEAD, porcelain status, `diff HEAD --binary`) |
| selected package | guarded | guarded, unchanged |
| private review runtime | did not exist | guarded; only the review's own output directory may appear |
| installed package area | inside the whole-data-dir guard | guarded explicitly |
| existing review artifacts | inside the whole-data-dir guard | guarded explicitly, one directory each |
| `local_queue.json` | guarded (would break concurrent queue work) | **not** guarded, deliberately |
| cognition, conversation, Chroma, dashboard chat | guarded — guaranteed false failure | not guarded |

Two details worth stating plainly:

- **Existing reviews are guarded one directory at a time**, not through the review area that contains them. The
  research queue keeps `local_queue.json` in that same directory and the adapter deliberately allows other
  deterministic queue work while a review runs. Guarding the parent would have re-created the same class of false
  failure this repair removes.
- **No live application state is copied into the private runtime.** The package stays where it was installed and is
  verified there by the reviewer's own loader and digests.

## Verification

`tools/v2731_11_0_private_review_runtime_tests.py` — 52 deterministic checks, no provider contact and no detached
process. They drive the real runner, the real private runtime and the real guard through a stub model, so the guard
alone decides each outcome. Each adversarial mutation is performed by the stub mid-review, strictly between the
guard's opening and closing snapshots.

| required property | result |
|---|---|
| live-runtime churn does not trip the guard | pass — cognition, conversation runtime/session/policy state, Chroma and dashboard chat all written mid-review, plus a real queue write |
| package mutation trips it | pass — reported as a `package:` change |
| source mutation trips it | pass — reported as a `source_tree:` change |
| protected review-artifact mutation trips it | pass — reported against that review's directory |
| private-runtime mutation outside review output is detected | pass — the stray file is named |
| existing review artifacts remain unchanged | pass — byte-compared after every adversarial run |
| reviewer baseline digest unchanged | pass — checked before the first run and after the last |
| chat invocation, detached execution, reconnection/status, receipt-only memory | pass — routing, detached start, re-discovery of a running job, and a receipt carrying ids and status but no conclusion |

Regression suites re-run and passing: `v2731_4_0` (conversational adapter, 46 checks), `v2731_10_0` (conversation
path routing, 149 checks), `v1175_0_2`, `v1176_0_2`, `v1177_0_2`, `v1178_0_2`, `v1259_3_5`, `v1489_trial2`,
`v2730_0`.

## Operating note

Because the source tree is now guarded, editing the repository while a detached review runs will trip the guard — as
it should. That is a real source mutation during a review, not a false positive.

## Live smoke test — passed

A bounded package, `G-SMOKE` (3 parts, 319 characters), was installed in the live area and reviewed through the
normal conversation surface (`POST /api/dashboard-chat`, which runs `run_conversation_turn`): "Review G-SMOKE
independently." then "confirm G-SMOKE". Ordinary chat continued while it ran.

| | |
|---|---|
| job | `job_e1e1ac1346cf487c`, package `G-SMOKE` |
| window | 2026-09-16T23:47:58Z → 2026-09-17T00:01:23Z (13.4 minutes) |
| **mutation guard** | **passed, 0 changes** |
| source tree guarded | true |
| guarded roots | the private runtime, `research_packages`, and the preserved `research_reviews/72a40f4dc8a09ae3` |
| coverage | 3/3 parts, 100%, 15 grounded observations |
| provider attempts | 11 |
| review | `b486a8364765f2e8`, published to the live review area |
| **live application files written during the guarded window** | **34** |

Those 34 writes are the same categories that failed the 2h G-INVAR run: `cognition/` (including
`cognitive_cycle_state.json` and `belief_revision.json`), `conversation_runtime/`, `conversation_sessions/`,
`conversation_policy_state/`, `dashboard_chat/`, `chat_actions/` and `chroma/chroma.sqlite3`. The review coexisted
with all of it and its guard reported nothing.

Ordinary conversation was answered normally throughout, including while the review was mid-run.

## A defect the smoke test exposed, and its repair

The confirmation started the review correctly, but the operator was told "I repeated my previous response instead of
responding to what you just said." Nothing false was asserted and nothing failed — the start simply was not reported.

The receipt sentence was templated, so two successful starts in one session differed only by package and job id:

    Started the independent read-only review of G-INVAR. It is running as job job_955f1d999e07f538. ...
    Started the independent read-only review of G-SMOKE.  It is running as job job_e1e1ac1346cf487c. ...

Measured against the conversation's own duplicate thresholds (jaccard 0.72 / sequence 0.86), that pair scores
**0.85 / 0.89**, so the second was replaced by the repetition fallback.

A started review now reports facts that differ per run — package, start time and job id — and the wording was chosen
by measuring candidates against the live guard rather than by eye:

    G-SMOKE: independent read-only review started 2026-09-16T23:47:58Z, job job_e1e1ac1346cf487c.

The same template for two different runs scores **0.50 / 0.75**. `tools/v2731_10_0_conversation_path_review_routing_tests.py`
now confirms two reviews end to end and asserts that the second receipt survives the guard unchanged.

Two further checks were tightened while proving it: the one-review-at-a-time rule made the old replay check pass
incidentally, so it now asserts the real guarantee — an executed proposal is refused by the runner before reaching
any executor, and is no longer waiting.
