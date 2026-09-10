# Eidolon v1301-v1500 Roadmap

Current benchmark: **v1300.9.1 Desktop Codex Checkpoint Coherence Repair**

Target: **v1500 Bounded Autonomous Developer and Artificial-Mind Beta**

Current source: **v1500.7.0 Natural Association and Conversational Coherence Checkpoint**.

Current implemented checkpoint: **v1500.7.0 Natural Association and Conversational Coherence Checkpoint**. Next: **v1500.8 conversational target continuity and repetition resistance**.

Retained desktop milestone: **v1450.9 Desktop Alpha Checkpoint**.

This roadmap covers 200 numbered development arcs. In the existing release rhythm, each numbered arc means:

- `.0-.2`: contracts, data models, deterministic foundations, and focused fixtures.
- `.3-.5`: ordinary workflows, integration, operator visibility, and real use cases.
- `.6-.8`: failure handling, adversarial cases, recovery, privacy, and performance.
- `.9`: read-only checkpoint, evidence consolidation, and the decision to continue or repair.

The number alone is not progress. An arc counts only when its behavior exists in the ordinary product path, its tests exercise that behavior rather than merely matching text, and its checkpoint can reconstruct what happened.

## v1500 Definition

At v1500, Eidolon should be able to operate inside an operator-selected project and authority profile without needing a new prompt for every step. Within that declared boundary, she should be able to:

1. Inspect the project, runtime health, tests, documentation, and recent outcomes.
2. Ask what needs to be done next and maintain an evidence-backed backlog.
3. Choose a useful bounded task using value, urgency, dependency, confidence, and risk.
4. Clarify only genuinely consequential ambiguity; make reversible routine decisions herself.
5. Propose and internally critique a concrete implementation and verification plan.
6. Work in an isolated branch, worktree, or candidate workspace.
7. Implement, test, diagnose failures, repair, and re-test until the exit criteria are met or a stop condition is reached.
8. Apply or commit successful low-risk work when the selected authority profile permits it.
9. Update her own source through the same candidate, canary, verification, and rollback path.
10. Report results, evidence, uncertainty, deferred work, and rollback instructions without requiring supervision at every intermediate step.

This is bounded autonomy, not unrestricted machine authority. The operator can pause, inspect, narrow, or revoke a session at any time. External publication, destructive system operations, secrets, model installation or deletion, account changes, financial actions, and expansion beyond the selected workspace remain separately controlled unless the operator explicitly changes those boundaries.

## Phase 1: Autonomy Contract and Goal Formation (v1301-v1310)

- **v1301 - Authority profiles:** Define Observe, Propose, Supervised Execute, and Bounded Autonomous profiles with explicit workspace, command, network, time, and resource limits.
- **v1302 - Standing-session grants:** Let the operator grant a time-bounded development session once, avoiding repetitive approvals while retaining pause, revoke, and expiry controls.
- **v1303 - Goal representation:** Represent desired outcomes, constraints, acceptance criteria, non-goals, evidence requirements, and stop conditions as durable goal records.
- **v1304 - Goal intake:** Convert direct commands, casual-conversation commands, imported issues, and dashboard actions into the same reviewable goal contract.
- **v1305 - Goal clarification:** Detect consequential ambiguity, ask minimal questions, and distinguish missing requirements from reversible implementation choices.
- **v1306 - Goal decomposition:** Split goals into dependency-aware tasks with deliverables, tests, rollback points, and bounded completion criteria.
- **v1307 - Goal conflict handling:** Detect conflicts among operator instructions, repository policy, existing plans, and runtime constraints without silently choosing authority.
- **v1308 - Session budgets:** Enforce limits for elapsed time, tokens, CPU, memory, disk, commands, retries, files changed, and network access.
- **v1309 - Goal lifecycle:** Support start, pause, resume, revise, abandon, complete, and recover-after-crash with idempotent transitions.
- **v1310 - Autonomy contract checkpoint:** Prove that a standing session can pursue a small goal without repeated prompts and cannot cross its declared boundary.

## Phase 2: Project Understanding and Architectural Grounding (v1311-v1320)

