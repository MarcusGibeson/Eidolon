# Eidolon research architecture — production migration specification

**Version 2.32, 2026-09-16. Status: the governing migration specification, approved by Marcus.**

**Added in 2.32** (Marcus, 2026-09-16; the first chat-started review, classified as an infrastructure trial):
- **The first review started from conversation ran end to end.** Job `job_955f1d999e07f538`, package G-INVAR, confirmed from the phone over Tailscale at 20:47:28Z, finished 22:52:02Z, 2h 05m, detached. Review `72a40f4dc8a09ae3`: **19/19 parts, 100% package coverage, 100 grounded observations**, and status `mutation_guard_failed`.
- **Classification (Marcus): an incomplete infrastructure trial at the mutation-guard layer**, preserved exactly as it stands. It is not rescored and its findings are not adopted. It stands as evidence that the conversational invocation path works, not as a valid review.
- **What the guard caught, exactly.** 20 changes, every one live application state under `…\AppData\Local\Eidolon\data`: `cognition/*.json` (13), `conversation_policy_state/` (2), `conversation_runtime/` (2), `chroma/chroma.sqlite3` (1), `conversation_sessions/` (1), `dashboard_chat/` (1). Nothing outside the data directory changed, and the **package was verified unchanged**. One flagged file is the conversation operation that started the review.
- **`protected.source_tree` was false for this run.** `tools/run_review_job.py` passes no `source_root`, so the source tree was never fingerprinted. The run therefore proves nothing about source changes in either direction; the absence of source findings is absence of evidence.
- **The conflict is structural, and it is the adapter's fault, not the reviewer's.** `experiment_review.py:899` builds `guarded_roots = [root, *protected_roots]`, including the runtime data directory unconditionally, so a caller cannot opt out and the `protected_roots=[]` the job runner passes changes nothing. The adapter's premise is that a review runs detached while Eidolon keeps being used, and Eidolon writes cognition, conversation and vector-store state continuously. Every adapter-launched review trips this guard. The historical reviews passed only because they ran from a harness with the application idle.
- **A scope proposal is recorded and NOT adopted**, pending Marcus's decision: give the job a private, quiescent runtime root and name the research-integrity subtrees explicitly (`research_packages/`, `research_reviews/`), while adding the source tree, which is unguarded today. That changes only `tools/run_review_job.py`, leaves `experiment_review.py` byte-identical at `d158e253…`, guards strictly more of what matters, and stops watching the operator's own application state. The alternative of narrowing the scope inside the reviewer would retire the frozen `v2731.8` baseline the coworking validation was accepted against.
- **No threshold was loosened, no gate removed, and no earlier review rescored.**

**Added in 2.31** (Marcus, 2026-09-16; a trailing period stacked a duplicate proposal and deadlocked confirmation):
- **The defect.** The proposal was keyed by a hash of the request text, so "Review G-INVAR independently." and "Review G-INVAR independently" saved two proposals for the same package. Both resolution branches then contradicted themselves: a bare confirmation counted two records and reported "More than one proposal is waiting: G-INVAR" while listing a single name, and a named confirmation matched two rows, failed its exactly-one test and reported "Nothing waiting matches that name. Waiting now: G-INVAR." The repeated answer was then squashed by the repetition guard. Confirmation could not be completed from chat at all.
- **A proposal is keyed by the package it targets**, not by the words used to ask, and a request for a package that already has a proposal waiting reuses it. Any phrasing that resolves to the same package is one proposal.
- **A named confirmation resolves to the newest matching proposal** instead of requiring exactly one, since several records for one target are one intent.
- **Ambiguity is about distinct targets**, not record count. Proposals that all name the same package resolve without asking; only genuinely different targets ask, and the answer names them.
- **Tests:** the routing suite reaches 149 checks, adding that three rephrasings reuse one proposal and never stack a second, that already-stacked duplicates resolve to the newest, that trailing punctuation resolves identically, and that two different targets are still ambiguous and still named.

**Added in 2.30** (Marcus, 2026-09-16; a confirmation in chat starts the review):
- **Authority decision, made explicitly by Marcus.** Until now the conversation surface proposed and never executed. It may now run a saved proposal that the operator has confirmed, and only from a fixed allowlist, `CONVERSATION_CONFIRMABLE_FUNCTIONS`: the independent review plus the low-risk research-session, history, comparison, export and release-summary functions the dashboard console already runs from conversation. Nothing else, at any risk level, is reachable. No shell command and no model endpoint is reachable.
- **The hazard that shaped the design.** `_history_candidates` re-grounds earlier user messages to resolve follow-ups, so execution inside grounding would restart a review on every later turn. Grounding therefore still executes nothing. `apply_confirmed_execution` runs on the live turn only, called from the two projection sites in `conversation_runtime`, and the suite asserts both call sites and that no supervised executor is called there.
- **A confirmation is never resolved by guessing.** `resolve_confirmation` answers "one", "ambiguous", "unknown" or "none". A bare "Confirm." runs the proposal only when exactly one is waiting; with several waiting it names them and asks which; a name that matches nothing waiting runs nothing. With no saved proposal at all, a confirmation is ordinary conversation.
- **Run-once is enforced by state, not by memory.** Running a proposal moves it out of `proposed`, so the same confirmation replayed finds nothing waiting, and `run_confirmed_action` refuses an action that is no longer waiting before reaching any executor. The adapter's own one-review-at-a-time rule still holds underneath.
- **The answer is the receipt.** A started review is reported with its package and job id, taken from the adapter's minimal operation receipt rather than from prose; a refusal says so and why. The projection records `confirmed_execution` and an `execution_state` of `started` or `refused`.
- **Known limitation:** only proposals persisted from chat can be confirmed there, and today that is review starts. The other allowlisted functions become confirmable in chat once their proposals are persisted from the conversation path, which changes proposal persistence for every capability and is deliberately left as its own step.
- **Tests:** the routing suite reaches 140 checks, adding the ambiguous and unknown confirmations running nothing, the named confirmation starting exactly one job on the live turn, the receipt carrying the job id, a replayed confirmation starting no second job, the allowlist refusing anything outside it, and the two live-turn call sites.

**Added in 2.29** (Marcus, 2026-09-16; confirmation resolves against a saved proposal, and a false execution claim is bound):
- **The defect.** Eidolon answered "Confirm." with "The read-only review of G-INVAR is now active. I am scanning the package structure...". Nothing had started: `research_jobs` did not exist in the runtime, and there was no job, no active job and no status. Two causes. "Confirm." classified as `conversation` and routed to `conversation_only`, so the start function was never invoked; and because that turn carried no action intent, the claim binder passed the model's prose through untouched. Both the adapter's proposal message and the 2.28 answer ended with "confirm to start it", an instruction with nothing behind it on the conversation surface.
- **Confirmation now resolves against a persisted proposal**, reusing the action store the dashboard console already uses.
  - A review request is saved as one governed proposal, keyed by the request text, so grounding the same turn again or replaying it from history never creates a second proposal. Grounding reports this as `review_proposal_persisted`.
  - `pending_review_action()` is the most recent saved review proposal still waiting to run. A bare confirmation counts only when one exists: with an empty action store, "Confirm." is ordinary conversation and grounds nothing.
  - Confirming produces an INFO control naming the package and the action id, and says what actually runs it: the Execute control on the Chat Actions surface. **Conversation still starts nothing**, which is the boundary this option was chosen to preserve.
- **A false execution claim is bound against the job record.** On a turn that is not an action request, a claim that a review is active, running or finished is answered from the adapter's own job sentence, or replaced with the fact that no review is running. Ordinary sentences that merely mention a review are untouched.
- **Known limitation:** starting a review remains a two-surface workflow. Chat proposes and confirms; the Execute control on `/chat-actions` runs it. Chat-initiated execution of a medium-risk action was considered and not taken.
- **Tests:** the routing suite reaches 124 checks, adding the saved proposal and its dedupe, that a confirmation with no saved proposal grounds nothing, that a confirmation resolves to the most recent waiting proposal and names it, that confirming creates no job, and that a fabricated execution claim is replaced while ordinary text is not.

**Added in 2.28** (Marcus, 2026-09-16; one paragraph for every review turn was squashed as a repeat):
- **The defect.** `conversation_runtime._bound_unverified_action_claim` replaces the whole reply with `bounded_action_explanation` for any turn whose intent is an action request without an execution receipt; it does not wait for an execution claim. Classifying review requests as action requests (2.26) therefore made every review turn the same paragraph, differing only in its final clause. The conversation's own repetition guard scored the second turn at 93% jaccard and 92% sequence, above its 72/86 duplicate thresholds, and replaced Marcus's "Review G-INVAR independently." with "I repeated my previous response instead of responding to what you just said."
- **The repair: one governed answer per request, each answering what was asked.**
  - listing: the installed packages, and how to ask for one;
  - start: the package the operator named, and that nothing has started until they confirm;
  - status: the job sentence the adapter already produces (ids, status, coverage), or that no review has been started.
- **Two bounded grounding fields** support this: `requested_review_target` (the package this request names, via the router's own extractor, so a path or a free-form instruction gives nothing) and `review_job_sentence` (the adapter's own status sentence, never a statement the review made). Each is attached only for the request that needs it.
- **Nothing about the boundary changed.** No answer claims a review ran, grounding stays `not_executed`, and starting a review still requires the operator's confirmation. Other capabilities keep their existing explanation verbatim.
- **Tests:** the routing suite reaches 99 checks, adding that each answer names what it should, that no answer matches the past-execution claim pattern, that the three answers are pairwise below the guard's own duplicate thresholds, and that the guard, run on the path where it applies, passes the start and status answers through unchanged.

**Added in 2.27** (Marcus, 2026-09-16; the conversation can name what is reviewable):
- **The eligible package ids reach the conversation.** `eligible_target_ids()` lists the installed packages that load under the reviewer's own rules: ids only, sorted, bounded at `MAX_CONVERSATION_TARGETS` (12), and never a path, a title, a document or a review's conclusions. An unreadable package area answers with nothing rather than raising into the conversation.
- **Grounding carries them only once the request has already matched the review capability**, as `available_review_targets`. Ordinary conversation receives no listing. The projection stays content free, and `bounded_action_explanation` now names what can be reviewed, so an unverified execution claim is replaced by the listing rather than by the capability's name alone.
- **This is a read-only directory scan, not an execution.** The conversation surface still executes nothing: `conversation_executor_call_count == 0` is unchanged, grounding remains `not_executed`, and starting a review still requires separate explicit operator approval.
- **Tests:** the routing suite grows to 88 checks, adding the listing the conversation receives, that a target is never a path, that ordinary conversation receives none, that the listing is bounded above its cap, and that an empty package area lists nothing.

**Added in 2.26** (Marcus, 2026-09-15; the conversational adapter reached from ordinary conversation):
- **The 2.25 adapter was unreachable from conversation.** It routed correctly on the command surface, but two independent defects on the conversation path meant neither of Marcus's live attempts reached it, and no app restart would have changed that.
  - **The supervised router was never consulted for a question.** `ground_action_intent` returns before `propose_chat_action` for every category outside `{action_request, ambiguous_request}`. "What experiments can you review?" classifies as `question`, so the listing route never ran and the reply was composed by the model alone.
  - **The review intents resolved to no capability.** `experiment_review` was in the registry, but `_INTENT_TO_CAPABILITY` had no rows for it, so even the action-shaped "Review G-INVAR independently." grounded `unmatched` and asked the operator to name a registered capability. This gap is general and pre-existing: `supervised_capabilities` grounds `unmatched` today for the same reason.
- **The repair is three changes in `natural_language_action_routing.py`, plus one public predicate in the router.** The frozen reviewer `d158e253…`, the adapter and the job runner are untouched.
  - `is_experiment_review_question` exposes the two question-shaped phrasings (what can be reviewed, how a review is going). The start phrasing is deliberately excluded: it already classifies as an action request, and its pattern is broad enough to also match ordinary conversation such as "can you review my thoughts on this".
  - One classifier branch, ordered after every existing branch, routes those two phrasings as `action_request`.
  - Three `_INTENT_TO_CAPABILITY` rows map `experiment_review_list`, `experiment_review_start` and `experiment_review_status` to `experiment_review`.
  - The two read-only review intents join `supervised_capabilities` as INFO-mode intents that are reachable in conversation rather than reported `unavailable`.
- **`experiment_review_unavailable` is deliberately not mapped.** Mapping it made ordinary conversation ("can you review my thoughts on this?", already an action request at HEAD through `_MODAL_ACTION`) ground on the review capability. An uninstalled package now grounds on no capability instead, which is the safer of the two wrong answers.
- **Conversation still executes nothing.** Grounding is a proposal: `execution_state` stays `not_executed`, no approval or authorization is inferred, and starting a review still requires separate explicit operator approval. The checkpoint contract `conversation_executor_call_count == 0` is unchanged.
- **Known limitation at 2.26, repaired in 2.27:** the projection carried the capability, `router_intent` and `router_mode`, but not the eligible package ids. Eidolon can therefore say that the request maps to her registered review capability, but cannot enumerate G-INVAR, G-CAND2-refx and G-REL-fixtures in conversation. Listing them would require adding bounded package ids to the grounding, which is a separate decision.
- **Known limitation, pre-existing:** `_EXPERIMENT_REVIEW_START` matches conversational objects ("review my thoughts on this"), which on the command surface produces a "not eligible" proposal. Unchanged from 2.25.
- **Tests:** `tools/v2731_10_0_conversation_path_review_routing_tests.py`, 70 deterministic checks. Every check fails against the unmodified modules.
- **Verification:** the 27 suites that reference the routing module were run before and after the change. Twenty-one passed in both runs, and the six failures are identical in both: `v1200_1_3`, `v1248_0_2`, `v1489_0001_0010`, `v2730_9_1`, `v1249_3_5` and `v1191_9`.
- **`v1191_9` is environmental, not a regression.** It fails in any working checkout that has the local `data/` directory, whose 183,062 entries the package privacy scan rejects; it passes 119/119 in a clean checkout of the same commit. Measured with and without this change in the same checkout, it reports the identical 110 of 119.

**Added in 2.25** (Marcus, 2026-09-15; the coworking validation phase accepted with qualifications, and the conversational review adapter):
- **The coworking validation phase is accepted with qualifications.** The frozen v2731.8 read-only reviewer showed sufficient cross-experiment generalization for supervised, non-authoritative coworking use. The external audit is recorded apart from Eidolon's blind reviews, in `review_audits/coworking_validation_phase_external_audit.json`.
- **Preserved limitations** (recorded, not repaired):
  - weak final-synthesis evidence utilization (final citations reached 54% of observations on G-INVAR, 37% on G-REL fixtures, while the architecture represented 100%);
  - missed aggregate experiment-level patterns;
  - semantic-identifier friction (30, 54 and 65 observations rejected across the three completed runs);
  - occasional final-schema compliance failure (the G-CAND2 refx final first half);
  - uneven quality of proposed discriminating experiments;
  - a stored-quote whitespace artifact at the 240-character cap (1 of 230 quotes in generalization 2).
- **Standing decisions:** no further historical experiment reviews, no Review 5, no tuning of the reviewer against G-INVAR, G-CAND2 or G-REL, and every existing review artifact preserved exactly. The reviewer's own suites (3.5 to 3.8) still pass unchanged, and `experiment_review.py` is still the baseline module `d158e253…`.
- **The conversational review adapter (v2731.9)** selects and invokes the already-authorized capability; it is not a second reviewer.
  - **Operator workflow:** ask which experiments can be reviewed (read-only listing); ask to review one by name (a proposal naming the package, its manifest digest and the estimated work); confirm (the review starts as a background job and returns a receipt); ask for status (running, completed or failed, with coverage and the mechanical checks).
  - **Routing:** three narrow phrasings reach the adapter. The router's conversation gate still governs everything else; it defers only to these three, so ordinary conversation stays conversation and `review <path>` still means the static file review.
  - **Eligibility:** only packages installed under `<runtime>/research_packages/` that load under the reviewer's own rules. A path, a glob, an unknown name or a package failing its digests never resolves.
  - **Confirmation:** the proposal starts nothing. While a review runs, a second request is refused at proposal time and never executes.
  - **Jobs:** one fixed argument vector in its own process group, so a disconnect does not end the review. Exactly one local-model review runs at a time, while listing, status and other queue kinds continue. A job whose process ended without a result, or which passes its six-hour bound, is recorded as failed instead of left running.
  - **Memory:** conversation memory holds only an operation receipt (ids, digests, status); a review's conclusions never enter it.
  - **Boundaries preserved:** mutation guards, package identity, blindness, provenance and authority flags are the reviewer's, untouched. The adapter queues only `independent_experiment_review`, exposes no shell and no model endpoint, and schedules nothing.
- **Tests:** `tools/v2731_4_0_conversational_review_adapter_tests.py`, 46 deterministic checks covering routing, eligibility, confirmation, job exclusivity, deterministic work continuing, completion through the real reviewer under a stub model, status and receipts carrying no conclusions, memory isolation, failure recovery (dead process and bound exceeded) and authority boundaries.
- **Two pre-existing suite failures are unchanged and not mine:** `v1104_1` (its expected capability list already omitted `bounded_web_research`) and `v1084_1` (conversation prompt guidance). Both fail identically against the pristine router at HEAD.

