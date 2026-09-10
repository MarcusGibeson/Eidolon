# Eidolon

Current source: **v2730.9.3 Native Review Repairs and Operator Execution**.

Current repair scope: public research subjects, exact repair bindings, atomic policy/receipt state, governed local operator execution, and Windows verification. See [operator instructions](docs/REVIEW_REPAIRS_V2730_9_3.md). Live SaaS and self-development acceptance remains to be demonstrated; this source version alone is not certification.

Prior development checkpoint: v2730.9.2 introduced the experimental instruments. Independent native review identified gaps repaired in v2730.9.3. Intentional architecture debt remains and the live campaign is unstarted. Next: combined SaaS-development and supervised self-development live testing after native verification and operator installation.

## Operator quick start

- Windows setup: `powershell -ExecutionPolicy Bypass -File setup.ps1`
- Linux or macOS setup: `bash setup.sh`
- Start the dashboard: `python eidolon.py dashboard`
- Run the bounded verifier: `python eidolon.py verify`
- Inspect training evidence: `python tools/eidolon_training_dataset.py status`

These commands do not grant installation, promotion, model-management, destructive-operation, or independent authority.

The v1500 human daily-use trial established supervised self-development and then exposed concrete conversation continuity failures. v1500.1 repairs identity, durable personal memory, family relationships, aliases, corrections, compound statements, and grounded uncertainty. v1500.2 consolidates those lessons into a reusable provider-neutral entity-association graph. v1500.3 connects that graph to ordinary conversation through a bounded grammar for project, file, provider, preference, and ownership facts. Direct questions use only user-attributable edges, unsupported questions fail with uncertainty, assistant text is excluded from evidence, and durable storage still requires an explicit remember request.

v1500.3.1 repairs the first live association trial: one short standalone association statement now receives a deterministic grounded acknowledgement instead of an unnecessary provider paraphrase. Mixed conversational statements continue through the ordinary conversation path.

v1500.4 adds a dedicated operator-private entity-association panel with structured inspection and exact correction, retraction, restore, and permanent deletion controls. Every mutation is bound to a revision-sensitive association ID; stale forms fail closed. Correction preserves lineage, retraction is reversible, and deletion requires a retracted record, exact `DELETE`, verified semantic cleanup, and a content-free tombstone.

v1500.5 connects that governed store to ordinary conversation. An explicit correction such as `Actually Project Neptune uses llama.cpp, not Ollama` updates the exact active durable association, while `Forget what Project Neptune uses` retracts it reversibly. Responses come from the actual mutation result without provider contact. The dashboard now preserves the active conversation and open association panel, returns to the edited record, and shows immediate working feedback during its slow refresh.

v1500.6 removes that slow refresh bottleneck. The live chat page no longer rescans every operation record for every conversation before first paint, no longer loads the active transcript twice, and limits the initial selector to 30 sessions. Recovery and attention state load asynchronously through existing read-only endpoints. Ordinary navigation now presents Chat, Memory, Development, Activity, Settings, and Advanced; the full historical operator catalog remains available inside Advanced.

v1500.7 makes the association graph usable in ordinary language. Role references such as `my mom`, `my dad`, and `my fiancee` resolve to attributable entities before relationship reasoning; direction-aware answers keep the requested subject first; singular `it` follow-ups resolve only from an unambiguous user-authored association. Newer durable single-value relationships supersede older conflicting edges across restart while retaining private lineage. Family and project association prompt blocks are now relevance-gated, so unrelated casual turns no longer carry the entire relationship graph.

v1500.8 keeps each response aimed at the newest message. Short follow-ups resolve against the latest completed turn, explicit corrections and topic shifts receive structural priority, and cancelled or failed replies never become continuity evidence. A provider-neutral output gate removes repeated sentences and catches strongly paraphrased repeats without making another model request. Content-free diagnostics expose when the gate acted while preserving conversation privacy and all existing authority boundaries.