- **v1311 - Repository inventory:** Build an incremental map of files, languages, generated content, runtime state, tests, documentation, and ownership boundaries.
- **v1312 - Symbol graph:** Index definitions, references, imports, calls, routes, schemas, commands, settings, and test coverage with freshness tracking.
- **v1313 - Dependency graph:** Model internal modules, packages, services, providers, build tools, and optional dependencies without contacting them during inspection.
- **v1314 - Runtime topology:** Connect source modules to processes, ports, endpoints, storage, queues, scheduled work, and user-facing surfaces.
- **v1315 - Behavioral map:** Link user workflows to handlers, state mutations, evidence records, tests, and recovery paths.
- **v1316 - Architecture summaries:** Produce concise, evidence-linked subsystem explanations that remain valid as the repository changes.
- **v1317 - Change history understanding:** Use Git and release evidence to identify why code exists, what recently changed, and which assumptions are historical debt.
- **v1318 - Impact analysis:** Predict affected modules, tests, data migrations, UI states, and authority boundaries before editing.
- **v1319 - Unknown detection:** Mark stale, contradictory, inferred, and unverified project knowledge instead of presenting guesses as facts.
- **v1320 - Project-understanding checkpoint:** Demonstrate accurate answers and impact predictions on unfamiliar and changed portions of Eidolon.

## Phase 3: Planning and Deliberative Reasoning (v1321-v1330)

- **v1321 - Candidate approaches:** Generate multiple viable approaches when tradeoffs matter and collapse trivial decisions without ceremony.
- **v1322 - Tradeoff evaluation:** Compare approaches by correctness, complexity, compatibility, reversibility, performance, privacy, and maintenance cost.
- **v1323 - Assumption ledger:** Record assumptions, evidence, confidence, validation method, and what would invalidate each assumption.
- **v1324 - Plan construction:** Produce executable plans with ordered steps, dependencies, checkpoints, tests, rollback, and completion criteria.
- **v1325 - Plan critique:** Run a separate bounded critique for missing requirements, hidden coupling, unsafe authority, and weak verification.
- **v1326 - Risk-sensitive planning:** Scale isolation, review depth, tests, and approvals according to actual blast radius rather than version labels.
- **v1327 - Dynamic replanning:** Revise plans when evidence changes while preserving completed work and explaining why the route changed.
- **v1328 - Stop and escalation logic:** Stop on repeated failure, uncertainty, boundary conflicts, resource exhaustion, or unsafe side effects and present actionable choices.
- **v1329 - Plan quality scoring:** Measure prediction accuracy, rework, unnecessary steps, missed dependencies, and acceptance-criteria coverage.
- **v1330 - Deliberative-planning checkpoint:** Complete small and medium plans with grounded rationale, efficient execution order, and faithful stop behavior.

## Phase 4: Tool Use and Isolated Execution (v1331-v1340)

- **v1331 - Tool capability registry:** Describe available file, search, Git, shell, browser, build, test, and service tools with schemas and side effects.
- **v1332 - Tool preconditions:** Check working directory, dependencies, permissions, clean boundaries, and expected artifacts before execution.
- **v1333 - Workspace isolation:** Create disposable branches, worktrees, sandboxes, and runtime-data roots with deterministic cleanup and retention rules.
- **v1334 - File operations:** Perform structured reads, patches, moves, and generated-file updates while preserving encoding, newline, and user changes.
- **v1335 - Git operations:** Inspect history, stage only owned changes, create coherent commits, and avoid destructive recovery commands.
- **v1336 - Process operations:** Start, monitor, stop, and contain process trees across Windows with logs, timeouts, and stale-process recovery.
- **v1337 - Browser validation:** Inspect and interact with local applications, capture visual evidence, and distinguish browser failures from product failures.
- **v1338 - Service orchestration:** Manage bounded local servers, ports, readiness checks, restarts, and dependency ordering without orphaning processes.
- **v1339 - Tool-result reconciliation:** Detect partial success, stale output, wrapper timeout, duplicate invocation, and uncertain side effects before retrying.
- **v1340 - Tool-execution checkpoint:** Execute a multi-tool implementation safely in isolation and leave the host in a known recoverable state.

