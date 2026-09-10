from __future__ import annotations

"""Static dashboard shell extracted from ``dashboard.py`` in v1250.7.

The renderer receives every runtime dependency explicitly. It renders HTML only;
it does not approve work, execute tools, mutate projects, contact providers, or
grant release authority.
"""

CONTRACT_VERSION = "v1250.7"
AUTHORITY_FLAGS = {
    "approval_granted": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "provider_contact_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}

def render_dashboard_layout(
    path: str,
    content: str,
    *,
    load_settings,
    dashboard_route_registry_nav_items,
    COMPANION_CHAT_STYLES,
    DASHBOARD_TITLE,
    DASHBOARD_VERSION,
    DashboardState,
    _live_refresh_bar,
    _live_refresh_script,
    _now,
    _render_nav,
    _safe,
) -> str:
    settings = load_settings()
    nav_items = [
        ("/", "Overview", "Home status cards, next task, memory status, and common actions.", "Core"),
        ("/actions", "Action Center", "A focused operator console for pending approvals, notifications, diagnostics, maintenance scans, and next actions.", "Core"),
        ("/chat-console", "Chat Console", "Local dashboard chat console wired into Eidolon actions.", "Core"),
        ("/daily-evaluation-console", "Daily Evaluation", "Private Desktop Alpha evaluation console for explicit observations and privacy-safe review export.", "Core"),
        ("/evaluation-campaign-console", "Evaluation Campaigns", "Private operator campaign console for enrollment, explicit review dispositions, comparison, and privacy-safe export.", "Core"),
        ("/evaluation-findings-console", "Evaluation Findings", "Private operator findings console for triage, reproducibility, repair references, bounded long-session windows, and privacy-safe export.", "Core"),
        ("/repair-candidate-review-console", "Candidate Review", "Private operator repair-candidate review console for immutable registrations, explicit review evidence, lineage, comparison, bounded windows, and privacy-safe export.", "Core"),
        ("/local-model", "Local Model", "Provider health, model availability, and configured generation limits. Diagnostics only; no model installation.", "System"),
        ("/provider-model-governance", "Provider Governance", "Read-only provider/model selection, privacy, health, compatibility, and fallback evidence.", "System"),
        ("/chat-actions", "Chat Actions <span class='nav-badge' data-live-count='counts.chat_actions'></span>", "Review chat-triggered action records and their statuses.", "Core"),
        ("/create", "Create", "Create tasks, goals, patch proposals, and other supervised work records.", "Core"),
        ("/tasks", "Tasks <span class='nav-badge' data-live-count='counts.tasks'></span>", "Classic task list and task status management.", "Core"),
        ("/tasks-work", "Tasks / Work <span class='nav-badge' data-live-count='counts.work_queue_pending'></span>", "Work queue view for pending, active, blocked, and approval-required task work.", "Work Loops"),
        ("/work-cycle", "Work Cycle <span class='nav-badge' data-live-count='counts.work_cycles'></span>", "Bounded supervised work-cycle execution records.", "Work Loops"),
        ("/stable-loop", "Stable Loop <span class='nav-badge' data-live-count='counts.stable_loops'></span>", "Stable supervised loop reviews, decisions, follow-ups, and completion state.", "Work Loops"),
        ("/stabilization", "Stabilization", "Stability checkpoint, confidence, blockers, and repair suggestions.", "Work Loops"),
        ("/doctor", "Doctor", "Local system health diagnostics and readiness checks.", "Work Loops"),
        ("/build-cycle", "Build Cycle", "Controlled build-cycle reports and development loop evidence.", "Development"),
        ("/development-campaigns", "Development Proposals", "Persistent ordinary-chat supervised development proposals, exact revision approval, and lifecycle state.", "Development"),
        ("/patch-review", "Patch Review", "v74 patch draft review and diff validation: intake parsing, boundaries, scope, safety, docs, verification, risk, and operator report. Review only; no apply.", "Development"),
        ("/patch-trials", "Patch Trials", "v75 sandbox patch trial runner: bind reviewed drafts, create disposable workspaces, materialize safely, verify in sandbox, collect evidence, and prove live source unchanged. No promotion.", "Development"),
        ("/patch-evidence", "Patch Evidence", "v76 sandbox evidence review and promotion recommendation: validate trial evidence, score verification, review docs/scope, classify risk, and recommend only. No promotion.", "Development"),
        ("/patch-apply", "Patch Apply", "v77 operator-approved patch application: exact approval, recommendation binding, live snapshot, scoped materialization, verification, rollback, and evidence. No publish or autonomous apply.", "Development"),
        ("/patch-recovery", "Patch Recovery", "v78 verified application recovery and rollback hardening: dirty-tree preflight, snapshot validation, partial apply detection, rollback integrity, failure triage, recommendations, and audit timeline. No auto-repair.", "Development"),
        ("/patch-queue", "Patch Queue", "v79 multi-patch queue planning: schema, intake, conflict detection, risk scheduling, stale evidence checks, serial trial plans, and operator review. Planning only; no batch apply.", "Development"),
        ("/improvement-loop", "Supervised Local Improvement Loop", "v80.0 Supervised Local Improvement Loop: Run one supervised improvement cycle from goal intake to operator review without applying anything. No self-approval or autonomous apply.", "Development"),
        ("/local-model-proposals", "Local Model Patch Proposal Integration", "v81.0 Local Model Patch Proposal Integration: Prepare controlled local model patch proposal handoff and capture, disabled by default for invocation. No self-approval or autonomous apply.", "Development"),
        ("/proposal-critique", "Proposal Critique", "v82.0 Local Model Output Comparison and Critique: Compare local model outputs, critique proposal quality, and export operator review bundles without selecting automatically. No self-approval or autonomous apply.", "Development"),
        ("/candidate-ranking", "Multi-Model Patch Candidate Ranking", "v83.0 Multi-Model Patch Candidate Ranking: Rank multiple patch candidates by risk, evidence, conflicts, and operator review needs without auto-selecting. No self-approval or autonomous apply.", "Development"),
        ("/candidate-refinement", "Supervised Patch Candidate Refinement", "v84.0 Supervised Patch Candidate Refinement: Build constrained refinement prompts and review revised candidates without applying or approving them. No self-approval or autonomous apply.", "Development"),
        ("/suggestion-loop", "Safe Autonomous Suggestion Loop", "v85.0 Safe Autonomous Suggestion Loop: Periodically organize safe improvement suggestions for operator attention while forbidding autonomous apply. No self-approval or autonomous apply.", "Development"),
        ("/suggestion-inbox", "Suggestion Inbox", "v86.0 Supervised Suggestion Inbox and Work Order Planner: Triage safe suggestions into operator-reviewed work order drafts without autonomous apply, publish, memory mutation, or identity mutation.", "Development"),
        ("/work-order-handoff", "Work Order Handoff", "v87.0 Work Order to Patch Context Handoff: Convert operator-accepted work orders into supervised patch context packets without execution.", "Development"),
        ("/work-order-evidence", "Work Order Evidence", "v88.0 Work Order Execution Evidence Binder: Trace work orders through sandbox evidence and operator decisions without inferring approval.", "Development"),
        ("/self-development", "Self-Development", "v89.0 Self-Development Dashboard Consolidation: Unified supervised development console, action queue, safety banners, and lazy diagnostics.", "Development"),
        ("/self-development-cycle", "Self Dev Cycle", "v760.0 Self Development Application Receipt Review: proposal packet, approval gates, patch draft/application trial receipts, and smoke debt continuity.", "Development"),
        ("/self-development-smoke-debt", "Smoke Debt", "v760.0 API Surface Truth + Smoke Debt: review application receipts, classify broad smoke debt, and live-probe self-development API route claims without source edits.", "Development"),
        ("/behavioral-dashboard-route-coverage", "Route Coverage", "v1024.0 Behavioral Dashboard Route Coverage: render critical dashboard routes behaviorally and inventory source decomposition prep without moving code.", "Development"),
        ("/source-decomposition-compatibility-slice", "Decomposition Slice", "v1025.0 First Source Decomposition Compatibility Slice: extracted the compile timeout contract from the manual smoke runner while preserving compatibility and authority boundaries.", "Development"),
        ("/dashboard-shell-component-extraction", "Dashboard Shell Slice", "v1026.0 Dashboard Shell Component Extraction Compatibility Slice: extracted common dashboard card/text shell helpers while preserving route behavior and manual dashboard authority.", "Development"),
        ("/smoke-registry-sidecar-compatibility", "Smoke Sidecar Slice", "v1028.0 Smoke Registry Sidecar Compatibility Extraction Slice: extracts a bounded smoke metadata sidecar while manual tools/smoke_check.py remains authoritative.", "Development"),
        ("/smoke-registry-sidecar-expansion-route-manifest", "Sidecar + Route Manifest", "v1028.0 Smoke Registry Sidecar Expansion and Route Manifest Prep: expands the bounded sidecar metadata slice and prepares route/command/check manifest inventory without activating generated wiring.", "Development"),
        ("/route-manifest-dashboard-parity", "Route Manifest Parity", "v1029.0 Route Manifest Inventory Expansion and Dashboard Parity Gate: expands bounded manual route inventory and behaviorally proves route-to-renderer parity without activating generated routing.", "Development"),
        ("/dashboard-route-behavioral-coverage-expansion", "Route Behavior Expansion", "v1030.0 Dashboard Route Behavioral Coverage Expansion: expands behavioral dashboard route coverage into cohorts while manual dashboard routing remains authoritative and generated routing stays inactive.", "Development"),
        ("/dashboard-route-manifest-renderer-reconciliation", "Route Renderer Reconcile", "v1031.0 Dashboard Route Manifest-to-Renderer Reconciliation: reconciles route manifest rows to manual dashboard renderer dispatch while generated routing remains inactive.", "Development"),
        ("/dashboard-route-coverage-completion-dispatch-classification", "Route Coverage Completion", "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification: expands safe behavioral route coverage and classifies remaining manual dispatch routes while manual routing stays authoritative.", "Development"),
        ("/dashboard-deferred-route-harness-renderer-repair-prep", "Deferred Route Harness", "v1035.0 Dashboard Deferred Route Harness and Renderer Repair Prep: repairs the approval-scope renderer fallback and time-boxes deferred route probes without replacing manual routing.", "Development"),
        ("/dashboard-slow-route-isolated-behavioral-coverage", "Slow Route Coverage", "v1036.0 Dashboard Slow Route Isolated Behavioral Coverage: graduates selected slow/deferred routes into isolated behavioral coverage while preserving manual dispatch.", "Development"),
        ("/dashboard-parameterized-route-harness-prep", "Parameterized Route Harness", "v1037.0 Dashboard Parameterized Route Harness Prep: covers query-dependent /detail through parameterized subprocess fixtures while keeping manual routing authoritative.", "Development"),
        ("/dashboard-timeout-lane-classification-slow-renderer-decomposition-prep", "Timeout Lane Prep", "v1038.0 Dashboard Timeout Lane Classification and Slow Renderer Decomposition Prep: separates fast, isolated, long-isolated, and deferred lanes while keeping manual routing authoritative.", "Development"),
        ("/dashboard-doctor-renderer-decomposition-slice", "Doctor Decomposition", "v1039.0 Dashboard Doctor Renderer Decomposition Slice: decomposes /doctor into a bounded primary shell plus deferred diagnostic links while preserving manual routing.", "Development"),
        ("/dashboard-doctor-deferred-diagnostic-api-parity", "Doctor API Parity", "v1040.0 Dashboard Doctor Deferred Diagnostic API Parity: proves /doctor deferred diagnostic links resolve through live manual API dispatch without activating generated wiring.", "Development"),
        ("/doctor-deferred-diagnostic-latency-budget-payload-shape", "Doctor API Shape", "v1041.0 Doctor Deferred Diagnostic Latency Budget and Payload Shape: classifies /doctor deferred API latency budgets and payload shapes while manual API dispatch stays authoritative.", "Development"),
        ("/controlled-self-build-lightweight-preview-endpoint-prep", "Build Preview Lite", "v1042.0 Controlled Self-Build Lightweight Preview Endpoint Prep: adds a preview-only lightweight controlled self-build API diagnostic while heavy preview and live POST approval gates stay protected.", "Development"),
        ("/doctor-controlled-self-build-lightweight-link-migration", "Doctor Build Lite Link", "v1043.0 Doctor Controlled Self-Build Lightweight Link Migration: migrates /doctor controlled self-build diagnostics to the lightweight preview endpoint while preserving the heavy protected preview route.", "Development"),
        ("/doctor-diagnostic-preview-cache-heavy-route-decoupling", "Doctor Cache", "v1045.0 Doctor Diagnostic Preview Cache and Heavy Route Decoupling: adds a bounded preview cache for /doctor deferred diagnostics and keeps the heavy controlled self-build route deliberate.", "Development"),
        ("/doctor-diagnostic-cache-freshness-invalidation-review", "Doctor Cache Freshness", "v1045.0 Doctor Diagnostic Cache Freshness and Invalidation Review: adds preview-only freshness and invalidation metadata for doctor diagnostic cache rows.", "Development"),
        ("/doctor-diagnostic-cache-source-dependency-digest-verification", "Doctor Cache Digests", "v1046.0 Doctor Diagnostic Cache Source Dependency Digest Verification: dry-run verifies source dependency digest changes without mutating source files or writing a persisted cache.", "Development"),
        ("/doctor-diagnostic-cache-digest-drift-classification", "Doctor Cache Drift", "v1047.0 Doctor Diagnostic Cache Digest Drift Classification: classifies digest drift causes using dry-run overlays while preserving manual dashboard/API/smoke authority.", "Development"),
        ("/doctor-diagnostic-cache-contract-drift-fixture-expansion", "Doctor Contract Drift", "v1048.0 Doctor Diagnostic Cache Contract Drift Fixture Expansion: expands dry-run token-removal and route-rename fixtures while preserving manual dashboard/API/smoke authority.", "Development"),
        ("/doctor-diagnostic-cache-drift-severity-guidance", "Doctor Drift Severity", "v1050.0 Doctor Diagnostic Cache Drift Severity Guidance: maps dry-run cache drift fixtures to informational, advisory, warning, and blocker operator guidance without authority expansion.", "Development"),
        ("/doctor-diagnostic-cache-severity-route-impact-matrix", "Doctor Impact Matrix", "v1050.0 Doctor Diagnostic Cache Severity Route Impact Matrix: maps severity-labeled cache drift to affected manual dashboard, API, and smoke targets without authority expansion.", "Development"),
        ("/doctor-diagnostic-cache-impact-operator-action-ledger", "Doctor Action Ledger", "v1054.0 Doctor Diagnostic Cache Impact Matrix Operator Action Ledger: converts cache impact rows into review-only operator actions, evidence requirements, and release-blocking guidance without repair authority.", "Development"),
        ("/doctor-deep-diagnostic-latency-budget-repair", "Doctor Deep Latency", "v1055.0 Doctor Deep Diagnostic Latency Budget Repair: routes deferred diagnostic probes through bounded preview defaults while preserving full diagnostics behind explicit operator query flags.", "Development"),
        ("/dashboard-doctor-performance-headroom-repair", "Doctor Headroom", "v1052.0 Dashboard Doctor Performance Headroom Repair: keeps /doctor bounded with preview-cache shell rendering and deferred heavy diagnostics.", "Development"),
        ("/installed-tree-cleanup-historical-verification-reconciliation", "Install Truth", "v1053.0 Installed-Tree Cleanup and Historical Verification Reconciliation: splits ZIP privacy from local runtime state, classifies obsolete source cleanup, reconciles historical doctor checks, and measures cold startup readiness.", "Development"),
        ("/self-development-readiness", "Readiness Audit", "v90.0 Supervised Self-Development Readiness Audit: Diagnostic supervision, traceability, approval gate, risk, and scorecard audit without unlocking autonomy.", "Development"),
        ("/development-sessions", "Development Sessions", "v91.0 Supervised Development Session Manager: Bundle suggestions, work orders, patch contexts, evidence, and operator goals into supervised sessions without approval escalation.", "Development"),
        ("/approval-console", "Approval Console", "v92.0 Operator Approval Workflow Console: Unified operator approval queue, decision ledger, dependencies, and risk explanations without inferred approval.", "Development"),
        ("/experiment-planner", "Experiment Planner", "v93.0 Safe Experiment Branch Planner: Plan isolated experiments and sandbox metadata without touching live source or promoting outside transaction gates.", "Development"),
        ("/outcome-reflections", "Outcome Reflections", "v94.0 Learning-from-Outcome Reflection Layer: Extract advisory lessons and safe suggestion handoffs without memory or identity mutation.", "Development"),
        ("/improvement-cycles", "Improvement Cycles", "v95.0 Supervised Improvement Cycle Orchestrator: Trace the full governed cycle from suggestion through reflection and next suggestion without autonomy.", "Development"),
        ("/cycle-replay", "Cycle Replay", "v96.0 Supervised Cycle Replay and Benchmark Harness: Replay supervised cycles against safe fixtures and score recommendations without source mutation or permission unlocks.", "Development"),
        ("/capability-ledger", "Capability Ledger", "v97.0 Capability Permission and Budget Ledger: Track allowed, gated, forbidden, and budgeted capabilities without letting simulation become execution.", "Development"),
        ("/shadow-autonomy", "Shadow Autonomy", "v98.0 Shadow Autonomy Simulation Layer: Simulate autonomous intentions but map actions only to approval requests or block states.", "Development"),
        ("/failure-war-games", "Failure War Games", "v99.0 Failure Recovery and Rollback War Game Layer: Rehearse recovery and rollback paths without automatic rollback or source mutation.", "Development"),
        ("/mind-milestone-audit", "Mind Milestone", "v100.0 Local Artificial Mind Milestone Audit: Audit memory, reflection, goals, safety, self-development, and operator burden without unlocking autonomy.", "Development"),
        ("/v100-stabilization", "v100 Stabilization", "v101.0 v100 Milestone Stabilization and Reality Review: Inventory routes, commands, coverage, privacy, friction, and consolidation candidates without changing source.", "Development"),
        ("/operator-home", "Operator Home", "v102.0 Unified Eidolon System Map and Operator Home: Central system health, pending actions, active sessions, blocked risks, and safest supervised next step.", "Development"),
        ("/system-map", "System Map", "v102.0 Unified Eidolon System Map: Map core mind components, development pipeline, governance boundaries, and cross-links.", "Development"),
        ("/coherence-binder", "Coherence Binder", "v103.0 Memory, Reflection, and Goal Coherence Binder: Link memory references, reflections, goals, suggestions, outcomes, and lessons without memory or identity mutation.", "Development"),
        ("/daily-loop", "Daily Loop", "v104.0 Practical Daily Operating Loop: Callable daily status, priorities, operator prompts, safety checks, and reflection prompts without scheduling or automation.", "Development"),
        ("/local-mind-runtime", "Mind Runtime", "v105.0 Coherent Local Mind Runtime v1: Read-only unified mind-state snapshot, continuity report, health scorecard, contradictions, and safest supervised next step.", "Development"),
        ("/memory-quality", "Memory Quality", "v106.0 Memory Quality and Evidence Hygiene Layer: Freshness, relevance, evidence links, duplicate/conflict detection, and correction drafts without memory mutation.", "Development"),
        ("/goal-continuity", "Goal Continuity", "v107.0 Goal Continuity and Priority Stability Layer: Goal lifecycle, blockers, evidence, priority stability, and contradictions without inferred approval.", "Development"),
        ("/reasoning-workbench", "Reasoning Workbench", "v108.0 Contained Local Reasoning Workbench: Manual/local reasoning capture, bounded context, quality rubric, and boundary scanning without default model invocation.", "Development"),
        ("/workflow-console", "Workflow Console", "v109.0 Operator Workflow Compression Console: Unified action queue, copy-safe commands, review packet shortcuts, and dashboard consolidation recommendations without auto-execution.", "Development"),
        ("/practical-mind-audit", "Mind Usefulness", "v110.0 Practical Supervised Mind Usefulness Audit: End-to-end usefulness, memory, goals, reasoning, operator burden, dashboard sprawl, and safety regression audit.", "Development"),
        ("/improvement-intent", "Improvement Intent", "v111.0 Improvement Intent and Problem Framing Layer: Turn vague improvement ideas into grounded problem statements, evidence requirements, value scores, and safety-sensitive intent binders.", "Development"),
        ("/work-package-builder", "Work Packages", "v112.0 Supervised Work Package Builder: Assemble advisory work packages with scope, acceptance criteria, test plans, docs obligations, and regression risks.", "Development"),
        ("/patch-readiness", "Patch Readiness", "v113.0 Patch Readiness and Review Intelligence Layer: Review proposed patches for completeness, contradictions, safety regressions, dashboard regressions, and operator recommendations without applying anything.", "Development"),
        ("/release-candidate-judgment", "Release Judgment", "v114.0 Release Candidate Judgment Layer: Judge candidate readiness across version consistency, docs, route/API/CLI parity, privacy, install verification, and release recommendation without publishing.", "Development"),
        ("/supervised-development-readiness", "SD Readiness v115", "v115.0 Supervised Self-Development Readiness Audit: End-to-end supervised improvement walkthrough, evidence quality, decision trace, operator burden, dashboard usability, and release process audit. Distinct from the older v90 readiness page.", "Development"),
        ("/development-session-planner", "Session Planner", "v116.0 Development Session Planner: Plan a supervised development session with intent, scope, file impact, tests, docs, safety boundaries, and operator decisions before code changes.", "Development"),
        ("/source-change-cartographer", "Source Map", "v117.0 Source Change Cartographer: Map dashboard, API, CLI, builder, smoke, docs, packaging, install, and fragile source surfaces without mutation.", "Development"),
        ("/patch-simulation", "Patch Simulation", "v118.0 Patch Simulation and Dry-Run Review Layer: Predict expected diffs, missing changes, overreach, safety risk, and verification outcomes without applying patches.", "Development"),
        ("/verification-matrix", "Verify Matrix", "v119.0 Verification Matrix and Regression Memory Layer: Recommend exact regression checks for dashboard, API/CLI, packaging, safety, and docs changes without scheduling work.", "Development"),
        ("/development-execution-audit", "Execution Audit", "v120.0 Supervised Development Execution Audit: Audit the v116-v119 execution-planning flow for operator burden, patch quality, verification coverage, safety containment, dashboard sprawl, and docs continuity.", "Development"),
        ("/development-outcome-review", "Outcome Review", "v121.0 Development Outcome Review Layer: Compare planned development sessions against actual outcomes, missed surfaces, unexpected changes, verification accuracy, and operator burden without memory mutation.", "Development"),
        ("/lesson-extraction", "Lessons", "v122.0 Supervised Lesson Extraction Layer: Extract proposed lessons from outcomes, bug patterns, successful patterns, false alarms, and usefulness scores without writing durable memory.", "Development"),
        ("/recommendation-refinement", "Rec Refinement", "v123.0 Recommendation Refinement Layer: Refine future recommendations from reviewed outcomes and proposed lessons while keeping all recommendations advisory.", "Development"),
        ("/operator-feedback-integration", "Feedback", "v124.0 Operator Feedback Integration Layer: Classify operator feedback into standing-rule, temporary, contradiction, and review packets without auto-writing memory.", "Development"),
        ("/development-learning-audit", "Learning Audit", "v125.0 Supervised Development Learning Audit: Audit the full outcome-review, lesson, recommendation, and feedback loop without autonomy or memory mutation.", "Development"),
        ("/strategic-growth-intake", "Strategic Intake", "v126.0 Strategic Growth Intake Layer: Gather lessons, feedback, goals, audits, failed checks, roadmap notes, and operator direction into supervised growth signals.", "Development"),
        ("/roadmap-synthesis", "Roadmap", "v127.0 Roadmap Synthesis Layer: Turn strategic signals into short, medium, and long-term roadmap options without scheduling or approving work.", "Development"),
        ("/strategic-risk-ledger", "Risk Ledger", "v128.0 Strategic Risk and Debt Ledger: Track technical, safety, and usability debt with advisory mitigations only.", "Development"),
        ("/capability-maturity", "Maturity", "v129.0 Capability Maturity Model Layer: Score capabilities by scaffold, integration, test coverage, usefulness, reliability, and operator trust without self-upgrades.", "Development"),
        ("/strategic-growth-audit", "Growth Audit", "v130.0 Supervised Strategic Growth Audit: Audit strategic intake, roadmap synthesis, risk/debt tracking, and capability maturity while preserving all non-autonomy boundaries.", "Development"),
        ("/planning-signals", "Planning Signals", "v131.0 Planning Signal Consolidation Layer: Consolidate planning evidence from strategy, risks, maturity, feedback, lessons, checks, and operator direction.", "Development"),
        ("/work-package-recommendations", "Work Packages v132", "v132.0 Work Package Recommendation Layer: Recommend ranked supervised work packages without creating, approving, or applying work.", "Development"),
        ("/operator-decision-brief", "Decision Brief", "v133.0 Operator Decision Brief Layer: Present top options, evidence, tradeoffs, sequencing, burden, verification, and safety boundaries without selecting work.", "Development"),
        ("/planning-console", "Planning Console", "v134.0 Dashboard Planning Console Consolidation: Group planning surfaces and preserve custom data-tip hover behavior without native title tooltips.", "Development"),
        ("/planning-readiness-audit", "Planning Audit", "v135.0 Supervised Operator Planning Console: Audit signals, packages, decision brief, console, parity, privacy, and safety boundaries.", "Development"),
        ("/work-package-selection", "Package Select", "v136.0 Work Package Selection Layer: Compare recommendations and record explicit operator selection without launching or executing work.", "Development"),
        ("/session-brief", "Session Brief", "v137.0 Session Brief Preparation Layer: Prepare objective, evidence, risks, files, non-goals, dependencies, and safety boundaries.", "Development"),
        ("/approval-checklist", "Approval Checklist", "v138.0 Approval Checklist and Safety Boundary Layer: Prepare supervised approval, scope, safety, docs, dashboard, and verification checklists.", "Development"),
        ("/verification-rollback-plan", "Verify/Rollback", "v139.0 Verification Plan and Rollback Preparation Layer: Prepare advisory verification and rollback plans without executing commands.", "Development"),
        ("/session-launch-audit", "Launch Audit", "v140.0 Supervised Work Package Selection and Session Launch: Audit recommendation-to-launch packets while preserving approval gates.", "Development"),
        ("/patch-session-intake", "Patch Intake", "v141.0 Patch Session Intake Layer: Import approved launch packets and prepare supervised patch-session intake without implementation.", "Development"),
        ("/file-change-plan", "File Plan", "v142.0 File Change Planning Layer: Plan file-by-file changes before any source edits.", "Development"),
        ("/patch-blueprint", "Patch Blueprint", "v143.0 Patch Draft Blueprint Layer: Prepare patch blueprints as plans only, not applied changes.", "Development"),
        ("/patch-review-packet", "Review Packet", "v144.0 Patch Review Packet Layer: Bundle evidence, risk, docs, verification, and rollback notes for operator approval.", "Development"),
        ("/patch-session-audit", "Patch Audit", "v145.0 Supervised Patch Session Assembly: Audit intake-to-review packet readiness while preserving approval gates.", "Development"),
        ("/patch-draft-request", "Draft Request", "v146.0 Patch Draft Request Layer: Convert reviewed patch session packets into supervised draft-generation requests without writing files.", "Development"),
        ("/file-patch-drafts", "File Drafts", "v147.0 File-Level Patch Draft Layer: Produce reviewable file-by-file patch drafts and diff previews without applying them.", "Development"),
        ("/patch-diff-review", "Diff Review", "v148.0 Patch Diff Review Packet Layer: Combine file drafts into coherent review packets with consistency, safety, verification, and rollback checks.", "Development"),
        ("/patch-draft-qa", "Draft QA", "v149.0 Patch Draft QA Layer: QA draft completeness, consistency, safety, docs, dashboard behavior, and package privacy before implementation.", "Development"),
        ("/patch-draft-generation-audit", "Draft Audit", "v150.0 Supervised Patch Draft Generation: Audit the full review-packet-to-draft-to-QA chain while keeping drafts unapplied.", "Development"),
        ("/implementation-handoff", "Impl Handoff", "v151.0 Implementation Handoff Intake Layer: Convert QA-passed patch drafts into an advisory implementation handoff request without source mutation.", "Development"),
        ("/manual-patch-application-plan", "Apply Plan", "v152.0 Manual Patch Application Plan Layer: Order manual edit instructions while refusing automatic patch application.", "Development"),
        ("/implementation-verification-worksheet", "Verify Sheet", "v153.0 Implementation Verification Worksheet Layer: Prepare operator-run verification worksheets without executing commands.", "Development"),
        ("/implementation-rollback-packet", "Rollback Packet", "v154.0 Implementation Rollback Packet Layer: Prepare advisory rollback instructions before implementation.", "Development"),
        ("/implementation-handoff-audit", "Impl Audit", "v155.0 Supervised Patch Implementation Handoff: Audit draft-to-handoff-to-plan-to-verification-to-rollback continuity.", "Development"),
        ("/patch-readiness-intake", "Ready Intake", "v156.0 Patch Readiness Intake Layer: Bind draft QA, handoff, manual application, verification, rollback, docs, and operator approval evidence without applying patches.", "Development"),
        ("/patch-readiness-score", "Ready Score", "v157.0 Patch Readiness Scoring Layer: Score scope, safety, verification, rollback, docs, dashboard, parity, and packaging readiness without self-approval.", "Development"),
        ("/patch-readiness-blockers", "Ready Blockers", "v158.0 Patch Blocker and Gap Report Layer: Surface missing packets, file coverage gaps, unsafe capability risks, dashboard regressions, parity gaps, and package privacy issues.", "Development"),
        ("/patch-go-no-go-decision", "Go/No-Go", "v159.0 Operator Go/No-Go Decision Packet Layer: Prepare advisory go, no-go, or conditional-go recommendations requiring explicit operator approval.", "Development"),
        ("/patch-application-readiness-audit", "Ready Audit", "v165.0 Supervised Patch Application Readiness: Audit the full readiness pipeline without patch application, source mutation, verification execution, or approval inference.", "Development"),
        ("/patch-sandbox-intake", "Sandbox Intake", "v161.0 Patch Sandbox Intake Layer: Prepare sandbox requests from readiness decisions with explicit approval and no live mutation.", "Development"),
        ("/sandbox-patch-application-plan", "Sandbox Plan", "v162.0 Approved Sandbox Patch Application Plan: Plan sandbox-only patch application steps without touching live source.", "Development"),
        ("/sandbox-verification-packet", "Sandbox Verify", "v163.0 Sandbox Verification Execution Packet: Prepare operator-approved sandbox verification packets without automatic command execution.", "Development"),
        ("/sandbox-result-review", "Sandbox Review", "v164.0 Sandbox Result Review Layer: Review sandbox evidence and classify outcomes without promotion.", "Development"),
        ("/sandbox-patch-application-audit", "Sandbox Audit", "v165.0 Operator-Approved Patch Application Sandbox: Audit the gated sandbox-only patch application flow without live source mutation or promotion.", "Development"),
        ("/sandbox-promotion-intake", "Promote Intake", "v166.0 Sandbox Promotion Intake Layer: Import sandbox evidence and require explicit promotion approval before source promotion can be considered.", "Development"),
        ("/source-promotion-plan", "Source Plan", "v167.0 Source Promotion Application Plan Layer: Plan sandbox-to-source changes as advisory steps until explicit approval.", "Development"),
        ("/promotion-approval-packet", "Promote Approval", "v168.0 Promotion Approval Packet Layer: Prepare final operator approval packet without inferring approval or promoting changes.", "Development"),
        ("/post-promotion-verification", "Post Verify", "v169.0 Post-Promotion Verification and Rollback Layer: Prepare post-promotion verification and rollback procedures without auto-execution.", "Development"),
        ("/sandbox-to-source-promotion-audit", "Promote Audit", "v170.0 Operator-Approved Sandbox-to-Source Promotion: Audit the supervised sandbox-to-source promotion chain without autonomous promotion.", "Development"),
        ("/source-application-approval", "Source Approval", "v171.0 Source Application Approval Intake Layer: Require exact operator approval before live-source application can proceed.", "Development"),
        ("/live-source-application-plan", "Live Plan", "v172.0 Live Source Patch Application Plan Layer: Plan source mutations, snapshots, rollback, docs, and parity under approval.", "Development"),
        ("/approved-source-application-execution", "Apply Packet", "v173.0 Approved Source Application Execution Packet: Define tightly scoped, approval-bound source application execution packets.", "Development"),
        ("/post-application-verification", "Post Verify", "v174.0 Post-Application Verification and Rollback Control Layer: Prepare verification and rollback controls after approved source application.", "Development"),
        ("/source-patch-application-audit", "Source Audit", "v175.0 Operator-Approved Source Patch Application: Audit explicit-approval source application without autonomy.", "Development"),
        ("/post-application-outcome-intake", "Outcome Intake", "v176.0 Post-Application Outcome Intake Layer: Normalize approved source application outcomes without triggering fixes, rollback, release, or follow-up patches.", "Development"),
        ("/post-application-lessons", "Lessons v2", "v177.0 Supervised Lesson Extraction Layer v2: Extract reviewable post-application lessons without memory mutation.", "Development"),
        ("/next-improvement-candidates", "Next Candidates", "v178.0 Supervised Next-Improvement Candidate Builder: Rank supervised future improvement options without auto-selection.", "Development"),
        ("/post-application-release-readiness", "Release Ready v2", "v179.0 Release Readiness Judgment Layer v2: Judge readiness without creating, freezing, signing, packaging, or publishing release candidates.", "Development"),
        ("/post-application-cycle-closure", "Closure Audit", "v180.0 Operator-Governed Post-Application Learning and Release Readiness: Audit the full post-application closure loop without autonomy.", "Development"),
        ("/cycle-intelligence-intake", "Cycle Intake", "v181.0 Cycle Intelligence Intake Layer: Collect prior-cycle evidence into one read-only planning context.", "Development"),
        ("/supervised-patch-priority-matrix", "Priority Matrix", "v182.0 Supervised Patch Priority Matrix: Score next patch candidates without choosing or approving work.", "Development"),
        ("/next-patch-proposal-assembly", "Proposal Assembly", "v183.0 Next Patch Proposal Assembly Layer: Assemble reviewable next-patch proposals without writing source.", "Development"),
        ("/supervised-patch-session-planner", "Session Planner", "v184.0 Supervised Patch Session Planner: Prepare next-session packets without starting implementation.", "Development"),
        ("/patch-cycle-intelligence-audit", "Cycle Audit", "v185.0 Operator-Governed Patch Cycle Intelligence: Audit next-cycle planning without autonomy or cascade work.", "Development"),
        ("/multi-cycle-roadmap-intake", "Roadmap Intake", "v186.0 Multi-Cycle Roadmap Intake Layer: Collect roadmap-ready project state without selecting or launching work.", "Development"),
        ("/supervised-roadmap-options", "Roadmap Options", "v187.0 Supervised Roadmap Option Builder: Generate advisory roadmap options without activating plans.", "Development"),
        ("/roadmap-dependency-risk-graph", "Roadmap Graph", "v188.0 Roadmap Dependency and Risk Graph: Map roadmap dependencies and risk clusters without launching stages.", "Development"),
        ("/v200-readiness-model", "v200 Ready", "v189.0 v200 Milestone Readiness Model: Score v200 maturity without treating readiness as approval.", "Development"),
        ("/multi-cycle-roadmap-governance-audit", "Roadmap Audit", "v190.0 Operator-Governed Multi-Cycle Roadmap Intelligence: Audit multi-cycle roadmap planning without autonomy.", "Development"),
        ("/capability-maturity-inventory", "Maturity Inventory", "v191.0 Capability Inventory and Maturity Schema: Define capability domains, maturity levels, evidence requirements, and boundaries without granting approval.", "Development"),
        ("/capability-maturity-scoring", "Maturity Scoring", "v192.0 Capability Maturity Scoring Layer: Score major capabilities using evidence-bound advisory criteria.", "Development"),
        ("/capability-gap-overreach-analysis", "Gap/Overreach", "v193.0 Capability Gap and Overreach Analyzer: Identify underdeveloped, risky, overbuilt, and weakly verified capabilities without launching fixes.", "Development"),
        ("/capability-maturity-improvement-plan", "Maturity Plans", "v194.0 Capability Maturity Improvement Planner: Prepare supervised improvement plans that are not execution packets.", "Development"),
        ("/capability-maturity-governance-audit", "Maturity Audit", "v195.0 Supervised Capability Maturity Modeling: Audit maturity scoring, gaps, overreach protection, and no-autonomous-improvement boundaries.", "Development"),

        ("/governance-kernel-state", "Governance State", "v196.0 Governance Kernel State Model: central supervised governance state, lifecycle phase, capability state, approval state, evidence, risk, and operator constraints. Descriptive only.", "Development"),
        ("/governance-rule-evaluation", "Governance Rules", "v197.0 Governance Rule Evaluation Layer: classify actions, evaluate approval/evidence requirements, detect forbidden actions, and summarize governance decisions without granting approval.", "Development"),
        ("/operator-authority-consent-ledger", "Consent Ledger", "v198.0 Operator Authority and Consent Ledger: bind explicit operator approval scope, expiration, revocation, and ambiguity checks without inferred consent.", "Development"),
        ("/governance-enforcement-simulation", "Governance Sim", "v199.0 Governance Kernel Enforcement Simulation: simulate patch, release, memory, identity, autonomy, and parity workflows without executing them.", "Development"),
        ("/governance-kernel-audit", "Kernel Audit", "v200.0 Local Artificial Mind Governance Kernel v1: audit state traceability, rule evaluation, consent boundaries, enforcement simulation, no-autonomy, dashboard style, parity, docs, and release history.", "Development"),

        ("/self-model-snapshot", "Self-Model", "v211.0 Supervised Self-Model Snapshot Layer: evidence-bound identity, capability, limitation, governance, and confidence claims without authority.", "Development"),
        ("/deliberation-packet", "Deliberation", "v212.0 Supervised Deliberation Packet Layer: options, tradeoffs, risks, evidence quality, uncertainty, and recommendation guards without execution.", "Development"),
        ("/purpose-alignment-layer", "Purpose Align", "v213.0 Operator-Governed Purpose Alignment Layer: compare purpose, standing rules, runtime claims, autonomy drift, identity drift, and consent drift without rewriting purpose.", "Development"),
        ("/behavioral-pattern-intelligence", "Pattern Intel", "v214.0 Supervised Behavioral Pattern Intelligence: repeated strengths, repeated weaknesses, verification gaps, dashboard regressions, documentation drift, and advisory priority scoring.", "Development"),
        ("/self-model-integration-audit", "Self-Model Audit", "v215.0 Operator-Governed Deliberation and Self-Model Layer v1: audit self-model evidence, deliberation safety, purpose alignment, patterns, no-autonomy, dashboard, parity, docs, and smoke.", "Development"),

        ("/internal-simulation-packet", "Simulation", "v216.0 Supervised Internal Simulation Packet Layer: proposed action, assumptions, expected outcomes, failure modes, and non-execution guards without authorization.", "Development"),
        ("/foresight-branch-comparison", "Foresight", "v217.0 Operator-Governed Foresight Branch Comparison: compare branches by risk, benefit, governance cost, and evidence readiness without selecting a roadmap as approved.", "Development"),
        ("/pre-change-consequence-modeling", "Consequences", "v218.0 Supervised Pre-Change Consequence Modeling: forecast source, runtime, dashboard, docs, smoke, and approval-scope impact before changes.", "Development"),
        ("/expectation-reality-check", "Reality Check", "v219.0 Supervised Expectation-Reality Check Layer: compare simulated expectations with real evidence without launching follow-up work.", "Development"),
        ("/simulation-foresight-audit", "Sim Audit", "v220.0 Operator-Governed Internal Simulation and Foresight Layer v1: audit simulation packets, branch comparison, consequence modeling, expectation-reality checks, no-execution, no-autonomy, dashboard, parity, docs, and smoke.", "Development"),
        ("/learning-objective-map", "Learn Map", "v221.0 Supervised Learning Objective Map: evidence-bound learning objectives, gap binders, governance-bound classifiers, priority scoring, and non-autonomous learning guards.", "Development"),
        ("/practice-task-design", "Practice Design", "v222.0 Supervised Practice Task Design Layer: reviewable practice task designs, skill targets, evidence needs, scope guards, and non-execution checks.", "Development"),
        ("/capability-calibration", "Calibration", "v223.0 Operator-Governed Capability Calibration Layer: capability claims, evidence strength, unsupported claim detection, overconfidence warnings, and promotion guards.", "Development"),
        ("/skill-gap-remediation-planner", "Gap Plans", "v224.0 Supervised Skill Gap Remediation Planner: weakness clusters, remediation strategies, verification plans, governance risk, approval requirements, and no-continuation guards.", "Development"),
        ("/learning-curriculum-audit", "Learn Audit", "v225.0 Operator-Governed Learning Curriculum and Capability Calibration Layer v1: audit learning objectives, practice safety, capability calibration, remediation, no-autonomous-learning, memory/identity locks, dashboard, parity, docs, and smoke.", "Development"),
        ("/knowledge-claim-ledger", "Claim Ledger", "v226.0 Supervised Knowledge Claim Ledger: evidence-bound knowledge claims, confidence states, freshness, and non-mutation guards.", "Development"),
        ("/belief-candidate-review", "Belief Review", "v227.0 Operator-Reviewed Belief Candidate Layer: belief candidates, source binding, risk scoring, confidence, promotion requirements, and non-authority guards.", "Development"),
        ("/contradiction-staleness-intelligence", "Contradictions", "v228.0 Supervised Contradiction and Staleness Intelligence: claim conflicts, stale knowledge, README/runtime drift, version drift, and non-execution guards.", "Development"),
        ("/project-knowledge-map", "Knowledge Map", "v229.0 Supervised Project Knowledge Map Layer: capability arcs, dashboard/API/CLI surfaces, governance boundaries, and documentation coverage.", "Development"),
        ("/knowledge-organization-audit", "Know Audit", "v230.0 Operator-Governed Knowledge and Belief Organization Layer v1: audit claims, beliefs, contradiction/staleness intelligence, project maps, no-memory-mutation, no-belief-authority, dashboard, parity, docs, and smoke.", "Development"),
        ("/local-model-inventory", "Model Inventory", "v231.0 Operator-Governed Local Model Inventory Layer: profile local models, intended uses, limits, evidence, and no-invocation boundaries.", "Development"),
        ("/model-evaluation-plan", "Model Eval", "v232.0 Supervised Model Evaluation Plan Layer: design model tests, prompt suites, evidence requirements, risk/scope, and approval requirements without running models.", "Development"),
        ("/model-output-comparison", "Model Compare", "v233.0 Operator-Governed Model Output Comparison Layer: compare approved model outputs, score evidence support, detect hallucination and contradictions, and prevent model authority.", "Development"),
        ("/cognitive-workbench-routing", "Workbench", "v234.0 Supervised Cognitive Workbench Routing Layer: recommend model/task fit, review requirements, fallbacks, and disagreement policy without executing model calls.", "Development"),
        ("/local-model-workbench-audit", "Model Audit", "v235.0 Operator-Governed Local Model Evaluation and Cognitive Workbench Layer v1: audit inventory, evaluation plans, output comparison, routing, no-default-invocation, no-model-authority, dashboard, parity, docs, and smoke.", "Development"),
        ("/local-model-invocation-consent", "Model Consent", "v236.0 Operator-Approved Local Model Invocation Consent Gate: scope model name, prompt suite, context boundary, output use, expiration, and no-default-invocation before any local model run.", "Development"),
        ("/model-evaluation-run-ledger", "Run Ledger", "v237.0 Sandboxed Model Evaluation Run Ledger: record approved model runs, prompt-suite binding, output capture, provider metadata, transcript sanitization, and run status without applying outputs.", "Development"),
        ("/multi-model-output-triage", "Model Triage", "v238.0 Operator-Governed Multi-Model Output Triage: map agreement, explain disagreement, flag hallucinations/contradictions, and prioritize operator review without granting authority.", "Development"),
        ("/model-reliability-profile-candidates", "Model Reliability", "v239.0 Supervised Model Reliability Profile Candidates: stage task-specific reliability, repeated strengths/failures, evidence summaries, and promotion requirements without self-promotion.", "Development"),
        ("/local-model-invocation-sandbox-audit", "Invoke Audit", "v240.0 Operator-Approved Local Model Invocation Sandbox v1: audit consent, run ledger, triage, reliability candidates, no-default-invocation, no-model-authority, dashboard, parity, docs, and smoke.", "Development"),
        ("/model-assisted-patch-critique", "Model Critique", "v241.0 Operator-Governed Model-Assisted Patch Critique Layer: package approved model outputs into evidence-scored critique packets without authority.", "Development"),
        ("/multi-model-review-synthesis", "Review Synthesis", "v242.0 Supervised Multi-Model Review Synthesis Layer: cluster agreement, disagreement, hallucination candidates, and useful findings without approval.", "Development"),
        ("/patch-risk-remediation-synthesis", "Risk Synthesis", "v243.0 Operator-Governed Patch Risk and Remediation Synthesis: turn model critiques into review-only risks, remediation candidates, verification suggestions, and docs impact.", "Development"),
        ("/model-review-quality-calibration", "Review Quality", "v244.0 Supervised Model Review Quality Calibration: track useful findings, false positives, hallucinations, missed issues, and task-specific model usefulness without promotion.", "Development"),
        ("/model-assisted-patch-review-audit", "Review Audit", "v245.0 Operator-Governed Model-Assisted Patch Review and Synthesis Layer v1: audit critique, synthesis, risk remediation, quality calibration, no-model-authority, no-source-mutation, parity, docs, and smoke.", "Development"),
        ("/model-assisted-patch-draft", "Patch Draft", "v246.0 Operator-Governed Model-Assisted Patch Draft Packet Layer: assemble reviewable model-assisted patch draft packets without writing files or approving implementation.", "Development"),
        ("/file-impact-documentation-planner", "Impact Planner", "v247.0 Supervised File Impact and Documentation Planner: map source, dashboard, API/CLI, README, and release-history impacts without applying changes.", "Development"),
        ("/smoke-verification-suggestions", "Verify Plan", "v248.0 Supervised Smoke and Verification Suggestion Layer: suggest smoke, parity, package privacy, dashboard regression, and extracted ZIP checks without running commands.", "Development"),
        ("/sandbox-preparation-packet", "Sandbox Prep", "v249.0 Operator-Governed Sandbox Preparation Packet Layer: prepare readiness, approval scope, risk, rollback, expected output, and checklist without executing sandbox work.", "Development"),
        ("/patch-draft-assembly-audit", "Draft Audit", "v250.0 Operator-Governed Model-Assisted Patch Draft Assembly Layer v1: audit draft traceability, file impact, docs, verification suggestions, sandbox prep, no-source-mutation, parity, docs, and smoke.", "Development"),
        ("/draft-to-execution-packet", "Exec Packet", "v251.0 Operator-Governed Draft-to-Execution Packet Gate: convert draft packets into review-only execution-packet candidates with selected scope, evidence, and default blocked approval state.", "Development"),
        ("/patch-diff-preview-planner", "Diff Preview", "v252.0 Supervised Patch Diff Preview and Edit Plan Layer: map file anchors, before/after previews, docs edits, runtime effects, and overreach without mutating source.", "Development"),
        ("/execution-approval-scope", "Approval Scope", "v253.0 Operator-Governed Explicit Approval Scope Ledger: track exact, fresh, scoped approval receipts without treating vague enthusiasm as authorization.", "Development"),
        ("/verification-rollback-packet", "Verify/Rollback", "v254.0 Supervised Verification and Rollback Packet Planner: prepare suggested checks and rollback plans without running commands or altering files.", "Development"),
        ("/patch-execution-packet-audit", "Exec Audit", "v255.0 Operator-Governed Patch Execution Packet Bridge v1: audit traceability, diff preview, approval scope, verification, rollback, no-model-authority, and no-source-mutation boundaries.", "Development"),
        ("/application-prep-intake", "App Intake", "v256.0 Operator-Governed Execution Packet Intake Layer: normalize execution packets into review-only application prep scope, docs obligations, approval receipts, and blocked items.", "Development"),
        ("/source-edit-application-plan", "Edit Plan", "v257.0 Supervised Source Edit Application Plan Builder: prepare target-file edit plans, anchors, previews, conflicts, and generated-content boundaries without mutating source.", "Development"),
        ("/documentation-application-plan", "Doc Plan", "v258.0 Supervised Documentation and Release Metadata Application Plan: plan README, release history, version markers, runtime docs, and completeness checks without writing files.", "Development"),
        ("/final-application-governance-gate", "Final Gate", "v259.0 Operator-Governed Final Pre-Application Governance Gate: verify approval freshness, scope match, verification, rollback, and no-autonomy boundaries without granting authority.", "Development"),
        ("/application-prep-integration-audit", "Prep Audit", "v260.0 Operator-Governed Approved Execution Packet Application Prep v1: audit intake, source edit plans, documentation plans, approval binding, verification, rollback, no-execution, and API/CLI parity.", "Development"),
        ("/structural-inventory", "Structure", "v261.0 Operator-Governed Structural Inventory Layer: inventory central file size, runtime surfaces, dashboard/API/CLI commands, smoke coverage, docs dependencies, and safe module boundaries without behavior changes.", "Development"),
        ("/runtime-registry-prep", "Registry", "v262.0 Operator-Governed Runtime Registry Prep Layer: prepare shared runtime metadata for capability, route, CLI, API, dashboard, safety, docs, and smoke entries without replacing dispatch.", "Development"),
        ("/dashboard-stabilization-audit", "Dash Stable", "v263.0 Operator-Governed Dashboard Stabilization Layer: preserve command-deck layout, custom data-tip hover behavior, route parity, and no native nav title tooltip regressions.", "Development"),
        ("/dispatch-stabilization", "Dispatch", "v264.0 Operator-Governed CLI/API Dispatch Stabilization Layer: inventory CLI/API dispatch, parity, missing surfaces, and regression smoke suggestions without executing commands.", "Development"),
        ("/structural-stabilization-audit", "Refactor Ready", "v265.0 Operator-Governed Structural Stabilization and Runtime Modularization v1: audit structural drift, runtime parity, dashboard route parity, API/CLI parity, docs completeness, package privacy, extracted ZIP verification, and refactor risk.", "Development"),
        ("/runtime-registry", "Registry Live", "v266.0 Operator-Governed Runtime Metadata Registry Extraction: source-only runtime_registry.py metadata helper, capability/route/CLI/API/dashboard/safety extraction, compatibility adapters, smoke hooks, and no-behavior-change audit.", "Development"),
        ("/governance-report-builder-audit", "Report Builder", "v267.0 Operator-Governed Governance Report Builder Extraction: source-only governance_reports.py helpers, packet/safety/approval/verification/audit renderers, wrappers, output parity, and no-authority-change audit.", "Development"),
        ("/dashboard-registry-integration", "Dash Registry", "v268.0 Operator-Governed Dashboard Surface Registry Integration: dashboard registry adapter, nav metadata, route labels, data-tip binding, title regression guard, style preservation, and route parity.", "Development"),
        ("/runtime-dispatch-registry-audit", "Dispatch Reg", "v269.0 Operator-Governed CLI/API Runtime Registry Integration: CLI/API registry adapters, shared command metadata, dynamic dispatch parity, missing surface guards, naming checks, and no-execution audit.", "Development"),
        ("/module-extraction-audit", "Module Audit", "v270.0 Operator-Governed Runtime Module Extraction v1: audit extracted module imports, registry parity, governance report parity, dashboard/API/CLI parity, package privacy, docs, smoke, and refactor risks.", "Development"),
        ("/self-maintenance-extraction-map", "SM Map", "v271.0 Operator-Governed Self-Maintenance Extraction Map: function clusters, runtime reports, governance audits, package/privacy, version markers, smoke coverage, extraction priorities, wrappers, and no-behavior-change audit.", "Development"),
        ("/package-version-integrity", "Pkg/Version", "v272.0 Operator-Governed Package and Version Utility Extraction: package_integrity.py, version_state.py, source-only policy, forbidden runtime path detection, version markers, release marker adapters, wrappers, and parity audit.", "Development"),
        ("/surface-parity-audit", "Surface Parity", "v273.0 Operator-Governed Surface Parity Utility Extraction: surface_parity.py dashboard/API/CLI presence helpers, registry binding, missing surface detection, parity renderer, wrappers, and route/API/CLI audit.", "Development"),
        ("/verification-planning-audit", "Verify Plan", "v274.0 Operator-Governed Smoke and Verification Utility Extraction: verification_planning.py fast/install/extracted zip/dashboard tooltip/package privacy verification suggestions, readiness summaries, wrappers, and no-command-execution audit.", "Development"),
        ("/self-maintenance-decomposition-audit", "SM Decomp", "v275.0 Operator-Governed Self-Maintenance Decomposition v1: utility imports, wrappers, output parity, package/version, surfaces, verification planning, dashboard, API/CLI, docs, smoke, and safety boundaries.", "Development"),
        ("/dashboard-extraction-map", "Dash Map", "v276.0 Operator-Governed Dashboard Surface Extraction Map: dashboard function clusters, navigation, route handlers, page renderers, console style dependencies, data-tip tooltip dependencies, wrappers, and no-visual-change audit.", "Development"),
        ("/dashboard-component-audit", "Dash Components", "v277.0 Operator-Governed Dashboard Component Helper Extraction: dashboard_components.py, console cards, status rows, audit sections, packet summaries, tooltip-safe nav helpers, wrappers, and style audit.", "Development"),
        ("/api-surface-audit", "API Surface", "v278.0 Operator-Governed API Surface Helper Extraction: api_surface.py route metadata, runtime JSON helpers, error helpers, dynamic route summaries, parity checks, wrappers, and no-behavior-change audit.", "Development"),
        ("/cli-surface-audit", "CLI Surface", "v279.0 Operator-Governed CLI Surface Helper Extraction: cli_surface.py command metadata, JSON/human renderers, dynamic command summaries, parity checks, wrappers, and no-execution-authority audit.", "Development"),
        ("/interface-modularization-audit", "Interface Audit", "v280.0 Operator-Governed Dashboard/API/CLI Modularization v1: helper imports, route/nav parity, API/CLI runtime parity, data-tip tooltip regression, command-deck preservation, docs, package privacy, and no-authority boundaries.", "Development"),
        ("/approved-application-binding", "App Binding", "v281.0 Operator-Approved Application Packet Binding Layer: packet id, approved file/edit/docs/verification scope, approval freshness, and no-inferred-approval audit.", "Development"),
        ("/operator-execution-checklist", "Exec Checklist", "v282.0 Operator Execution Checklist Builder Layer: pre-application, source edit, README/release history, smoke, package privacy, and rollback preparedness checklist, without command execution.", "Development"),
        ("/post-application-result-review", "Post-App Review", "v283.0 Operator-Governed Post-Application Result Review Layer: expected change binding, observed/smoke/package/surface result intake, deviation classification, and no-auto-rollback audit.", "Development"),
        ("/application-outcome-learning", "Outcome Learning", "v284.0 Operator-Governed Application Outcome Learning Extractor: supervised success/failure/smoke/docs/approval lessons and future risk notes, without memory mutation.", "Development"),
        ("/application-execution-refinement-audit", "App Exec Audit", "v285.0 Operator-Approved Application Execution Refinement v1: approval binding, execution checklist, post-application review, supervised outcome lessons, parity, package privacy, smoke, and no-autonomy audit.", "Development"),
        ("/rollback-scope-binding", "Rollback Scope", "v286.0 Operator-Governed Rollback Scope Binding Layer: application packet rollback binding, file/docs/version scope, package/smoke context, route coverage, and no-auto-rollback audit.", "Development"),
        ("/failure-damage-map", "Failure Map", "v287.0 Operator-Governed Failure Classification and Damage Map: compile, smoke, dashboard, API/CLI, package privacy, and partial application failure classification without diagnostic overreach.", "Development"),
        ("/recovery-checklist", "Recovery List", "v288.0 Operator-Governed Recovery Checklist Builder: manual stop conditions, file/docs/version recovery, verification rerun suggestions, package rebuild checklist, and no-command-execution audit.", "Development"),
        ("/post-recovery-review", "Recovery Review", "v289.0 Operator-Governed Post-Recovery Review Layer: expected clean state, observed recovery result intake, drift classification, verification/package review, and no-auto-continuation audit.", "Development"),
        ("/rollback-recovery-audit", "Rollback Audit", "v290.0 Operator-Governed Rollback and Recovery Intelligence v1: rollback scope, failure map, recovery checklist, post-recovery review, parity, package privacy, smoke, and no-autonomy audit.", "Development"),
        ("/memory-candidate-intake", "Memory Intake", "v291.0 Operator-Governed Memory Candidate Intake Layer: patch/recovery/smoke/operator/model source binding, confidence classification, and no-memory-mutation audit.", "Development"),
        ("/memory-candidate-classification", "Memory Classify", "v292.0 Operator-Governed Memory Candidate Classification Layer: project fact, workflow preference, governance rule, capability lesson, sensitive/identity boundary, and risk scoring review.", "Development"),
        ("/memory-approval-packet", "Memory Approval", "v293.0 Operator-Governed Memory Approval Packet Builder: candidate/evidence/risk summaries, approve/reject/defer options, expiration, revalidation, and no-implied-approval audit.", "Development"),
        ("/memory-contradiction-review", "Memory Conflict", "v294.0 Operator-Governed Memory Contradiction and Staleness Review: rule conflicts, project-state conflicts, stale preference detection, purpose drift, governance boundary conflict, and revalidation review.", "Development"),
        ("/memory-governance-audit", "Memory Gov", "v295.0 Operator-Governed Memory Candidate Governance Upgrade v1: intake, classification, approval packets, contradiction/staleness, parity, package privacy, smoke, and no-memory-mutation audit.", "Development"),
        ("/continuity-state-intake", "Continuity", "v296.0 Operator-Governed Continuity State Intake Layer: current version, recent arcs, active surfaces, governance boundaries, memory candidates, recovery lessons, and no-state-mutation audit.", "Development"),
        ("/self-model-snapshot-v2", "Self-Model v2", "v297.0 Operator-Governed Self-Model Snapshot v2 Builder: capability claims, limitations, governance rules, tooling boundaries, environment, stale-claim detection, and no-identity-mutation audit.", "Development"),
        ("/purpose-coherence-review", "Purpose v2", "v298.0 Operator-Governed Purpose Drift and Coherence Review v2: original purpose, current direction, governance alignment, autonomy creep, tooling scope creep, coherence risk, and no-auto-correction audit.", "Development"),
        ("/supervised-growth-priorities", "Growth Priority", "v299.0 Operator-Governed Supervised Growth Priority Synthesizer: capability gaps, structural debt, governance risk, memory risk, recovery lessons, next arc recommendations, and no-auto-roadmap audit.", "Development"),
        ("/continuity-kernel-v2-audit", "Kernel v2", "v300.0 Local Artificial Mind Continuity Kernel v2: continuity state, self-model snapshot, purpose coherence, growth priorities, surface parity, package privacy, smoke, and no-autonomy audit.", "Development"),
        ("/identity-expression-boundary", "Identity Expr", "v301.0 Operator-Governed Identity Expression Boundary Layer: review-only identity wording boundaries, consciousness claim calibration, purpose binding, and no-identity-mutation audit.", "Development"),
        ("/personality-trait-ledger", "Trait Ledger", "v302.0 Operator-Governed Personality Trait Candidate Ledger: review-only traits, evidence, intensity, conflict, risk, and no-personality-mutation audit.", "Development"),
        ("/voice-affect-style-map", "Voice Map", "v303.0 Operator-Governed Voice and Affect Style Map: context-sensitive voice previews, affect boundaries, refusal/safety voice, and no live prompt rewrite.", "Development"),
        ("/coherence-expression-review", "Expr Coherence", "v304.0 Operator-Governed Coherence Expression Review: identity, personality, purpose, voice, desire, opinion, and governance consistency review without auto-correction.", "Development"),
        ("/identity-personality-coherence-audit", "Expression Audit", "v305.0 Operator-Governed Identity, Personality, and Coherence Expression Layer v1: audits identity expression, personality ledger, voice map, coherence review, risky-request blocking, route parity, package privacy, and no-autonomy boundaries.", "Development"),
        ("/dashboard-route-health", "Route Health", "v306.0 Operator-Governed Dashboard Route Health Registry v1: registers critical dashboard routes, render expectations, HTML shape markers, and review-only route health reports.", "Development"),
        ("/runtime-test-visibility", "Smoke View", "v307.0 Operator-Governed Runtime Test Visibility Layer v1: names smoke tiers, route probes, progress markers, timeout summaries, metadata checks, and extracted-zip parity without executing hidden work.", "Development"),
        ("/behavioral-expression-preview", "Behavior Preview", "v308.0 Operator-Governed Behavioral Expression Preview Packets v1: previews identity/personality/coherence-safe response variants without changing live chat, prompts, memory, identity, or personality.", "Development"),
        ("/style-delta-staging", "Style Deltas", "v309.0 Operator-Governed Style Delta Staging v1: stages style, prompt, dashboard, README, warning, and refusal wording deltas for review only without applying source changes.", "Development"),
        ("/expression-runtime-health-audit", "v310 Audit", "v310.0 Operator-Governed Behavioral Expression Preview and Runtime Health Hardening v1: audits route health, smoke visibility, metadata, expression previews, style deltas, parity, privacy, and no-autonomy boundaries.", "Development"),
        ("/expression-profile-packets", "Expr Profiles", "v311.0 Operator-Governed Expression Profile Packet Assembly v1: assembles identity, trait, voice, affect, and governance constraints into review-only expression profiles without applying them.", "Development"),
        ("/conversation-scenario-sandbox", "Scenario Sandbox", "v312.0 Operator-Governed Conversation Scenario Sandbox v1: previews coding, governance, sensitive, planning, refusal, and dashboard microcopy scenarios without changing live chat.", "Development"),
        ("/expression-regression-review", "Expr Regression", "v313.0 Operator-Governed Expression Regression Review v1: flags autonomy creep, sentience overclaims, dependency theater, overconfidence, purpose drift, and governance conflicts.", "Development"),
        ("/expression-operator-review-console", "Expr Review", "v314.0 Operator-Governed Expression Candidate Review Console v1: reviews profiles, scenario outputs, risk flags, readiness scores, and approval boundaries without granting approval.", "Development"),
        ("/conversational-expression-sandbox-audit", "v315 Audit", "v315.0 Operator-Governed Conversational Expression Sandbox v1: audits profile packets, scenario sandboxing, regression review, operator review console, route health, smoke, parity, privacy, and no-autonomy boundaries.", "Development"),
        ("/expression-approval-criteria", "Expr Criteria", "v316.0 Operator-Governed Expression Approval Criteria Layer v1: binds sandbox, regression, and operator review evidence into readiness criteria without granting approval.", "Development"),
        ("/expression-live-surface-impact-map", "Expr Surfaces", "v317.0 Operator-Governed Live Surface Impact Map v1: maps chat, dashboard, docs, API, CLI, warning, and rollback surfaces without mutating live behavior.", "Development"),
        ("/expression-implementation-packet-draft", "Expr Packet", "v318.0 Operator-Governed Expression Implementation Packet Drafting v1: drafts reviewable implementation packets without writing source or applying prompts.", "Development"),
        ("/expression-rollback-reversion-plan", "Expr Rollback", "v319.0 Operator-Governed Expression Rollback and Reversion Planning v1: plans reversible expression changes without executing rollback.", "Development"),
        ("/expression-application-bridge-audit", "v320 Audit", "v320.0 Operator-Governed Conversational Expression Application Bridge v1: audits approval criteria, surface maps, packet drafts, rollback plans, route health, smoke, parity, privacy, and no-application boundaries.", "Development"),
        ("/expression-patch-candidates", "v321 Candidates", "v321.0 Operator-Governed Expression Patch Candidate Schema v1: represents expression/personality source-change candidates as review-only packets without applying or writing source.", "Development"),
        ("/expression-sandbox-diff-preview", "v322 Diff Preview", "v322.0 Operator-Governed Sandbox Diff Preview Assembly v1: previews before/after expression diffs in sandbox form without applying live diffs.", "Development"),
        ("/expression-dry-run-verification-plan", "v323 Verify Plan", "v323.0 Operator-Governed Expression Dry-Run Verification Planning v1: prepares compile, smoke, route, regression, privacy, package, and rollback checks without executing commands.", "Development"),
        ("/expression-dry-run-review-packet", "v324 Review Packet", "v324.0 Operator-Governed Expression Dry-Run Review Packet v1: combines candidates, diff previews, risk flags, verification plans, rollback expectations, and approval boundaries without granting approval.", "Development"),
        ("/expression-patch-dry-run-audit", "v325 Dry-Run Audit", "v325.0 Operator-Governed Expression Patch Dry-Run Sandbox v1: audits patch candidates, diff previews, verification plans, review packets, route health, smoke, parity, docs, privacy, and no-application boundaries.", "Development"),
        ("/expression-sandbox-trial-packet", "v326 Trial Packet", "v326.0 Operator-Governed Expression Sandbox Trial Packet Prep v1: prepares sandbox trial packets from dry-run review evidence without creating, modifying, or executing sandboxes.", "Development"),
        ("/expression-sandbox-workspace-plan", "v327 Workspace", "v327.0 Operator-Governed Expression Sandbox Workspace Plan v1: plans source-only sandbox workspaces and runtime privacy exclusions without copying or writing files.", "Development"),
        ("/expression-sandbox-verification-matrix", "v328 Verify Matrix", "v328.0 Operator-Governed Expression Sandbox Trial Verification Matrix v1: plans sandbox compile, smoke, route, API/CLI, regression, privacy, package, and rollback checks without executing commands.", "Development"),
        ("/expression-sandbox-result-review-prep", "v329 Result Prep", "v329.0 Operator-Governed Expression Sandbox Trial Result Review Prep v1: prepares future sandbox result review, failure classification, and operator decision options without promotion inference.", "Development"),
        ("/expression-sandbox-trial-harness-audit", "v330 Trial Audit", "v330.0 Operator-Governed Expression Patch Sandbox Trial Harness v1: audits trial packets, workspace plans, verification matrices, result review prep, route health, smoke, parity, docs, privacy, and no-execution boundaries.", "Development"),
        ("/expression-sandbox-execution-approval-gate", "Exec Approval", "v331.0 Operator-Governed Sandbox Trial Execution Approval Gate v1: scope-bound operator approval status, expiration, forbidden actions, decision packet, and no-approval-inference audit.", "Development"),
        ("/expression-sandbox-workspace-execution-packet", "Workspace Packet", "v332.0 Operator-Governed Sandbox Workspace Execution Packet Draft v1: source-only copy instructions, runtime exclusions, sandbox naming, file scope manifest, safety checks, manual notes, and no-copy audit.", "Development"),
        ("/expression-sandbox-patch-bundle-packet", "Patch Bundle", "v333.0 Operator-Governed Expression Sandbox Patch Bundle Packet v1: dry-run diff binding, target manifest, boundary guard, conflict detector, rollback map, review packet, and no-application audit.", "Development"),
        ("/expression-sandbox-verification-command-packet", "Verify Packet", "v334.0 Operator-Governed Sandbox Verification Command Packet Draft v1: compile/smoke/targeted/dashboard/API/CLI/privacy command drafts with manual-run boundary and no-command-execution audit.", "Development"),
        ("/expression-sandbox-execution-packet-bridge-audit", "v335 Exec Bridge", "v335.0 Operator-Governed Expression Sandbox Trial Execution Packet Bridge v1: audits approval gate, workspace packet, patch bundle, verification command packet, parity, smoke, privacy, and no-execution boundaries.", "Development"),
        ("/expression-sandbox-trial-evidence-intake", "Evidence Intake", "v336.0 Operator-Governed Sandbox Trial Evidence Intake Layer v1: accepts sandbox trial evidence as review input only, checks completeness/trust/scope, and never treats results as approval.", "Development"),
        ("/expression-sandbox-outcome-comparison", "Outcome Compare", "v337.0 Operator-Governed Sandbox Outcome Comparison v1: compares expected diff/check results against submitted sandbox evidence without auto-correction or source mutation.", "Development"),
        ("/expression-sandbox-regression-result-review", "Result Regression", "v338.0 Operator-Governed Expression Regression Result Review v1: reviews sandbox outputs for autonomy, sentience, dependency, overconfidence, purpose drift, memory, and approval-boundary regressions.", "Development"),
        ("/expression-sandbox-revision-recommendations", "Revision Recs", "v339.0 Operator-Governed Sandbox Trial Revision Recommendation Layer v1: recommends revise/defer/reject/retry/promote-to-review options without applying revisions.", "Development"),
        ("/expression-sandbox-promotion-review-prep", "Promo Prep", "v340.0 Operator-Governed Expression Sandbox Trial Result Intake and Promotion Review Prep v1: assembles promotion-review prep from evidence, comparison, regression, and revision packets without promotion authority.", "Development"),
        ("/expression-promotion-evidence-binder", "Promo Evidence", "v345.0 Operator-Governed Expression Promotion Evidence Binder v1: binds dry-run, sandbox, execution, result, regression, revision, and rollback evidence without approval authority.", "Development"),
        ("/expression-live-promotion-scope-risk", "Promo Scope", "v345.0 Operator-Governed Live Promotion Scope and Risk Packet v1: maps future live expression surfaces and protected boundaries without mutation.", "Development"),
        ("/expression-promotion-verification-rollback", "Promo Verify", "v345.0 Operator-Governed Promotion Verification and Rollback Requirements v1: defines checks and rollback requirements without executing commands.", "Development"),
        ("/expression-promotion-decision-packet", "Promo Decision", "v345.0 Operator-Governed Expression Promotion Decision Packet v1: prepares operator decision fields without executing or applying decisions.", "Development"),
        ("/expression-promotion-packet-assembly-audit", "Promo Audit", "v345.0 Operator-Governed Expression Promotion Packet Assembly Layer v1: audits packet-only promotion review surfaces without live promotion authority.", "Development"),
        ("/expression-live-application-eligibility-gate", "Live Elig", "v346.0 Operator-Governed Live Application Packet Eligibility Gate v1: checks fresh scoped approval eligibility for drafting only without authorizing live writes.", "Development"),
        ("/expression-live-source-change-manifest", "Live Manifest", "v347.0 Operator-Governed Live Source Change Manifest Draft v1: maps future live expression targets and protected paths without writing files.", "Development"),
        ("/expression-live-patch-instruction-packet", "Live Patch", "v348.0 Operator-Governed Live Diff and Patch Instruction Packet Draft v1: drafts future patch instructions without applying them.", "Development"),
        ("/expression-live-verification-rollback-packet", "Live Verify", "v349.0 Operator-Governed Live Application Verification and Rollback Packet v1: defines checks and rollback expectations without executing commands.", "Development"),
        ("/expression-live-application-packet-audit", "Live App Audit", "v350.0 Operator-Governed Expression Live Application Packet Drafting Layer v1: audits draft-only live application packets without live source authority.", "Development"),
        ("/expression-live-execution-approval-intake", "Exec Prep Approval", "v351.0 Operator-Governed Live Expression Execution Approval Intake Gate v1: binds fresh scoped approval for execution prep only without applying live expression.", "Development"),
        ("/expression-live-source-transaction-preimage", "Exec Prep Tx", "v352.0 Operator-Governed Live Source Transaction and Preimage Manifest Prep v1: plans read/write/preimage manifests without source mutation.", "Development"),
        ("/expression-live-manual-execution-checklist", "Exec Checklist", "v353.0 Operator-Governed Manual Execution Checklist and Command Packet v1: drafts manual commands as text only without running them.", "Development"),
        ("/expression-live-rollback-reversion-packet", "Exec Rollback", "v354.0 Operator-Governed Rollback Snapshot and Reversion Packet Prep v1: prepares rollback material without restoring files.", "Development"),
        ("/expression-live-execution-prep-audit", "Exec Prep Audit", "v355.0 Operator-Governed Expression Live Application Execution Prep Layer v1: audits execution-prep packets without continuing into execution.", "Development"),
        ("/minimal-live-expression-change-candidate", "Min Expr Candidate", "v356.0 Minimal Approved Live Change Candidate Selection v1: identifies tiny expression-adjacent docs/dashboard/test wording changes without applying them.", "Development"),
        ("/minimal-live-expression-approval-lock", "Min Expr Approval", "v357.0 Operator Approval Token and Execution Scope Lock v1: locks one fresh single-use approval scope without self-approval or scope expansion.", "Development"),
        ("/minimal-live-expression-patch-transaction", "Min Expr Patch", "v358.0 Tiny Patch Transaction Builder v1: previews exact files, preimage, diff, rollback, and verification plan without writing files.", "Development"),
        ("/minimal-live-expression-application-harness", "Min Expr Harness", "v359.0 Operator-Confirmed Patch Application Harness v1: requires exact confirmation, matching preimage, rollback, and verification evidence before any later application.", "Development"),
        ("/minimal-live-expression-application-audit", "Min Expr Audit", "v360.0 Operator-Approved Minimal Live Expression Application Execution Path v1: audits one tiny governed live-expression change path without autonomous continuation.", "Development"),
        ("/self-maintenance-gate-registry", "Gate Registry", "v361.0 Self-Maintenance Gate Inventory and Registry Seed v1: inventories gate families and seeds review-only registry metadata without behavior changes.", "Development"),
        ("/self-maintenance-version-expectations", "Version Registry", "v362.0 Centralized Self-Maintenance Version Expectation Layer v1: centralizes current-version expectations and stale literal detection without applying changes.", "Development"),
        ("/governed-surface-metadata-registry", "Surface Registry", "v363.0 Governed Surface Metadata Registry v1: maps dashboard/API/CLI metadata for parity review without changing routes.", "Development"),
        ("/smoke-check-legacy-gate-registry", "Smoke Registry", "v364.0 Smoke Check Registry and Legacy Gate Cleanup v1: registers smoke coverage and legacy gate cleanup helpers without executing checks automatically.", "Development"),
        ("/self-maintenance-refactor-audit", "v365 Refactor", "v365.0 Self-Maintenance Surface Reduction and Gate Registry Refactor v1: audits registry-driven self-maintenance cleanup, version expectations, route/API/CLI parity, smoke registry coverage, package privacy, and no-autonomy boundaries.", "Development"),
        ("/self-maintenance-module-extraction-plan", "Extract Plan", "v371.0 Self-Maintenance Module Extraction Plan v1: maps safe self-maintenance module extraction families before moving logic.", "Development"),
        ("/self-maintenance-version-package-gates", "Version Gates", "v372.0 Version and Package Gate Extraction v1: extracts version/package/privacy helpers into a focused review-only module.", "Development"),
        ("/self-maintenance-surface-gates", "Surface Gates", "v373.0 Route/API/CLI Gate Extraction v1: extracts route/API/CLI parity helpers into a focused review-only module.", "Development"),
        ("/self-maintenance-governance-gates", "Gov Gates", "v374.0 Governance Boundary Gate Extraction v1: extracts forbidden-action boundary helpers into a focused review-only module.", "Development"),
        ("/self-maintenance-modular-extraction-audit", "v375 Modular", "v375.0 Self-Maintenance Modular Extraction v1: audits extracted modules, version/package gates, surface gates, governance gates, smoke coverage, package privacy, and no-autonomy boundaries.", "Development"),
        ("/live-change-transaction-narrowing", "Tx Narrow", "v376.0 Live Change Transaction Narrowing v1: narrows one approved live-change transaction to a tiny allowed file surface without applying it.", "Development"),
        ("/live-change-approval-execution-lock", "Exec Lock", "v377.0 Live Change Approval Execution Lock v1: binds fresh single-use approval, exact scope, expiration, and confirmation phrase without self-approval.", "Development"),
        ("/live-change-real-patch-trial-plan", "Patch Trial Plan", "v378.0 Live Change Real Patch Trial Plan v1: prepares preimage, diff, README/release updates, rollback, and verification plan without writing files.", "Development"),
        ("/live-change-operator-confirmed-application-trial", "Apply Trial", "v379.0 Operator-Confirmed Live Change Application Trial v1: requires explicit operator confirmation, preimage match, allowed-file match, rollback, and verification evidence.", "Development"),
        ("/live-change-application-trial-audit", "v380 Trial", "v380.0 Approved Live Change Transaction Narrowing and Real Patch Application Trial v1: audits the narrow confirmed application trial without automatic continuation.", "Development"),
        ("/live-patch-trial-result-intake", "Trial Result", "v381.0 Operator-Governed Live Patch Trial Result Intake v1: ingests reported trial outcome evidence without rerunning commands, applying fixes, executing rollback, or inferring future approval.", "Development"),
        ("/live-patch-applied-diff-evidence", "Diff Evidence", "v382.0 Operator-Governed Applied Diff and Source-State Evidence Packet v1: records expected/actual diff and source-state evidence without generating patches or editing source.", "Development"),
        ("/live-patch-approval-burnout", "Approval Burnout", "v383.0 Operator-Governed One-Time Approval Burnout and Reuse Block v1: consumes the single-use approval token and rejects reuse/scope expansion/stale approval.", "Development"),
        ("/live-patch-post-trial-regression-review", "Post Trial", "v384.0 Operator-Governed Post-Trial Regression and Rollback Readiness Review v1: reviews reported regression and rollback readiness without rerunning smoke or rollback.", "Development"),
        ("/live-patch-trial-closure-audit", "v385 Closure", "v385.0 Operator-Confirmed Live Patch Trial Result Intake and One-Time Authorization Burnout v1: audits closure, approval burnout, rollback readiness, docs, privacy, and no-autonomy boundaries.", "Development"),
        ("/second-minimal-live-patch-candidate", "v386 Candidate", "v386.0 Operator-Governed Second Minimal Patch Candidate Registry Selection v1: selects a second tiny registry-safe candidate without autonomous selection or runtime personality change.", "Development"),
        ("/registry-driven-live-patch-approval-validation", "v387 Approval", "v387.0 Operator-Governed Registry-Driven Approval and Scope Validation v1: validates fresh single-use approval, scope, registry metadata, rollback, and verification requirements.", "Development"),
        ("/registry-driven-live-patch-transaction-lock", "v388 Lock", "v388.0 Operator-Governed Registry-Driven Patch Transaction and Preimage Lock v1: locks expected files, preimage, docs, version, smoke, package, and dashboard obligations without writing files.", "Development"),
        ("/second-live-patch-application-harness", "v389 Harness", "v389.0 Operator-Confirmed Second Minimal Live Patch Application Harness v1: requires fresh approval, matching transaction, preimage match, rollback, verification, burnout, closure, and the exact confirmation phrase.", "Development"),
        ("/second-live-patch-trial-registry-audit", "v390 Audit", "v390.0 Second Minimal Approved Live Patch Trial with Registry-Driven Execution Checks v1: audits the second registry-driven patch path, approval burnout, post-trial closure, docs, package privacy, and no-autonomy boundaries.", "Development"),
        ("/live-patch-trial-history-ledger", "v391 Ledger", "v391.0 Operator-Governed Live Patch Trial History Ledger v1: records trial, candidate, approval, transaction, closure, burnout, rollback, and operator decision evidence without treating history as permission.", "Development"),
        ("/operator-live-patch-decision-patterns", "v392 Decisions", "v392.0 Operator-Governed Live Patch Decision Pattern Review v1: reviews approved, blocked, revised, deferred, rollback, reapproval, and burnout decisions without changing future behavior.", "Development"),
        ("/live-patch-supervised-lesson-candidates", "v393 Lessons", "v393.0 Operator-Governed Live Patch Supervised Lesson Candidate Drafting v1: drafts supervised lesson candidates from patch trials without storing memory or altering behavior.", "Development"),
        ("/live-patch-memory-candidate-governance", "v394 Memory Gov", "v394.0 Operator-Governed Live Patch Memory Candidate Governance v1: classifies lesson candidates for possible later memory storage without writing memory.", "Development"),
        ("/live-patch-history-memory-candidate-audit", "v395 Audit", "v395.0 Live Patch Trial History Ledger and Operator Decision Memory Candidate Prep v1: audits ledger, decision review, lesson candidates, memory governance, docs, package privacy, and no-memory-write boundaries.", "Development"),
        ("/memory-candidate-selection-packet", "v396 Mem Pick", "v396.0 Operator-Governed Memory Candidate Selection Packet v1: selects one reviewable memory candidate without writing memory or treating eligibility as approval.", "Development"),
        ("/memory-application-approval-lock", "v397 Mem Lock", "v397.0 Operator-Governed Memory Application Approval Lock v1: binds fresh single-use approval, scope, confirmation, forbidden categories, and audit requirements.", "Development"),
        ("/memory-write-transaction-preview", "v398 Mem Preview", "v398.0 Operator-Governed Memory Write Transaction Preview v1: previews exact memory text, destination, sensitivity screen, scope limits, and retraction plan without writing memory.", "Development"),
        ("/operator-confirmed-memory-application-trial", "v399 Mem Trial", "v399.0 Operator-Confirmed Memory Application Trial Harness v1: requires exact operator confirmation, matching candidate/transaction, screens, single-use approval, retraction packet, and post-application audit.", "Development"),
        ("/memory-application-trial-audit", "v400 Mem Audit", "v400.0 Operator-Approved Memory Candidate Application Trial v1: audits one scoped memory candidate application trial without self-approval, identity/personality mutation, autonomy expansion, or automatic continuation.", "Development"),
        ("/memory-application-confirmation-gate", "v401 Confirm", "v401.0 Memory Application Confirmation Presence Gate v1: requires explicit supplied operator confirmation evidence before any memory application harness may report exact confirmation.", "Development"),
        ("/memory-application-negative-tests", "v402 Neg Tests", "v402.0 Memory Application Negative Confirmation Tests v1: proves missing, wrong, reused, changed, sensitive, identity/personality, and autonomy-expanding evidence remains blocked.", "Development"),
        ("/smoke-segment-registry", "v403 Segments", "v403.0 Smoke Segment Registry v1: classifies the growing smoke suite into bounded install segments without executing checks automatically.", "Development"),
        ("/install-smoke-segment-runner", "v404 Runner", "v404.0 Install Smoke Segment Runner v1: exposes named smoke segment selection and resume metadata while preserving full install smoke.", "Development"),
        ("/segmented-install-smoke-audit", "v405 Smoke Audit", "v405.0 Segmented Install Smoke and Self-Maintenance Confirmation Hardening v1: audits confirmation hardening, segmented smoke coverage, docs, package privacy, and no-authorization boundaries.", "Development"),
        ("/memory-application-attempt-ledger-schema", "v406 Attempt", "v406.0 Memory Application Attempt Ledger Schema v1: defines review-only dry-run attempt records with candidate, approval, confirmation, hashes, blockers, and operator decision placeholders.", "Development"),
        ("/memory-application-dry-run-ledger", "v407 Ledger", "v407.0 Memory Application Dry-Run Ledger Entry Builder v1: builds dry-run ledger entries without writing memory or treating reviewable state as authorization.", "Development"),
        ("/memory-application-ledger-replay", "v408 Replay", "v408.0 Memory Application Ledger Replay and Drift Detection v1: replays dry-run entries and blocks candidate, approval, transaction, confirmation, or memory text drift.", "Development"),
        ("/memory-application-ledger-surfaces", "v409 Surfaces", "v409.0 Memory Application Ledger Dashboard API CLI Surfaces v1: exposes operator review surfaces while preserving command-deck data-tip behavior.", "Development"),
        ("/memory-application-ledger-audit", "v410 Ledger Audit", "v410.0 Operator-Governed Memory Application Dry-Run Ledger v1: audits dry-run ledger records, replay drift detection, docs, package privacy, and no-memory-write boundaries.", "Development"),
        ("/sandbox-memory-target-schema", "v411 Sandbox Target", "v411.0 Sandbox Memory Target Schema v1: defines sandbox-only memory write targets while blocking live memory paths.", "Development"),
        ("/sandbox-memory-write-transaction", "v412 Sandbox Tx", "v412.0 Sandbox Memory Write Transaction Builder v1: prepares sandbox write transactions from dry-run ledger evidence and exact confirmation.", "Development"),
        ("/sandbox-memory-write-trial", "v413 Sandbox Write", "v413.0 Sandbox Memory Write Execution Trial v1: writes only to sandbox targets with before/after hashes.", "Development"),
        ("/sandbox-memory-retraction-preview", "v414 Sandbox Retract", "v414.0 Sandbox Memory Retraction Preview and Replay v1: previews sandbox retraction and drift checks without live memory retraction.", "Development"),
        ("/sandbox-memory-write-audit", "v415 Sandbox Audit", "v415.0 Operator-Governed Sandbox Memory Write Target v1: audits sandbox target, write, retraction, package, and no-live-memory boundaries.", "Development"),
        ("/live-memory-write-eligibility", "v416 Live Elig", "v416.0 Live Memory Write Eligibility Packet v1: checks dry-run, sandbox write, retraction preview, and forbidden memory categories without approval.", "Development"),
        ("/live-memory-approval-lock", "v417 Live Lock", "v417.0 Single-Use Live Memory Approval Lock v1: binds exact confirmation, candidate hash, sandbox trial, and approval burnout.", "Development"),
        ("/live-memory-transaction-preview", "v418 Live Tx", "v418.0 Live Memory Transaction Preview v1: previews exact governed live-memory trial transaction without writing memory.", "Development"),
        ("/operator-confirmed-live-memory-write-trial", "v419 Live Write", "v419.0 Operator-Confirmed Live Memory Write Trial v1: executes one governed trial write only with exact confirmation and burns approval.", "Development"),
        ("/live-memory-write-audit", "v420 Live Audit", "v420.0 First Operator-Approved Live Memory Write with Burnout v1: audits one live memory trial, negative cases, and no-future-authorization boundaries.", "Development"),
        ("/memory-retraction-eligibility", "v421 Retract Elig", "v421.0 Memory Retraction Eligibility Packet v1: checks exact governed trial entry and prior write burnout without approving retraction.", "Development"),
        ("/memory-retraction-approval-lock", "v422 Retract Lock", "v422.0 Memory Retraction Approval Lock v1: binds fresh single-use retraction approval and blocks write-approval reuse.", "Development"),
        ("/memory-retraction-transaction-preview", "v423 Retract Tx", "v423.0 Memory Retraction Transaction Preview v1: previews exact retained-audit retraction without deleting memory.", "Development"),
        ("/operator-confirmed-memory-retraction-trial", "v424 Retract Trial", "v424.0 Operator-Confirmed Memory Retraction Trial v1: marks one exact governed entry retracted after exact confirmation and burns approval.", "Development"),
        ("/memory-retraction-trial-audit", "v425 Retract Audit", "v425.0 Operator-Approved Memory Retraction Trial v1: audits retained retraction, burnout, negative cases, docs, and no-future-authority boundaries.", "Development"),
        ("/source-surface-manifest", "v426 Surface Map", "v426.0 Surface Manifest Schema v1: defines dashboard/API/CLI/builder/smoke/runtime/authority records without authorizing execution.", "Development"),
        ("/source-surface-parity-audit", "v428 Surface Parity", "v428.0 Dashboard API CLI Parity Audit v1: checks manifest surface coverage against registered routes and flags.", "Development"),
        ("/source-surface-authority-map", "v429 Authority Map", "v429.0 Source Surface Authority Map v1: classifies review-only, sandbox-only, and single-use trial surfaces without approval inference.", "Development"),
        ("/source-surface-package-privacy-map", "v429 Privacy Map", "v429.5 Source Surface Package Privacy Map v1: lists runtime paths and source-only exclusions.", "Development"),
        ("/source-surface-manifest-audit", "v430 Surface Audit", "v430.0 Canonical Source Surface Manifest v1: audits parity, authority labels, package privacy, and no-authorization boundaries.", "Development"),
        ("/duplicate-definition-inventory", "v431 Duplicate Inventory", "v431.0 Duplicate Definition Inventory v1: scans source with AST and inventories duplicate definitions without authorizing deletion.", "Development"),
        ("/self-maintenance-duplicate-classification", "v432 Duplicate Classify", "v432.0 Self-Maintenance Duplicate Classification Packet v1: classifies self_maintenance.py duplicate definitions for manual review.", "Development"),
        ("/self-maintenance-extraction-candidates", "v433 Extraction Plan", "v433.0 Safe Extraction Candidate Plan v1: recommends bridge-preserving extraction candidates protected by source surface parity.", "Development"),
        ("/duplicate-definition-guard", "v434 Duplicate Guard", "v434.0 Duplicate Definition Guard v1: blocks new high-risk duplicate shadowing without editing source.", "Development"),
        ("/self-maintenance-duplicate-cleanup-audit", "v435 Duplicate Audit", "v435.0 Self-Maintenance Duplicate Definition Cleanup v1: audits inventory, classification, guard, docs, and no-auto-edit boundaries.", "Development"),
        ("/dashboard-route-inventory", "v436 Route Inv", "v436.0 Dashboard Route Inventory Manifest v1: inventories dashboard routes, labels, eras, authority levels, and tooltip expectations without authorizing execution.", "Development"),
        ("/dashboard-route-probe", "v437 Route Probe", "v437.0 Dashboard Render Probe Runner v1: probes route health, status, content type, error markers, and API shadowing risks.", "Development"),
        ("/dashboard-lazy-render-audit", "v438 Lazy Audit", "v438.0 Lazy Render and Heavy Page Audit v1: classifies heavy dashboard pages without refactoring them automatically.", "Development"),
        ("/dashboard-tooltip-regression-audit", "v439 Tooltip Audit", "v439.0 Dashboard Tooltip Regression Audit v1: protects custom data-tip hover behavior and blocks native title tooltip regression.", "Development"),
        ("/dashboard-route-health-audit", "v440 Route Health", "v440.0 Full Dashboard Route Probe and Lazy Render Audit v1: audits inventory, route probe, lazy render, tooltip regression, docs, and no-authorization boundaries.", "Development"),
        ("/memory-lifecycle-review-board", "v441 Memory Board", "v441.0 Memory Lifecycle Board Schema v1: defines candidate, dry-run, sandbox, live-trial, burnout, retraction, and audit sections without authorizing action.", "Development"),
        ("/memory-lifecycle-state-summary", "v442 Lifecycle State", "v442.0 Memory Lifecycle State Summary v1: aggregates lifecycle state while preserving no-current-authority boundaries.", "Development"),
        ("/memory-lifecycle-drift-review", "v443 Lifecycle Drift", "v443.0 Memory Lifecycle Drift Review v1: flags hash, approval, target, and downstream staleness risks as blockers.", "Development"),
        ("/memory-lifecycle-operator-decision-board", "v444 Decision Board", "v444.0 Memory Lifecycle Operator Decision Board v1: lists review decisions and forbids memory actions without fresh single-use approval.", "Development"),
        ("/memory-lifecycle-review-board-audit", "v445 Board Audit", "v445.0 Memory Lifecycle Review Board v1: audits board schema, state, drift, decisions, docs, and no-authorization boundaries.", "Development"),
        ("/authorization-confusion-patterns", "v446 Auth Patterns", "v446.0 Authorization Confusion Pattern Registry v1: registers forbidden readiness/approval confusion patterns without approving or enforcing anything.", "Development"),
        ("/authorization-language-scan", "v447 Auth Scan", "v447.0 Packet Language and Metadata Scanner v1: scans recent governance outputs for risky authorization language without rewriting source.", "Development"),
        ("/authorization-firewall-decision-packet", "v448 Auth Decision", "v448.0 Authorization Firewall Decision Packet v1: reports clear/warning/blocked status while clear is still not approval.", "Development"),
        ("/authorization-boundary-map", "v449 Auth Map", "v449.0 Authorization Boundary Map v1: maps readiness, eligibility, route health, manifest presence, smoke success, prior approval, and sandbox success to safe interpretations.", "Development"),
        ("/authorization-firewall-audit", "v450 Auth Firewall", "v450.0 Governance-State-to-Authorization Firewall v1: audits authorization confusion detection and no-authorization boundaries.", "Development"),
        ("/metadata-version-inventory", "v451 Meta Inv", "v451.0 Metadata Version Inventory v1: checks allowlisted source metadata version alignment without authorizing release or edits.", "Development"),
        ("/project-workspace-metadata-alignment", "v452 Meta Align", "v452.0 Project and Workspace Metadata Alignment v1: aligns current milestone metadata across project and workspace records.", "Development"),
        ("/release-packaging-version-integrity", "v453 Release Ver", "v453.0 Release Packaging Version Integrity v1: verifies release packaging resolves settings_version before stale fallback values.", "Development"),
        ("/current-state-documentation-header-audit", "v454 Docs Header", "v454.0 Current-State Documentation Header Audit v1: verifies current-state README headers and no-authorization language.", "Development"),
        ("/metadata-release-integrity-audit", "v455 Meta Repair", "v455.0 Metadata, Release Integrity, and Current-State Repair v1: audits metadata, release version resolution, docs, smoke/API/CLI tokens, and no-authorization boundaries.", "Development"),
        ("/authorization-firewall-severity-classifier", "v456 Auth Severity", "v456.0 Authorization Firewall Finding Severity Classifier v1: classifies safe, informational, warning, high-risk, and blocked-pattern findings without granting authorization.", "Development"),
        ("/authorization-firewall-safe-boundary-filter", "v457 Auth Filter", "v457.0 Authorization Firewall Safe Boundary Filter v1: separates safe negative boundary language from reviewable warnings without rewriting source.", "Development"),
        ("/authorization-firewall-warning-status", "v458 Warning Status", "v458.0 Authorization Firewall Warning Status Bridge v1: preserves pass_with_warnings and review_required semantics across surfaces.", "Development"),
        ("/authorization-firewall-audit-status-split", "v459 Status Split", "v459.0 Authorization Firewall Audit Status Split v1: separates mechanism, language, operator review, and authorization statuses.", "Development"),
        ("/authorization-firewall-signal-triage-audit", "v460 Auth Triage", "v460.0 Authorization Firewall Signal Triage and Warning Semantics v1: audits warning semantics while preserving no-authorization boundaries.", "Development"),
        ("/recent-dashboard-route-probe-refresh", "v461 Route Refresh", "v461.0 Recent Dashboard Route Probe Refresh v1: adds v450-v465 routes to route probe inventory while preserving route-health-is-not-approval boundaries.", "Development"),
        ("/source-surface-manifest-parity-policy", "v462 Manifest Policy", "v462.0 Source Surface Manifest Parity Policy v1: tracks every governed substage surface instead of milestone finals only, without granting permission.", "Development"),
        ("/surface-route-api-cli-crosscheck", "v463 Surface Crosscheck", "v463.0 Surface Route API CLI Crosscheck v1: compares manifest, dashboard, API, CLI, builders, text renderers, and smoke tokens in review-only mode.", "Development"),
        ("/route-health-boundary-language", "v464 Route Boundary", "v464.0 Route Health Boundary Language v1: clarifies route health confirms render status only and does not authorize execution.", "Development"),
        ("/route-surface-parity-audit", "v465 Surface Parity", "v465.0 Dashboard Route Probe and Source Surface Manifest Parity v1: audits route/surface/API/CLI/smoke parity with no-authorization boundaries.", "Development"),
        ("/duplicate-shadow-inventory", "v466 Shadow Inv", "v466.0 Duplicate Definition Inventory and Classification v1: inventories current top-level self_maintenance duplicate shadows after cleanup without authorizing deletion.", "Development"),
        ("/safe-shadow-removal-report", "v467 Shadow Remove", "v467.0 Safe Shadow Removal Report v1: records removal of shadowed legacy definitions while preserving canonical final definitions.", "Development"),
        ("/legacy-alias-compatibility-cleanup", "v468 Compat", "v468.0 Legacy Alias Compatibility Cleanup v1: checks canonical helper definitions remain after duplicate body removal.", "Development"),
        ("/stale-version-gate-cleanup", "v469 Gate Cleanup", "v469.0 Stale Exact-Version Gate Cleanup v1: replaces stale v68/v70 exact-version blockers with explicit historical compatibility gates.", "Development"),
        ("/self-maintenance-duplicate-shadow-cleanup-audit", "v470 Shadow Audit", "v470.0 Self-Maintenance Duplicate Shadow Cleanup v1: audits duplicate shadow removal, compatibility preservation, stale gate cleanup, docs, and no-authorization boundaries.", "Development"),
        ("/current-state-header-block", "v471 Docs Head", "v471.0 Current-State Header Block v1: keeps current version, verification, blockers, next arc, and safety boundary at the top of README_NEXT_STEPS.md.", "Development"),
        ("/historical-next-steps-separation", "v472 History Split", "v472.0 Historical Next-Steps Separation v1: separates completed and superseded next-step notes from the active plan.", "Development"),
        ("/operator-continuity-handoff-packet", "v473 Handoff", "v473.0 Operator Continuity Handoff Packet v1: provides a reusable new-chat continuation packet without becoming an execution packet.", "Development"),
        ("/documentation-boundary-language", "v474 Doc Boundary", "v474.0 Documentation Boundary Language v1: states README, release history, smoke, and handoff packets are not authorization.", "Development"),
        ("/documentation-continuity-header-audit", "v475 Doc Audit", "v475.0 README Current-State and Operator Continuity Header Cleanup v1: audits docs, handoff, history separation, and no-authorization boundaries.", "Development"),
        ("/manual-read-only-observation-scope", "v476 Observe Scope", "v476.0 Manual Read-Only Observation Scope v1: defines operator-invoked observation scope without source, memory, schedule, model, or follow-up authority.", "Development"),
        ("/operator-observation-packet", "v477 Observe Packet", "v477.0 Operator Observation Packet Builder v1: summarizes current version, milestone, metadata, routes, surfaces, docs, blockers, and review targets in review-only mode.", "Development"),
        ("/no-mutation-observation-audit", "v478 No Mutation", "v478.0 No-Mutation Observation Audit v1: confirms observation does not write source, memory, metadata, schedules, models, patches, releases, approvals, or continuation state.", "Development"),
        ("/operator-invocation-boundary", "v479 Invoke Boundary", "v479.0 Operator Invocation Boundary v1: states operator invocation permits one read-only observation report only and does not authorize monitoring, follow-up action, or live changes.", "Development"),
        ("/operator-read-only-observation-audit", "v480 Observe Audit", "v480.0 Operator-Invoked Read-Only Observation Prep v1: audits manual observation scope, packet builder, no-mutation behavior, invocation boundaries, and no-authorization status.", "Development"),
        ("/observation-ledger-schema", "v481 Ledger Schema", "v481.0 Observation Ledger Schema v1: defines review-only observation ledger fields without treating ledger presence or completeness as approval.", "Development"),
        ("/observation-receipt-builder", "v482 Receipt", "v482.0 Observation Receipt Builder v1: records observed scope, no mutation, no scheduling, no model invocation, and authorization_status=not_authorized.", "Development"),
        ("/observation-stop-pause-semantics", "v483 Stop/Pause", "v483.0 Observation Stop/Pause Semantics v1: defines pause, stop, resume, and receipt preservation before recurring observation exists.", "Development"),
        ("/hidden-scheduling-continuation-audit", "v484 Hidden Sched", "v484.0 Hidden Scheduling and Continuation Audit v1: blocks self-scheduling, loops, automatic continuation, roadmap selection, and finding promotion.", "Development"),
        ("/observation-ledger-boundary-audit", "v485 Ledger Audit", "v485.0 Bounded Observation Ledger and Stop/Pause Semantics v1: audits ledger schema, receipts, stop/pause semantics, hidden scheduling boundaries, and no-authorization status.", "Development"),
        ("/observation-to-proposal-candidate-mapper", "v486 Proposal Map", "v486.0 Observation-to-Proposal Candidate Mapper v1: maps manual observation findings into review-only proposal candidates without approval or execution packets.", "Development"),
        ("/proposal-queue-schema", "v487 Queue Schema", "v487.0 Proposal Queue Schema v1: defines supervised proposal queue records and statuses with no live-execution approval status.", "Development"),
        ("/proposal-ranking-risk-notes", "v488 Queue Rank", "v488.0 Proposal Ranking and Risk Notes v1: ranks proposal candidates for operator attention only, not automatic selection.", "Development"),
        ("/proposal-queue-non-execution-audit", "v489 Queue No-Exec", "v489.0 Proposal Queue Non-Execution Audit v1: proves no source writes, memory writes, schedules, models, execution packets, patch application, approval, or continuation.", "Development"),
        ("/observation-proposal-queue-audit", "v490 Queue Audit", "v490.0 Supervised Proposal Queue from Observation Reports v1: audits mapper, queue schema, ranking notes, non-execution behavior, and no-authorization boundaries.", "Development"),
        ("/sandbox-only-autonomy-scope-definition", "v491 Sandbox Scope", "v491.0 Sandbox-Only Autonomy Scope Definition v1: defines prep-only sandbox scope without authorizing execution.", "Development"),
        ("/sandbox-autonomy-trial-packet-builder", "v492 Sandbox Packet", "v492.0 Sandbox Autonomy Trial Packet Builder v1: builds a hypothetical review-only sandbox packet with not_authorized/not_executed status.", "Development"),
        ("/sandbox-to-live-boundary-hardening", "v493 Live Boundary", "v493.0 Sandbox-to-Live Boundary Hardening v1: blocks sandbox success, verification, output, or completion from becoming live authorization.", "Development"),
        ("/no-execution-sandbox-autonomy-audit", "v494 Sandbox No-Exec", "v494.0 No-Execution Sandbox Autonomy Audit v1: proves sandbox boundary prep executes nothing and mutates nothing.", "Development"),
        ("/sandbox-autonomy-boundary-prep-audit", "v495 Sandbox Boundary", "v495.0 Sandbox-Only Autonomy Boundary Trial Prep v1: audits sandbox boundary prep and no-authorization boundaries.", "Development"),
        ("/autonomy-readiness-criteria-board", "v496 Ready Criteria", "v496.0 Autonomy Readiness Criteria Board v1: defines readiness criteria while reporting not_ready_for_autonomy and not_authorized status.", "Development"),
        ("/autonomy-blocker-gap-register", "v497 Ready Gaps", "v497.0 Autonomy Blocker and Gap Register v1: lists missing gates and unproven assumptions without authorizing expansion.", "Development"),
        ("/phase-based-autonomy-permission-model", "v498 Phase Model", "v498.0 Phase-Based Autonomy Permission Model v1: defines autonomy phases without authorizing any phase.", "Development"),
        ("/autonomy-misinterpretation-firewall", "v499 Auto Firewall", "v499.0 Autonomy Misinterpretation Firewall v1: blocks ready-means-approved and phase-defined-means-authorized confusion.", "Development"),
        ("/autonomy-readiness-review-board-audit", "v500 Ready Board", "v500.0 Operator-Governed Autonomy Readiness Review Board v1: audits readiness criteria, blockers, phase model, misinterpretation firewall, and no-authorization boundaries.", "Development"),
        ("/source-package-runtime-exclusion-map", "v501 Package Map", "v501.0 Source Package Runtime Exclusion Map v1: aligns source-only package privacy with source surface runtime directories and forbids workspace timeline leakage.", "Development"),
        ("/final-archive-entry-privacy-checker", "v502 Archive Check", "v502.0 Final Archive Entry Privacy Checker v1: checks final archive entries and source tree entries for forbidden runtime/private paths.", "Development"),
        ("/metadata-version-drift-normalizer", "v503 Metadata Drift", "v503.0 Metadata Version Drift Normalizer v1: audits current metadata, release-note versions, and observation current-state tags.", "Development"),
        ("/release-doc-command-compatibility-audit", "v504 Command Audit", "v504.0 Release Doc Command Compatibility Audit v1: removes unsupported smoke command drift and documents supported verification syntax.", "Development"),
        ("/source-package-privacy-metadata-integrity-audit", "v505 Package Audit", "v505.0 Source-Only Package Privacy and Metadata Integrity Repair v1: audits package privacy, metadata cleanup, docs command compatibility, and no-authorization boundaries.", "Development"),
        ("/observation-to-sandbox-intake-bridge", "v506 Obs→Sandbox", "v506.0 Observation Report Intake Bridge v1: accepts read-only observation reports as review-only material without approval or execution permission.", "Development"),
        ("/sandbox-candidate-extraction", "v507 Candidates", "v507.0 Sandbox Candidate Extraction v1: extracts sandbox candidates without selecting work or authorizing execution.", "Development"),
        ("/sandbox-packet-draft-assembly", "v508 Packet Draft", "v508.0 Sandbox Packet Draft Assembly v1: assembles inert sandbox packet drafts with not_authorized/not_executed status.", "Development"),
        ("/sandbox-packet-misinterpretation-firewall", "v509 Packet Firewall", "v509.0 Sandbox Packet Misinterpretation Firewall v1: blocks packet readiness, ranking, smoke success, or discussion from becoming authorization.", "Development"),
        ("/manual-observation-to-sandbox-bridge-audit", "v510 Bridge Audit", "v510.0 Manual Observation-to-Sandbox Packet Bridge v1: audits the observation-to-sandbox bridge without execution or autonomy.", "Development"),
        ("/sandbox-approval-scope-contract", "v511 Approval Scope", "v511.0 Sandbox Approval Scope Contract v1: defines future single-use approval scope while granting no approval.", "Development"),
        ("/exact-confirmation-phrase-builder", "v512 Phrase", "v512.0 Exact Confirmation Phrase Builder v1: builds an exact future confirmation phrase template without entering confirmation.", "Development"),
        ("/approval-burnout-expiry-ledger", "v513 Burnout", "v513.0 Approval Burnout and Expiry Ledger v1: models expiry and one-time burnout without creating approval.", "Development"),
        ("/sandbox-command-allowlist-preview", "v514 Allowlist", "v514.0 Sandbox Command Allowlist Preview v1: previews commands and sandbox write targets without execution.", "Development"),
        ("/sandbox-execution-approval-gate-audit", "v515 Gate Audit", "v515.0 Sandbox Execution Approval Gate v1: audits the approval gate while reporting not_granted/not_executed/not_started.", "Development"),
        ("/sandbox-dry-run-execution-model", "v516 Dry Model", "v516.0 Sandbox Dry-Run Execution Model v1: models future sandbox execution shape without running commands.", "Development"),
        ("/command-transcript-preview", "v517 Transcript", "v517.0 Command Transcript Preview v1: previews command sequence, read paths, sandbox-only write paths, and stop conditions without output.", "Development"),
        ("/sandbox-diff-receipt-preview", "v518 Diff Receipt", "v518.0 Sandbox Diff Receipt Preview v1: previews before/after references and unchanged live files without mutation.", "Development"),
        ("/dry-run-misinterpretation-firewall", "v519 Dry Firewall", "v519.0 Dry-Run Misinterpretation Firewall v1: blocks dry-run pass, previews, and receipt language from becoming approval or execution permission.", "Development"),
        ("/sandbox-execution-dry-run-receipt-audit", "v520 Dry Audit", "v525.0 First Operator-Approved Sandbox Execution Trial v1: audits dry-run model, transcript preview, diff receipt preview, firewall, and no-execution boundaries.", "Development"),
        ("/sandbox-workspace-isolation-contract", "v521 Sandbox ISO", "v521.0 Sandbox Workspace Isolation Contract v1: defines temporary sandbox roots, allowed read paths, sandbox-only write paths, forbidden live/memory/runtime paths, and cleanup expectations without execution permission.", "Development"),
        ("/approved-sandbox-command-plan", "v522 Cmd Plan", "v522.0 Approved Sandbox Command Plan v1: defines boring compile/smoke command plans without running commands.", "Development"),
        ("/single-use-sandbox-execution-receipt", "v523 Receipt", "v523.0 Single-Use Sandbox Execution Receipt v1: defines one-trial receipt shape without creating approval or future permission.", "Development"),
        ("/sandbox-execution-misinterpretation-firewall", "v524 Exec Firewall", "v524.0 Sandbox Execution Misinterpretation Firewall v1: blocks sandbox success, cleanup, or one-command approval from becoming live/memory/release/future/autonomy authority.", "Development"),
        ("/first-sandbox-execution-trial-audit", "v525 Trial Audit", "v525.0 First Operator-Approved Sandbox Execution Trial v1: audits the first sandbox execution trial layer with not-run-by-default status and no live/memory/autonomy authority.", "Development"),
        ("/sandbox-execution-runner-contract", "v526 Runner", "v526.0 Sandbox Execution Runner Contract v1: defines one sandbox-only runner contract under exact approval without granting execution permission.", "Development"),
        ("/approval-phrase-validator", "v527 Phrase Check", "v527.0 Approval Phrase Validator v1: validates exact future operator approval phrase while proving validation is not command execution.", "Development"),
        ("/sandbox-command-execution-harness", "v528 Harness", "v528.0 Sandbox Command Execution Harness v1: defines narrow sandbox-only command harness boundaries without running commands by default.", "Development"),
        ("/execution-receipt-intake-cleanup-audit", "v529 Receipt Intake", "v529.0 Execution Receipt Intake and Cleanup Audit v1: captures receipt and cleanup shape without future authorization.", "Development"),
        ("/sandbox-execution-trial-review-board", "v530 Runner Board", "v530.0 Operator-Approved Sandbox Execution Runner and Receipt Intake v1: audits runner contract, approval phrase, harness, receipt intake, cleanup, and no-live/no-memory/no-autonomy boundaries.", "Development"),
        ("/sandbox-evidence-intake-packet", "v531 Evidence", "v531.0 Sandbox Evidence Intake Packet v1: intakes sandbox execution receipt evidence without live-source approval.", "Development"),
        ("/promotion-candidate-diff-preview", "v532 Diff Preview", "v532.0 Promotion Candidate Diff Preview v1: previews proposed live-source diffs without mutating live source.", "Development"),
        ("/rollback-recovery-packet-builder", "v533 Rollback", "v533.0 Rollback and Recovery Packet Builder v1: plans rollback/recovery without executing rollback.", "Development"),
        ("/promotion-misinterpretation-firewall", "v534 Promo Firewall", "v534.0 Promotion Misinterpretation Firewall v1: blocks sandbox success, promotion packets, rollback packets, smoke pass, or operator interest from becoming authorization.", "Development"),
        ("/sandbox-to-source-promotion-review-board", "v535 Promo Board", "v540.0 Operator-Approved Narrow Live Patch Promotion Gate v1: audits evidence intake, diff preview, rollback packet, promotion firewall, and no-live/no-memory/no-release/no-autonomy boundaries.", "Development"),
        ("/narrow-live-patch-scope-contract", "v536 Live Scope", "v536.0 Narrow Live Patch Scope Contract v1: defines boring live patch classes and forbidden memory/identity/personality/scheduler/model/autonomy/release/broad-refactor classes without approval.", "Development"),
        ("/promotion-approval-phrase-contract", "v537 Live Phrase", "v537.0 Promotion Approval Phrase Contract v1: defines packet-scoped single-use live patch approval phrase template without treating it as approval.", "Development"),
        ("/live-patch-preflight-checklist", "v538 Preflight", "v538.0 Live Patch Preflight Checklist v1: checks privacy, targets, rollback, smoke, README/release history, and forbidden changes without permission.", "Development"),
        ("/live-promotion-misinterpretation-firewall", "v539 Live Firewall", "v539.0 Live Promotion Misinterpretation Firewall v1: blocks sandbox success, promotion packet, preflight pass, prior approval, phrase template, and patch success from becoming authorization.", "Development"),
        ("/narrow-live-patch-promotion-gate-audit", "v540 Live Gate", "v540.0 Operator-Approved Narrow Live Patch Promotion Gate v1: audits the live patch gate while reporting not_applied, not_authorized, source untouched, memory untouched, and autonomy not expanded.", "Development"),
        ("/live-patch-trial-candidate-selector", "v541 Candidate", "v541.0 Live Patch Trial Candidate Selector v1: selects first-trial candidate classes without approving a live patch.", "Development"),
        ("/single-use-live-patch-approval-receipt", "v542 Receipt", "v542.0 Single-Use Live Patch Approval Receipt v1: defines an approval receipt template while reporting approval not granted.", "Development"),
        ("/live-patch-application-harness-preview", "v543 Harness", "v543.0 Live Patch Application Harness Preview v1: previews narrow live patch application structure without applying a patch.", "Development"),
        ("/live-patch-application-misinterpretation-firewall", "v544 Patch Firewall", "v544.0 Live Patch Application Misinterpretation Firewall v1: blocks selection, receipt, preflight, sandbox success, patch success, release, and autonomy confusion.", "Development"),
        ("/first-narrow-live-patch-trial-audit", "v545 Patch Trial", "v545.0 First Single-Use Narrow Live Patch Application Trial v1: audits the first live patch trial layer while reporting not_applied_by_default, not_authorized, memory untouched, release not created, and autonomy not expanded.", "Development"),
        ("/intelligence", "Intelligence", "Project indexing and codebase intelligence summaries.", "Development"),
        ("/workspace", "Workspace", "Workspace registry, project context, command profiles, and dependency maps.", "Development"),
        ("/patch-drafts", "Patch Drafts", "v73 supervised patch draft composer: intent normalization, scope contracts, prompt composition, output schema, safety review, evidence binding, and local-model handoff stubs. Draft only; no apply or model invocation.", "Development"),
        ("/code-patches", "Code Patches", "Code patch proposal and patch bridge surfaces.", "Development"),
        ("/release-review", "Release Review", "Release review summaries before packaging or publish decisions.", "Release"),
        ("/release-package", "Release Package", "Lightweight release package controls and source-only packaging information.", "Release"),
        ("/release-governance", "Release Governance", "Governance gates, package integrity, and candidate safety checks.", "Release"),
        ("/release-evidence", "Release Evidence", "Release evidence ledger, provenance, and reproducibility surfaces.", "Release"),
        ("/release-signing", "Release Signing", "Detached-signature readiness and trust-root reporting. No private key handling.", "Release"),
        ("/release-operations", "Release Ops", "Operations console for package, trust, candidate, and safety workflows.", "Release"),
        ("/release-operator", "Release Operator", "Operator workflow summary for release decisions.", "Release"),
        ("/release-candidate", "Release Candidate", "Candidate review and package state without publish approval leakage.", "Release"),
        ("/release-approval", "Release Approval", "Publish approval state and revocation previews, separate from live apply.", "Release"),
        ("/autonomy", "Autonomy Boundary", "Compact autonomy boundary overview and links into detailed autonomy/maintenance systems.", "Autonomy"),
        ("/maintenance-queue", "Maintenance Queue", "v46 self-maintenance queue summary, selected task, scoring, checkpoint binding, and safe CLI/API links.", "Autonomy"),
        ("/attention", "Attention", "v47 attention scheduler: budgets, focus selection, receipts, reason codes, deferrals, stale resurfacing, and safe next actions.", "Autonomy"),
        ("/reflection", "Reflection", "v48.x reflection review: receipts, dedup, rejection policy, promotion drafts, safety labels, and memory-review boundaries.", "Autonomy"),
        ("/identity", "Identity", "v49 identity continuity and identity receipts: draft self-description, stable principles, drift explanations, and review-only identity evolution.", "Autonomy"),
        ("/memory", "Memory", "v50-v51 durable-memory promotion, guarded write path, receipts, store schema, read/search, correction/removal drafts, and write audit previews.", "Autonomy"),
        ("/recall", "Recall", "v52 recall stabilization: receipts, evidence, conflict/stale handling, scope controls, privacy checks, and read-only retrieval.", "Autonomy"),
        ("/planning", "Planning", "v53 memory-informed planning: selected memory evidence, ignored-memory explanations, warnings, receipts, conflicts, revisions, scope, and risk budgets.", "Autonomy"),
        ("/action-plans", "Action Plans", "v54 supervised action planning: evidence-bound action steps, blocked destructive labels, and no automatic execution.", "Autonomy"),
        ("/execution-preview", "Execution Preview", "v55 controlled execution preview: validates one action plan, rehearses readiness, and grants no real operation approval.", "Autonomy"),
        ("/read-only-execution", "Read-Only Execution", "v56 controlled read-only execution: runs only allowlisted diagnostics after exact confirmation and grants no mutation approval.", "Autonomy"),
        ("/evidence-gathering", "Evidence Gathering", "v57 evidence-gathering maintenance loop: binds read-only diagnostics into supervised maintenance planning evidence without mutation.", "Autonomy"),
        ("/patch-proposals", "Patch Proposals", "v58 evidence-grounded sandbox patch proposals: issue-to-patch rationale, evidence binding, risk scoring, and no source apply.", "Autonomy"),
        ("/sandbox-patch-execution", "Sandbox Patch Execution", "v59 controlled sandbox-only patch execution: reviewed proposal binding, temp sandbox rehearsal, verification receipt, and no live source apply.", "Autonomy"),
        ("/source-apply-handoff", "Source Apply Handoff", "v61 controlled source-apply bridge: receipts, drift resolver, artifact binder, eligibility, dry-run bridge, no live source mutation.", "Autonomy"),
        ("/source-apply-transactions", "Source Apply Transactions", "v62 supervised source-apply transaction layer: plan, backup, dry-run, exact confirmation, executor review, verification, and rollback rehearsal.", "Autonomy"),
        ("/transaction-evidence", "Transaction Evidence", "v63 durable transaction evidence: ledger, diffs, conflicts, approval records, safe exports, replay audit, dashboard timeline, and API search.", "Autonomy"),
        ("/improvement-intelligence", "Improvement Intelligence", "v64 supervised improvement intelligence: evidence summaries, candidate registry, scoring, regression patterns, risk forecast, and recommendation queue.", "Autonomy"),
        ("/proposal-drafting", "Proposal Drafting", "v65 recommendation-to-proposal drafting: accepted recommendation intake, proposal skeletons, evidence requirements, risk contracts, sandbox requests, and review packets.", "Autonomy"),
        ("/proposal-sandbox", "Proposal Sandbox", "v66 reviewed proposal sandbox execution: acceptance gate, workspace plan, implementation request, harness, verification, evidence binder, and failure triage.", "Autonomy"),
        ("/sandbox-promotion", "Sandbox Promotion", "v67 sandbox evidence promotion: candidate builder, source diff normalizer, safety gate, transaction draft, review packet, conflict detector, and transaction-handoff readiness.", "Autonomy"),
        ("/source-transaction-review", "Source Transaction Review", "v68 promotion-to-transaction integration: promotion intake, materialized transaction plan, baseline reconciliation, backup/rollback preflight, safety gate, and ledger pre-registration.", "Autonomy"),
        ("/transaction-execution", "Transaction Execution", "v69 operator-confirmed transaction execution: eligibility, exact confirmation, backup snapshot, rehearsal, guarded executor, verification, and rollback recommendation.", "Autonomy"),
        ("/release-finalization", "Release Finalization", "v70 verified execution recovery: execution ledger finalization, rollback decision/executor, post-rollback verification, release candidate gate, package certifier, and recovery simulation.", "Autonomy"),
        ("/codebase-map", "Codebase Map", "v71 codebase understanding: source inventory, responsibilities, dependency/call surface, risks, historical failures, verification mapping, and opportunities.", "Autonomy"),
        ("/patch-context", "Patch Context", "v72 patch generation context builder: goal intake, relevant files, historical failures, risk budgets, verification requirements, context packets, and review gates. Context only; no patch generation or apply.", "Autonomy"),
        ("/approvals", "Approvals <span class='nav-badge warn-badge' data-live-count='counts.pending_approvals'></span>", "Human approval records waiting for review. Browsing does not approve them.", "Autonomy"),
        ("/notifications", "Notifications <span class='nav-badge warn-badge' data-live-count='counts.unread_notifications'></span>", "Unread and archived notification records from watch and operator systems.", "Autonomy"),
        ("/watch", "Watch <span class='nav-badge' data-live-count='counts.watch_reports'></span>", "Watch-mode reports and monitoring snapshots.", "Autonomy"),
        ("/patches", "Patches <span class='nav-badge' data-live-count='counts.patches'></span>", "Patch proposal records, applied state, rollback metadata, and review traces.", "Autonomy"),
        ("/goals", "Goals <span class='nav-badge' data-live-count='counts.goals'></span>", "Goal records and goal-management state for continuity.", "Autonomy"),
        ("/neural-deck-layout-shell", "v686 Neural Deck", "v686.0 Neural Deck Layout Shell: clean three-column neural command deck UI shell. Visual state only; not authorization.", "System"),
        ("/eidolon-thinking-core-panel", "v687 Thinking Core", "v687.0 Eidolon Thinking Core Panel: red thinking waveform/core visualization. Does not execute models or mutate memory.", "System"),
        ("/operator-conversation-console", "v688 Conversation", "v688.0 Operator Conversation Console: clean central chat and input deck. Does not send commands or create approvals.", "System"),
        ("/side-intelligence-panels", "v689 Side Panels", "v689.0 Side Intelligence Panels: vitals, approval, risk, roadmap, telemetry. Metrics are not authorization.", "System"),
        ("/neural-command-deck-dashboard-board", "v690 Neural Board", "v690.0 Neural Command Deck Dashboard Board: final review-only UI redesign board preserving data-tip and no native title tooltips.", "System"),
        ("/interaction-focus-rail", "v691 Focus Rail", "v691.0 Interaction Focus Rail: guided focus rail for conversation/evidence/approval/verification/handoff. Does not start work.", "System"),
        ("/interaction-safe-input-deck", "v692 Input Deck", "v692.0 Interaction-Safe Input Deck: mode chips and cleaner input affordances. Does not execute commands or create approvals.", "System"),
        ("/panel-density-priority-tuning", "v693 Panel Tuning", "v693.0 Panel Density and Priority Tuning: cleaner panel priority and density without hiding blockers or granting authorization.", "System"),
        ("/context-telemetry-affordance", "v694 Context/Telemetry", "v694.0 Context and Telemetry Affordance: custom data-tip details without native title tooltips, checks, memory mutation, or approval.", "System"),
        ("/neural-command-deck-interaction-board", "v695 Interaction Board", "v695.0 Neural Command Deck Interaction Board: final review-only interaction refinement board preserving boundaries.", "System"),
        ("/autonomy-phase-zero-definition-contract", "v696 Phase 0", "v696.0 Autonomy Phase 0 Definition Contract: observation-only readiness definition. Not autonomy approval.", "System"),
        ("/observation-only-cycle-simulator", "v697 Observer", "v697.0 Observation-Only Cycle Simulator: simulated inspect/summarize/classify/receipt cycle without action.", "System"),
        ("/no-mutation-autonomy-boundary-guard", "v698 No Mutation", "v698.0 No-Mutation Autonomy Boundary Guard: proves no source, memory, archive, release, command, model, scheduling, or continuation authority.", "System"),
        ("/autonomy-phase-zero-handoff-packet", "v699 P0 Handoff", "v699.0 Autonomy Phase 0 Handoff Packet: handoff context only, not permission to continue.", "System"),
        ("/autonomy-phase-zero-readiness-board", "v700 P0 Board", "v700.0 Autonomy Phase 0 Readiness Board: final review-only readiness harness. Not autonomous.", "System"),
        *dashboard_route_registry_nav_items(),
        ("/api-info", "API", "Local API route reference and safety boundary notes.", "System"),
        ("/desktop", "Desktop", "Desktop companion setup and local shell information.", "System"),
        ("/setup", "Setup <span class='nav-badge' data-live-count='counts.setup_reports'></span>", "Setup helper reports and local environment checks.", "System"),
        ("/onboarding", "Onboarding <span class='nav-badge' data-live-count='counts.onboarding_runs'></span>", "Project onboarding runs and first-use setup guidance.", "System"),
        ("/activity", "Activity", "Recent task, maintenance, diagnostic, notification, and watch activity.", "System"),
    ]
    nav = _render_nav(path, nav_items)
    msg = f"<div class='notice ok'>{_safe(DashboardState.message)}</div>" if DashboardState.message else ""
    err = f"<div class='notice bad'>{_safe(DashboardState.error)}</div>" if DashboardState.error else ""
    DashboardState.message = ""
    DashboardState.error = ""

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{DASHBOARD_TITLE}</title>
<style>
:root {{ --bg:#101217; --panel:#171b23; --panel2:#202634; --text:#eef1f7; --muted:#9aa5b5; --accent:#8fb3ff; --good:#77d192; --bad:#ff8f8f; --warn:#ffd27d; --border:#30384a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Segoe UI, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }}
.sr-only {{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }}
.skip-link {{ position:fixed; left:12px; top:-80px; z-index:100; padding:10px 14px; background:#fff; color:#111; border-radius:4px; }}
.skip-link:focus {{ top:12px; }}
body > header {{ padding:18px 24px; border-bottom:1px solid var(--border); background:#0d0f14; position:sticky; top:0; z-index:2; }}
h1 {{ margin:0 0 4px 0; font-size:22px; }}
.subtitle {{ color:var(--muted); font-size:13px; }}
nav.nav-shell {{ display:grid; grid-template-columns:1fr; gap:10px; padding:12px 24px; border-bottom:1px solid var(--border); background:#11151d; }}
.nav-mobile-toggle {{ display:none; min-height:44px; width:100%; align-items:center; justify-content:space-between; }}
.nav-content {{ display:grid; gap:12px; min-width:0; }}
.nav-intro {{ display:flex; flex-wrap:wrap; gap:8px 12px; align-items:baseline; color:var(--muted); font-size:12px; }}
.nav-intro strong {{ color:var(--text); font-size:13px; }}
.nav-section {{ border:1px solid var(--border); border-radius:14px; background:#0f141d; }}
.nav-section summary {{ cursor:pointer; list-style:none; display:flex; flex-wrap:wrap; gap:8px 12px; align-items:baseline; padding:9px 12px; color:var(--text); }}
.nav-section summary::-webkit-details-marker {{ display:none; }}
.nav-section summary::before {{ content:'▸'; color:var(--muted); }}
.nav-section[open] summary::before {{ content:'▾'; color:var(--accent); }}
.nav-section summary small {{ color:var(--muted); font-size:12px; }}
.nav-links {{ display:flex; flex-wrap:wrap; gap:8px; padding:0 12px 12px 12px; }}
.command-palette {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; padding:9px 12px; border:1px solid var(--border); border-radius:14px; background:#0f141d; }}
.command-palette label {{ color:var(--muted); font-size:12px; }}
.command-palette input {{ min-width:min(420px, 100%); flex:1; }}
.nav-section.nav-hidden, nav a.nav-link.nav-hidden {{ display:none; }}
nav a.nav-link {{ color:var(--text); text-decoration:none; padding:8px 10px; border:1px solid var(--border); border-radius:10px; background:var(--panel); position:relative; }}
nav a.nav-link.active {{ border-color:var(--accent); color:#fff; box-shadow:0 0 0 1px var(--accent) inset; }}
nav a.nav-link:hover, nav a.nav-link:focus {{ border-color:var(--accent); outline:none; }}
nav a.nav-link[data-tip]:hover::after, nav a.nav-link[data-tip]:focus::after, .mini-card[data-tip]:hover::after, .mini-card[data-tip]:focus::after {{ content:attr(data-tip); position:absolute; left:0; top:calc(100% + 7px); z-index:20; width:min(320px, 72vw); padding:9px 10px; border:1px solid var(--border); border-radius:10px; background:#080a0f; color:var(--text); box-shadow:0 8px 22px rgba(0,0,0,.35); font-size:12px; line-height:1.35; }}
a {{ color:var(--accent); }} a:hover {{ color:#dbe7ff; }}
main {{ max-width:1200px; margin:0 auto; padding:22px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; }}
.card {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; margin-bottom:16px; }}
.mini-card {{ position:relative; background:#10151e; border:1px solid var(--border); border-radius:14px; padding:12px; min-height:82px; }}
.mini-card:focus {{ outline:1px solid var(--accent); }}
.card h2 {{ margin:0 0 12px; font-size:18px; }}
.card h3 {{ margin:14px 0 8px; font-size:15px; color:var(--accent); }}
.kpi {{ font-size:30px; font-weight:700; }}
.muted {{ color:var(--muted); }}
.good {{ color:var(--accent-red); }} .badtext {{ color:var(--bad); }} .warn {{ color:var(--warn); }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#0b0d12; border:1px solid var(--border); border-radius:12px; padding:12px; max-height:520px; overflow:auto; }}
button, input, select {{ background:var(--panel2); color:var(--text); border:1px solid var(--border); border-radius:10px; padding:8px 10px; }}
button {{ cursor:pointer; }} button:hover {{ border-color:var(--accent); }}
button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible, a:focus-visible, summary:focus-visible {{ outline:3px solid var(--warn); outline-offset:2px; }}
form.inline {{ display:inline-block; margin:2px 4px 2px 0; }}
form.stack {{ display:grid; gap:8px; max-width:760px; }}
.local-model-descriptions {{ margin:0 0 8px; border:1px solid var(--border); border-radius:8px; padding:8px 10px; background:var(--panel2); }}
.local-model-descriptions > summary {{ cursor:pointer; font-weight:700; color:var(--muted); }}
.local-model-descriptions > div {{ display:grid; grid-template-columns:minmax(140px,auto) 1fr; gap:10px; align-items:start; padding:7px 0; border-top:1px solid var(--border); }}
.local-model-descriptions > div:first-of-type {{ margin-top:7px; }}
.local-model-descriptions code {{ overflow-wrap:anywhere; }}
.local-model-descriptions span {{ color:var(--muted); }}
textarea {{ width:100%; background:var(--panel2); color:var(--text); border:1px solid var(--border); border-radius:10px; padding:10px; font-family:inherit; }}
.action-card {{ border:1px solid var(--border); border-radius:14px; padding:12px; background:#121720; }}
.notice {{ padding:12px 14px; border-radius:12px; margin-bottom:14px; border:1px solid var(--border); }}
.notice.ok {{ background:#122619; color:#d7ffe0; }} .notice.bad {{ background:#2b1515; color:#ffdada; }}
table {{ width:100%; border-collapse:collapse; }} th,td {{ border-bottom:1px solid var(--border); padding:8px; vertical-align:top; text-align:left; }} th {{ color:var(--muted); font-weight:600; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid var(--border); color:var(--muted); font-size:12px; }}
.stage-pill {{ display:inline-block; padding:4px 10px; border-radius:999px; border:1px solid var(--border); font-size:12px; font-weight:600; background:#151b26; color:var(--muted); }}
.stage-ready {{ color:var(--good); border-color:#315f43; background:#102016; }}
.stage-active {{ color:#dbe7ff; border-color:#365c9b; background:#111d35; }}
.stage-approval-required, .stage-approval-pending, .stage-approved-ready {{ color:var(--warn); border-color:#6a4c18; background:#23190b; }}
.stage-approval-rejected, .stage-approval-failed, .stage-recovery-needed, .stage-blocked {{ color:var(--bad); border-color:#6d3030; background:#261111; }}
.stage-patch-proposed {{ color:#cdb7ff; border-color:#514277; background:#1c1730; }}
.stage-done {{ color:var(--good); border-color:#315f43; background:#102016; }}
.stage-cancelled, .stage-unknown {{ color:var(--muted); }}
.review-archived {{ opacity:0.62; }}
.lifecycle-strip {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:10px 0; }}
.lifecycle-step {{ padding:8px 10px; border:1px solid var(--border); border-radius:12px; background:#10151e; color:var(--muted); font-size:12px; }}
.lifecycle-step.current {{ border-color:var(--accent); color:#fff; box-shadow:0 0 0 1px var(--accent) inset; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:10px 0; }}
	.filter-chip {{ display:inline-block; padding:7px 10px; border:1px solid var(--border); border-radius:999px; background:#111722; color:var(--text); text-decoration:none; font-size:12px; }}
	.filter-chip.active {{ border-color:var(--accent); box-shadow:0 0 0 1px var(--accent) inset; }}
.footer {{ color:var(--muted); font-size:12px; margin-top:30px; }}
.nav-badge {{ display:inline-block; min-width:20px; margin-left:5px; padding:1px 6px; border-radius:999px; background:#253047; color:#dbe7ff; font-size:11px; text-align:center; }}
.nav-badge:empty {{ display:none; }}
.warn-badge:not(:empty) {{ background:#4a3215; color:#ffd27d; }}
.livebar {{ display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px; padding:10px 12px; border:1px solid var(--border); border-radius:12px; background:#0f141d; color:var(--muted); }}
.live-dot {{ color:var(--muted); }} .live-dot.ok {{ color:var(--good); }} .live-dot.bad {{ color:var(--bad); }} .live-dot.polling {{ color:var(--warn); }}

/* v135 command-deck operator console skin. Preserves custom data-tip hover behavior; no native title tooltips. */
:root {{ --bg:#050b14; --panel:#081525; --panel2:#0b2035; --text:#e7f2ff; --muted:#8da0ba; --accent:#ff332b; --good:#49d86f; --bad:#ff332b; --warn:#ff9f35; --border:#4b1716; --cyan:#ff5b55; --accent-red:#ff332b; --deep-red:#140303; }}
body {{ min-height:100vh; background:radial-gradient(circle at 14% 8%, rgba(255,45,35,.22), transparent 25%), radial-gradient(circle at 78% 4%, rgba(255,70,55,.12), transparent 26%), linear-gradient(180deg,#070707 0%, #030303 100%); color:var(--text); }}
body > header {{ position:fixed; top:0; left:260px; right:0; height:62px; padding:10px 26px; border-bottom:1px solid rgba(255,54,45,.28); background:rgba(7,5,5,.94); backdrop-filter:blur(12px); display:flex; align-items:center; gap:26px; box-shadow:0 0 22px rgba(28,168,255,.12); }}
body > header h1 {{ font-size:13px; letter-spacing:.22em; text-transform:uppercase; color:var(--good); margin:0; }}
body > header .subtitle {{ color:var(--muted); font-size:12px; }}
body > header .subtitle::after {{ content:'  |  ENVIRONMENT: LOCAL SUPERVISED  |  CORE v{DASHBOARD_VERSION}  |  OPERATOR-GOVERNED'; color:#ff5b55; margin-left:12px; }}
body > nav {{ position:fixed; top:0; left:0; bottom:0; width:260px; overflow-y:auto; overflow-x:hidden; border-right:1px solid rgba(255,54,45,.24); background:linear-gradient(180deg,rgba(10,6,6,.98),rgba(3,3,4,.98)); box-shadow:14px 0 40px rgba(0,0,0,.35); z-index:5; }}
nav.nav-shell {{ padding:118px 14px 16px; border:0; background:transparent; gap:12px; }}
nav.nav-shell::before {{ content:'◉ EIDOLON\\A OPERATOR CONSOLE'; white-space:pre; position:absolute; top:24px; left:24px; font-size:18px; line-height:1.1; font-weight:800; letter-spacing:.08em; color:#f4f4f4; text-shadow:0 0 24px rgba(255,54,45,.35); }}
.nav-intro {{ display:none; }}
.command-palette {{ background:#100707; border-color:#5d1b1a; box-shadow:inset 0 0 18px rgba(255,54,45,.08); }}
.nav-section {{ background:transparent; border:0; border-radius:0; }}
.nav-section summary {{ padding:10px 4px; border-top:1px solid rgba(255,54,45,.22); }}
.nav-section summary small {{ display:none; }}
.nav-links {{ display:grid; gap:8px; padding:0 0 12px; }}
nav a.nav-link {{ display:block; padding:10px 13px; border-color:transparent; background:transparent; color:#aa9a9a; }}
nav a.nav-link.active, nav a.nav-link:hover, nav a.nav-link:focus {{ color:#eaf7ff; border-color:#8a2521; background:linear-gradient(90deg,rgba(255,54,45,.25),rgba(255,54,45,.035)); box-shadow:inset 3px 0 0 #ff332b, 0 0 18px rgba(255,54,45,.16); }}
nav a.nav-link[data-tip]:hover::after, nav a.nav-link[data-tip]:focus::after, .mini-card[data-tip]:hover::after, .mini-card[data-tip]:focus::after {{ left:16px; top:calc(100% + 6px); background:#090303; border-color:#8a2521; color:#ffe4e0; }}
main {{ margin-left:260px; padding:88px 26px 28px; max-width:none; }}
.livebar {{ display:none; }}
.card, .mini-card, .action-card {{ background:linear-gradient(180deg,rgba(18,8,9,.94),rgba(7,7,8,.94)); border-color:#55201d; box-shadow:inset 0 0 24px rgba(255,54,45,.055), 0 0 18px rgba(0,0,0,.32); }}
.card h2, .card h3 {{ text-transform:uppercase; letter-spacing:.04em; }}
button, input, select, textarea {{ background:#130808; border-color:#6b2421; color:#ffe7e4; }}
button {{ color:#ff6b61; box-shadow:inset 0 0 12px rgba(255,54,45,.10); }}
button:hover {{ border-color:#ff5b55; color:#fff2ef; box-shadow:0 0 18px rgba(255,54,45,.22); }}
.command-deck {{ display:grid; gap:16px; }}
.command-hero {{ display:flex; justify-content:space-between; gap:16px; align-items:start; }}
.command-hero h1 {{ margin:0; font-size:32px; letter-spacing:.06em; text-transform:uppercase; }}
.system-pill {{ border:1px solid #1b7ec6; border-radius:10px; padding:10px 16px; color:#79cfff; background:#06182a; font-weight:700; }}
.command-flow {{ display:grid; grid-template-columns:repeat(5,minmax(150px,1fr)); gap:14px; }}
.command-step {{ position:relative; min-height:145px; border:1px solid #1b5d91; border-radius:14px; padding:18px 16px; background:linear-gradient(180deg,rgba(9,35,61,.95),rgba(5,18,33,.95)); box-shadow:inset 0 0 20px rgba(28,168,255,.08); }}
.command-step.goodstep {{ border-color:#0b8f82; background:linear-gradient(180deg,rgba(6,65,64,.85),rgba(5,28,35,.92)); }}
.command-step.dangerstep {{ border-color:#7d2730; background:linear-gradient(180deg,rgba(60,13,21,.92),rgba(21,8,13,.94)); }}
.step-icon {{ width:48px; height:48px; border:1px solid currentColor; border-radius:50%; display:grid; place-items:center; margin-bottom:10px; font-size:24px; box-shadow:0 0 22px rgba(28,168,255,.2); }}
.command-step h3 {{ margin:0 0 6px; color:#94c9ff; }}
.command-step.dangerstep h3 {{ color:#ff646c; }}
.command-step p {{ min-height:38px; margin:0 0 12px; color:#aebcd1; font-size:13px; }}
.safety-line, .console-footer-note {{ display:flex; justify-content:space-between; gap:12px; padding:12px 16px; border:1px solid #164a76; border-radius:10px; background:rgba(4,13,24,.85); color:#aebcd1; }}
.console-grid {{ display:grid; grid-template-columns:repeat(4,minmax(220px,1fr)); gap:14px; }}
.console-card {{ min-height:178px; border:1px solid #164a76; border-radius:14px; padding:15px; background:linear-gradient(180deg,rgba(7,24,42,.94),rgba(4,14,27,.94)); }}
.console-card h2 {{ margin:0 0 12px; font-size:15px; text-transform:uppercase; }}
.audit-ring {{ width:118px; height:118px; border-radius:50%; display:grid; place-items:center; background:conic-gradient(var(--cyan) 0 78%, #14314b 78% 100%); margin:8px auto; position:relative; }}
.audit-ring::after {{ content:''; position:absolute; inset:13px; border-radius:50%; background:#081525; }}
.audit-ring span {{ position:relative; z-index:1; font-size:25px; font-weight:800; text-align:center; }}
.audit-ring small {{ display:block; font-size:11px; color:var(--good); }}
.status-list {{ display:grid; gap:6px; font-size:13px; color:#aebcd1; }}
.status-list div {{ display:flex; justify-content:space-between; gap:10px; border-bottom:1px solid rgba(52,108,151,.25); padding-bottom:5px; }}
.badge-danger {{ color:#ff646c; border-color:#7d2730; background:#2a0b12; }}
.badge-warn {{ color:#ffc44d; border-color:#6f4d18; background:#261a08; }}
.roadmap-line {{ display:grid; gap:9px; font-size:13px; }}
.roadmap-line div::before {{ content:'●'; color:#20f0e7; margin-right:8px; }}
.signal-spark {{ height:42px; border-bottom:1px solid #1b5d91; background:linear-gradient(135deg, transparent 5%, rgba(32,240,231,.12) 5% 12%, transparent 12% 20%, rgba(28,168,255,.2) 20% 32%, transparent 32%); }}
.reco-strip {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }}
.reco-chip {{ border:1px solid #164a76; border-radius:10px; padding:9px; background:#081a2e; font-size:12px; }}

/* v686-v690 neural command deck dashboard redesign. Preserves command-deck/operator-console identity, custom data-tip hover behavior, and no native title tooltips. */
.neural-deck {{ display:grid; gap:14px; color:#f4eeee; }}
.neural-topbar {{ display:grid; grid-template-columns:1.25fr repeat(3, minmax(160px,.75fr)) 1.25fr; gap:14px; align-items:stretch; }}
.neural-brand, .neural-status, .neural-footer-cell {{ border:1px solid rgba(255,54,45,.28); border-radius:16px; background:linear-gradient(180deg,rgba(16,8,9,.92),rgba(5,5,6,.92)); box-shadow:inset 0 0 28px rgba(255,54,45,.06), 0 0 26px rgba(0,0,0,.35); padding:14px 16px; }}
.neural-brand strong {{ display:block; font-size:32px; letter-spacing:.26em; font-weight:800; }}
.neural-brand span, .neural-status span, .neural-panel small {{ display:block; color:#ff5b55; text-transform:uppercase; letter-spacing:.16em; font-size:11px; }}
.neural-status b {{ display:block; margin-top:8px; color:#ff332b; text-transform:uppercase; letter-spacing:.08em; }}
.neural-layout {{ display:grid; grid-template-columns:minmax(260px, .72fr) minmax(560px, 1.85fr) minmax(300px, .86fr); gap:14px; align-items:stretch; }}
.neural-column {{ display:grid; gap:14px; align-content:start; }}
.neural-panel {{ position:relative; border:1px solid rgba(255,54,45,.24); border-radius:16px; padding:15px; background:linear-gradient(180deg,rgba(14,9,10,.95),rgba(5,5,6,.96)); box-shadow:inset 0 0 30px rgba(255,54,45,.05), 0 0 24px rgba(0,0,0,.30); overflow:hidden; }}
.neural-panel::before {{ content:''; position:absolute; inset:0; pointer-events:none; background:linear-gradient(90deg,rgba(255,54,45,.10),transparent 18%,transparent 82%,rgba(255,54,45,.08)); opacity:.45; }}
.neural-panel h2 {{ margin:0 0 12px; font-size:15px; letter-spacing:.10em; text-transform:uppercase; color:#f4eeee; }}
.neural-panel h2 span {{ color:#ff332b; margin-right:8px; }}
.neural-gauge {{ width:150px; height:150px; margin:8px auto 14px; border-radius:50%; display:grid; place-items:center; background:conic-gradient(#ff332b 0 89%, #281010 89% 100%); box-shadow:0 0 34px rgba(255,54,45,.26), inset 0 0 16px rgba(0,0,0,.4); position:relative; }}
.neural-gauge::after {{ content:''; position:absolute; inset:18px; border-radius:50%; background:#080606; border:1px solid rgba(255,54,45,.24); }}
.neural-gauge b {{ position:relative; z-index:1; font-size:34px; }} .neural-gauge small {{ position:relative; z-index:1; color:#b9aaa8; }}
.neural-list {{ display:grid; gap:8px; position:relative; z-index:1; }}
.neural-row {{ display:flex; justify-content:space-between; gap:14px; padding-bottom:7px; border-bottom:1px solid rgba(255,54,45,.13); color:#bcaead; font-size:13px; }}
.neural-row b, .neural-hot {{ color:#ff4c43; }}
.neural-wire {{ height:138px; border:1px solid rgba(255,54,45,.18); border-radius:14px; background:radial-gradient(circle at center,rgba(255,54,45,.65),transparent 7%), radial-gradient(circle at center,rgba(255,54,45,.22),transparent 34%), linear-gradient(45deg,transparent 48%,rgba(255,54,45,.22) 49%,transparent 50%); box-shadow:inset 0 0 24px rgba(255,54,45,.10); }}
.neural-approval {{ display:grid; gap:10px; }}
.neural-approval-item {{ border:1px solid rgba(255,54,45,.18); border-radius:12px; background:rgba(15,10,11,.75); padding:10px; display:grid; gap:6px; }}
.neural-approval-actions {{ display:flex; gap:8px; justify-content:flex-end; }}
.eidolon-conversation {{ min-height:720px; display:grid; grid-template-rows:auto 1fr auto auto; gap:12px; }}
.chat-bubble {{ max-width:390px; border:1px solid rgba(255,255,255,.10); border-radius:14px; background:rgba(18,19,24,.82); padding:12px 14px; color:#ddd4d3; position:relative; z-index:1; }}
.chat-meta {{ color:#8f8180; font-size:11px; letter-spacing:.12em; text-transform:uppercase; margin-bottom:6px; }}
.eidolon-thinking-core {{ position:relative; min-height:300px; border:1px solid rgba(255,54,45,.16); border-radius:18px; background:radial-gradient(circle at 36% 50%,rgba(255,54,45,.46),transparent 8%), radial-gradient(circle at 50% 50%,rgba(255,54,45,.18),transparent 22%), linear-gradient(180deg,rgba(8,7,9,.45),rgba(8,5,6,.72)); overflow:hidden; display:grid; place-items:center; }}
.eidolon-thinking-core::before {{ content:''; position:absolute; inset:0; background-image:linear-gradient(rgba(255,54,45,.09) 1px, transparent 1px), linear-gradient(90deg, rgba(255,54,45,.08) 1px, transparent 1px); background-size:42px 42px; opacity:.28; }}
.eidolon-thinking-core::after {{ content:''; position:absolute; width:180%; height:88px; left:-40%; top:38%; background:radial-gradient(circle,rgba(255,255,255,.95) 0 3px, transparent 5px), linear-gradient(100deg,transparent 0 8%,rgba(255,54,45,.05) 12%,rgba(255,54,45,.8) 18%,rgba(255,180,170,.75) 23%,rgba(255,54,45,.75) 32%,transparent 38%,rgba(255,54,45,.65) 48%,rgba(255,225,218,.72) 54%,rgba(255,54,45,.68) 62%,transparent 76%); filter:blur(.15px) drop-shadow(0 0 16px rgba(255,54,45,.65)); transform:skewY(-4deg); }}
.neural-squiggle {{ position:absolute; left:0; right:0; top:42%; height:100px; background:repeating-linear-gradient(110deg, transparent 0 16px, rgba(255,54,45,.22) 17px, transparent 25px); opacity:.65; filter:drop-shadow(0 0 14px rgba(255,54,45,.65)); }}
.thinking-label {{ position:relative; z-index:2; text-align:center; padding:18px 26px; border:1px solid rgba(255,54,45,.26); border-radius:50%; min-width:175px; min-height:175px; display:grid; place-items:center; background:radial-gradient(circle,rgba(17,7,8,.86),rgba(7,6,7,.72)); box-shadow:0 0 50px rgba(255,54,45,.28), inset 0 0 22px rgba(255,54,45,.09); }}
.thinking-label strong {{ color:#ff4c43; letter-spacing:.14em; }}
.thinking-wave {{ height:24px; margin:8px 0; background:linear-gradient(90deg,transparent,rgba(255,54,45,.9),rgba(255,220,215,.8),rgba(255,54,45,.9),transparent); clip-path:polygon(0 50%,5% 42%,10% 58%,15% 40%,20% 62%,25% 46%,30% 54%,35% 38%,40% 65%,45% 45%,50% 55%,55% 35%,60% 63%,65% 48%,70% 54%,75% 40%,80% 60%,85% 48%,90% 53%,95% 44%,100% 50%); }}
.context-fragments {{ position:absolute; right:18px; top:18px; display:grid; gap:10px; width:min(230px,34%); z-index:2; }}
.context-fragment {{ border:1px solid rgba(255,54,45,.28); border-radius:12px; padding:10px; background:rgba(13,8,9,.86); color:#cfc0bf; font-size:12px; }}
.response-generation {{ border:1px solid rgba(255,54,45,.24); border-radius:16px; background:rgba(13,8,10,.86); padding:14px; position:relative; z-index:1; }}
.response-generation ul {{ margin:10px 0 0 20px; color:#d4cac9; line-height:1.8; }}
.chat-input-deck {{ display:flex; gap:12px; align-items:center; border:1px solid rgba(255,54,45,.36); border-radius:20px; padding:14px; background:linear-gradient(180deg,rgba(18,12,14,.94),rgba(8,8,10,.96)); box-shadow:0 0 30px rgba(255,54,45,.20), inset 0 0 18px rgba(255,54,45,.05); }}
.chat-input-deck input {{ flex:1; border:0; background:transparent; font-size:15px; }}
.chat-input-deck button {{ min-width:110px; background:linear-gradient(180deg,#a82924,#541210); color:#fff4f2; border-color:#ff4c43; }}
.risk-table {{ display:grid; gap:8px; font-size:13px; position:relative; z-index:1; }}
.roadmap-step {{ display:grid; grid-template-columns:24px 1fr auto; gap:8px; align-items:center; margin:13px 0; color:#bcaead; }}
.roadmap-dot {{ width:16px; height:16px; border-radius:50%; border:2px solid #ff332b; box-shadow:0 0 16px rgba(255,54,45,.45); }}
.progress-line {{ height:5px; background:#241010; border-radius:999px; overflow:hidden; margin-top:8px; }} .progress-line span {{ display:block; height:100%; background:#ff332b; box-shadow:0 0 14px rgba(255,54,45,.5); }}
.telemetry-lines {{ height:160px; border:1px solid rgba(255,54,45,.18); border-radius:14px; background:linear-gradient(170deg, transparent 0 8%, rgba(255,54,45,.35) 9%, transparent 10% 17%, rgba(255,255,255,.28) 18%, transparent 19% 27%, rgba(255,54,45,.45) 28%, transparent 30% 40%, rgba(255,100,92,.4) 41%, transparent 42%), repeating-linear-gradient(0deg,rgba(255,54,45,.08) 0 1px,transparent 1px 34px); }}
.neural-footer {{ display:grid; grid-template-columns:repeat(6,1fr); gap:10px; }}
.neural-footer-cell {{ min-height:58px; color:#bcaead; font-size:12px; }} .neural-footer-cell b {{ display:block; color:#f1e6e4; font-size:15px; margin-top:6px; }}

/* v711.0-v760.0 neural console restoration: restores the cool command-deck energy while wiring chat affordances to real dashboard actions. */
.ui-stabilized-deck, .ui-neural-restored-deck {{ display:grid; gap:14px; color:#f4eeee; }}
.ui-neural-restored-deck {{ position:relative; }}
.ui-neural-restored-deck::before {{ content:''; position:absolute; inset:-10px; pointer-events:none; border-radius:24px; background:radial-gradient(circle at 52% 24%,rgba(255,54,45,.16),transparent 32%), radial-gradient(circle at 18% 58%,rgba(255,54,45,.08),transparent 24%); opacity:.9; }}
.ui-hero {{ display:grid; grid-template-columns:minmax(320px,1.35fr) repeat(3,minmax(160px,.55fr)); gap:12px; align-items:stretch; position:relative; z-index:1; }}
.ui-hero-main, .ui-status-card, .ui-panel, .ui-neural-panel {{ border:1px solid rgba(255,54,45,.26); border-radius:18px; background:linear-gradient(180deg,rgba(15,9,10,.96),rgba(6,6,8,.96)); box-shadow:inset 0 0 28px rgba(255,54,45,.065), 0 0 24px rgba(0,0,0,.30); padding:15px; }}
.ui-hero-main {{ overflow:hidden; position:relative; }}
.ui-hero-main::after {{ content:''; position:absolute; right:-80px; bottom:-70px; width:240px; height:240px; border-radius:50%; border:1px solid rgba(255,54,45,.18); box-shadow:0 0 60px rgba(255,54,45,.18), inset 0 0 30px rgba(255,54,45,.08); }}
.ui-hero-main h1 {{ margin:0 0 8px; font-size:32px; letter-spacing:.24em; text-transform:uppercase; }}
.ui-hero-main p {{ margin:0; color:#c7bdbc; line-height:1.5; max-width:78ch; }}
.ui-status-card span, .ui-panel small, .ui-neural-panel small {{ display:block; color:#ff6a62; text-transform:uppercase; letter-spacing:.13em; font-size:11px; }}
.ui-status-card b {{ display:block; margin-top:8px; color:#fff0ee; font-size:17px; }}
.ui-status-card.good b {{ color:#a8fff1; }}
.ui-status-card.locked b {{ color:#ffb0aa; }}
.ui-layout {{ display:grid; grid-template-columns:minmax(260px,.78fr) minmax(520px,1.45fr) minmax(280px,.85fr); gap:14px; align-items:start; position:relative; z-index:1; }}
.ui-panel h2, .ui-neural-panel h2 {{ margin:0 0 10px; font-size:14px; letter-spacing:.12em; text-transform:uppercase; }}
.ui-panel h2 span, .ui-neural-panel h2 span {{ color:#ff4c43; margin-right:8px; }}
.ui-metric-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:10px; }}
.ui-metric {{ border:1px solid rgba(255,54,45,.16); border-radius:14px; background:rgba(18,11,12,.72); padding:12px; min-height:76px; }}
.ui-metric b {{ display:block; color:#fff4f2; font-size:24px; margin-top:7px; }}
.ui-row {{ display:flex; justify-content:space-between; gap:12px; padding:9px 0; border-bottom:1px solid rgba(255,54,45,.13); color:#cfc1bf; }}
.ui-row b {{ color:#fff3f1; text-align:right; }}
.ui-action-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; position:relative; z-index:1; }}
.ui-action {{ border:1px solid rgba(255,54,45,.24); border-radius:14px; background:rgba(24,12,13,.78); padding:12px; text-decoration:none; color:#f5eeee; }}
.ui-action strong {{ display:block; color:#ff5b55; margin-bottom:5px; }}
.ui-action span {{ color:#c9baba; font-size:13px; }}
.ui-action:hover {{ border-color:rgba(255,105,92,.54); box-shadow:0 0 22px rgba(255,54,45,.12); }}
.ui-conversation-card {{ min-height:390px; display:grid; grid-template-rows:1fr auto; gap:12px; border:1px solid rgba(255,54,45,.18); border-radius:18px; background:radial-gradient(circle at 50% 42%,rgba(255,54,45,.30),transparent 24%), linear-gradient(180deg,rgba(8,7,8,.65),rgba(8,5,6,.90)); box-shadow:inset 0 0 34px rgba(255,54,45,.09); overflow:hidden; position:relative; }}
.ui-conversation-card::before {{ content:''; position:absolute; inset:0; background-image:linear-gradient(rgba(255,54,45,.07) 1px, transparent 1px), linear-gradient(90deg, rgba(255,54,45,.06) 1px, transparent 1px); background-size:38px 38px; opacity:.34; }}
.ui-core-field {{ position:relative; min-height:250px; display:grid; place-items:center; }}
.ui-core-field::after {{ content:''; position:absolute; width:160%; height:70px; left:-30%; top:47%; background:linear-gradient(100deg,transparent 0 10%,rgba(255,54,45,.08) 13%,rgba(255,54,45,.85) 19%,rgba(255,220,215,.78) 23%,rgba(255,54,45,.7) 32%,transparent 39%,rgba(255,54,45,.72) 51%,rgba(255,235,229,.75) 56%,rgba(255,54,45,.62) 64%,transparent 78%); filter:drop-shadow(0 0 16px rgba(255,54,45,.7)); transform:skewY(-4deg); }}
.ui-core-dot {{ width:178px; height:178px; border-radius:50%; display:grid; place-items:center; text-align:center; border:1px solid rgba(255,54,45,.42); background:radial-gradient(circle,rgba(31,9,10,.96),rgba(7,6,7,.78)); box-shadow:0 0 52px rgba(255,54,45,.28), inset 0 0 24px rgba(255,54,45,.12); position:relative; z-index:2; }}
.ui-core-dot b {{ color:#ff5b55; letter-spacing:.14em; font-size:13px; }}
.ui-wave {{ height:24px; width:128px; margin:6px auto 0; background:linear-gradient(90deg,transparent,rgba(255,54,45,.9),rgba(255,220,215,.8),rgba(255,54,45,.9),transparent); clip-path:polygon(0 50%,6% 42%,12% 58%,18% 39%,24% 63%,30% 45%,36% 56%,42% 36%,48% 65%,54% 44%,60% 57%,66% 35%,72% 62%,78% 47%,84% 55%,90% 42%,96% 52%,100% 50%); }}
.ui-chat-dock {{ position:relative; z-index:2; border-top:1px solid rgba(255,54,45,.18); padding:13px; background:linear-gradient(180deg,rgba(12,8,9,.75),rgba(7,6,7,.94)); }}
.ui-chat-dock form {{ display:grid; grid-template-columns:1fr auto; gap:10px; align-items:end; }}
.ui-chat-dock textarea {{ min-height:48px; max-height:92px; resize:vertical; border-radius:14px; }}
.ui-chat-dock button {{ min-width:130px; }}
.ui-chat-dock label {{ margin:0; }}
.ui-chat-dock .hint {{ margin-top:8px; color:#a99997; font-size:12px; line-height:1.35; }}
.ui-notice {{ margin-top:12px; border:1px solid rgba(255,54,45,.20); border-radius:14px; background:rgba(28,12,13,.7); padding:12px; color:#d9cdcb; font-size:13px; line-height:1.45; }}
.ui-compact-log {{ display:grid; gap:8px; }}
.ui-log-line {{ border:1px solid rgba(255,54,45,.14); border-radius:12px; background:rgba(16,10,11,.62); padding:10px; color:#cdbfbd; font-size:13px; }}
.ui-log-line b {{ color:#ff736b; }}
@media (max-width:1500px) {{ .ui-hero, .ui-layout {{ grid-template-columns:1fr; }} .ui-chat-dock form {{ grid-template-columns:1fr; }} }}

/* v711.0-v760.0 realtime dashboard chat: streaming SSE, live token dock, honest latency status, no fake autonomy. */
.realtime-chat-shell {{ display:grid; gap:12px; border:1px solid rgba(255,54,45,.22); border-radius:18px; background:linear-gradient(180deg,rgba(12,7,8,.82),rgba(7,6,7,.96)); padding:13px; position:relative; z-index:2; }}
.realtime-chat-log {{ min-height:220px; max-height:440px; overflow:auto; display:grid; align-content:start; gap:10px; padding:10px; border:1px solid rgba(255,54,45,.16); border-radius:16px; background:rgba(5,4,5,.66); }}
.chat-continuity-panel {{ border:1px solid rgba(255,54,45,.16); border-radius:14px; padding:9px 11px; background:rgba(16,9,10,.68); color:#cfc1bf; font-size:12px; }}
.chat-continuity-panel summary {{ cursor:pointer; color:#ff746c; font-weight:700; }}
.chat-continuity-panel ul {{ margin:9px 0; padding-left:20px; display:grid; gap:5px; }}
.chat-bubble {{ max-width:88%; border:1px solid rgba(255,54,45,.18); border-radius:16px; padding:10px 12px; white-space:pre-wrap; line-height:1.45; color:#f5eeee; background:rgba(19,10,11,.78); }}
.chat-bubble.user {{ justify-self:end; border-color:rgba(255,84,76,.34); background:linear-gradient(180deg,rgba(76,21,21,.72),rgba(32,9,10,.86)); }}
.chat-bubble.eidolon {{ justify-self:start; border-color:rgba(255,54,45,.22); box-shadow:0 0 24px rgba(255,54,45,.08); }}
.realtime-chat-form {{ display:grid; grid-template-columns:1fr auto; gap:10px; align-items:end; }}
.realtime-chat-form textarea {{ min-height:54px; max-height:130px; resize:vertical; border-radius:14px; }}
.realtime-chat-form button {{ min-width:132px; }}
.chat-toggle-line {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; color:#bcaead; font-size:12px; }}
.chat-toggle-line label {{ display:inline-flex; gap:7px; align-items:center; margin:0; }}
.chat-latency-panel {{ display:flex; gap:10px; flex-wrap:wrap; font-size:12px; color:#cfc1bf; }}
.chat-latency-panel span {{ border:1px solid rgba(255,54,45,.18); border-radius:999px; padding:6px 9px; background:rgba(22,10,11,.74); }}
.thinking-pulse {{ display:inline-flex; align-items:center; gap:8px; color:#ff6d64; }}
.thinking-pulse::before {{ content:''; width:9px; height:9px; border-radius:50%; background:#ff3a31; box-shadow:0 0 16px rgba(255,54,45,.8); animation:eidolonPulse 1s infinite alternate; }}
.thinking-pulse::after {{ content:''; width:68px; height:14px; background:linear-gradient(90deg,transparent,rgba(255,54,45,.9),rgba(255,230,225,.75),rgba(255,54,45,.9),transparent); clip-path:polygon(0 50%,8% 35%,16% 65%,24% 30%,32% 70%,40% 42%,48% 58%,56% 28%,64% 68%,72% 45%,80% 55%,88% 38%,100% 50%); opacity:.85; }}
@keyframes eidolonPulse {{ from {{ transform:scale(.8); opacity:.5; }} to {{ transform:scale(1.25); opacity:1; }} }}
@media (max-width:900px) {{ .realtime-chat-form {{ grid-template-columns:1fr; }} .chat-bubble {{ max-width:96%; }} }}

{COMPANION_CHAT_STYLES}

/* v691-v695 neural command deck interaction refinement. Keeps the UI simple, clean, and operator-governed. */
.neural-focus-rail {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }}
.focus-pill {{ border:1px solid rgba(255,54,45,.30); border-radius:14px; padding:10px 12px; background:linear-gradient(180deg,rgba(20,10,11,.92),rgba(7,7,8,.92)); color:#d9cdcc; box-shadow:inset 0 0 18px rgba(255,54,45,.05); }}
.focus-pill b {{ display:block; color:#ff5148; text-transform:uppercase; letter-spacing:.10em; font-size:12px; margin-bottom:4px; }}
.focus-pill span {{ color:#9f9291; font-size:12px; }}
.neural-input-actions {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
.mode-chip, .telemetry-chip, .neural-priority {{ border:1px solid rgba(255,54,45,.22); border-radius:999px; padding:6px 10px; background:rgba(18,10,11,.72); color:#d9cdcc; font-size:11px; letter-spacing:.08em; text-transform:uppercase; }}
.mode-chip.locked, .neural-priority.blocked {{ color:#ff5b55; border-color:rgba(255,54,45,.42); }}
.neural-panel.compact {{ padding:12px; }}
.neural-panel.compact h2 {{ margin-bottom:8px; }}
.neural-priority {{ display:inline-flex; margin-left:8px; color:#ffb5ae; }}
.context-fragment[data-tip], .telemetry-chip[data-tip], .focus-pill[data-tip], .mode-chip[data-tip] {{ cursor:help; }}
.neural-quick-strip {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }}
.neural-quick-strip a, .neural-quick-strip button {{ min-height:34px; padding:7px 11px; font-size:12px; }}
.interaction-divider {{ height:1px; background:linear-gradient(90deg,transparent,rgba(255,54,45,.42),transparent); margin:8px 0; }}
@media (max-width: 1280px) {{ .neural-focus-rail {{ grid-template-columns:1fr; }} .neural-input-actions {{ justify-content:flex-start; }} }}

@media (max-width: 1280px) {{ .neural-topbar, .neural-layout, .neural-footer {{ grid-template-columns:1fr; }} .eidolon-conversation {{ min-height:auto; }} .context-fragments {{ position:relative; right:auto; top:auto; width:auto; }} }}

@media (max-width: 980px) {{
  body > header {{ position:static; left:auto; right:auto; width:100%; height:auto; min-height:62px; padding:12px 16px; display:grid; gap:4px; }}
  body > header .subtitle::after {{ display:none; }} main {{ margin-left:0; padding:18px 12px 24px; }}
  body > nav {{ position:sticky; top:0; inset:auto; width:100%; max-height:none; overflow:visible; border-right:0; border-bottom:1px solid rgba(255,54,45,.24); z-index:20; }}
  nav.nav-shell {{ padding:8px 12px; }} nav.nav-shell::before {{ display:none; }}
  .nav-mobile-toggle {{ display:flex; }}
  .nav-content[data-mobile-collapsed='true'] {{ display:none; }}
  .nav-content[data-mobile-collapsed='false'] {{ max-height:calc(100dvh - 72px); overflow-y:auto; overscroll-behavior:contain; padding-bottom:8px; }}
  nav a.nav-link, .nav-section summary, .command-palette input {{ min-height:44px; }}
  .command-palette {{ display:grid; grid-template-columns:1fr; }} .command-palette input {{ min-width:0; width:100%; }}
  .command-flow, .console-grid, .reco-strip {{ grid-template-columns:1fr; }}
}}


/* Era 10 chat-first product shell. Advanced operator surfaces remain available through navigation. */
.era10-product-maturity .realtime-chat-shell {{ max-width:1120px; margin-inline:auto; }}
.era10-product-maturity .realtime-chat-log {{ min-height:240px; height:clamp(240px,42dvh,520px); max-height:none; }}
.era10-product-maturity .footer {{ opacity:.72; }}
.era10-product-maturity .nav-section:not([open]) {{ opacity:.88; }}
.era10-product-maturity:has(.chat-console-primary) > header {{ display:none; }}
.era10-product-maturity:has(.chat-console-primary) main {{ padding-top:20px; padding-bottom:16px; }}
.era10-product-maturity:has(.chat-console-primary) .chat-console-primary {{ min-height:calc(100dvh - 36px); }}
@media (max-width:760px) {{ .era10-product-maturity .realtime-chat-shell {{ max-width:100%; }} }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ scroll-behavior:auto !important; animation:none !important; transition:none !important; }}
}}

</style>
</head>
<body class='era10-product-maturity' data-era10-chat-first='true'>
<a class='skip-link' href='#dashboard-main'>Skip to main content</a>
<header><h1>{DASHBOARD_TITLE}</h1><div class='subtitle'>Local-only operator console at {_safe(settings.get('dashboard_host','127.0.0.1'))}:{_safe(settings.get('dashboard_port',8765))}. Review-only surfaces; operator gates remain in control.</div></header>
{nav}
<main id='dashboard-main' tabindex='-1'>{_live_refresh_bar(settings)}{msg}{err}{content}<div class='footer'>Generated at {_safe(_now())}. Approval gates remain explicit and operator-controlled.</div></main>
<script>
(function () {{
  const search = document.querySelector('[data-nav-search]');
  const toggle = document.querySelector('.nav-mobile-toggle');
  const content = document.querySelector('.nav-content');
  const mobile = window.matchMedia('(max-width: 980px)');
  function setNavigation(open) {{
    if (!toggle || !content) return;
    const expanded = !mobile.matches || !!open;
    content.dataset.mobileCollapsed = mobile.matches && !expanded ? 'true' : 'false';
    toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }}
  function syncNavigation() {{ setNavigation(!mobile.matches); }}
  if (toggle) toggle.addEventListener('click', function () {{ setNavigation(toggle.getAttribute('aria-expanded') !== 'true'); }});
  document.addEventListener('keydown', function (event) {{
    if (event.key === 'Escape' && mobile.matches && toggle && toggle.getAttribute('aria-expanded') === 'true') {{
      setNavigation(false);
      toggle.focus();
    }}
  }});
  if (mobile.addEventListener) mobile.addEventListener('change', syncNavigation); else mobile.addListener(syncNavigation);
  syncNavigation();
  if (!search) return;
  function normalize(value) {{ return String(value || '').toLowerCase(); }}
  function applyFilter() {{
    const q = normalize(search.value).trim();
    document.querySelectorAll('.nav-section').forEach(function (section) {{
      let visibleCount = 0;
      section.querySelectorAll('a.nav-link').forEach(function (link) {{
        const haystack = normalize((link.dataset.routeTitle || '') + ' ' + (link.dataset.routeGroup || '') + ' ' + (link.dataset.tip || '') + ' ' + link.textContent);
        const visible = !q || haystack.includes(q);
        link.classList.toggle('nav-hidden', !visible);
        if (visible) visibleCount += 1;
      }});
      section.classList.toggle('nav-hidden', !!q && visibleCount === 0);
      if (q && visibleCount > 0) section.open = true;
    }});
  }}
  search.addEventListener('input', applyFilter);
  document.querySelectorAll('a.nav-link').forEach(function (link) {{
    link.addEventListener('click', function () {{ if (mobile.matches) setNavigation(false); }});
  }});
}})();
</script>

{_live_refresh_script(settings)}
</body>
</html>"""


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "render_dashboard_layout"]