v1500.9 consolidates the first operator-led daily-use trials. Self-reflection and milestone questions stay conversational and are grounded in Eidolon's actual supervised-development capabilities. Specific conversational mistakes remain answerable, rejected relational framing is not repeated, mixed casual-plus-command turns preserve the human context beside verified action receipts, and explicit repeated diagnostic commands route correctly. The full release verifier now uses a bounded current integration profile, while broad historical verification remains resumable through the segmented verifier.

v1500.9.1 repairs release self-knowledge exposed by the next live trial. Direct questions about v1500.9 now use authoritative local release evidence instead of generic model biography. An explicit request to inspect release metadata and README files is treated as one bounded, provider-free read-only action and can claim results only from its completed receipt. Missing evidence fails closed instead of producing invented NLP, safety, or documentation claims.

v1500.9.2 separates four conversational acts that the first repair still blurred together. Direct release questions receive grounded knowledge, evidence questions name the four allowlisted sources and their digest, explicit inspection requests execute through one governed receipt before showing results, and next-work questions use the authoritative v1501 objective with a concrete rationale. The exact four-message operator trial is now a deterministic end-to-end regression.

v1500.9.3 repairs the remaining wish-to-command boundary. Wishes, hopes, someday language, hypotheticals, suggestions, and explanatory questions no longer create supervised development proposals merely because they contain a coding verb. A mixed turn still extracts and routes one explicit imperative, and the proposal stores only that live command. The retained v1259 integration fixture now reflects the current governed conversational response while preserving exact authority checks.

v1501.0 turns read-only improvement discovery into a paced, restart-safe supervised initiative queue. When explicitly asked to compare three improvements, Eidolon ranks bounded source evidence by quality, value, novelty, effort fit, and risk, selects one, and records exactly one active initiative. Chat controls can inspect, defer, dismiss, or advance it to proposal review; none of those controls creates a proposal, contacts a provider, prepares a workspace, modifies source, grants approval, installs, or promotes anything.

v1501.0.1 repairs the first live queued implementation. Disposable workspaces now exclude retained installation backups and other generated source-only omissions, failed workspaces can be rebuilt under the same exact authorization, and immediate failure receipts name the actual bounded blocker instead of collapsing it to an exception class.

v1501.1 closes the missing final link in the supervised development cycle. Ordinary chat can review an exact isolated candidate, verify its persisted checks, syntax, workspace hashes, and active-target baseline, then install that review transactionally after an explicit candidate-bound command. A combined `Review and install candidate improvement-...` command is also accepted as exact operator authority for that named candidate. Installation keeps rollback copies outside source, rejects drift and stale digests, and replays completed receipts without duplicate writes.

v1501.2 turns the previously manual sequence into one resumable reversible cycle. `Continue your supervised development.` reconciles installed work, retains any in-progress initiative, or selects one distinct evidence-backed candidate; it then advances proposal creation, disposable workspace preparation, implementation, and verification exactly once. It always stops at operator review with active source unchanged. Replays return the existing boundary instead of duplicating work, while installation and promotion remain explicit operator decisions.

v1501.3 connects that cycle to a normalized, content-free evidence intake. Operator-confirmed defects, failing tests, diagnostics, performance regressions, conversation findings, missing capabilities, security debt, and structural debt now share attributable provenance, freshness, impact, practical-benefit, and acceptance-criteria fields. Structural extraction is capped and labeled as maintainability work instead of being presented as a demonstrated product capability; higher-impact evidence remains visible when it is not yet safely mapped to an implementable candidate.

The cumulative Mobile Browser campaign through v1599.9 layers operator evidence review, value-aware initiative selection, defect/feedback intelligence, bounded repair/retry, and restart-safe multi-cycle campaign coordination onto those existing governed paths. It does not create a second evidence store or execution engine and does not grant installation, promotion, provider, model-management, secret, destructive-operation, or authority-expansion rights.