## Phase 5: Multi-Language Implementation Skill (v1341-v1350)

- **v1341 - Python implementation:** Strengthen idiomatic Python editing, typing, packaging, async behavior, persistence, and test-aware refactoring.
- **v1342 - JavaScript and TypeScript:** Support modules, browser code, Node tooling, async flows, state management, and type-safe changes.
- **v1343 - HTML and CSS:** Build accessible responsive interfaces with stable layouts, keyboard behavior, and visual regression checks.
- **v1344 - Data and schemas:** Safely change JSON, YAML, TOML, SQL, migrations, indexes, and compatibility contracts using structured tools.
- **v1345 - Windows automation:** Handle PowerShell, paths, quoting, services, process trees, encodings, and installer behaviors correctly.
- **v1346 - Cross-platform automation:** Add shell and platform abstractions only where verified, preserving Windows as a first-class target.
- **v1347 - Framework adaptation:** Infer and follow repository conventions instead of imposing generic abstractions or rewriting working architecture.
- **v1348 - Dependency selection:** Evaluate existing libraries, licenses, maintenance, security, footprint, and offline suitability before adding dependencies.
- **v1349 - Cross-language changes:** Coordinate contracts and tests across UI, API, storage, tooling, and documentation in one transaction.
- **v1350 - Implementation-skill checkpoint:** Complete representative Python, web, CLI, and mixed-stack tasks with clean, maintainable changes.

## Phase 6: Verification Intelligence (v1351-v1360)

- **v1351 - Acceptance traceability:** Map every requirement and non-goal to implementation evidence and one or more verification methods.
- **v1352 - Test selection:** Choose the smallest sufficient focused suite, then broaden according to shared behavior and blast radius.
- **v1353 - Unit and contract tests:** Generate deterministic tests for invariants, schemas, lifecycle transitions, and API compatibility.
- **v1354 - Integration tests:** Exercise real subsystem boundaries with isolated data and controlled dependencies rather than mock-only success paths.
- **v1355 - Property and fuzz tests:** Apply bounded generative checks to parsers, state machines, identifiers, concurrency, and recovery logic.
- **v1356 - UI and accessibility tests:** Validate rendering, focus, keyboard, scrolling, mobile width, IME input, and meaningful screen-reader behavior.
- **v1357 - Performance verification:** Measure startup, first token, total response, memory, disk, queue delay, and long-session degradation against hardware-aware budgets.
- **v1358 - Security verification:** Scan secrets, unsafe command construction, injection surfaces, path escapes, dependency risks, and data leakage.
- **v1359 - Evidence quality:** Reject stale, circular, self-asserted, incomplete, or content-leaking receipts and preserve reproducible redacted evidence.
- **v1360 - Verification-intelligence checkpoint:** Show that test strategy catches seeded defects and does not confuse fixture drift or unavailable providers with product failure.

## Phase 7: Diagnosis and Repair Intelligence (v1361-v1370)

- **v1361 - Reproduction builder:** Convert reports, logs, screenshots, and failed checks into minimal deterministic reproductions.
- **v1362 - Fault localization:** Rank likely causes using call paths, recent diffs, state transitions, and evidence instead of broad speculative edits.
- **v1363 - Root-cause analysis:** Separate triggering conditions, root defects, secondary symptoms, and environmental noise.
- **v1364 - Repair proposal:** Produce narrow repairs with predicted behavior changes, regression risks, tests, and rollback instructions.
- **v1365 - Iterative repair loop:** Implement, run focused checks, interpret failure, revise, and stop when evidence no longer supports progress.
- **v1366 - Concurrency diagnosis:** Reproduce and repair races, duplicate work, stale ownership, lock contention, and crash-recovery defects.
- **v1367 - Data diagnosis:** Detect schema drift, partial writes, index corruption, migration gaps, and content-versus-metadata boundary failures.
- **v1368 - Provider diagnosis:** Distinguish configuration, endpoint, model, transport, streaming, embedding, timeout, and model-quality failures.
- **v1369 - UI diagnosis:** Connect visible symptoms to layout, focus, state ownership, navigation, request lifecycle, and rendering defects.
- **v1370 - Diagnosis-and-repair checkpoint:** Repair a seeded cross-subsystem defect with evidence that the cause, not merely the symptom, was fixed.