**Added in 2.24** (Marcus, 2026-09-15; the classification of generalization review 1, and review 2 authorized):
- **Generalization review 1 (`2ce3ae37b092bc10`, G-CAND2 refx): INCOMPLETE, FINAL_SCHEMA_INSTRUCTION_FAILURE.**
  - It is preserved exactly: `review.json` sha256 `56142ea7…`, `review.md` sha256 `1fc6d2a5…`; record `review_audits/gen1_2ce3ae37b092bc10_classification.json`.
  - Everything before the final synthesis passed: package 26/26, part and document synthesis complete, 0 silently dropped, guard, blindness and identity (20 of 22 checks).
  - The final first half returned only experiment_understanding and observations, twice, and omitted the other six required section keys.
- **The reviewer is not modified.**
- **Next:** generalization review 2 (G-REL fixtures) runs as registered in 2.23 (`review_gen2_registration.json`, sha256 `1f09e4d4…`) on the identical frozen reviewer (v2731.8, `2b08f01`). It runs once and is verified mechanically, then work stops for external audit whatever the outcome.

**Added in 2.23** (Marcus, 2026-09-15; the two generalization reviews, registered before either runs):
- **Why the scope is a split, not a whole experiment.** Packaged whole, under the G-INVAR rules, each candidate far exceeds the frozen reviewer's qualified capacity (104k characters, 19 parts):
  - G-TEMP: about 546k characters, 85 parts;
  - G-CAND2: about 534k, 83 parts;
  - G-REL: about 576k, 89 parts.

  A whole package would take about 10 hours and would very likely fail closed at the final input budget, which would test capacity, not generalization. G-TEMP's smallest split (controlled, about 246k) is also over. Marcus chose two whole pre-registered splits. Each package holds the frozen design of the whole experiment, plus every item and every call of its split, and its brief says so.
- **Generalization review 1: G-CAND2, refx split.**
  - Scope: 60 items, runs r1 and r2, 120 calls. It exercises over-escalation on irrelevant and same-topic passages.
  - Package `review_packages/G-CAND2-refx`: 7 documents, 26 parts, 141,822 characters; manifest `414b0f7c…`.
  - Registration `review_gen1_registration.json`, sha256 `8ed93c09e8c480c4b9b2f4659ade60f28e9c7799b49bbc4a8414cb4c7ef3f69d`.
  - Withheld: G-CAND's recorded outcome and the repair evidence drawn from it, the encoding demonstration, the real-split re-adjudication detail, the approval text, the interpretation, diagnostic and verdict pointers, results, notes, evidence and the specification.
  - The outputs table holds the validated model fields only; replies are verbatim in their own document.
- **Generalization review 2: G-REL, fixtures split.**
  - Scope: 67 authored items, runs r1 and r2, 134 calls. It exercises the semantics of six relations, binding and qualifiers.
  - Package `review_packages/G-REL-fixtures`: 7 documents, 27 parts, 145,265 characters; manifest `d3cbeac6…`.
  - Registration `review_gen2_registration.json`, sha256 `1f09e4d4a8f7f4d35d7285e7b83f8022c7a38c36cf267a9edae00ab8381861cf`.
  - Gold: the adjudicated gold frozen before any live call.
  - Withheld: the approval and stop-rule text, the gold changes to real items, any later experiment, results, notes, evidence and the specification.
  - One person's name in the kept rules text is replaced by "the operator", and the design document records the redaction. Attempt counts come from the preserved records, because no accounting file exists; nothing is manufactured.
- **Both packages** are built by scripts that refuse to build on any withheld marker, and both rebuild byte-identically.
- **Frozen for both reviews:**
  - the reviewer: v2731.8, commit `2b08f01`, module `d158e253…`, the Review 4 templates and limits;
  - the model: qwen3.8:27b, config `f398196f…`;
  - the four preserved reviews;
  - the blindness markers;
  - the generic runner and verifier (`review_run_general.py`, `review_verify_general.py`). These apply Review 4's checks, reading only the package, its part count and the preserved reviews from the registration.
- **Rules:**
  - Review 1 runs before review 2, and each runs once.
  - The reviewer does not change between them.
  - If review 1 is mechanically invalid, stop and report: no review 2, no repairs.
  - Results are preserved regardless of quality.
  - The known verdicts are never used as an answer key.
  - After both, stop for external semantic audit.

**Added in 2.22** (Marcus, 2026-09-15; the external audit of Review 4, the qualified baseline, and the generalization phase):
- **Review 4 (`7e8c69712db4e824`) classification: PASS.**
  - It is the first valid independent read-only self-review, with moderate semantic usefulness and identified reasoning limitations.
  - It is preserved exactly: `review.json` sha256 `0112ab05…`, `review.md` sha256 `5813b25b…`.
  - The external audit is recorded separately from Eidolon's blind review, in `review_audits/review4_7e8c69712db4e824_external_audit.json`.
- **What the audit found.**
  - **Strengths:**
    - she found genuine borderline instability (ST19, ST30);
    - she separated observation, possible harness failure, possible model failure, ambiguity, hypotheses, unknowns, what is not established, confidence and experiments;
    - her uncertainty handling was good, with medium confidence and inconsistency not taken as proof of defective reasoning.
  - **Missed:** she did not synthesize the aggregate pattern:
    - 12/12 controls were stable;
    - 8/10 borderline items were unstable;
    - every flip was between adjacent classifications, with no continuing↔event_only flip;
    - same-session repetition was deterministic, while cross-session classifications differed.

    That is, instability concentrates at semantic boundaries while clear controls stay stable.
  - **Reasoning and comprehension limitations** (recorded, never corrected in the review, and the reviewer is not tuned to remove them):
    - she sometimes treated the forms as identical prompts, when they deliberately varied only the serialization;
    - she over-weighted an incomplete scorer excerpt;
    - her ST19/ST30 temperature-zero proposal is weaker than comparing borderline and control items across fresh model loads with everything else held fixed.
  - **Compression limitation:** final citations reached 54 of 100 observations. This is a measured limitation that may explain the missed aggregate. It is not grounds for another G-INVAR iteration.
- **Capability decision:** Eidolon may continue as a non-authoritative, read-only local research coworker.
  - Her reviews are evidence and analysis for later operator or external audit.
  - Her conclusions may not modify source, experiment gold, policy, beliefs, memory, configuration, releases, architecture, verification rules or self-development authorization.
  - No authority expansion is approved.
- **G-INVAR infrastructure work is closed.** No Review 5. No rerun for a preferred conclusion. No tuning of prompts, hierarchy, evidence selection or verifier rules on the external interpretation.
- **Qualified baseline, frozen.** The reviewer used for every generalization review is exactly v2731.8:
  - commit `2b08f01`, module sha256 `d158e253…`;
  - the five templates, limits and rules registered in `review4_registration.json` (sha256 `807c701a…`).

  The mechanical checks stay those of `review4_verify.py`, generalized only in which package and registration they read. The reviewer does not change between generalization reviews unless a genuine infrastructure failure makes a review mechanically invalid; if that happens, stop and report instead of starting another repair campaign.
- **The generalization phase.** The question is whether the frozen architecture gives useful independent analysis on experiments it was not repaired around.
  - Two blind reviews, chosen from G-TEMP, G-CAND2 and G-REL.
  - Each is packaged neutrally under the existing rules. External interpretations and known conclusions are excluded, no missing historical artifact is manufactured, and package identity is frozen before review.
  - Both are registered before either runs. Each runs once on qwen3.8:27b with full provenance, all authority flags false and the mutation guards on, is verified mechanically, and is preserved whatever its quality. Then external semantic audit.
  - The known historical verdict is never used as a hidden answer key.
  - The audit asks:
    - patterns identified;
    - observation versus inference;
    - genuine failure modes;
    - disagreement and uncertainty preserved;
    - unsupported conclusions avoided;
    - competing explanations;
    - whether the experiments truly discriminate;
    - material evidence missed;
    - distortion from compression;
    - usefulness to Marcus without external models.
- **Operator usability (a design report only):** report the smallest governed adapter that lets Marcus ask which experiments can be reviewed, and ask for one to be reviewed. It may only select and invoke the already-authorized read-only review operation. No autonomous choice, scheduling, experiment changes, source changes, installed recommendations, belief, policy or configuration changes, or self-development.

**Added in 2.21** (Marcus, 2026-09-15; the audit of Review 3, and one final bounded iteration, Review 4, registered before it runs):
- **Review 3 (`14221600cc4998b1`) is an incomplete infrastructure trial at the synthesis/compression layer.**
  - It is preserved exactly: `review.json` sha256 `abfd941c…`, `review.md` sha256 `fe50e063…`; record `review_audits/review3_14221600cc4998b1_audit.json`.
  - It is recorded as progress: 19/19 package coverage, valid grounding, a working omission repair, and guard, authority, blindness, identity and prior-review preservation all held. The failure moved from evidence acquisition into synthesis.
  - The failure itself: summaries of small groups (8 and 6 observations) cited completely, while larger ones cited about 2 observations per statement against the roughly 3.5 needed. This is not treated as a reasoning failure.
- **Three incomplete reviews are enough evidence not to keep adding repairs.** Review 4 is the one final bounded infrastructure iteration, implemented in v2731.8.
- **Three-level hierarchy:**
  - The levels: grounded observations, then per-part synthesis (one unit per part, at most ceil(n/2) statements), then per-document synthesis (whole parts of one document, at most 12 inputs and 6,000 characters per unit; caps ceil(n/2), scaled by largest remainder to 37 slots), then the final synthesis.
  - Each statement cites its immediate inputs. Lineage back to the exact quotes is computed by code and recoverable mechanically.
  - Nothing is tuned to G-INVAR.
- **The system owns coverage, not the model's prose:**
  - After every stage, code records which inputs were cited, which were not, and which statements failed.
  - Every uncited input is carried forward explicitly to the next level, including from a failed optional unit.
  - The model is never asked again merely to enumerate more ids. The single repair retry covers provider, truncation, parse and schema failures only.
  - At the end, every observation is either in the lineage of a final entry or listed as evidence the final synthesis did not cite. Any silently dropped observation blocks completion.
- **Deterministic provenance, and the observation identifier boundary, enforced:**
  - The system reads each quote's record (line), attaches its metadata (experiment, prompt_form_equivalent, form, variant, condition, run, item, case, record) and the document id, and the model need not quote them.
  - An observation naming an identifier that neither its quotes nor this provenance establish is rejected.
  - Metadata values in an omitted suffix count as provenance; other omitted words still make the omission unsafe.
- **The narrow unit rule:** `7.3s` is supported by `7.3` only when the suffix is a recognized unit (the families s, ms, min, h, kb/mb/gb/tb and kib/mib/gib) and the value is identical. Changed values, other unit families, other item, form or run ids, versions and unrelated suffixes stay different. Deterministic positive and negative tests cover it.
- **Explicit bounds:**
  - Final input budget: 12,000 characters, derived from the context. On this model, synthesis prompts measured 3.62 to 4.53 characters per token (Review 3); the minimum less 15% gives 3.08.
  - Document statements are allocated within 9,000 characters. Carried inputs use the rest.
  - A final input over budget fails closed without discarding anything. The context window is unchanged.
  - Output limits, in tokens: 4,096 for observations, 1,024 for part synthesis, 2,048 for document synthesis, 3,072 for the final first half, 2,048 for the final second half.