Development from v1451 through v1488 completes the portable implementation and deterministic verification of Phase 16 security/privacy/authority hardening, Phase 17 model/provider intelligence, Phase 18 autonomous project operations, and the portable portion of Phase 19 reliability/adversarial validation.

The security arc adds canonical workspace containment, typed command policy, scoped network policy, secret redaction, untrusted-content isolation, supply-chain review, privacy classification, tamper-evident audit lineage, and incident-response planning without granting independent authority. Provider intelligence adds measured capability records, evidence-based native-certification contracts, privacy-aware routing, compact context construction, bounded structured-output recovery, streaming reconciliation, recovery guidance, quality calibration, and resource-aware pacing without model-management side effects.

Autonomous operations now include threshold-gated health work, reproduced-failure triage, bounded dependency/documentation/performance/data maintenance, source-only release preparation, project isolation, and self-update preflight through the existing candidate/shadow/canary/rollback model. v1480 is validated by an accelerated seven-day temporal replay; it does **not** claim seven wall-clock days elapsed in this harness.

Reliability validation through v1488 covers long-session transitions, restart recovery, resource pressure, provider failure, concurrency, upgrade/rollback, adversarial authority attacks, and held-out unfamiliar-project task fixtures. Native machine restarts and the v1489 human daily-use trial remain external evidence gates and are not fabricated by Linux fixtures.

Retained v1450 native baseline: **v1450.9 Desktop Alpha Checkpoint**.

Retained v1400 baseline: **v1400.9 Autonomous Developer Gamma Checkpoint**.

Retained v1250 roadmap markers: **v1250.3-v1250.5**, **v1250.6-v1250.8**, **v1250.9**, **ready_for_postponed_desktop_codex_review**.

Retained checkpoint lineage: **v1254.9**, **v1255.9**, **v1265.9**, **v1270.9**, **v1280.9**, **v1290.9**, and **v1300.9**.

<details id="retained-pre-v1250-compatibility">
<summary>Retained pre-v1250 verifier compatibility appendix</summary>

Current source: v1219.9 Conversational Supervised Repaired-Candidate Rollback

The post-v1200 supervised-development continuation now supports one exact, operator-authorized, transactional repaired-candidate rollback and returns its result for operator review. Installation, promotion, certification, release, model management, and independent authority remain unavailable.

Historical milestone: v1200.0 Cognitive Beta and Autonomous Developer Alpha

Archived heading: v1200.0 milestone

v1200 completes the scheduled Windows/Desktop decision gate and adds the first real, bounded developer-alpha execution path. Conversational action classification is now consistent across the ordinary runtime, CLI, and dashboard preview. The command below creates a private proposal without writing a workspace:

`python eidolon.py developer-alpha propose "Make me a web page with a calculator built into it" --json`

The returned proposal ID can be executed once only after explicit approval:

`python eidolon.py developer-alpha execute --proposal-id <proposal-id> --approve --json`

The approved alpha writes HTML, CSS, JavaScript, and arithmetic tests only beneath the external runtime `developer_alpha/workspaces` directory. It runs the JavaScript test with Node, records a private receipt, rejects unapproved execution, makes replay idempotent, and never writes Eidolon source or grants release authority. This is a demonstrated supervised transaction fixture, not code-generation evidence: the calculator files are deterministic literals used to test approval, isolation, validation, receipts, and replay. General coding evidence comes from the later `isolated_coding_execution.py` path and its provider-backed, disposable-workspace verification contracts.

Next: v1200.1-v1225 expands this narrow proven path into provider-generated implementation, broader test adapters, dashboard approval UX, and multi-project daily use without weakening operator authority.

Current source: v1199.9 Final Source-Only Candidate Checkpoint

Retained historical verifier markers: Current source: v1190.5 (historical only); v1190.3-v1190.5 Operator Navigation and Coordinated Experience Transitions; Current source: v1190.8 (historical only); v1190.6-v1190.8 Unified Experience Reliability and Privacy Hardening; v1190.9 Unified Experience checkpoint.