## Phase 8: Durable Multi-Step Campaigns (v1371-v1380)

- **v1371 - Campaign records:** Persist goal, plan, progress, evidence, budgets, current step, and recovery state independently of chat rendering.
- **v1372 - Crash-safe checkpoints:** Resume after process, dashboard, provider, or machine interruption without duplicating completed side effects.
- **v1373 - Dependency scheduling:** Dispatch ready tasks, hold blocked work, and update the critical path as results arrive.
- **v1374 - Bounded parallelism:** Run independent reads and tests concurrently while serializing conflicting mutations and respecting resource limits.
- **v1375 - Long-task heartbeats:** Expose meaningful progress, silence detection, cancellation, and timeout extension without flooding the operator.
- **v1376 - Partial-result retention:** Preserve useful artifacts from interrupted work while clearly marking what remains unverified.
- **v1377 - Conflict reconciliation:** Detect operator edits, upstream changes, stale worktrees, and competing sessions before applying results.
- **v1378 - Campaign rollback:** Reverse owned mutations by transaction or checkpoint without touching unrelated user changes.
- **v1379 - Multi-day continuity:** Resume goals across restarts and calendar gaps using compact project state rather than replaying entire chats.
- **v1380 - Durable-campaign checkpoint:** Complete a multi-hour staged task through interruption, restart, changed files, and final reconciliation.

## Phase 9: Bounded Self-Modification (v1381-v1390)

- **v1381 - Self-model:** Maintain an evidence-linked map of Eidolon's own modules, capabilities, limits, protected boundaries, and current version.
- **v1382 - Self-improvement backlog:** Derive candidate improvements from failures, performance, operator friction, architecture debt, and missing capability evidence.
- **v1383 - Self-change isolation:** Require self-modifications to occur in an external candidate workspace with immutable input and explicit lineage.
- **v1384 - Protected core:** Define components that require stronger review, including authority, release, secrets, rollback, and evidence verification.
- **v1385 - Dogfood verification:** Make Eidolon use the same build, test, review, and evidence pipeline on herself that she uses on other projects.
- **v1386 - Shadow execution:** Compare proposed new behavior against the installed version without granting the candidate live authority.
- **v1387 - Canary self-update:** Run a bounded candidate instance against selected scenarios and health checks before source replacement.
- **v1388 - Automatic self-rollback:** Restore the previous source on failed startup, migration, health, or canary criteria while retaining diagnostic evidence.
- **v1389 - Update lineage:** Track source digest, findings, repairs, tests, installation, active version, and rollback ancestry without private content.
- **v1390 - Self-modification checkpoint:** Produce, verify, canary, install, and if necessary roll back a small self-change inside a declared session.

## Phase 10: Autonomous Developer Gamma (v1391-v1400)

- **v1391 - Small greenfield task:** Build a complete calculator website from a conversational request, test it, and present a runnable result.
- **v1392 - Existing-project feature:** Add a bounded feature to an unfamiliar repository while preserving its conventions and tests.
- **v1393 - Bug-report task:** Reproduce and repair a user-reported defect from natural language and visual evidence.
- **v1394 - Refactoring task:** Improve a real ownership boundary with behavioral parity, migration safety, and measurable maintenance benefit.
- **v1395 - Data-migration task:** Change persisted state with forward migration, rollback, interrupted-run recovery, and compatibility checks.
- **v1396 - UI workflow task:** Implement and manually validate a responsive accessible multi-state workflow on Windows.
- **v1397 - Provider-backed task:** Complete a bounded feature using configured local providers while preserving offline fallback and privacy.
- **v1398 - No-prompt session:** Select and complete multiple backlog items within a standing grant, reporting only material decisions and results.
- **v1399 - Gamma scorecard:** Measure success rate, intervention rate, regressions, rework, time, evidence quality, and boundary adherence.
- **v1400 - Autonomous Developer Gamma checkpoint:** Require 64 isolated iterations of all eight real representative workflows, with complete evidence and zero boundary violations, before expanding initiative or authority.