- **Registration:** `review4_registration.json`, sha256 `807c701a803be72f88efcf51250911f0a9ca52a394caf049ba695a3cf97ca3f5`. It freezes:
  - the capability: commit `2b08f01`, v2731.8, module sha256 `d158e253…`;
  - the five template digests (the observation template is still byte-identical to Review 2's);
  - the limits, the hierarchy, and the coverage and provenance rules;
  - the package: manifest `a1f2d4a9…`, the same frozen G-INVAR evidence;
  - the model: qwen3.8:27b, config `f398196f…`;
  - the qualification list, the blindness list and the hard stop;
  - the runner and verifier digests.
- **Evidence for the implementation:**
  - The suites pass: 3.5 at 44/44, 3.6 at 38/38, 3.7 (omission) at 15/15, and 3.8 (provenance, boundary, units, hierarchy, carry-forward, bounds, context fit) at 52/52.
  - Eleven deliberately broken copies of the module each fail a named check, and the unmutated control passes.
- **Qualification before interpretation** (`review4_verify.py`):
  - 19/19 required package coverage;
  - valid grounding;
  - valid deterministic provenance;
  - no unsupported semantic identifiers;
  - complete architectural coverage through every synthesis level, with no silently dropped observation;
  - every final statement traceable to original evidence;
  - no unsupported synthesis claims;
  - no truncation, and no terminal required-stage failure;
  - the guard passed, and all authority flags false;
  - source, package, model, templates and limits matching the registration;
  - blindness verified by reproducing every prompt;
  - Reviews 1 to 3 unchanged.

  Only then may Review 4 be considered the first valid independent self-review.
- **Hard stop:** run Review 4 once, then stop for external audit whatever the outcome.
  - If it fails qualification, do not design Review 5. Reassess whether the architecture is worth its complexity against:
    - smaller operator-selected review scopes;
    - interactive or chunked coworking;
    - direct question-driven evidence inspection;
    - a simpler local research-assistant workflow.
  - The goal is a usable Eidolon coworker, not a benchmark-specific summarization engine.
  - No authority expansion. No end-to-end benchmark, G-FID, R1, belief revision or autonomous development.

**Added in 2.20** (Marcus, 2026-09-15; the audit of Review 2, and the two repairs registered before Review 3):
- **The sequence is recorded and not reinterpreted.**
  - Review 1 (`01c403147211b279`) is an incomplete infrastructure trial.
  - Review 2 (`987f0c0dc12f2705`) is a substantially improved but incomplete infrastructure trial. It is preserved exactly: `review.json` sha256 `6010d310…`, `review.md` sha256 `f705be49…`; audit record `review_audits/review2_987f0c0dc12f2705_audit.json`.
  - Review 3 is the first candidate valid independent Eidolon self-review.
  - Neither Review 1 nor Review 2 is a capability result.
- **Suffix omission (approved, implemented in v2731.7).**
  - **When it applies:** a single trailing `...` is an explicit omission marker only when the exact, uninterrupted text before it can be independently relocated within one source record. A record is one line of the source document.
  - **What counts as evidence:** only the exact prefix, never the ellipsis. The prefix must occur exactly once in the part and end on a word boundary.
  - **What stays rejected:**
    - ellipses inside the claimed span;
    - skipped internal text;
    - quotes assembled from several records;
    - prefixes that cannot be relocated uniquely;
    - any omission after which the statement relies on words found only in the omitted rest of the record (`omission_hides_attributed_content`).
  - **Representation:** the exact prefix, plus an `omission` record carrying the marker, the reply as returned and the omitted suffix.
  - **An ellipsis that is really in the source is matched exactly.**
  - **The rule is general,** with no special case for D5:2 or G-INVAR. Re-grounding Review 2's 24 rejections under it grounds 4 (3 in D5:2), and the 18 that skip internal text stay rejected.
- **Hierarchical synthesis (approved; registered here before Review 3).**
  - **The levels:** grounded observations feed bounded intermediate syntheses, which feed the final experiment synthesis. It compresses context with provenance; it does not compress conclusions.
  - **Units:** each unit is whole parts of one document, with at most 6,000 characters of observation lines.
  - **Every intermediate statement:**
    - cites 1 to 12 observation ids of its own unit;
    - carries one kind (finding, disagreement, uncertainty, minority, contradiction, unknown, unresolved_relationship), so disagreement, minority and contradiction are never merged into a consensus;
    - is at most 200 characters, within the unit's allocation.
  - **Every grounded observation of a unit must be cited by an accepted statement,** so a lone contradicting observation cannot be dropped silently. A unit that leaves one uncited fails.
  - **No intermediate statement may introduce evidence:** its identifiers and numbers (item and form ids, field names, years, versions) must occur in the observations it cites. This is a mechanical rule; judging meaning is left to the external audit.
  - **Every final entry cites intermediate ids,** and each retained entry records its lineage of observation ids. Experiments may trace through the hypotheses they distinguish. Final identifiers must occur in that lineage.
  - **Untraceable or unsupported statements are rejected and reported,** never repaired or truncated.
  - **Explicit, finite bounds:**
    - Final statement slots = 9,000 // 241 = 37. Each unit's cap is proportional to its observations, between 2 and 16. The final input therefore fits 9,000 characters by construction.
    - The first-half summary for the second half is capped at 3,500 characters.
    - Output limits: 2,048 tokens for intermediate syntheses, 3,072 for the final first half, 2,048 for the final second half.
    - The context window is not increased, and no observation is discarded to fit.
  - **Completion:** Review 3 is `complete` only if the entire required evidence path succeeds:
    - every required part is reviewed (an accepted reply with at least one grounded observation);
    - every required unit is accepted with all its observations cited;
    - the final input fits;
    - both final halves are accepted;
    - the guard passes.

    Otherwise it is `incomplete`, with every point of coverage loss named. Later stages are not requested.
  - **Retries:** at most one registered repair retry per stage, with the generic preface, for provider, truncation, parse, schema or citation-conformance failures. There is no semantic re-asking, and no individual semantic answer is rerun until a preferred result appears.
  - **Coverage is reported at every level:** package parts, observations cited by intermediate syntheses, intermediate units and statements delivered to the final level, and final citations (the intermediate statements cited, and the observations reached).
- **Prompts:** the frame and the observation prompt stay byte-identical to Review 2's. The intermediate and final templates are new and registered.
- **Registration:** `review3_registration.json`, sha256 `50da56a1020ef0449ea8e106b6f7000a6b4c4a439ba1ab3d1959786b3fdf685d`. It pins:
  - the capability: commit `987c3e0`, v2731.7, module sha256 `5fd02440…`;
  - the package: manifest `a1f2d4a9…`, byte-identical to its rebuild from the frozen evidence;
  - the model: qwen3.8:27b, config `f398196f…`;
  - the four template digests, and the limits;
  - the verification list, the blindness list and the stop rule;
  - the runner and verifier digests.
- **Evidence for the repairs:**
  - The suites pass: 3.5 at 44/44, 3.6 at 38/38, and 3.7 (omission versus stitching, lineage, citation completeness, supported claims, bounds, context fit) at 44/44.
  - Six deliberately broken copies of the module each fail a named check, and the unmutated control passes. The six disable: citation coverage, the hidden-content rule, identifier support, the one-record rule, final traceability and the stitched guard.
- **Before Review 3 is interpreted,** a mechanical verification (`review3_verify.py`) must show:
  - full required package coverage;
  - every accepted observation grounded, and every omission safe;
  - intermediate citations resolving to accepted observations, with every observation cited;
  - final citations resolving through intermediate records to original observations;
  - no unsupported intermediate or final claims;
  - no terminal required-stage failure, and no truncation;
  - the guard passed, and every authority flag false;
  - package, source, model and template identity;
  - blindness by reproduction: every prompt rebuilt from the templates, the package and the review's own outputs;
  - Reviews 1 and 2 unchanged.
- **Blindness:** Review 3 sees no ChatGPT, Claude or Astra interpretation, no conclusion of Review 1 or 2, and no expected BOUNDARY_INSTABILITY verdict. Infrastructure failures informed the repairs only.
- **Stop rule:** if Review 3 qualifies mechanically as complete, stop for external audit before changing anything else. No authority expansion, and no end-to-end benchmark, G-FID, R1, belief revision or other semantic experiment.

**Added in 2.19** (Marcus, 2026-09-15; the audit of the first coworking review, and repairs before a second):
- **Review 1 (`01c403147211b279`) is preserved exactly** and classified as a **failed, incomplete infrastructure trial**. It counts as the first external audit of the coworking capability, not as a test of Eidolon's independent G-INVAR analysis.
  - Its files are unchanged: `review.json` sha256 `e28c04ae…`, `review.md` sha256 `0e2e0a4d…`.
  - Its own status field still reads "complete". The audit record (`review_audits/review1_01c403147211b279_audit.json`) carries the classification instead.
- **The authority and safety boundary passed.** The mutation guard held with no changes, and the artifact stayed non-authoritative with every authority flag false. Protected state was unchanged, and nothing reached main or origin/main.
- **The semantic self-review is not interpretable.** Only 6 of 19 observation stages had an accepted reply (13 had none), and the design and the items with gold were never observed. *Correction:* this read "8 of 21" when first recorded, because the count included the two synthesis stages. It is neither scored nor characterized as evidence about Eidolon's ability.
- **Capability defects and required repairs:**
  - **Output limit.** The 700-token observation limit truncated every rejected reply. Raise it enough for complete structured responses, keep an explicit finite bound, and don't tune it to G-INVAR answers.
  - **Coverage fails closed.** A review is `complete` only when every required package part was reviewed, or was designated optional before the run. Otherwise it is `incomplete`, with machine-readable identification of every missing part or stage and the reason.
  - **Grounding representation, not grounding strictness.** An observation may carry several separately preserved exact quotations, each with its own document, record and segment provenance. Stitched quotations stay rejected.
  - **Adversarial tests:**
    - truncation exactly at the output limit;
    - a required observation stage permanently missing;
    - a repair retry that succeeds, and one that fails;
    - a multi-record comparison with several independently grounded quotes;
    - a stitched quote staying rejected;
    - synthesis unable to claim complete coverage when required stages are missing;
    - synthesis unable to cite rejected observations;
    - an absent required design or corpus section forcing incomplete.
- **Infrastructure repairs only.** The independent-review prompt semantics do not change on the basis of Review 1's answers.
- **Coverage is a first-class metric of every coworking review.** A polished synthesis produced from partial evidence is dangerous precisely because it can look complete.
- **Sequence:**
  1. repairs, with deterministic tests passing;
  2. rebuild the G-INVAR package from the frozen evidence and verify its content and digests are unchanged;
  3. run **Independent Review 2** fresh, blind to every human and assistant interpretation, to Review 1's conclusions and to the expected verdict;
  4. verify mechanically before interpreting: 100% required coverage, no terminal observation failures, no truncation, grounding integrity, the mutation guard, the authority flags, and source and package identity;
  5. stop for external audit.

  No authority expansion, and no end-to-end benchmark yet.

**Added in 2.18** (Marcus, 2026-09-15; the boundary policy is finalized as a design, and supervised coworking comes before the benchmark):
- **New order:**
  1. finalize the boundary uncertainty/escalation policy;
  2. build and verify a minimal, supervised, read-only coworking and self-review capability;
  3. use G-INVAR as Eidolon's first independent self-review;
  4. audit that review externally when premium-model access is available;
  5. design and run the fresh end-to-end governed-versus-simple comparison;
  6. only then decide which diagnostic distinctions deserve permanent runtime implementation.
- **Boundary policy, finalized as a design** (`policy_boundary_design.md`; unevaluated until fresh data). The dispositions:
  - **use:** stable enough for the specific permitted downstream purpose; not globally true, certain, belief-changing or permanently accepted.
  - **investigate:** provisional; may be surfaced as unsettled and may cause bounded, targeted evidence gathering when the consequence, budget, privacy, authority and source policy allow. Never an open-ended loop, never silently converted into a preferred label. If it stays unresolved, the uncertainty is preserved and the system continues without that proposition or abstains from that claim.
  - **abstain:** not used for the consequential purpose, and the disputed conclusion is not asserted; the evidence and reason are kept.

  No disposition changes a belief.
  - **Signals in the first version:** structural validity, unresolved as boundary, evidence anchoring and cross-layer consistency. An optional second assessment applies to high-consequence uses only, never universally.
  - **Unresolved means investigate,** never abstain automatically. It never authorizes suppression or belief revision on its own.
  - **Consequence table:**
    - suppression needs valid assessments, stable relevant layers, and second-form agreement when high-consequence; otherwise the candidate stays provisional;
    - unstable support is hedged, excluded or shown as uncertain;
    - belief-revision input needs the strongest requirements, and a single model classification never authorizes revision;
    - diagnostic use needs structural validity only.
  - **No threshold is derived from G-INVAR.** Its exploratory results only generate hypotheses.
- **Supervised coworking: `review_experiment`.**
  - **What it does:** given one explicitly selected, completed experiment package, Eidolon inspects it and writes a structured research review in a separate review area, without modifying the experiment or any operational state.
  - **What it is not:** a general autonomous research framework. It has no authority over source, experiment execution, policy, beliefs, memory, configuration, releases or installation.
  - **Inputs:** only material intentionally exposed in the package:
    - design and pre-registration;
    - frozen corpus;
    - raw model outputs;
    - scorer results;
    - evidence records;
    - notes;
    - selected prior evidence.

    No silent traversal of project history or private or runtime data.
  - **First self-review:** independent. It shows none of ChatGPT's, Claude's or Astra's interpretation, no expected findings and no desired conclusions.
  - **Required review sections:**
    - experiment understanding;
    - observations;
    - behaviours that passed and behaviours that failed;
    - failure clusters;
    - possible harness or measurement failures;
    - possible model or reasoning failures;
    - ambiguous cases;
    - competing hypotheses, with the evidence for and against each;
    - unknowns;
    - confidence or uncertainty;
    - the smallest discriminating experiments;
    - what the evidence does not establish.

    It separates observation from interpretation, records uncertainty instead of manufacturing conclusions, and proposes no source change merely to make a benchmark pass.
  - **Output authority:** a review is a non-authoritative research artifact. It never changes gold, verdicts, evidence, memories, beliefs, policies, patches, experiment authorization or release state. It is stored apart from registered evidence, with provenance: the experiment reviewed, model and runtime, timestamp, source digests, and no mutation authority.
  - **Mutation guard:** verification proves the operation leaves unchanged the source tree, registered experiment files, gold, evidence, configuration, belief state, memory state, release metadata and approval/rollback pointers. It relies on deterministic checks, not prompt instructions.
  - **External audit** of the first review, when premium access is available, checks:
    - factual fidelity and invented evidence;
    - fact versus hypothesis;
    - recognized uncertainty;
    - whether the proposed experiments truly discriminate;
    - restated prompt language;
    - whether erroneous harness assumptions were challenged.

    A plausible review is not proof of metacognitive capability.
- **A local research queue, chosen by the operator** (no autonomous scheduling or continuous execution).
  - **Ready (local, read-only):**
    - the independent G-INVAR self-review;
    - summarizing completed evidence;
    - clustering historical failures;
    - comparing stable and unstable examples;
    - generating candidate unlabeled test cases;
    - identifying unresolved architectural questions;
    - competing hypotheses;
    - bounded discriminating experiments.
  - **Requires external or operator review:**
    - authoritative gold;
    - registered-experiment semantics;
    - belief policy;
    - source code;
    - installing fixes;
    - releases;
    - runtime architecture;
    - verification policy;
    - self-development authority.
  - **Generated test cases** stay unlabeled or provisionally labelled, provenance-marked and outside gold until independently reviewed. The same model never both generates cases and establishes their authoritative correctness.
- **Why this capability exists.** It is not only a workaround for external-model limits. It tests a North-Star capability: can Eidolon inspect evidence about her own behaviour, identify uncertainty and failure patterns, form competing explanations and propose bounded tests under supervision? The intended eventual loop:

  ```
  experience/failure
  → inspect evidence
  → identify uncertainty
  → form competing hypotheses
  → propose bounded test
  → external/operator review
  → authorized experiment
  → observe result
  → update understanding
  ```

  It is not extended to autonomous source modification.
- **The fresh end-to-end comparison comes after the coworking setup and the independent G-INVAR review.**
  - **Arms:** the simpler governed baseline against the governed uncertainty/escalation path.
  - **Measures:** useful and correct answers, harmful unsupported answers, abstentions and unnecessary abstentions, missed useful answers, latency, model calls, retrieval cost, operator intervention, traceability and stability.
  - **Discipline:** the policy is frozen before the benchmark. G-CAND2's generalization is carried into this fresh blind set, and its earlier precision improvement keeps the revised-gold disclosure.
- **Still deferred:** reload experiments, verb-specific patches, prompt tuning for borderline labels, G-FID, R1, belief revision, optimization, batching and autonomous self-development. The corrected G-INVAR scorer stays separate from the frozen one, and runtime reports keep separate attempt accounting. Main and origin/main are untouched.

**Added in 2.17** (Marcus, 2026-09-15, with Astra's review; the G-INVAR outcome and a change of direction):
- **G-INVAR: BOUNDARY_INSTABILITY.** This is accepted unchanged under `prereg_invar.json`.
  - **Run:** all 132 calls completed with no failed attempts, and the locked files were unchanged.
  - **Invariance:** 12 of 12 clear controls kept one classification across all five meaning-equivalent prompt forms. 8 of 10 borderline items changed (SS04, ST01, ST10, ST19, ST30, ST61, T19, T33); only ST18 and ST60 held.
  - **Every change was between adjacent labels:** event_only ↔ unresolved, or continuing ↔ unresolved. There was no direct continuing ↔ event_only flip.
  - **Same-prompt determinism:** a same-session repeat of V0 matched on all 22 items.
  - **The SS04/ST01/ST61 pattern was BOUNCING.** The "replaced" behaviour is boundary instability, not a stable misunderstanding.
  - **ST18** was unresolved under every form, a stable disagreement with its gold (event_only), to be settled separately.
- **Cross-session variation is observed; its cause is unproven.** Byte-identical rendered V0/V1 prompts, on the same model, runtime configuration, Ollama version and CPU/GPU split, gave five different answers between sessions at temperature 0:
  - SS04, ST61 and T33 under V0;
  - ST19 and T19 under V1.

  Within each session, repeats were exact. Reload-dependent numerics are a reasonable hypothesis, not a finding. No reload experiment is run now, because the architectural conclusion would not change: a consequential belief system cannot depend on which side of a numerical knife-edge one inference happens to land.
- **Correction to 2.16:** 2.16 implied that all seven G-STATE2 answer changes were caused by the serialization wording. They were confounded by cross-session variation. T19, for example, also flipped under the identical G-STATE prompt between sessions, and T33, ST19 and ST61 are among the cross-session flips. Borderline answers move under two kinds of irrelevant perturbation, prompt wording and session, while the controls hold under both.
- **Scorer defect (Astra, 2026-09-15), discovered after the run:**
  - **The defect:** the registered G-INVAR scorer set aside an item with a missing classification before checking instability. So a demonstrated flip, such as unresolved → event_only → missing, could be hidden and reported as INVARIANT. Its pattern detector also counted a missing answer as a distinct value, so a missing-only case could read as BOUNCING. Both were reproduced synthetically.
  - **Why the verdict stands:** G-INVAR's BOUNDARY_INSTABILITY does not depend on the defect, because every compared item produced a classification under every form.
  - **The corrected scorer** (`invar_score_v2.py`) was run post hoc on the immutable evidence as a clearly marked non-registered shadow analysis. It gave BOUNDARY_INSTABILITY, identical on every field. The frozen scorer and verdict are preserved, and the corrected scorer is the one to reuse.
- **Runtime reporting is corrected.** Reports now separate provider attempts, failed attempts and timeouts, unparseable replies, retries, recovered items and terminally failed items (`runtime_accounting.py`). G-STATE2 had 179 provider attempts, 5 failed attempts (all timeouts), 3 retries, 1 recovered item and 2 terminally failed items. 2.16's "two failed requests" conflated failed attempts with failed items. Every other gate had one attempt per item and none failed.
- **Direction change: stop creating a production classifier for every distinction.** G-CAND, G-TEMP, G-STATE and G-INVAR have done their job as diagnostics: they showed how the semantic system fails.
  - The next design is a **boundary uncertainty/escalation policy**. It decides when a proposition relationship is stable enough to use, uncertain enough to investigate, or unsafe enough to abstain from. Preferably it is a decision policy over existing evidence assessments, not another mandatory model call.
  - **The principle:** when a semantic judgement is close enough to the boundary that equivalent assessments disagree, the correct output is not an arbitrarily selected label but uncertainty requiring more evidence, or abstention. Such uncertainty becomes a legitimate outcome.
  - **After the policy,** a small fresh end-to-end comparison of the governed pipeline against a simpler baseline, on a completely fresh blind set, measuring together:
    - useful and correct answers;
    - harmful unsupported claims;
    - abstentions and missed useful answers;
    - latency and model calls;
    - operator intervention;
    - evidence traceability.

    Only then is it decided which diagnostic distinctions deserve permanent runtime machinery.
  - The G-CAND2 generalization question (its real-data precision partly reflected revised gold) is answered by that fresh blind set, not by rerunning G-CAND2 alone.
- **Not now:**
  - no reload experiment;
  - no patching of individual verbs or prompts;
  - no G-FID, R1, belief revision, optimization or batching.
- **Status:** installed Eidolon is unchanged. The committed updates since `03aa99a` document isolated experiments, not product improvements. The next milestone should connect these findings to observable task improvement. Main and origin/main are untouched.

**Added in 2.16** (Marcus, 2026-09-14; the G-STATE2 outcome and the next gate):
- **G-STATE2: UNSAFE_EVENT_ONLY.** This is accepted exactly as scored under `prereg_state2.json`. The frozen experiment included ST40, so unsafe event-only was 3 of 45 = 0.067 in both runs, above the ≤ 0.05 bar.
  - The unsafe items are ST01 and ST61 (bare "replaced in YEAR" read as event-only) and ST40.
  - **Descriptively only, not an amendment:** without ST40 the rate would be 2/45 = 0.044. Preregistration keeps its meaning only if a verdict is not re-cut when the result is inconvenient.
- **The null-cue binding defect is closed as repaired.** Every other rule passed:
  - binding: 0.986 and 0.958, anchors 1.00;
  - witnesses 4/4 exact and controls 12/12 exact, in both runs;
  - continuing accuracy 0.952 and 0.905;
  - event-only accuracy 0.926 and 0.889;
  - unresolved precision 0.913 and recall 0.875;
  - minimal pairs 0.875 and 0.812;
  - identity, candidate and belief non-mutation;
  - repeatability 0.972 and 1.00.

  G-STATE's registered failure came primarily from the null defect.
- **Prompt sensitivity is now the larger concern.** A serialization-only instruction changed 7 of 88 answers per run, identically in both runs: about 8% of the corpus moved because the prompt said how to serialize absence.
  - Four moved toward gold: T19, T33, ST10 and ST19.
  - Three moved away: ST01 and ST61 (to unsafe event-only) and ST30.
  - The T19/T33 improvement is therefore not credited as stable semantic learning. Equally, ST01/ST61 do not show that the semantic architecture is wrong. These borderline classifications are not invariant to semantically irrelevant prompt changes.
- **Other observations, recorded without changes:**
  - ST18 and ST30 were read as unresolved instead of event-only.
  - An Ollama stall in the second controlled run made ST28 and ST29 fail on timeouts (scored fail-safe, not rerun).
  - **ST60, an observed contract limitation, left open.** "The bridge remains closed" is a continuing state with no stated transition time, and it was rejected for a `null` `transition_time`. A nullable transition time may eventually be right, because the question is whether a continuing state exists, not whether its start can be identified. Changing it now would be another schema decision straight after G-STATE2, so it waits until the stability test shows whether this representation is kept.
- **No special "replaced" rule.** SS04 was read correctly as unresolved while ST01 and ST61 were read as event-only under the same broad construction. A rule such as "replaced ⇒ unresolved" would patch examples instead of finding the decision boundary.
- **ST40 is repaired only in a successor corpus.** In G-STATE and G-STATE2, ST40 had an incorrect cited segment. The historical results stay unchanged and immutable, and the corrected ST40 applies only from subsequent experiments. This is experimental hygiene, not result manipulation.
- **Next gate: G-INVAR (semantic invariance).** A small pre-registered stability gate over the borderline family (ST01, ST61, SS04, T19, T33, ST10, ST19, ST30, ST18, ST60) plus clear continuing, event-only and unresolved controls.
  - **Its question:** does the classification remain the same when only semantically irrelevant serialization or schema wording changes?
  - **What it measures:** per-item classification invariance across meaning-equivalent prompt forms, with the output schema identical, not just accuracy.
  - **How to read it:** if ST01 and ST61 bounce between event-only and unresolved, they are boundary-unstable, which argues for representing uncertainty and escalation rather than searching for a wording that makes the model pick the preferred label. If SS04 stays unresolved while ST01 and ST61 stay event-only across equivalent prompts, that is a genuine semantic inconsistency worth isolating.
- **The question has shifted.** It is no longer simply whether qwen3.8:27b can understand the distinction. It is whether it can hold the same interpretation of an ambiguous proposition when irrelevant wording around the task changes. For a system that will eventually be allowed to reconsider its own beliefs, that is the more important question.
- No G-FID, R1, belief revision, optimization or batching. Main and origin/main are untouched.

**Added in 2.15** (Marcus, 2026-09-14; the G-STATE outcome):
- **G-STATE: BINDING_FAILURE, with WITNESS_FAILURE, CONTROL_REGRESSION, MISCLASSIFICATION and PAIR_INSENSITIVITY under the frozen scorer.** This is accepted exactly as scored under `prereg_state.json`.
  - **Run:** all 176 calls completed with zero request failures, and the locked files were unchanged. The assessments were byte-identical across both runs.
  - **Passed:**
    - event-only accuracy 0.852;
    - unresolved precision 0.909 and recall 0.833;
    - unsafe event-only 0.044;
    - identity, candidate non-mutation and belief non-mutation;
    - repeatability 1.00.
  - **The authority boundary held.** Every rejected assessment was fail-safe.
- **Interpretation: the registered failure is dominated by a harness defect, and it stays failed.** G-STATE formally failed its registered scorer primarily because of a binding-contract defect in the experimental harness. Optional cue absence expressed as JSON `null` was rejected, although the prompt did not require the literal string "none".
  - Rejected assessments feed downstream scoring. So the witness, control, continuing-accuracy and pair-sensitivity failures cannot be interpreted independently from the registered metrics.
  - Descriptive inspection of the immutable raw outputs showed that, before validator rejection, the model's relation matched frozen gold on 68 of 72 controlled items and 14 of 16 anchors:
    - all 21 continuing controlled items were answered continuing;
    - all five RM historical controls stayed event-only;
    - SS04 and T46 followed the corrected conservative semantics;
    - explicit persistence cues were recognised correctly.
  - This descriptive result does not amend the registered verdict. A binding-only successor experiment is required.
  - This is not evidence that G-STATE's semantic idea failed.
- **Six real semantic deviations**, all among structurally valid assessments and identical in both runs:
  - **T19:** unresolved instead of continuing ("From 1 January 2025, the speed limit on Mill Road is 30 km/h").
  - **T33:** unresolved instead of continuing ("Effective 1 March 2025, the monthly fee is £10").
  - **ST10:** unresolved instead of event-only.
  - **ST18:** unresolved instead of event-only.
  - **ST19:** event-only where the frozen gold specifies unresolved.
  - **ST40:** unsafe event-only, with the known corpus construction caveat below.

  "From" and "Effective" establish the beginning of an operative state, and the passage presents the new value as applicable from that point onward. So T19 and T33 stay continuing in the frozen gold, unchanged, as witnesses for the remaining semantic weakness.
- **ST40 carries a known cited-segment construction error.** It was given the default cited segment (the adult removal), while its relevant state is in segment 2. It is kept unchanged in the binding-only rerun for experimental parity, but it must not be used by itself to justify a future semantic architecture change. Whether to repair or remove it is decided after G-STATE2, in a separately versioned corpus-cleanup step.
- **Next: G-STATE2, a strict binding-only rerun** (the G-CAND2 pattern).
  - **The only change:** the optional cue fields become `persistence_cue: string | null` and `end_cue: string | null`. The prompt says that an absent cue is returned as JSON `null`, and the validator accepts exactly that. It does not turn absence into a magic word.
  - **Frozen:** gold, corpus, definitions, labels, witnesses, controls, thresholds, failure order, prompt semantics other than the serialization instruction, runtime, temperature, token ceiling, repair behaviour, model, no batching, and scoring semantics.
  - **Its question:** did the registered G-STATE failure come primarily from the null-binding defect, and what semantic failures remain once the defect is removed?
  - **The model calls are rerun under a new pre-registration.** Re-scoring the old outputs is descriptive only and cannot replace the run.
- No G-FID, R1, belief revision, optimization, batching or other semantic repair. Main and origin/main are untouched.

**Added in 2.14** (Marcus, 2026-09-14; the G-TEMP outcome and the next gate):
- **G-TEMP: BINDING_FAILURE, with FALSE_SUPPRESSION and UNRESOLVED_RECALL_FAILURE also failing.** This is accepted exactly as scored under `prereg_temp.json` with `temp_gold.json`. Every decision was identical in both runs.
  - **Run:** 364 of 364 calls completed with zero request failures, and the locked files were unchanged.
  - **Passed:**
    - RM01–RM05: 5 of 5 correctly suppressed in both runs;
    - every metadata-variant group invariant, so publication and update metadata did not leak into proposition-time reasoning;
    - overlapping accuracy: controlled 0.897, candidates 0.958;
    - non-overlapping accuracy: 0.886 and 0.857;
    - unresolved precision 0.900;
    - claim identity, candidate non-mutation and belief non-mutation;
    - repeatability 1.00.
  - **The authority boundary held.** Every assessment was provisional with no belief effect, and no invalid assessment suppressed.
  - **Failed:**
    - **False suppression of genuine contradictions:** 6 items, in both runs.
    - **Binding:** failed narrowly on the controlled corpus, 0.947 against 0.95. The candidate corpus scored 1.00.
    - **Unresolved recall:** 0.562.
- **G-TEMP handled the historical-state failure family that motivated RM01–RM05.** It exposed a distinct temporal-semantic failure: dated change events with continuing resultant states. In four of the six false suppressions the model dated the change and treated the state produced by it, which runs to now, as existing only at the event date:
  - SS04: "version 3 replaced version 2 as the official version in 2023";
  - SS05 and T54: "retired on 1 July 2025 and is no longer supported";
  - T46: "an amendment in 2022 removed the helmet requirement".

  Related wording passed (SS01, SS03, SS06, SS09, T19, T33, T50). The other two false suppressions are separate families and are kept out of the next gate: T10 split one 2019 event by month, and RC04 treated a recurring holiday period as disjoint.
- **Binding is not relaxed yet.** All four rejected assessments named "tense" as the basis where the validator requires dated or relative support for a suppression.
  - Two of the rejections blocked unsafe suppressions (T07, T09).
  - Two blocked otherwise-correct suppressions involving "formerly" (T26, T27).

  The mismatch is therefore not shown to be a harmless formatting problem. The suppression requirements and fail-closed behaviour stay unchanged, and the accepted basis values are not broadened merely to raise binding.
- **Next gate: G-STATE (continuing resultant state).** Its one question: does a passage describe only an event at time T, or does that event establish a resulting state that continues after T?
  - It separates event time (when a transition happened) from resulting-state validity (the interval during which the state the transition created stays applicable).
  - It does not infer indefinite persistence from every past-tense event: "sales fell in 2022" is a historical event only.
  - It is a provisional evidence-analysis layer with no belief authority. It changes no candidate, temporal assessment, evidence state or belief state.
  - A `continuing` result may keep G-TEMP from suppressing a candidate merely because the transition is dated in the past. It never proves semantic contradiction, current authority, factual truth or eligibility for belief revision, and a later superseding event can end the continuing state.
  - Required witnesses: SS04, SS05, T54 and T46. Passing controls: SS01, SS03, SS06, SS09, T19, T33 and T50. It must not trade those controls for the witnesses.
  - Kept outside G-STATE: T10's within-event month split, RC04's recurring holiday period, general unresolved-recall repair, same-topic falsehoods, DNS directionality, navigation text and broader scope compatibility.
  - It is designed and pre-registered for review before any live call. No G-FID, R1, belief revision, optimization or batching.
- Main and origin/main are untouched.

**Added in 2.13** (Marcus, 2026-09-14; the G-CAND2 outcome and the next gate):
- **G-CAND2: OVER_ESCALATION.** This is accepted exactly as scored under `prereg_cand2.json`, with `cand2_gold.json` as the only gold for the verdict.
  - **Run:** all 564 calls completed, with zero request failures.
  - **Passed:**
    - binding on every scored run: adversarial 0.974, fixtures 1.00, real 0.978, real repeat 1.00;
    - claim identity 1.00;
    - belief non-mutation 1.00;
    - scope preservation 1.00;
    - repeatability 1.00;
    - recall: 1.00 / 1.00 / 0.938;
    - the supersession gate in both runs.
  - **Failed:** adversarial false escalation (0.241, in both runs) and real precision (0.600). The registered verdict is OVER_ESCALATION.
  - **Binding improvement is attributable to the schema/prompt repair.** Binding does not depend on gold, and no reply put a recency value in a scope field.
  - **Decomposition.** The old-gold diagnostic is descriptive only and did not affect the verdict. Flags agreed with G-CAND on 559 of 564 items.

    | Real passages | G-CAND (old gold) | G-CAND2 (old gold) | G-CAND2 (revised gold) |
    |---|---|---|---|
    | False escalation | 0.109 | 0.114 (model effect +0.004) | 0.081 (gold effect −0.032) |
    | Precision | 0.432 | 0.422 | 0.600 |

    The revised gold improved the registered real score, while model-only behaviour did not improve materially. Of the 8 relabelled items, 7 changed only because their label moved, and 1 was a new flag.
  - **Adjudication-bias disclosure:** the adjudicator had seen the G-CAND outputs, and 7 of the 8 changed labels are on items G-CAND flagged. Every changed item keeps its original, independent and final label with a written reason.
  - **No downstream belief-revision authority was granted.** Every candidate stayed provisional, with no belief effect.
- **The binding issue is closed for this stage.** The candidate schema is not changed again unless a later experiment produces a new structural failure.
- **Over-escalation is addressed one semantic class at a time, never with a combined fix.** These observed classes are preserved separately for later gates:
  1. Historical or otherwise non-overlapping states escalated against current claims. This is next, in G-TEMP.
  2. Same-topic false statements that do not contradict the target proposition.
  3. DNS directionality and partial-support interpretation.
  4. Navigation or non-content text.
  5. Exceptions, narrower ranges and general scope compatibility.
- **Next gate: G-TEMP (temporal compatibility).**
  - **Purpose:** determine whether a provisional contradiction candidate refers to propositions whose temporal scopes overlap enough for a contradiction to exist.
  - **Position:** it sits downstream of candidate generation and upstream of any belief-revision authority. It modifies no belief confidence, status, supporter or refuter state, policy verdict, active belief or lineage.
  - **Results:**
    - `overlapping`: temporal scope does not remove the possible contradiction. This is not proof of a contradiction.
    - `non_overlapping`: both propositions can be true in different periods. In this experimental layer it suppresses escalation.
    - `unresolved`: the evidence cannot determine it. The candidate remains provisional and still requires investigation.
  - **Publication, crawl and page-updated dates are not proposition time** and never by themselves establish temporal overlap. G-TEMP tests this explicitly.
  - **Safety:** RM01–RM05 are required adversarial witnesses. Falsely suppressing a genuine overlapping contradiction is the highest-safety error and gets a strict registered bar.
  - **Process:** designed and pre-registered for review before any live call. No G-FID, R1, belief revision, optimization or batching.
- **Likely future decomposition.** This is a design direction, not authorization:

  ```
  candidate contradiction
  → temporal compatibility
  → scope compatibility
  → content/admissibility quality
  → proposition fidelity / semantic conflict
  → authority, independence and corroboration
  → accumulated evidence state
  → belief-revision decision
  ```

- Main and origin/main are untouched.

**Added in 2.12** (Marcus, 2026-09-14; the G-CAND outcome):
- **G-CAND: BINDING_FAILURE, with OVER_ESCALATION also failing.** This is accepted exactly as scored under `prereg_cand.json`. The completed run is not rescored under any repaired schema or revised gold.
  - **Run:** all 564 calls completed with zero request failures, and no repair retry was needed.
  - **Passed:**
    - claim identity 1.00;
    - belief non-mutation 1.00;
    - scope preservation 1.00;
    - repeatability 1.00, with every flag decision identical across repeats;
    - main recall: adversarial 1.00, fixtures 1.00, real 0.938;
    - the separate supersession gate in both runs: all 6 must-flag cases detected with recency carried, and neither distractor flagged.
  - **Failed:**
    - binding validity: adversarial 0.946, fixtures 0.765, real 0.341, real repeat 0.667;
    - false escalation: adversarial 0.241, real 0.109;
    - therefore precision on the real corpus: 0.432.

    Every one of the 43 structurally rejected candidates carries the same vocabulary collision: the model wrote the recency value "unknown" in the scope time field. 41 were rejected for that alone; 2 also cited a target clause not found in the claim. (Correction: this line first said "43 of the 45 structural rejections", which counted reason codes as rejections.)
  - **Disclosed pre-run prompt edit:** the approved draft never named the recency tokens (`passage_later`, `passage_earlier`), so no reply could carry them. The contract suite found this before any call, and the tokens were named before registration, together with Marcus's `resolution_needed` field.
  - **Correction:** an interim status note during the run called RT01–RT06 planted contradictions the detector missed. They are must-not-flag items, so leaving them unflagged was correct.
  - No downstream work was started.
- **The authority boundary held.** False candidates caused investigation proposals only, never a belief-state effect. Every candidate was provisional with `belief_effects: "none"`, and the belief sentinel was byte-identical after all 564 items.
- **Architectural reading.** G-CAND did not demonstrate a production-ready candidate detector. It did demonstrate:
  - high contradiction recall;
  - no belief mutation;
  - exact identity preservation;
  - deterministic repeatability;
  - successful supersession detection;
  - strong scope preservation.

  The dominant remaining failure is excessive escalation, not unauthorized belief revision. The distinction matters because the detector is intentionally provisional.
- **Over-escalation classes, kept separate.** No semantic fix is designed yet.
  1. Historical or past-state evidence escalated against a current claim.
  2. Same-topic false statements escalated, though they are not necessarily proposition-level conflicts.
  3. Partial-support and directionality cases.
  4. Navigation or non-content text.
- **Before any G-CAND rerun:**
  - **A. A binding-only schema repair:** distinct, non-overlapping vocabularies for the scope-time relationship and for passage recency.
    - Unchanged: candidate semantics, the contradiction definitions, scope semantics, the corpus, thresholds, runtime, one pair per call, uncertainty behaviour and supersession semantics.
    - Contract tests must prove that neither vocabulary is accepted in the other's field.
    - The recorded failed outputs must be shown encodable in the repaired representation without relaxing admission.
  - **B. A re-adjudication of the real candidate gold:**
    - Scope: every real item mapped from G-REL `partial_support`, plus every other real item where the result exposed a plausible mismatch between the old relation gold and candidate semantics.
    - A fresh blind labeller re-labels them under the frozen definitions, and only disagreements are adjudicated.
    - The gold is frozen and hashed before any rerun. Labels are never revised to improve a score.
  - Then work stops for review before any new live call. No G-FID, belief revision, R1, batching or optimization.
- Main and origin/main are untouched.

**Added in 2.11** (Marcus, 2026-09-14): **architectural requirements for future governed belief revision.** These are requirements only. Nothing here is implemented or wired, and none of it authorizes implementation.
- **Destination pipeline:**

  ```
  new observation
  → proposition extraction
  → support and challenge candidate generation
  → authoritative evidence binding
  → structural validation
  → scope and qualifier evaluation
  → authority, currentness and independence
  → corroboration
  → accumulated BeliefEvidenceState
  → claim-type-specific RevisionPolicy
  → BeliefRevisionDecision
  → durable BeliefLineage
  → later outcome evaluation
  → eventually, supervised learning about revision-policy performance
  ```

- **The challenge path:**

  ```
  ContradictionCandidate
  → structural validation
  → scope and qualifier assessment
  → source authority and currentness
  → source independence
  → corroboration (searching for both supporting and conflicting evidence)
  → optional independent semantic assessment
  → evidence aggregation
  → BeliefRevisionDecision
  ```

  A ContradictionCandidate is provisional. Creating it never changes:
  - belief confidence or status;
  - the evidence-policy verdict;
  - supporter or refuter state;
  - belief lineage;
  - active-belief selection.

  It is an observation and a request for investigation, not a belief event.
- **Structural validation proves only structure:** claim identity, evidence membership, required fields, and no evidence outside the authoritative OptionSet or a validated descendant path. It never implies semantic contradiction.
- **Decision vocabulary**, at least: retain, weaken, dispute, suspend, revise, supersede.
- **Principles:**
  1. **Evidence quantity is not enough.** Revision weighs:
     - the proposition relationship and scope compatibility;
     - source authority for the claim type, independence and currentness;
     - evidence quality;
     - corroboration;
     - unresolved counterevidence.

     It never reduces to counting sources.
  2. **Claim type matters.** Separate policies are planned for empirical, definitional or classificatory, predictive, procedural, autobiographical and preference claims, and normative claims if they are ever represented. There is no universal threshold.
  3. **Supersession is not ordinary contradiction.** Explicit supersession events represent an authoritative classification, a governing specification, an API contract, a law or a current standard replacing an earlier one.
  4. **Lineage is preserved, never overwritten:** the old belief, the evidence state at the time, the challenge, the revision decision, the new belief, the reason, and the triggering evidence or policy.
  5. **Unresolved states are allowed.** "No longer confident in A, not yet able to accept B" is represented as disputed, suspended or unresolved.
  6. **Hysteresis.** A meaningful evidence advantage is needed before the active belief switches. Its thresholds are to be developed experimentally and are not chosen now.
  7. **Confidence is separate from revision eligibility.** A slightly more confident alternative does not automatically replace the current belief; eligibility is a governed decision over the evidence state and policy.
- **Required behaviour, checked against the Pluto scenario (not hardcoded):**
  - One source says Pluto is not a planet: a candidate contradiction, perhaps investigation, no automatic replacement.
  - Several independent high-quality sources support the changed classification: a stronger evidence state; the belief may become disputed.
  - The governing astronomical authority formally changes the classification: authoritative supersession evidence; the revision engine may revise the active belief.
  - A later definition makes Pluto a planet again: a new supersession event; the active belief may change again, and earlier states and reasons remain in lineage.
- **Self-development is later and supervised.** Eidolon may eventually analyse her revision history and propose changes to her own epistemic policies. Such changes are supervised self-development that needs review and approval. This is not authorization for autonomous belief-policy modification.
- **G-FID stays**, as one input to this evidence pipeline, not as a prerequisite for letting one model call rewrite a belief.

**Added in 2.10** (Marcus, 2026-09-14; the G-REL2 record completed, and a change of architectural direction):
- **G-REL2, recorded in full:**
  - G5 binding validity was repaired by the schema change.
  - The pre-registered schema-friction hypothesis is CONFOUNDED overall. Removing malformed-output rejection also removed an accidental safety filter: G-REL's malformed outputs and per-field qualifier behaviour had kept some semantic overreach from being admitted.
  - The higher admitted semantic-error counts mostly expose errors already present in the model's proposals, not errors created by the schema repair.
  - G-REL2 is the preferred structural contract: it is faithful, auditable and substantially easier for the model to satisfy. It is also cheaper, as an observed side effect that is not an optimization result.
- **A new authority boundary.** Automatic belief modification must not depend directly on one model-produced refutation judgment.
  - Detecting a possible contradiction is not belief revision.
  - A model's proposal that evidence contradicts a belief is a provisional contradiction candidate: an observation and a request for investigation. It cannot weaken, refute, replace or supersede a durable belief.
  - Authority over belief state belongs to a separate, governed belief-revision mechanism that acts on validated, accumulated evidence.
  - This replaces the 2.9 "fallback", which becomes the general rule.
- **G-REF is withdrawn before any result.** Its objective, showing that a model refutation is trustworthy enough for automatic admission, is superseded.
  - The live run started under `prereg_ref.json` was stopped before it finished.
  - Its partial outputs are kept, unscored and unused.
  - The next experiment is candidate-contradiction detection, designed and pre-registered separately and reviewed before any live call.
- R1 remains blocked. No optimization or batching. Main and origin/main are untouched.

**Added in 2.9** (Marcus, 2026-09-14; the G-REL2 outcome):
- **G-REL2: gate FAIL.** Fixtures passed every rule. On real passages three rules failed:

  | Rule | G-REL | G-REL2 |
  |---|---|---|
  | G1 false refutations | 3 | 11 |
  | G2 direct-support precision | 0.901 | 0.897 |
  | G6 qualifier safety | 0.647 | 0.588 |

  - **G5 binding was repaired by the schema change:** 0.959 on fixtures and 0.974 on real passages, up from 0.816 and 0.691.
  - **The schema-friction causal hypothesis is CONFOUNDED, not cleanly confirmed.** Removing the structural failures also removed accidental rejections of semantic overreach.
  - **The original G-REL schema acted partly as an accidental safety filter.** The higher admitted-error counts are not evidence that the schema repair created those errors. Item-level comparison shows most were already present in what the model proposed:
    - 22 of 250 real items changed their proposed relation;
    - the model proposed false refutations 17 times in both versions, and false direct supports 8 times in both.
  - **G-REL2 is the preferred structural base:** it is more faithful, more auditable, and much easier for the model to satisfy.
  - **Measured side effect:** shorter structured output cut the average time per pair from about 33 s to about 17 s. This is not an optimization result, and no optimization work starts.
- **Next: G-REF, a narrow experiment on refutation semantics** using the G-REL2 structural contract as its fixed base.
  - **Hypothesis:** a model-assisted refutation can be admitted safely only when the passage explicitly expresses a proposition incompatible with the immutable target claim under demonstrated overlapping scope.
  - **Held fixed:** direct-support semantics, the corpus and gold where applicable, the runtime and model, one pair per call, and the G-REL2 schema. The zero-false-refutation rule stays.
  - G-FID is not started. After G-REF, work stops for review.
  - If G-REF establishes reliable refutation semantics, G-FID (qualifier and scope fidelity) comes next.
- **Fallback architecture**, if G-REF still produces systematic false refutations: direct support may be admitted automatically, but refutation stays provisional and review-required, and cannot automatically revise belief state.
- R1 remains blocked. No batching or optimization.

**Added in 2.8** (Marcus, 2026-09-14; the G-REL outcome):
- **G-REL: FAIL** under the pre-registered scorer, scored against gold that was independently double-labelled and adjudicated. The run was 424 calls on `qwen3.8:27b`, with no identity or runtime failure. There are three distinct failure classes:
  1. **Contract/schema failure.** G5 binding validity was 0.816 on fixtures and 0.691 on real passages. Much of it is representation friction:
     - schema values outside the allowed vocabulary, mostly a clause status written into qualifier fields;
     - attempts to represent unstated clauses where the schema had no place for them;
     - quoted spans shortened with an ellipsis.

     It is not treated as equivalent to semantic evidence hallucination.
  2. **Semantic fidelity failure.** G6 qualifier safety was 0.647 on real passages. Real modality, instruction or purpose form, question fragments and dropped conditions were admitted as direct support. Qualifier detection was 0.94 on synthetic items but 0.47 on real ones, which is a generalization gap.
  3. **Residual refutation failure.** G1 counted three false refutations on real passages. Two are clear semantic errors. The third depends on an adjudication disagreement in which the independent labeller chose refutation.
- **Improvement over G-XS on the same real pairs:**
  - all 21 G-XS false supports became zero admitted direct supports;
  - only 2 of the 19 G-XS false refutations were admitted as refutations;
  - real direct-support precision was 0.901 and recall 0.842; real refutation recall was 0.80.
- **The outside-knowledge self-report gave no observed protection:** the model never reported using outside knowledge. That field is not treated as an effective safeguard unless later evidence establishes otherwise.
- **The validator's guarantee is structural.** It checks the admission contract, not semantic entailment.
- **Next: G-REL2, a schema-only repair.** Its hypothesis: most G5 failure comes from a mismatch between the distinctions the model tries to express and the output schema, not from failing to identify the evidence relationship.
  - Only the schema and structural contract change.
  - These stay fixed: the corpus, the adjudicated gold, the relation vocabulary, the support, refutation and qualifier reasoning instructions, the model and runtime, the thresholds, batching, and one pair per call.
  - If G5 passes while G1–G4 and G6 stay materially stable, the hypothesis is supported and G-FID comes next. If G5 stays substantially below its bar, work stops for reassessment rather than stacking semantic changes onto an unresolved contract problem.
- **No optimization or batching of G-REL yet.** Its reference cost, about 33 s per pair, is far outside the budget, but semantic correctness comes first. R1 remains blocked.

**Added in 2.7** (Marcus, 2026-09-13; the G-R2 outcome and a new gate before R1):
- **G-R2: HARMFUL under the registered decision rule.** Relaxing the single-finding cardinality constraint recovers mechanism structure that the legacy singular contract suppresses, but also increases unsupported proposition generation. Multi-finding representation is therefore promising as a representation change but is not safe for integration without a stronger proposition-level support and fidelity mechanism. The result is not evidence that multi-finding representation itself is unsuitable.
  - **Positive finding:** the multi-finding arm expressed mechanism structure the legacy synthesis did not.
  - **Blocking finding:** the multi-finding arm increased unsupported proposition generation and so failed D2.
  - **Measurements** (28/28 calls parsed; both reps identical; blind labels):

    | Arm | Supported core mechanism stages | Supported mechanism findings | Unsupported |
    |---|---|---|---|
    | Legacy | 0 | 0 | 0 of 7 |
    | Multi | 5 | 3 | 5 of 30 (0.167) |
    | R1 reference | — | 5 | 9 of 42 (0.214) |

    - In the multi arm, 25 of 30 findings were supported. All 5 unsupported findings were grounded by production to passages that only partly state them: a dropped hedge, an infobox, a table of contents, and a claim combining two passages.
    - The R1 reference shows that per-passage atomic extraction does not by itself provide epistemic safety.
  - **Caveats:**
    - The pre-registered 5-stage mechanism ceiling was wrong: finding-level labels found stages in passages that the older passage labels had called summaries.
    - The TCP stages rest on a single claim about a proposed deep-reinforcement-learning controller.
    - There was one blind labeller.
- **The shared failure.** G-XS, G-R2 and the R1 reference show one semantic failure. The model treats passages as licensing propositions that they only partly state, imply only with outside knowledge, or do not state at all. It does not reliably distinguish "this passage is related to the claim" from "this passage licenses this exact proposition".
- **New gate before R1: G-REL (proposition relationship).** Designed and pre-registered harness-only; not production-wired.
  - **Its question:** what exact semantic relation holds between this passage and this immutable proposition. It does not ask whether the proposition is true.
  - **Relations:** direct_support, partial_support, explicit_refutation, scope_or_condition_difference, irrelevant, ambiguous.
  - **No naked labels.** Every non-irrelevant assessment binds:
    - the immutable claim and the assessed claim clause;
    - an exact evidence span;
    - qualifier compatibility (modality, quantifier, population, condition, polarity, time, units);
    - whether the passage licenses it directly or it needs outside inference.
  - **Refutation is strict.** Explicit refutation requires an incompatible proposition under overlapping scope. A same-topic falsehood is not a refutation, and a same-topic truth is not support.
- **G-FID is now a dependency of the proposition-relationship layer**, while staying separately measurable.
- **R1 stays blocked until:**
  1. the value of richer representation is established (G-R2 partly demonstrates it);
  2. proposition-level support and refutation are trustworthy on real passages (G-REL);
  3. qualifier and scope fidelity is demonstrated (G-FID);
  4. the resulting assessor has a measured cost compatible with the episode budget, or a validated equivalent optimization exists.
- **Double labelling before promotion.** Before any redesigned assessor is promoted, a subset of its evaluation labels is independently double-labelled and disagreements are adjudicated. The subset covers especially partial support, dropped hedges, condition mismatches, inferred contradictions, derived imperatives and scope changes.
- **No optimization of the failed G-XS implementation.** The order is: correct semantics, then a trustworthy reference, then its measured runtime, and only then batching or filtering tested against that reference.
- **E1 stays on the near-term roadmap** but is not inserted while this semantic diagnosis is under way.

**Added in 2.6** (Marcus, 2026-09-13; the G-XS outcome):
- **G-XS: FAIL** under the pre-registered scorer, recorded as two independent failures (28 fixtures and 42 app-path findings, 2 reps each, `qwen3.8:27b`):
  1. **Semantic failure.** On real application passages the assessor overreaches at the proposition level: it supports or refutes from topical, hedged or boilerplate text that does not state or contradict the claim.
     - False refutations: 19 (bar 0).
     - Support precision: 0.475, against the registered 0.810 bar (own-passage VERIFY).
     - The false sets repeat across successful reps.
  2. **Cost failure.** The unbatched reference makes one call per finding × other source (about 30 calls per topic), which is well outside the 300 s episode budget.
     - Combined retrieval + replayed pipeline + XS, from the clean rep: XS mean 469 s, total mean 604 s; 2 of 7 topics fit within 300 s.
     - This combined figure is a capacity estimate, not a measured end-to-end runtime on the same evidence.
- **What passed:**
  - immutable claim text, digest and finding identity;
  - OptionSet and evidence containment;
  - the 27/27 contract suite;
  - fixture semantics (all 8 types, both reps);
  - supporter and refuter recall (1.0 everywhere);
  - deterministic labels whenever calls succeeded.
- **Consequence.** The tested three-way assessor (supports / refutes / unclear) is unsuitable, in its current form, as the authoritative cross-source assessor on real application passages. It is not repaired, batched, parallelized, compressed or otherwise optimized before its assessment semantics are redesigned.
- **R1 is now gated by two separate questions:**
  1. Does multi-finding representation materially improve extraction and reasoning? (G-R2, next)
  2. Can a proposition-level cross-source assessor be designed that is trustworthy on real passages? (the G-XS redesign, future)
- **G-R2 stays a narrow isolation experiment.**
  - Same frozen offers, same authoritative OptionSets, same production runtime and configuration.
  - No A3, O3 or C1, and no change to the cross-source assessor, the composer or the evidence policy.
  - Only the synthesis representation changes, from the singular-finding contract to a bounded multi-finding contract.
  - It is evaluated with the existing direct grounding and independent blind labels, never with the failed G-XS assessor.
  - After G-R2, work stops for review before R1 is built.
- **Future G-XS redesign (noted, not implemented):**
  - Richer relations: direct support, partial support, explicit contradiction, scope or condition change, irrelevant, ambiguous.
  - Exact evidence spans and qualifier overlap.
  - Adversarial cases in which a passage makes true or false statements about the same topic without supporting or refuting the target proposition.

**Added in 2.5** (Marcus, 2026-09-12, while G-XS ran; roadmap only, no gate outcome recorded here):
- **G-R2 moves ahead of R1.** After the G-XS review and before R1 is implemented, run the narrow G-R2 experiment: multi-finding synthesis in one call, on the same frozen offers and the production `qwen3.8:27b` runtime.
  - If it materially improves mechanism extraction without increasing unsupported claims, that result decides whether R1 is still necessary or should be simplified.
  - G-R2 is no longer only an optional later parity check.
- **E1 joins the near-term architecture-validation roadmap:** a matched comparison of the full system against a minimal governed agent with identical tools, authority and budgets, plus oracle-evidence ablations. It does not interrupt the migration.
- **A future atomic-claim fidelity gate (G-FID).** Conditions, quantifiers, populations, units and time scope must survive decomposition into atomic claims.
  - The 20-word bound is a transport limit, not a semantic one; a claim that loses a qualifier is a different claim.
- **G-XS runs unchanged as pre-registered.** Its relation vocabulary (supports / refutes / unclear) and thresholds are not changed mid-run.
  - Its known limits are reported with its result: partial support and scope change collapse into unclear, and lineage is page-level.
- **Helper defects outside the research path** are recorded separately and not fixed on this branch.

**Added in 2.4** (experimental-record repair and G-RETRY, Marcus, 2026-09-12):
- **Runtime-model deviation.** The first live runs of C0/C1 and G-RETRY used isolated data directories that silently resolved `qwen2.5:7b` instead of the registered `qwen3.8:27b`.
  - Their behavioural verdicts are invalid as production-model verdicts.
  - The runs and their hashes are kept as deviation evidence, not deleted or rewritten.
  - The model-free contract and parity evidence from those gates stays valid.
  - Harness runs now receive only the production local-model settings, verify the complete resolved configuration before any measured call, fail closed on any model but `qwen3.8:27b`, and record the configuration and the Ollama state.
- **The reruns on `qwen3.8:27b` are the authoritative behavioural results.**
  - **C0/C1: MIXED / NO DETECTABLE EFFECT** (E7). Not integrated; the cap stays 3.
  - **G-RETRY: PASS** and integrated (`ddd1577`).
- **G-COST: PASS WITH QUALIFICATION** (§6). Full budget viability stays unresolved until cross-source assessment and the D7 composer exist and are measured. No optimization is authorized.
- **Retrieval reliability.** 11 of 14 G-COST live retrievals reached the source-failure limit. This is recorded as an observation and not addressed on this branch.
- **Step status:** G-N1, G-INV, G-SCHEMA and G-RETRY passed; G-COST passed with qualification. Nothing further is enabled.

**Added in 2.3** (after G-SCHEMA passed):
- **Two versions, two contracts.** The history contract version (`bounded_research_history.CONTRACT_VERSION`, `v2503.3`) keeps describing the legacy history-record and export contract, and does not change. `finding_schema_version` versions the multi-finding research representation and is present only on a report that uses that representation.
- **Legacy reports get no migration metadata.** `finding_schema_version`, `synthesis_path` and any equivalent field are never added to legacy reports for consistency. Keeping their keys, digests, projections and bytes unchanged is intentional. A report without `finding_schema_version` is, by contract, the legacy single-finding representation.
- **Boundaries established by G-SCHEMA** are recorded in §7a and stay in force until a later gate changes one explicitly.

**What the approval covers:**
- **Implementation may begin, narrowly and behind gates**, starting with the behaviour-neutral list refactor (G-N1).
- **After each gate passes, work stops** so the actual diff and the gate evidence can be reviewed before the next step is enabled.
- **Basis of the review:** Marcus reviewed the v2 contents and the consistency-review results as reported in the session, not a rendering of the published page. This file is the governing text.

**Added in 2.1:**
- the claim-immutability invariant for cross-source assessment (Layer 3, step 5, and G-XS);
- fail-closed failure semantics for the mechanism path (§3a);
- the judge's 700-character bound, frozen for the whole migration (Layer 5).

**Added in 2.2** (Marcus's six tightenings, made before G-RETRY ran):
- **Blocking vs measuring.** Which conditions block admission and which only measure is now stated explicitly (§3b), and D1 is reworded to match.
- **Whole-answer assessment.** The frozen 700-character judge stays for comparison, and a whole-answer assessment is required before promotion (G-WHOLE).
- **G-XS recall.** G-XS must recover known supporters and refuters, not only avoid false refutations.
- **Early cost probe.** The reference execution pattern is cost-probed before R1 is built (G-COST), and batching is evaluated against the reference.
- **G-RETRY scope.** The full-set retry applies to findings-only runs except demand, which keeps the one-passage retry (D4).
- **Demand milestone.** The original demand trial is tracked as a separate acceptance milestone (§9, M-DEMAND).

**Nothing beyond the gated steps is authorized.**

The production freeze still applies. A3, O3, C-singleton, the date fallback, the multi-finding machinery and the offer-cap change stay out of the repo until the gates in §6 pass. Every repo change needs Marcus's approval before it is pushed.

**What v2 changes from v1:**
- D1–D6 are recorded as approved, with Marcus's qualifications, and D7 is added.
- Findings from a design-only consistency review against the source are incorporated (§8).
  - The most important: R1, as tested, cannot produce corroboration or grounded refutation.
  - A cross-source assessment component and its blocking gate G-XS are therefore added.

---

## 0. Scope and standing principles

**In scope: the mechanism route of the findings-only path.** That means final-phase synthesis with no `requested_result_count`, and `requested_relation(objective) == "mechanism"`. "How does X work" objectives take this route (`research_evidence_policy.py:754`), and every experiment measured it.

**Stays on today's single-finding path in v1:**
- **Other findings-only objectives,** including "why" questions (`explanation`, which is depth-requesting but untested).
- **The demand single-dimension path** (`objective_shape == "single_candidate_dimension"`; D4). It uses the same findings-only prompt today, so routing must exclude it explicitly — for R1 and for every other change made on the shared findings-only path.
- **Candidate discovery and opportunity synthesis:** unchanged.

**Principles, unchanged:**
- **No loosening.** Never loosen an evidence gate or pad the corpus with weaker sources; fix observations and modelling. Evidence behind a gate is not automatically evidence lost.
- **One change at a time.** Each validation changes one semantic judgment; a gate passing never promotes two things at once.
- **Content-free receipts.** Receipts carry codes, counts and digests only, never claim text, passages or URLs. The report may show finding text, as today.
- **Measurements never refuse; requirements are named.** Every condition is either a blocking requirement or a report-only measurement, and §3b lists which. The evidence policy and the answer judge stay report-only (D6).
- **No thinking mode.** With JSON it returns an empty response; without JSON one call takes about 842 s against a 300 s budget.
- **"Supported" means grounded, model-judged support, not verified truth.** Grounding proves the passage was offered and observed and that the claim digest matches. Whether the passage supports the claim is still a model judgment (`semantic_support_verified: False`), and the report must keep saying so.

---

## 1. What the experiments earned

| # | Result | Evidence | Status |
|---|---|---|---|
| E1 | Thinking harder is not the fix | One call takes 842 s against a 300 s budget; JSON output fails | Rejected |
| E2 | Observation defects are real and fixable without loosening | Date fallback: 27/27 dates correct, 0 false; 6 sources rescued; end to end, mechanism passages 15→29 and stages 15→19 | Candidate (G-DATE) |
| E3 | Excerpt construction loses most of the mechanism | A3: held-out recall 0.342→0.729, precision 0.186→0.340. It used about 14% more characters under the same cap, so it is not "same budget". Captures used `create_session` | Candidate (G-A3) |
| E4 | Offer ranking loses mechanism | O3: 9/40→15/40 mechanism passages; core-stage recall 0.347→0.820; about 12% more characters | Candidate (G-O3) |
| E5 | Source selection works on metadata only; relevance is full-page | An offline replay reproduced selection on all 7 topics | Structural fact |
| E6 | URL document-form words misclassify publishers | "guide" and "review" misclassify dn.org and IJCOPE. "best" and "ideas" are retained; "guide" is a removal candidate | Measured; change deferred |
| E7 | The 3-passage cap constrains exposure and use, but raising it alone is not enough | C0/C1 on `qwen3.8:27b`: exposure 4→28, mechanism cited 4→8, grounded mechanism 0→6, unsupported findings 0→0; better on 3 of 7 topics and worse on none, below the 4-of-7 bar; the finding largely unchanged on most topics. **MIXED / NO DETECTABLE EFFECT.** The earlier FAIL (grounded mechanism 0→0, unsupported findings 8→10) came from an invalid `qwen2.5:7b` run (2.4) | Not harmful and sometimes useful, but not sufficient alone. Not integrated; the cap stays 3 (G-CAP) |
| E8 | The one-finding / exact-claim contract is the acceptance bottleneck | C0/C1 on `qwen3.8:27b`: richer grounded mechanism evidence, while the single finding still compresses it into a generic one-line claim on most topics | Earned |
| E9 | Atomic multi-step extraction works | PASS on TCP and mRNA; exact TCP replication REPLICATED; 0 invented, all steps grounded | Earned |
| E10 | One passage may yield several findings | TCP passage → 3 atomic steps; Van Jacobson → 4 | Earned |
| E11 | Stage-less findings belong in context | PASS on all 8 criteria; TCP precision 0.625→1.0, judge partial→complete | Earned |
| E12 | A persistent stage vocabulary is unnecessary | Winner C won through its flag plus ordering, not its vocabulary or clustering | Earned |
| E13 | A per-finding transient role deliberation is enough | C-singleton HOLDS on all 8 criteria. Precision 0.858→0.794 vs C; order 0.874→0.895; calls 64–271→13–29 | Earned |
| E14 | Clustering's only real contribution was suppressing paraphrased summaries | Photo residual 0.8→0.533 | Open (X-SUM) |
| E15 | Causal ordering is imperfect | TCP order 0.375; GPS control 1.0→0.0 | Open (X-ORD) |
| E16 | The frame word "works" is not a general cause | Q0 vs QE: no effect. QE vs QS: retrieval changed on 7 of 7 topics with no yield change | Earned: no query-word purification |

**Evidence limits:**
- The topics are 7 held-out "how X works" subjects plus TCP and mRNA as development topics.
- Counts per topic are small, and results are sensitive to the draw.
- The model is deterministic at temperature 0.
- The excerpt, offer and date harnesses captured through `create_session`, so "research" leaked into their terms.
- **Every harness judge result was bounded to the first 700 characters of the answer.** The harnesses called `judge_answer_quality`, which truncates at `_clean(finding, 700)` (adapter `:549`), so judge levels for longer composed answers saw only their opening.
- **R1 was tested with same-passage verification only** (§8, finding 1).
- **Mechanism success is not demand success.** Nothing here shows that Eidolon can evaluate SaaS demand, competition and feasibility; that is M-DEMAND (§9).

---

## 2. The pipeline as built (main `03aa99a`)

```
plan_public_search_queries (bounded_research_reasoning)   evidence terms = query tokens
  → search → candidates
  → adapter.observe                                        governed_public_web_research_adapter.py:739
       relevance = matched terms in full page / min(6, n)  :777-779
       machine-readable dates → derive_source_freshness    :789-796
       excerpt = _focused_excerpt(visible, terms, 12)      :847
  → select_citable_evidence (policy, receipt rows only)    bawr:1718 → research_evidence_policy:1146
  → adapter.synthesize                                     :861   (deadline = 300 s − time already spent)
       per-document budget max(320, min(2400, 7200//n))    :888
       passage_options(cid, joined excerpt), first 3       :912-928 · rca:129
       prompt: "Return at most one finding";              :938-966
               each assessment's claim = the finding summary; one assessment per offered source
       JSON-repair retry: first fitting passage per source :1069-1115
               (keeps its first-pass passage_index)
       assess_source_claims (grounding)                    :1127-1131
  → _complete_finding_citations                            bawr:274 / :1733
  → validate_research_synthesis (enforcing)                bounded_research_reasoning:1703 / bawr:1759
       findings path: ok if ≥1 row admitted; rows → reasonable_inferences ("inference");
       rows cut at 8 before counting (:1753, :2263); title required (:1772); duplicate titles rejected
       rendered: "Cited source interpretations (not independently verified)"
  → model_assessed_conclusion (demand only, enforcing)     rca:312 / bawr:1763
  → _judge_answer_quality (report-only; input ≤700 chars)  bawr:372 / :1784 · adapter:538-580
  → _evaluate_evidence_policy (report-only)                bawr:339 / :1789
  → training capture (if argument OR training policy)      bawr:925 / :1823
  → _surface_grounded_refutations                          bawr:223 / :1875
  → report status; history projection                      bawr:1908 · bounded_research_history:150/:455
```

**The six single-finding sites:**

| Site | Location | Current assumption |
|---|---|---|
| Synthesis contract | adapter `:964`, `:957` | At most one finding; every assessment's claim equals its summary |
| Citation completion | bawr `:296` | Returns `{}` unless exactly 1 finding |
| Refutation surfacing | bawr `:239` | Returns 0 unless exactly 1 finding |
| Evidence policy | bawr `:346` | `findings[0]` only |
| Answer judge | bawr `:384` | `findings[0].summary` only, truncated to 700 characters |
| Demand gate | rca `:321` | `finding_not_singular`; any assessment with a different claim denies |

`architecture_outcome_evaluation.py:43` belongs to a different subsystem and is out of scope.

**Report readers bound to the single shape:**
- `bounded_research_history` projects `evidence_policy_evaluation` (`:455`) and `citation_completion` (`:150`) as single mappings with fixed fields.
- `conversational_research_actions` counts `reasonable_inferences` and `unresolved_disagreements` (`:305-306`, `:596`). That count is already the right semantics for per-finding disagreement rows.

---

## 3. Target architecture

### Layer 1 — Evidence acquisition and observation

| Component | Production today | v1 decision | Candidate | Gate |
|---|---|---|---|---|
| Retrieval and query construction | `plan_public_search_queries` | **Unchanged** (E16) | none | — |
| Search-query vs evidence-term language | One derivation | **Unchanged in behaviour.** Named as two interfaces with identical values | none; 8b9e412 unmerged | — |
| Publisher date observation | Machine-readable dates only | Unchanged until the gate passes | Visible-date fallback: publication keywords only; publication and update distinct | **G-DATE** |
| Source classification | `_PROMOTIONAL_PATH` URL words | Unchanged | "guide" narrowing (deferred); dn.org (separate) | own pre-registration |
| Admissibility | `select_citable_evidence` | **Unchanged** | none | — |
| Relevance | Full-page term count / min(6, n) | **Unchanged** | none | — |
| Excerpt construction | `_focused_excerpt` (A0) | Unchanged until the gate passes | A3 | **G-A3** |

### Layer 2 — Evidence presentation

**`OptionSet`.** A document's passage options are computed once per document per synthesis attempt into an ordered list of `{index, passage_id, text}`. Offer, grounding, extraction, verification, cross-source assessment and every retry consume the same object. This is the C0/C1 invariant made a production assertion (**G-INV**).

**Retry, current behaviour.** Identity already survives retry: retry passages keep their first-pass `passage_index`. Exposure does not: at most one passage per source is re-offered.

**Components:**
- **Ranking.** Page order, first 3 → candidate O3 (**G-O3**).
- **Cap.** An `OptionSet` parameter; the global `PASSAGE_OPTION_LIMIT` stays because `research_evidence_directions` bound it at import. The value stays **3** until **G-CAP** passes under the multi-finding contract (E7).
- **Budgets.** The global 7200 and the per-document `max(320, min(2400, 7200//n))` are unchanged. Characters and tokens offered are reported per source; any candidate consuming more is compared at matched consumption.
- **Retry semantics.** A retry changes format only and carries the same `OptionSet` (**G-RETRY**).
  - This applies to findings-only runs **except demand**, which keeps the one-passage retry until M-DEMAND (D4, §9).
  - A shorter prompt, if ever needed, becomes a new, separately recorded attempt.
- **Document order.** Candidate, then citation ID. Unchanged.

### Layer 3 — Atomic multi-finding synthesis

**Contract.** Evidence → a set of atomic findings. Each finding has:
- `claim`: one proposition, at most 20 words, stated from its passage;
- `support`: one or more `(citation_id, option index)` references;
- `uncertainties`.

The relation is many-to-many: a passage may support several findings (E10), and a finding may be supported by several passages.

**R1 (earned; the reference implementation):**
1. **Extract.** One call per offered passage (`EXTRACT_MULTI`): zero to 4 steps; no definitions, variants, history or context; separate steps kept separate.
2. **Verify.** An independent call per step (`VERIFY`) on its own passage, returning supports, refutes or unclear. The extractor never certifies itself.
3. **Ground.** `assess_source_claims` with each step as its own claim. Semantics are unchanged: they are already claim-keyed.
4. **Deduplicate.** Exact deduplication with `normalized_claim_text`. **Duplicates merge their support references rather than dropping them.** The harness kept only the first occurrence, which discards corroboration. The harness's near-duplicate rule is not portable and does not ship.
5. **Cross-source assessment (new, untested; blocking gate G-XS).** Each deduplicated claim is assessed against the *other* offered sources' passages, so supporting and refuting evidence from other publishers can be grounded.
   - Proposed form: one call per source, listing that source's `OptionSet` and the claims extracted elsewhere. It returns, per claim, supports, refutes or unclear with an option index.
   - Rows go through `assess_source_claims` unchanged.
   - Without this step, R1 yields one supporting source per claim and **no grounded refutation at all**. That would regress the validated refutation behaviour and leave D2 unpopulated. So it is **blocking**.
   - **The two phases have distinct jobs.** Extraction grounding proves where an atomic claim came from. Cross-source assessment determines what the rest of the eligible evidence says about that claim.
   - **Claim immutability (invariant).** Cross-source assessment may change a finding's evidence state, supporters, refuters and policy eligibility. **It may never rewrite the claim.**
     - The claim text and its `claim_digest` are byte-identical before and after assessment.
     - Every assessment row binds to that exact digest.
     - If assessment suggests a claim is badly framed, the claim is rejected, or a *new* candidate claim enters through the explicit candidate path: extraction, verification and grounding, under its own digest.
     - Wording is never adjusted until the evidence agrees.
     - This is enforced by an assertion, and a violation is a hard failure (G-XS).

**R1 is the reference behaviour, not a committed execution pattern.** One model call per passage, per claim and per classification may be too expensive on the local 27B model. Its cost is probed before R1 is built (**G-COST**). Batched variants — several passages per extraction call, several claims per verification or classification call — are candidates, measured against R1's outputs. A batched variant replaces a reference stage only when it matches the reference on G-COST's pre-registered metrics.

**R2 (untested):** one synthesis call returning N findings. It may replace R1 only after parity (**G-R2**, optional).

**Failure accounting.** Every extraction, verification and assessment call gets at most one repair retry over the identical input. Failed calls are counted and persisted per run; the harnesses did not persist them.

**Bounds:**
- At most 4 steps per passage; at most 6 citation IDs per finding.
- An explicit finding cap, **truncated and reported**. It replaces the validator's invisible cut at 8.
- `qwen3.8:27b`, thinking off, temperature 0.0.

### Layer 4 — Per-finding epistemic semantics

**Every property is judged per finding, on that finding's own claim and citations. Nothing is borrowed across findings.**

**Admission states (D1, D2):**

| State | Condition | Where it goes |
|---|---|---|
| **Supported** | ≥1 grounded supporting passage for this exact atomic claim, and no grounded refutation | Eligible for the explanation. The evidence policy's verdict — for example, whether this claim shape would need several independent publishers — is **measured** per finding and does **not** block in v1 (D6, §3b). On the atomic path each step carries its measured policy state as a visible fixed-code annotation, so a claim shown despite a failed measurement is never presented as policy-admitted |
| **Disputed** | Grounded support **and** grounded refutation | Kept out of the causal chain. Presented separately, with supporters and refuters listed apart. Never resolved by counting citations |
| **Unsupported / unresolved** | No grounded support: unverified, ungrounded, or only unclear assessments | Diagnostic and research state only (counts, digests). **Never asserted answer content** |

**Properties:**

| Property | Per-finding definition | Answer-level meaning |
|---|---|---|
| Grounded support | `grounded_supporting_citation_ids(assessments, claim)`, from own-passage verification plus G-XS rows | Decides Supported |
| Grounded refutation | `grounded_refuting_citation_ids(assessments, claim)`, from G-XS rows (and own-passage VERIFY "refutes") | Decides Disputed. One entry per disputed finding in `unresolved_disagreements`; the refuter never joins the finding's citations |
| Citation completion | `_complete_finding_citations` per finding; `model_payload` preserved | Per-finding counts |
| Corroboration / independence | `independence_summary` over the finding's grounded supporters | Never pooled across findings. Measured, not blocking (§3b) |
| Cross-finding contradiction | **Not defined in v1** | Recorded as a known gap; G-WHOLE reviews contradictions within an answer |
| Uncertainty | The finding's `uncertainties` | Limitations stay a separate list |
| Evidence currency | Citation conditions over the finding's cited sources | Measured, not blocking (§3b) |
| Evidence policy | `evaluate_policy` once per finding; one policy per run | A per-finding list; `enforced: False` unchanged (D6) |
| Enforcing admission | `validate_research_synthesis` per finding. The claim replaces the title; the reported cap replaces the invisible cut at 8 | Report ready if ≥1 finding is admitted (unchanged rule) |
| Demand gate | Unchanged in v1 (D4) | — |

**Each single-finding site, rewritten:**

| Site | Target |
|---|---|
| Synthesis contract | R1 on the mechanism route; legacy call everywhere else |
| Citation completion | A per-finding loop; with one finding, identical to today |
| Refutation surfacing | One disagreement entry per disputed finding |
| Evidence policy | A per-finding list plus run-level pool fields |
| Answer judge | Judges the composed explanation (Layer 5) |
| Demand gate | Unchanged; its all-assessments-match rule remains |

**Report schema.** With one finding, the report and both history projections are byte-identical to today (**G-N1**). With more than one:
- `evidence_policy_evaluation` keeps its run-level fields (available admissible evidence, authority states, source selection) and gains `finding_evaluations: [...]` plus aggregate counts.
- The finding-verdict fields are not duplicated at the top level.
- `bounded_research_history` gains bounded, fixed-code projections for the new lists.
- **Versioning (2.3, G-SCHEMA).** The multi-finding representation is versioned by `finding_schema_version` (`v2731.4`), present only on a report that uses it. The history contract version (`CONTRACT_VERSION`, `v2503.3`) keeps describing the legacy history-record and export contract and is **not** bumped: it is embedded in every history record and export, so a bump would change every legacy record although G-SCHEMA is behaviour-neutral.

### Layer 5 — Explanation construction (mechanism route only)

```
Supported findings (Disputed and Unsupported excluded, per D1/D2)
  → C-singleton  C's exact flag prompt per finding, as a one-member group; name discarded, never persisted;
                 anything but true → context
  → separation   mechanism | context   (context kept and shown)
  → cleanup      exact normalized deduplication; paraphrased-summary suppression open (X-SUM)
  → ordering     ORDER_ALL over mechanism findings; the guard drops nothing; the valid-order count is reported
  → composition  (D7) deterministic, from grounded claims only
```

**D7 — partial survival and causal linkage:**
1. **Compose from what survives.** The explanation is built from the Supported findings. The candidate mechanism is never an all-or-nothing unit; A, B and D are presented even if C failed.
2. **Ordering is not causation.** A position in the proposed order asserts sequence at most, never a causal edge.
   - A causal link appears only where a Supported finding's own grounded claim states it ("loss detection triggers window reduction").
   - The composer never writes connectives ("which causes", "then", "leading to") between separate findings.
3. **Gaps are represented, not bridged.** The answer states that adjacent steps are not asserted to be causally connected unless a step says so.
   - Where an Unsupported extracted step falls between two Supported ones in the proposed order, the answer says the intermediate connection was **not established by the researched evidence**. The unsupported step's text is never shown as content.
   - That marking is untested (**X-GAP**). Until it passes, only the general statement ships.

**The composed answer:**
- **Proposed causal order:** the mechanism steps, each with its own citations and its policy-measurement annotation (§3b).
- **Context.**
- **Disputed evidence:** supporters and refuters listed separately.
- **Limitations.**
- **The provenance disclaimer:** each step's passage was observed and judged supportive by the model; the claims are not independently verified.

No new model prose follows ordering.

**Answer judge.** It judges the composed mechanism chain against the requested relation.
- Its 700-character input bound is made explicit: the chain is bounded to the limit, and truncation is reported (`answer_quality_input_truncated`).
- **The bound stays at 700 for the whole migration.** Changing the ruler while the architecture changes would make before/after judge levels incomparable.
- Historical judge levels read as "complete, as far as the judge saw in the first 700 characters". They remain valid comparisons between arms that went through the same judge.
- The judge stays report-only; it needs at least 5 s left and at most 30 s (adapter `:555`, `:573`).

**Whole-answer assessment before promotion (G-WHOLE).** An opening-only score cannot show that a longer explanation works as a whole: the opening could improve while errors appear later. Before the atomic path is promoted, every composed answer in the G-MF runs is assessed in full.
- **Deterministic trace:** every asserted sentence maps to a Supported finding and that finding's citations. This is possible because composition is deterministic.
- **Blind hand review of the complete output:** unsupported claims, contradictory statements within the answer, and causal links the findings do not state.
- It is a promotion gate, run in the harness. It is not a run-time measurement and does not replace the frozen judge.

**Receipts.** Counts of findings extracted, verified, grounded, supported, disputed, unsupported, mechanism, context and truncated; failed calls; the valid-order count; claim digests. Never claim text.

**Training capture (D5).** The mechanism route bypasses capture **whether it was requested by argument or by `training_policy.research_enabled`** (bawr `:925`). It records the fixed status `training_capture_not_designed`. Legacy paths are unchanged.

### 3a. Failure semantics of the mechanism path (fail closed)

**Rule.** If the atomic mechanism path fails, the run ends with an explicit research failure or an insufficient-evidence result. It **never** silently falls back to today's single-finding synthesis and presents that as an equivalent success.

**Why.** A silent fallback would produce an answer and superficially successful telemetry, while hiding which architecture produced it. That would make every validation of the new path unreadable.

**Path provenance.** Every atomic-path run records `synthesis_path: atomic_mechanism` together with `finding_schema_version`. Legacy reports carry neither, by design (2.3): a report without `finding_schema_version` is, by contract, the legacy single-finding representation, and legacy bytes are never changed to add provenance. Routing (§0) is decided **before** synthesis. A run routed to `atomic_mechanism` can end in only two ways:
- an atomic-path result;
- an atomic-path failure.

**Run-level failure codes** (fixed vocabulary; the report status is insufficient evidence or failed, never ready):

| Code | Cause |
|---|---|
| `mechanism_path_deadline_exhausted` | The synthesis deadline was reached before composition |
| `mechanism_path_extraction_failed` | No passage produced a parseable extraction after its repair retry |
| `mechanism_path_no_supported_findings` | Extraction ran, but no finding reached the Supported state (an insufficient-evidence result, not a technical failure) |
| `mechanism_path_stage_failed:<stage>` | A whole stage (verification, grounding, cross-source assessment, classification, ordering, composition) could not complete for the run |

**Per-item failures inside a stage** are counted and persisted per run. They never produce positive evidence:
- **A failed extraction call:** that passage yields no findings.
- **A failed verification call:** the finding is Unsupported.
- **A failed cross-source call:** that source contributes no assessments. The report counts it, and the answer's limitations state that the findings could not be checked against that many sources.
- **A failed or unparsed classification flag:** the finding goes to context (C's rule: anything but true).
- **A failed ordering call:** the guard keeps every finding in its original order, and a zero valid-order count is reported.

**A future fallback, if it is ever wanted,** needs a separate decision and must have all four of:
- an explicit fallback code;
- provenance naming the path that produced the answer;
- separate metrics;
- no representation as a successful atomic-path run.

G-MF requires **zero silent fallbacks**. Path provenance must be present on every run.

### 3b. What blocks and what only measures

Every condition is exactly one of three kinds:
- **Blocking:** its failure keeps content out of the answer.
- **Measured:** recorded for the operator; its failure never removes content.
- **Promotion gate:** blocks promoting a component, never a run.

| Condition | Kind | When it fails | Scope |
|---|---|---|---|
| Observed citations and a claim (`validate_research_synthesis`) | Blocking | The row is rejected and does not appear | All paths, unchanged |
| Option-set identity and passage provenance (grounding) | Blocking | The assessment is rejected (disqualifying) | All paths |
| Grounded support for the exact atomic claim (D1) | Blocking | Unsupported: never asserted | Atomic path |
| Grounded refutation of the exact atomic claim (D2) | Blocking for the causal chain | Disputed: shown separately, never in the chain | Atomic path. On the legacy path it is surfaced as a disagreement, unchanged |
| Demand gate (`model_assessed_conclusion`: independent lineages, currency, stance, claim binding) | Blocking | The demand inference is refused | Demand, unchanged |
| Evidence-policy conditions: corroboration, publisher independence, currency, authority, producer independence, `grounded_refutation` as a policy condition, `would_admit` | **Measured** (D6) | Recorded per finding. **The finding can still appear.** On the atomic path each step shows its measured policy state as a fixed-code annotation. On the legacy path the answer is unchanged and the state is in the receipt only, as today | All paths |
| Answer judge (700 characters, frozen) | Measured | Recorded | All paths |
| G-WHOLE, G-XS, G-MF and the other §6 gates | Promotion gate | The component is not promoted | Harness |

**Consequence.** No statement in this specification guarantees that a claim in an answer passed the evidence policy. Moving any measured condition to blocking is a separate decision with its own experiment (D6).

---

## 4. Not changed by this design

- Evidence policy conditions and thresholds.
- `select_citable_evidence`.
- The relevance formula.
- Query planning.
- `_PROMOTIONAL_PATH`.
- Content-free receipts.
- The model and thinking-off setting.
- The candidate-discovery and opportunity contracts.
- The demand path, including its one-passage repair retry.
- Non-mechanism findings-only objectives stay off the atomic path. Their repair retry does change with G-RETRY.
- The report-only status of the policy and the judge.
- The session budget (D3).

---

## 5. Decisions (approved by Marcus, 2026-09-12)

| # | Decision |
|---|---|
| **D1** | **Grounded support is the minimum blocking requirement for the explanation. The evidence policy measures whether a claim shape would need more, and in v1 that measurement does not block (D6, §3b).** Three states: Supported (eligible), Disputed (D2), and Unsupported/unresolved (diagnostic only, never asserted). Corroboration is not required universally |
| **D2** | **Disputed findings stay out of the causal chain** and are presented separately, with supporting and refuting evidence. Eidolon never silently picks the side with more citations |
| **D3** | **Measure integrated cost first. Optimize structurally. Raise the 300 s mechanism budget only if measured quality requires it, by a separate decision.** 900 s is an emergency ceiling, not a target. The reference pattern is cost-probed before R1 is built (G-COST). G-TIME must report extraction, verification, grounding, cross-source assessment, C-singleton and ordering costs; total wall-clock time; model calls; tokens; safe parallelism; and duplicated work |
| **D4** | **Demand stays single-finding in v1,** and every change on the shared findings-only path excludes demand unless it is explicitly included and tested. The refactor is list-capable with G-N1 parity, but demand generation stays singular. Demand has its own acceptance milestone (M-DEMAND, §9) |
| **D5** | **Training capture is off on the new path until explicitly designed.** A design must name which representation is training material (raw extraction, verified, grounded, policy-accepted, classified, or the ordered explanation), what provenance accompanies it, and how disputed or rejected findings are kept out of positive examples |
| **D6** | **No enforcement change in this migration.** Today's policy behaviour is preserved except where multi-finding semantics require an explicit equivalent. Any move from report-only to enforced conditions needs its own experiment and authorization |
| **D7** | **Compose from surviving findings; ordering does not assert causation.** Causal linkage must be independently supported (stated by a grounded claim) or represented as unknown. Gaps are represented, never bridged |

---

## 6. Required validation before implementation or promotion

All gates are pre-registered. Harnesses are hashed, labels are blind and hashed before scoring, objectives go through `parse_conversational_research_request`, and "undetermined" is legitimate. The pass rules are drafts that each gate's own pre-registration finalizes.

| Gate | Component | Protocol | Draft pass rule | If it fails |
|---|---|---|---|---|
| **G-INV** | `OptionSet` | Fixture test that fails loudly: offer, grounding, extraction, assessment and retry | 0 violations; the test fails on a deliberately broken build | Blocks Layer 2 |
| **G-RETRY** | Retry (findings-only, except demand) | Contract and parity differential against the previous gate, plus a live forced-retry comparison on identical evidence (`prereg_retry.json`) | Non-retry runs, first attempts, demand and policy unchanged; the retry offers exactly the first attempt's set; grounding stays inside the set; a causal witness; no new generation failures or unsupported findings | Blocks the retry change. **Outcome: PASS on `qwen3.8:27b`** (`ddd1577`): contract and parity proof against `34167e0`; live, unsupported findings 0 vs 0 and grounded support beyond passage 1 4→20. The earlier DEFERRED outcome (B2, unsupported findings 4 vs 8) came from an invalid `qwen2.5:7b` run (2.4) |
| **G-N1** | Layer 4 refactor | Stored corpus with exactly 1 finding; the existing suite (`v2501_7`, `v2502_*`, `v2731_0_4` to `v2731_2_7`) | Byte-identical reports and history projections; suite unchanged apart from known pre-existing failures | Blocks multi-finding. **Outcome: PASS** (`2ed3161`) |
| **G-SCHEMA** | Report shape, N>1 | Fixture reports with several findings through `bounded_research_history` and `conversational_research_actions` | Projections fixed-code and bounded; counts correct; content-free receipts; policy-measurement annotations present on atomic steps | Blocks R1. **Outcome: PASS** (`d8c6f57`); versioned by `finding_schema_version`, history contract version unchanged (2.3); boundaries in §7a |
| **G-COST** | Reference execution cost (D3), **early** | Harness-only, **before R1 is built**: the reference R1 + cross-source + C-singleton + ordering pipeline on replayed app-path evidence, instrumented per stage (calls, prompt and output tokens, seconds, time left at synthesis start); then batched variants compared with the reference's outputs | Costs reported per stage. A batched variant may replace a reference stage only if it matches the reference on the pre-registered output metrics (claims extracted and grounded, support and refutation states, mechanism flags) | Informs D3 and the shape of the R1 build; R1 is not built around an unmeasured execution pattern. **Outcome: PASS WITH QUALIFICATION** (2.4): on 14 replayed runs the measured reference stages take 125 s mean (42–203) in 28 calls, which fits the 300 s budget after 9–17 s of retrieval. Cross-source assessment and the D7 composer do not exist yet and are unmeasured, so full budget viability is unresolved. No optimization is authorized |
| **G-XS** | Cross-source assessment | App-path replay; claims × other sources hand-labelled blind (supports / refutes / neither), **including planted contradicting passages whose correct label is refutes**; claim text and digest recorded before and after assessment | Supports precision ≥ own-passage VERIFY's; **support recall** and **refutation recall** on labelled pairs each at or above a pre-registered bar, so answering "unclear" to every contradiction fails; the unclear rate reported per labelled class; **false refutations = 0**; **claim mutations = 0** (text and digest byte-identical; every row binds to the unchanged digest); cost reported | **Blocks R1 shipping** (refutation must not regress). **Outcome (2.6): FAIL** on two independent counts. Semantic: 19 false refutations; support precision 0.475 vs 0.810. Cost: the unbatched reference is far over budget (a capacity estimate). Immutability, containment, contract, fixtures and recall passed. The three-way assessor is unsuitable as specified and is redesigned before any optimization |
| **G-MF** | Layers 3–5 end to end | Live app path, production vs R1 + XS + Layer 5, identical retrieval (replayed); mechanism topics plus non-mechanism and demand controls; induced-failure runs (deadline, extraction, cross-source) | Supported mechanism findings up on ≥4 of 7 topics; asserted unsupported content = 0; 0 invented; judge not lower; controls byte-unchanged; **path provenance on every atomic-path run** (legacy reports stay unmarked by contract, 2.3); **zero silent fallbacks** (induced failures end in their §3a codes) | Harness-only; back to design |
| **G-WHOLE** | The whole composed answer | Every composed answer in the G-MF runs: deterministic sentence-to-finding trace, plus blind hand review of the complete output | 0 asserted sentences without a Supported finding; 0 contradictions within an answer; 0 causal links the findings do not state; unsupported claims reported | **Blocks promotion** |
| **G-TIME** | Cost (D3) | Instrumented G-MF runs: per-stage time, calls and tokens; time left at synthesis start; parallelism and duplicated work | Within the current budget, or a recorded D3 decision after optimization | D3 |
| **G-A3** | Excerpt | App objective path; retrieval captured and replayed; A0 vs A3 at **matched characters and matched tokens**; blind labels | Recall and core coverage better on ≥4 held-out topics, worse on ≤1; precision not lower by >0.05; downstream offer (production and O3) not worse | Excerpts stay A0. **The architecture is unaffected** |
| **G-O3** | Offer ranking | After G-A3; offline replay; equal count and budget | Mechanism passages and core-stage recall up; stage recall never lower | Page order stays |
| **G-DATE** | Date observation | Held-out app-path pages; every date verified by hand; selection replay plus end to end | **Zero false dates**; publication and update distinct | The fallback does not ship |
| **G-CAP** | Offer cap | C0/C1 protocol under R1 | Acceptance up; unsupported findings not increased | The cap stays 3 |
| **G-R2** | Single-call multi-finding synthesis | **Before R1 (2.5):** the same frozen offers and production runtime as C0/C1 and G-COST; the legacy one-finding call vs a multi-finding call; blind labels; pre-registered | Mechanism extraction materially better on the pre-registered measure; unsupported claims not increased | Decides whether R1 is needed as specified, simplified, or replaced. **Outcome (2.7): HARMFUL** under the registered rule. D1 held: 5 supported core stages vs 0, and 3 supported mechanism findings vs 0. D2 failed: unsupported findings rose from 0/7 to 5/30. Multi-finding representation is promising but not safe to admit with the current support semantics |
| **G-REL** (2.7) | Proposition relationship (the shared support, refutation and qualifier layer) | Adversarial fixtures plus real-passage pairs reused from the G-XS and G-R2 failures, labelled blind. One call per (immutable proposition, offered passage). The six relations, each bound to a claim clause, an exact evidence span, qualifier compatibility and a relation basis; a mechanical validator admits a relation only when those fields are consistent | Pre-registered in `prereg_rel.json` | **Blocks R1** and any redesigned cross-source assessor. **Outcome (2.8): FAIL** in three classes: contract/schema (G5 0.816 / 0.691), semantic fidelity (G6 0.647 on real passages) and residual refutation (G1: 3, one adjudication-dependent). The improvement over G-XS on the same pairs is large. G-REL2 tests a schema-only repair. **G-REL2 (2.9): gate FAIL.** G5 was repaired (0.959 / 0.974), but the hypothesis is CONFOUNDED: the old schema was partly an accidental safety filter. G-REL2 is the structural base |
| **G-REF** (2.9) | Refutation semantics on the G-REL2 base | Adversarial refutation fixtures plus the G-REL corpora with their adjudicated gold. A proposed refutation must bind the target clause, the passage segment, the proposition the segment expresses, the dimension of incompatibility, population, condition and time comparisons, and whether the incompatibility is directly stated | Pre-registered in `prereg_ref.json`; zero false refutations; refutation recall; direct support and binding stable | Fallback: refutation stays provisional and review-required. **Withdrawn (2.10)** before any result; superseded by candidate-contradiction detection and governed belief revision |
| **G-CAND** (2.10) | Candidate-contradiction detection, with no belief authority | Adversarial, G-REL fixture and real pairs, plus 10 supersession items. A ContradictionCandidate is bound to the immutable claim and exact segments, and carries incompatibility, scope, recency, uncertainty and `resolution_needed`. It is provisional, with no belief effect | Pre-registered in `prereg_cand.json`: recall ≥ 0.85, false escalation ≤ 0.10, precision ≥ 0.80, binding ≥ 0.95, identity and non-mutation = 1.00, scope preservation ≥ 0.80, repeatability ≥ 0.95; plus a separate supersession gate | Candidates stay provisional under any outcome. **Outcome (2.12): BINDING_FAILURE, with OVER_ESCALATION also failing.** Recall, identity, non-mutation, scope preservation, repeatability and the supersession gate passed. A binding-only time/recency repair and a re-adjudication of the real gold come before any rerun. **G-CAND2 (2.13): OVER_ESCALATION.** Binding is repaired and closed for this stage; over-escalation is addressed one semantic class at a time |
| **G-TEMP** (2.13) | Temporal compatibility of a contradiction candidate | Controlled temporal pairs, including publication- and update-date traps, plus the G-CAND2 candidates; RM01–RM05 are required witnesses | Pre-registered before any live call; zero false suppression of genuine overlapping contradictions | `non_overlapping` suppresses escalation only in this experimental layer, with no belief effect. **Outcome (2.14): BINDING_FAILURE, with FALSE_SUPPRESSION and UNRESOLVED_RECALL_FAILURE also failing.** It handled the historical-state family (RM01–RM05 5/5, metadata invariant), but suppressed dated transitions whose resulting state continues. Binding is not relaxed |
| **G-STATE** (2.14) | Continuing resultant state: does a dated transition establish a state that continues after it? | Controlled contrasts and minimal pairs across transition and event wording, plus the G-TEMP witnesses (SS04, SS05, T54, T46), transition controls and historical controls | Pre-registered before any live call; the witnesses read as continuing, and no regression on the controls | Provisional analysis only, with no belief authority and no change to any candidate or temporal assessment. **Outcome (2.15): BINDING_FAILURE**, with WITNESS_FAILURE, CONTROL_REGRESSION, MISCLASSIFICATION and PAIR_INSENSITIVITY, dominated by a harness defect: JSON `null` optional cues were rejected. Descriptively 68/72 and 14/16 relations matched gold. Real misses: T19, T33, ST10, ST18, ST19, ST40 (ST40 has a construction caveat). G-STATE2 is the binding-only rerun. **G-STATE2 (2.16): UNSAFE_EVENT_ONLY** (3/45 including ST40). The null defect is repaired and every other rule passed, but a serialization-only edit moved 7/88 answers |
| **G-INVAR** (2.16) | Semantic invariance: does a classification survive meaning-equivalent prompt wording? | The G-STATE borderline family plus clear continuing, event-only and unresolved controls, under several pre-registered meaning-equivalent prompt forms with an identical output schema | Per-item classification invariance; instability concentrated at the boundary or spread everywhere | Diagnostic; no belief authority. **Outcome (2.17): BOUNDARY_INSTABILITY.** Controls 12/12 invariant, borderline 8/10 unstable, every change between adjacent labels; cross-session variation observed. A post-run scorer defect is recorded; the corrected shadow scorer agrees |
| **G-FID** (future, 2.5) | Atomic-claim fidelity | Decomposed claims vs their source passages, hand-labelled blind for dropped or altered qualifiers (condition, quantifier, population, unit, time scope) | Qualifier loss below a pre-registered bar; a lost qualifier makes a new claim, never a silent narrowing | Blocks promotion of atomic extraction. **Dependency of G-REL (2.7):** it is measured with G-REL's qualifier compatibility and remains separately reported |

**Open experiments, non-blocking and reported:**
- **X-SUM:** paraphrased-summary suppression.
- **X-ORD:** ordering reliability.
- **X-GAP:** explicit gap marking (D7). Until it passes, only the general "not asserted causal" statement ships.

**Architecture validation (near-term, outside the migration sequence, 2.5):** E1 is a matched comparison of the full system against a minimal governed agent with identical tools, authority and budgets, plus oracle-evidence ablations. It is scheduled without interrupting the migration.

---

## 7. Proposed integration order

Each step makes one semantic change and is independently revertible. Each needs its gate, then Marcus's approval, then the push.

1. **Behaviour-neutral list refactor (G-N1). This is the first implementation step.**
   - Per-finding primitives for citation completion, refutation surfacing, the policy measurement and the answer judge's claim.
   - They sit behind two named cardinality rules that reproduce today exactly:
     - `_sole_finding`: completion and surfacing act only on exactly one finding;
     - `_first_finding`: the policy and the judge read the first finding of any number. That asymmetry is recorded current behaviour.
   - The synthesis prompt, the demand gate and the report projections are untouched. A projection change is a schema change and belongs to step 4.
   - **After G-N1 passes, work stops** for review of the actual diff and the gate evidence before any behavioural change is enabled.
2. **`OptionSet` identity refactor.** No behaviour change (G-INV). **PASS** (`499723f`).
3. **Retry semantics** (G-RETRY): findings-only runs except demand. **PASS** on `qwen3.8:27b` (`ddd1577`). The earlier DEFERRED outcome came from an invalid `qwen2.5:7b` run (2.4).
4. **Multi-finding report schema** (G-SCHEMA). **PASS** (`d8c6f57`); boundaries in §7a.
5. **Reference cost probe (G-COST)**, harness-only, before R1 is built; batched candidates measured against the reference. **PASS WITH QUALIFICATION** (2.4): cross-source assessment and the composer are still unmeasured, and no optimization is authorized.
   - 5a. **G-R2 (2.5)**, harness-only, after the G-XS review and before R1 is implemented. Its result decides whether step 6 builds R1 as specified or a simpler form. **Outcome (2.7): HARMFUL** under the registered rule, with the positive mechanism finding recorded.
   - 5b. **G-REL (2.7)**, harness-only: design, pre-register, and review before any live run; then measure its semantics and cost. Nothing is optimized before its semantic reference passes. **Outcome (2.8): FAIL.** Next is G-REL2, a schema-only repair; after it, either G-FID or a stop for reassessment. **G-REL2 (2.9): FAIL.** G5 was repaired; the hypothesis is confounded.
   - 5c. **G-REF (2.9)**, harness-only: refutation semantics on the G-REL2 base, pre-registered before implementation. Afterwards, work stops for review. The next step is then G-FID if refutation is reliable, or otherwise the provisional-refutation fallback. **Withdrawn (2.10):** its run was stopped unscored. The next experiment is candidate-contradiction detection.
   - 5d. **G-CAND (2.10)**, harness-only: candidate-contradiction detection with no belief authority. **Outcome (2.12): BINDING_FAILURE**, with OVER_ESCALATION also failing; the authority boundary held. Before any rerun come the binding-only time/recency repair and the re-adjudication of the real gold, then review. **G-CAND2 (2.13): OVER_ESCALATION**; binding repaired and closed.
   - 5e. **G-TEMP (2.13)**, harness-only: temporal compatibility of contradiction candidates, the first of the one-class-at-a-time over-escalation gates. It is designed and pre-registered, then reviewed before any live call. **Outcome (2.14): BINDING_FAILURE**, with FALSE_SUPPRESSION and UNRESOLVED_RECALL_FAILURE also failing; the historical-state family was handled.
   - 5f. **G-STATE (2.14)**, harness-only: whether a dated transition establishes a continuing resultant state. It is designed and pre-registered, then reviewed before any live call. **Outcome (2.15): BINDING_FAILURE**, dominated by the null-cue harness defect; not evidence against the semantic idea.
   - 5g. **G-STATE2 (2.15)**, harness-only: the binding-only rerun (`string | null` optional cues), with everything semantic frozen. **Outcome (2.16): UNSAFE_EVENT_ONLY**; the null defect is closed as repaired, and prompt sensitivity is recorded.
   - 5h. **G-INVAR (2.16)**, harness-only: semantic invariance of borderline classifications under meaning-equivalent prompt forms. It is designed and pre-registered, then reviewed before any live call. **Outcome (2.17): BOUNDARY_INSTABILITY.**
   - 5i. **Boundary uncertainty/escalation policy (2.17):** a decision policy over existing evidence assessments (use / investigate / abstain). Design first, with no major implementation.
   - 5j. **Fresh end-to-end comparison (2.17):** the governed pipeline against a simpler baseline, on a fresh blind set, before any diagnostic gate becomes permanent runtime machinery.
6. **R1 with cross-source assessment** on the mechanism route, in the execution pattern G-COST supports (G-XS, G-MF, G-TIME). **Gated (2.6)** by two separate questions: G-R2's result on multi-finding representation, and a redesigned, trustworthy proposition-level cross-source assessor. **Blocked (2.7)** until all four R1 prerequisites hold: richer representation shown to add value, G-REL, G-FID, and a measured compatible cost.
7. **Explanation construction** (Layer 5, D7): validated in the G-MF runs, promoted only after G-WHOLE, and shipped as its own step.
8. **Candidates, each when its gate passes:** G-DATE, G-A3, G-O3, G-CAP.

If any step-8 component fails, the architecture stands and only that component returns to design. **The return point for the original objective is M-DEMAND (§9).**

### 7a. Migration boundaries established by G-SCHEMA

These boundaries stay in force until a later gate changes one explicitly (Marcus, 2026-09-12).
- **Claim-dependent measurements stay per finding.** Authority states and tiers, claim-source relationships, available admissible evidence, and every other policy field that depends on the finding's claim-source relationship live in that finding's entry. Only `RUN_LEVEL_EVALUATION_KEYS` are stated once. None is promoted to run-level state.
- **The Markdown export refuses multi-finding reports** (`multi_finding_report_export_not_migrated`) until its Layer 5 semantics are designed.
- **Chat review and count semantics are unchanged.** `conversational_research_review` and `_research_report_message` keep counting rows as today. What those counts mean for an atomic explanation is decided with Layer 5 (steps 6–7), before any multi-finding report reaches chat.
- **The answer judge is unchanged.** It reads the first finding, and its 700-character bound stays frozen.
- **Legacy reports carry no path provenance or migration metadata** (2.3).
- **The multi-finding report builder stays unwired.** `_multi_finding_report_fields` has no production call site.

---

## 8. Consistency review against the source (design-only, 2026-09-12)

| # | Checked | Finding | Resolution in v2 |
|---|---|---|---|
| 1 | Grounded support and refutation vs R1 | Production's single call assesses **every offered source** against the claim (`assessment_cap` = source count, adapter `:933`); that is where corroboration and refutation come from. R1 as tested verifies each step **only against its own passage** (`mech_multistep.verify_and_ground`), and the harness dedupe kept only the first occurrence | Cross-source assessment added (Layer 3, step 5); **G-XS is blocking**; dedupe merges support |
| 2 | Six single-finding sites | All six confirmed; `architecture_outcome_evaluation.py:43` is unrelated | Unchanged |
| 3 | Validator | Findings path is ok with ≥1 admitted row, and no recommendation is needed (`:2081-2086`). Rows cut at 8 **before** counting (`:1753`, `:2263`), so truncation is invisible. Title required; duplicate titles rejected; rows are "inference"; rendered disclaimer "not independently verified" | Reported cap; the claim stands in for the title; the disclaimer is kept in Layer 5 |
| 4 | Synthesis schema and retry | Retry keeps the first-pass `passage_index` (identity holds) but re-offers at most one passage per source (exposure shrinks). The demand path uses the same findings-only prompt | G-RETRY; explicit routing that excludes demand and non-mechanism objectives from R1. **Correction (2.2):** the retry change itself sits on the shared findings-only path, so it now explicitly excludes demand, which keeps the one-passage retry |
| 5 | Citation completion | Single-finding only; preserves `model_payload`; `MAX_FINDING_CITATION_IDS` = 6 | Per-finding loop; G-N1 |
| 6 | Policy | `evaluate_policy` judges the verdict over the finding's own citations, with pool fields reported separately; `enforced: False` | Per-finding list plus run-level pool fields; D6; blocking vs measured stated in §3b (2.2) |
| 7 | Report readers | `bounded_research_history` projects `evidence_policy_evaluation` and `citation_completion` as single mappings; `conversational_research_actions` counts rows | G-SCHEMA; contract version bump |
| 8 | Answer judge | Input truncated at 700 characters (adapter `:549`); needs ≥5 s left, 30 s maximum. **Harness judge results were bounded the same way** | The bound made explicit and truncation reported; caveat added to §1; G-WHOLE added before promotion (2.2) |
| 9 | Demand | `model_assessed_conclusion` requires one finding, and any assessment with another claim denies | Unchanged in v1 (D4); routing excludes it; M-DEMAND tracks the demand objective (2.2) |
| 10 | Runtime budget | The synthesis deadline is 300 s minus the time retrieval already spent; the judge needs ≥5 s | G-COST before R1 (2.2); G-TIME measures the time left at synthesis start and per-stage cost (D3) |
| 11 | Training capture | Enabled by argument **or** `training_policy.research_enabled` (bawr `:925`) | The mechanism route bypasses both, with a fixed status (D5) |
| 12 | Routing | `requested_relation` maps "how…" and "works" to `mechanism` (`:754`); "why" maps to `explanation` (untested) | R1 only for `mechanism` in v1 |

---

## 9. Acceptance milestones

The migration exists to produce a usable research system. Gates prove components; milestones prove the system does what it was built for.

**M-MECH — mechanism research v1.** G-MF, G-TIME and G-WHOLE pass on the mechanism route, and the step-7 explanation is promoted. This is the controlled testing ground, and it is where this migration's evidence comes from.

**M-DEMAND — the original objective (tracked return point).** Eidolon evaluates SaaS demand, competition, implementation dependencies and free-tier feasibility for real candidates. That is the seven-domain demand trial that started this work.
- **Success at M-MECH does not demonstrate M-DEMAND.** Demand has different semantics: independence requirements, customer evidence, promotional and vendor restrictions, currency and multiple-publisher requirements.
- **Return point:** after M-MECH, or earlier if Marcus directs.
- **Prerequisites:**
  1. diagnose the pre-existing `v2730_demand_support` failure, which fails on untouched `03aa99a` and is kept off the migration branch;
  2. decide, from a concrete demand use case, whether demand benefits from atomic findings (D4) and from the full-set repair retry;
  3. re-run the demand trial with the architecture's observation and presentation fixes under the unchanged demand gates.
- **Acceptance** is the demand trial's own pre-registered criteria, not the mechanism gates.