Archived heading: v1199.9 Final Source-Only Candidate Checkpoint

This read-only checkpoint consolidates v1199.2 final-candidate preparation, v1199.5 operator review, and v1199.8 reliability hardening into one source-discovered handoff surface. It preserves the source manifest, retained verification, unresolved-risk ledger, Desktop Codex handoff, native-provider handoff, privacy boundary, authority boundary, exact review lineage, exact reliability lineage, and inherited-debt truth.

No candidate or handoff is accepted, no risk is waived, no verifier is executed by the product contract, and no installation, promotion, certification, publication, release, provider/model contact, source/runtime mutation, automatic recovery, global-profile pass claim, or authority grant occurs.

Next: the separate **v1200 Cognitive Beta and Autonomous Developer Alpha decision gate**, including Desktop Codex review, native-provider review, current verification, historical-debt accounting, privacy and authority review, upgrade/rollback evidence, long-session evidence, responsiveness and cancellation evidence, and an explicit operator decision. Reaching v1200 source does not itself install, promote, certify, publish, release, or grant independent authority.

Current source: v1199.8 Final Candidate Reliability and Handoff Hardening

Archived heading: v1199.6-v1199.8 Final Candidate Reliability and Handoff Hardening

Adds read-only, content-free reliability evidence for candidate manifest drift, retained verification drift, unresolved-risk drift, Desktop and native-provider handoff drift, privacy and authority boundary drift, and review replay. The candidate remains unaccepted, risks remain unwaived, and no global-profile pass, installation, promotion, certification, publication, release, or authority grant is inferred.

Next bounded unit: v1199.9 Final Source-Only Candidate checkpoint. The v1200 Desktop Codex and native-provider decision gate remains required.

Archived heading: v1199.5 Operator Final-Candidate Review and Handoff Acceptance

Current source: v1199.5. This read-only bundle adds approve, reject, and defer review across final candidate acceptance, retained verification, unresolved risks, Desktop Codex handoff, and native-provider handoff. All outcomes are presentation-only. No candidate is accepted, risk is waived, approval is consumed, or installation, promotion, certification, publication, release, provider contact, mutation, automatic continuation, or authority grant occurs. The next bounded unit is v1199.6-v1199.8 Final Candidate Reliability and Handoff Hardening. The v1200 Desktop Codex and native-provider decision gate remains mandatory.

Archived heading: v1199.2 Final Source-Only Candidate Preparation Foundations

Current source: v1199.2 Final Source-Only Candidate Preparation Foundations.

This bundle adds content-free final-candidate preparation evidence for source manifests, retained verification, unresolved risks, Desktop Codex handoff, native-provider handoff, privacy boundaries, authority boundaries, and release boundaries. It does not prepare, promote, certify, publish, release, install, or grant authority to a candidate.

Next bounded unit: v1199.3-v1199.5 Operator Final-Candidate Review and Handoff Acceptance.

The v1200 Desktop Codex and native-provider decision gate remains unchanged.

Current source: v1198.9 Feature Freeze and Architecture Consolidation Checkpoint

Feature freeze, architecture ownership, operator review, performance, documentation, and verifier reconciliation are consolidated in one read-only, content-free checkpoint.

Next bounded unit: v1199.0-v1199.2 Final Source-Only Candidate Preparation Foundations.

No files are moved, merged, deleted, or rewritten. No profiling, verifier execution, freeze exception, approval consumption, installation, promotion, certification, publication, release, or authority expansion occurs. No global quick/full-profile pass is claimed.

Retained historical markers: v1198.2 Feature Freeze and Architecture Consolidation Foundations; v1198.3-v1198.5 Operator Freeze Exceptions and Consolidation Review; v1198.6-v1198.8 Performance, Documentation, and Verifier Reconciliation Hardening; v1198.9 Feature Freeze and Architecture Consolidation Checkpoint.