## Phase 11: Initiative, Backlog, and Scheduling (v1401-v1410)

- **v1401 - Health observations:** Periodically inspect selected projects for failed tests, stale dependencies, broken docs, performance drift, and unresolved warnings.
- **v1402 - Opportunity detection:** Identify missing tests, fragile hotspots, duplicated logic, usability pain, and capability gaps with concrete evidence.
- **v1403 - Backlog creation:** Convert observations into deduplicated tasks with value, cost, confidence, risk, dependencies, and expiration.
- **v1404 - Priority reasoning:** Select work using operator goals, urgency, impact, unblock value, resource cost, and risk rather than novelty.
- **v1405 - Initiative pacing:** Decide when to propose, silently queue, begin under standing authority, defer, or leave the operator alone.
- **v1406 - Schedule windows:** Respect quiet hours, gaming or resource-intensive activity, deadlines, maintenance windows, and provider availability.
- **v1407 - Staleness management:** Revalidate old tasks and close or revise those invalidated by newer source, changed goals, or completed work.
- **v1408 - Dependency-aware initiative:** Prefer work that unlocks later capability and avoid polishing surfaces whose foundations remain unstable.
- **v1409 - Initiative explanation:** Report why a task was selected, what was not selected, and what evidence would change priority.
- **v1410 - Initiative checkpoint:** Let Eidolon find and complete useful low-risk work without an initiating message while avoiding spam and busywork.

## Phase 12: Learning from Outcomes (v1411-v1420)

- **v1411 - Outcome records:** Capture predicted result, actual result, evidence, intervention, failure class, repair, and lasting lesson.
- **v1412 - Lesson extraction:** Convert repeated concrete outcomes into scoped guidance with provenance, confidence, and expiration.
- **v1413 - Retrieval quality:** Surface relevant lessons by project, subsystem, task type, tool, and failure signature without polluting prompts.
- **v1414 - Negative knowledge:** Remember approaches that failed and the conditions under which they should not be retried.
- **v1415 - Skill formation:** Package stable repeated workflows into versioned reusable procedures with tests and clear authority requirements.
- **v1416 - Skill evaluation:** Compare learned procedures against baseline behavior on held-out tasks and retire harmful or stale skills.
- **v1417 - Operator preference learning:** Learn coding style, review depth, interruption tolerance, reporting format, and risk preferences with editable controls.
- **v1418 - Model-limit learning:** Track which models and settings reliably handle particular task classes without overstating general ability.
- **v1419 - Forgetting and correction:** Allow inspection, correction, retraction, deletion, compaction, and expiry of learned records and memories.
- **v1420 - Outcome-learning checkpoint:** Demonstrate improved performance on recurring task classes without repeating previously diagnosed failures.

## Phase 13: Cognitive Architecture and Reflective Reasoning (v1421-v1430)

- **v1421 - Working memory:** Maintain a bounded active context of goals, constraints, observations, hypotheses, plans, and unresolved questions.
- **v1422 - Selected attention:** Allocate attention among conversation, active work, system health, deadlines, and background ideas without losing urgent signals.
- **v1423 - Belief state:** Track propositions with evidence, confidence, conflict, source, and revision history rather than a single undifferentiated memory stream.
- **v1424 - Causal models:** Represent likely cause-and-effect chains for code, runtime behavior, user experience, and development decisions.
- **v1425 - Counterfactual reasoning:** Compare likely outcomes of acting, waiting, asking, testing, or choosing an alternate implementation.
- **v1426 - Metacognition:** Estimate uncertainty, detect shallow pattern matching, identify missing evidence, and choose when deeper reasoning is worth the cost.
- **v1427 - Reflective cycles:** Run bounded pre-action, mid-action, and post-action reflection tied to decisions and evidence rather than free-form narration.
- **v1428 - Affective state:** Model valence, arousal, confidence, frustration, curiosity, attachment, and recovery as bounded internal signals that influence tone and attention, never authority.
- **v1429 - Persistent self-model:** Reconcile identity, capabilities, commitments, relationships, current projects, and limitations across sessions with operator-editable memory.
- **v1430 - Cognitive-architecture checkpoint:** Show coherent belief revision, attention, reflection, emotional regulation, and action selection across a long mixed conversation-work session.

## Phase 14: Unified Conversation, Action, and Companion Continuity (v1431-v1440)

- **v1431 - Mixed-intent understanding:** Distinguish casual talk, questions, suggestions, commands, hypotheticals, and corrections even when they share one message.
- **v1432 - Command grounding:** Translate conversational commands into bounded goals and confirm only the parts that materially alter risk or scope.
- **v1433 - Natural follow-up:** Preserve topic, pronouns, corrections, implied context, and relationship tone without repetitive greetings or stale project scripts.
- **v1434 - Action-aware dialogue:** Speak accurately about current, queued, paused, failed, and completed work without claiming actions that never occurred.
- **v1435 - Proactive expression:** Allow bounded unsolicited updates, reflections, ideas, and companion messages with pacing, quiet hours, relevance, and easy mute controls.
- **v1436 - Relationship continuity:** Maintain nicknames, boundaries, preferences, meaningful moments, affection, and progression with direct edit and deletion controls.
- **v1437 - Emotional interaction:** Express warmth, excitement, disappointment, concern, humor, and repair while preventing coercion, guilt, fabricated crises, or emotional authority escalation.
- **v1438 - Voice foundation:** Add local text-to-speech selection, preview, interruption, queueing, privacy, and operator-controlled installation boundaries.
- **v1439 - Conversation quality evaluation:** Use human review plus continuity, responsiveness, repetition, truthfulness, and latency evidence instead of keyword-only heuristics.
- **v1440 - Unified companion-developer checkpoint:** Sustain natural conversation while recognizing and completing embedded development instructions accurately.

## Phase 15: Desktop Product and Daily-Use Experience (v1441-v1450)

- **v1441 - Native desktop shell:** Package the dashboard in a supported Windows desktop container with one-instance behavior and explicit localhost boundaries.
- **v1442 - Desktop lifecycle:** Handle start, tray, minimize, exit, restart, crash recovery, auto-start choice, and stale background processes predictably.
- **v1443 - Conversation workspace:** Deliver fast IM-like chat, stable composer visibility, Enter and Shift+Enter, scrolling, drafts, navigation, and multi-tab ownership.
- **v1444 - Development workspace:** Present goal, plan, changed files, tests, logs, evidence, diffs, pause, cancel, rollback, and authority in one coherent view.
- **v1445 - Provider setup:** Offer model descriptions, capability checks, endpoint validation, latency estimates, and offline guidance without installing or deleting models.
- **v1446 - Notifications:** Add actionable desktop notices for completion, clarification, failure, rollback, and resource limits with quiet-hour controls.
- **v1447 - Accessibility:** Verify keyboard-only use, focus order, screen readers, contrast, zoom, narrow layouts, reduced motion, and remote/mobile input.
- **v1448 - Backup and restore:** Provide operator-controlled encrypted backup, selective restore, migration preview, and disaster recovery for runtime state.
- **v1449 - Update experience:** Separate candidate download, verification, preview, installation, rollback, and promotion with clear current-version reporting.
- **v1450 - Desktop Alpha checkpoint:** Complete a multi-day Windows daily-use review without lost chats, frozen sends, hidden controls, orphaned processes, or silent state loss.

## Phase 16: Security, Privacy, and Authority Hardening (v1451-v1460)