Current source: v1198.8 Performance, Documentation, and Verifier Reconciliation Hardening

Feature freeze remains active. Performance, documentation, verifier registration, ownership, historical truth, and inherited debt are reconciled through bounded read-only evidence. No profiling or verifier execution, source consolidation, exception application, release, or authority grant occurs.

Next bounded unit: v1198.9 Feature Freeze and Architecture Consolidation checkpoint.

Retained historical markers: v1198.2 Feature Freeze and Architecture Consolidation Foundations; v1198.3-v1198.5 Operator Freeze Exceptions and Consolidation Review; v1198.5 checkpoint surface; v1198.6-v1198.8 Performance, Documentation, and Verifier Reconciliation Hardening.

Retained checkpoint markers: v1197.9 runtime lifecycle checkpoint; v1196.9 adversarial privacy and authority checkpoint; v1195.9 long-session soak checkpoint; v1194.9 unified cognitive and developer experience checkpoint; v1193.9 verifier ownership checkpoint; v1192.9 evidence compaction checkpoint; v1191.9 responsiveness checkpoint; v1190.9 unified experience checkpoint.

Retained roadmap arcs: v1196.0-v1196.2 Adversarial Privacy and Authority Foundations; v1197.0-v1197.2 Runtime Migration Foundations; v1198.0-v1198.2 Feature Freeze and Architecture Consolidation Foundations.

Retained roadmap marker: v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations.

Archived heading: Retained Verifier Compatibility Text

Current source: v1190.9 (historical verifier marker only)

v1190.9 Unified Experience Checkpoint

v1191.0-v1191.2 Responsiveness and Background-Work Foundations

Current source: v1191.8 (historical verifier marker only)

Current source: v1191.9 (historical verifier marker only)

v1191.9 Responsiveness and Background Work Checkpoint

The ordinary-chat bridge remains a proposal-only software-development campaign. Windows CRLF handling preserves byte-accurate rollback evidence.

v1192.0-v1192.2 Bounded Evidence Compaction Foundations

Current source: v1192.5 (historical verifier marker only)

Current source: v1192.8 (historical verifier marker only)

v1192.9 Bounded Evidence Compaction Checkpoint

The retained checkpoint preserves exact expansion and equivalence plus approve/reject/defer operator review. Original evidence is never replaced, deleted, or rewritten.

v1193.0-v1193.2 Verifier Ownership and Historical-Debt Foundations

Current source: v1193.9 (historical verifier marker only)

v1193.9 Verifier Ownership and Historical-Debt Consolidation Checkpoint

The retained checkpoint preserves deterministic focused/quick/full profile membership and budgets, partial-overlap deferral, and does not execute suites, delete fixtures, retire verifiers, or claim a global quick/full-profile pass.

v1194.0-v1194.2 Unified Cognitive and Developer Experience Foundations

v1194.9 Unified Cognitive and Developer Experience checkpoint

v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations

v1195.9 Long-Session and Multi-Day Soak checkpoint

v1196.0-v1196.2 Adversarial Privacy and Authority Foundations

v1196.9 Adversarial Privacy, Authority, Replay, and Recovery checkpoint

v1197.0-v1197.2 Runtime Migration Foundations

v1197.9 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install checkpoint

v1198.0-v1198.2 Feature Freeze and Architecture Consolidation Foundations

v1198.3-v1198.5 Operator Freeze Exceptions and Consolidation Review

v1198.6-v1198.8 Performance, Documentation, and Verifier Reconciliation Hardening

v1198.9 Feature Freeze and Architecture Consolidation Checkpoint

v1199.0-v1199.2 Final Source-Only Candidate Preparation Foundations

Desktop Codex and native-provider review remain scheduled for v1200.

Current source: v1189.9 (historical verifier marker only)

v1189.9 Persistent Supervised Developer Alpha Hardening Checkpoint

v1190.0-v1190.2 Unified Experience Foundations

</details>