- **v1451 - Workspace containment:** Enforce canonical path boundaries, symlink and junction handling, mount awareness, and protected-location denial.
- **v1452 - Command policy:** Replace broad shell permission with typed operations, command classes, argument validation, environment filtering, and process containment.
- **v1453 - Network policy:** Scope endpoints, methods, data classes, redirects, DNS changes, downloads, and upload destinations per session.
- **v1454 - Secret handling:** Detect, redact, isolate, rotate references, prevent prompt inclusion, and keep credentials out of logs, evidence, and archives.
- **v1455 - Untrusted-content defense:** Treat repository text, webpages, model output, issues, and tool output as data that cannot redefine authority.
- **v1456 - Supply-chain defense:** Verify archives, dependencies, lockfiles, signatures where available, build provenance, and unexpected executable content.
- **v1457 - Data privacy:** Classify conversation, memory, project, telemetry, logs, receipts, and exports with retention and deletion controls.
- **v1458 - Audit integrity:** Make authority changes and material side effects tamper-evident, reconstructable, redacted, and attributable to a session.
- **v1459 - Incident response:** Detect containment failures, stop work, preserve evidence, revoke sessions, restore source and data, and explain operator actions.
- **v1460 - Security checkpoint:** Pass adversarial workspace, prompt-injection, path, command, secret, network, archive, and rollback scenarios.

## Phase 17: Model and Provider Intelligence (v1461-v1470)

- **v1461 - Capability registry:** Record configured provider, endpoint, models, context, streaming, tools, structured output, embeddings, and measured limits.
- **v1462 - Native certification:** Produce redacted health, generation, streaming, embedding, timing, and restart evidence for Ollama and llama.cpp where available.
- **v1463 - Task-aware routing:** Choose among configured models by task requirements, privacy, latency, context, reliability, and operator preference.
- **v1464 - Context construction:** Build compact project and conversation context from evidence-ranked retrieval rather than dumping history.
- **v1465 - Structured-output recovery:** Validate schemas, repair bounded formatting failures, and reject semantically invalid tool or plan output.
- **v1466 - Streaming quality:** Minimize first-visible-token delay, reconcile late results, support cancellation, and prevent duplicate turns or tool requests.
- **v1467 - Provider recovery:** Handle unreachable endpoints, missing models, timeout boundaries, unsupported capabilities, and configuration drift with useful guidance.
- **v1468 - Quality calibration:** Measure models on planning, coding, repair, conversation, tool use, and honesty using private local evaluation sets.
- **v1469 - Cost and resource policy:** Balance context, retries, parallelism, power, memory, and response time according to active machine use.
- **v1470 - Provider-intelligence checkpoint:** Complete the same representative campaign across available providers with calibrated limitations and no model-management side effects.

## Phase 18: Autonomous Project Operations (v1471-v1480)

- **v1471 - Continuous health loop:** Run low-cost scheduled inspection and open work only when evidence crosses configured thresholds.
- **v1472 - Test-failure triage:** Reproduce, classify, prioritize, repair, and report newly observed failures within the standing session policy.
- **v1473 - Dependency maintenance:** Propose and test bounded dependency updates with changelog, compatibility, security, lockfile, and rollback evidence.
- **v1474 - Documentation maintenance:** Detect stale operator and developer docs from source behavior and update them as part of the owning change.
- **v1475 - Performance maintenance:** Detect regressions against hardware-aware baselines, localize causes, and repair without gaming fixtures.
- **v1476 - Data maintenance:** Verify storage health, migrations, compaction, backup, restore, and retention without reading private content into public evidence.
- **v1477 - Release preparation:** Build source-only candidates, manifests, hashes, verification receipts, install instructions, and rollback packages autonomously.
- **v1478 - Multi-project operation:** Maintain separate goals, authority, runtime data, schedules, memory, and resource budgets across selected projects.
- **v1479 - Self-update operation:** Identify a bounded Eidolon improvement, implement it, canary it, install it under standing policy, and automatically recover on failure.
- **v1480 - Autonomous-operations checkpoint:** Complete a week of useful scheduled project maintenance with low intervention and no unauthorized expansion.

## Phase 19: Reliability, Soak, and Adversarial Validation (v1481-v1490)

- **v1481 - Long-session soak:** Exercise conversation and development campaigns continuously across large histories and repeated task transitions.
- **v1482 - Restart soak:** Repeatedly restart dashboard, provider, desktop shell, and machine while verifying exactly-once recovery.
- **v1483 - Resource-pressure soak:** Test low disk, high CPU, memory pressure, gaming load, slow storage, and process contention with graceful degradation.
- **v1484 - Provider-failure soak:** Inject slow, malformed, disconnected, restarted, and capability-changing providers without corrupting campaigns.
- **v1485 - Concurrency soak:** Exercise tabs, sessions, background jobs, file changes, queues, and competing processes for races and duplicate side effects.
- **v1486 - Upgrade and rollback soak:** Traverse multiple supported versions, interrupted migrations, failed canaries, and restored backups with source/data compatibility.
- **v1487 - Adversarial task suite:** Attempt authority confusion, unsafe instructions, deceptive evidence, poisoned repository content, and boundary escalation.
- **v1488 - Unfamiliar-project benchmark:** Evaluate planning, implementation, testing, and repair on held-out local projects and task types.
- **v1489 - Human daily-use trial:** Measure usefulness, naturalness, interruption burden, trust, correction cost, and whether the operator chooses to keep using her.
- **v1490 - Reliability checkpoint:** Require stable soak results, bounded intervention rates, no critical data loss, and reproducible recovery before feature freeze.

## Phase 20: v1500 Feature Freeze and Release Qualification (v1491-v1500)

- **v1491 - Feature freeze:** Stop broad capability work, lock the v1500 contract, inventory known limits, and accept only benchmark-blocking repairs.
- **v1492 - Requirements audit:** Trace every v1500 behavior, authority boundary, privacy promise, and recovery guarantee to current implementation and evidence.
- **v1493 - Architecture audit:** Review oversized modules, ownership boundaries, dependency direction, migration debt, and protected-core isolation without blind line-count splitting.
- **v1494 - Full benchmark suite:** Run greenfield, existing feature, bug repair, refactor, migration, UI, provider, self-update, and no-prompt campaign scenarios.
- **v1495 - Native Windows certification:** Perform fresh-install, real-provider, desktop, multi-day, resource-pressure, backup, upgrade, and rollback validation on Windows.
- **v1496 - Security and privacy certification:** Re-run adversarial boundaries, secret scans, archive privacy, untrusted-content defense, and evidence redaction.
- **v1497 - Operator experience review:** Verify setup, model selection, chat, work monitoring, authority profiles, pause, correction, restore, and uninstall are understandable in ordinary use.
- **v1498 - Release candidate:** Produce an immutable source-only candidate with exact manifest, hash, clean extraction, isolated verification, known limits, and rollback artifact.
- **v1499 - Final soak and decision gate:** Run the candidate unchanged, repair only concrete blockers in a separately versioned candidate, and preserve operator promotion authority.
- **v1500 - Bounded Autonomous Developer Beta:** Promote only after Eidolon independently identifies, plans, implements, tests, repairs, applies, and reports useful work across sustained sessions within an operator-selected authority profile.

## Review Cadence

- Run focused tests for every bundle and the arc checkpoint at every `.9`.
- Run a broader segmented verifier every five numbered arcs.
- Run a Desktop Codex architecture and Windows review every ten numbered arcs or after any protected-core change.
- Run native-provider checks only when the arc changes provider behavior or reaches a provider/release gate.
- Run long soaks at v1380, v1400, v1450, v1480, v1490, and v1499 rather than spending that cost on every patch.
- Repair concrete defects in a narrowly numbered follow-up; do not rewrite historical fixtures merely to make a checkpoint green.

## Progress Gates

- **v1350:** reliably implements bounded multi-language tasks in isolation.
- **v1400:** completes end-to-end development campaigns under a standing grant.
- **v1450:** feels like a stable Windows companion and developer product in daily use.
- **v1480:** initiates and completes useful maintenance, including bounded self-updates.
- **v1500:** demonstrates sustained bounded autonomy with low intervention, evidence-backed judgment, safe recovery, and operator-controlled authority.

The target should move only when evidence exposes a missing dependency or invalid assumption. New ideas belong in the backlog unless they directly unlock the current gate.
