# Eidolon Era 6 Mobile Browser Work Ledger - v2099.9

Status: cumulative source-only Browser candidate; unreviewed, unpromoted, uninstalled.
Authoritative input: v2000.9 Era 5 Desktop Daily-Companion Coherence Gate.
Campaign: v2001.0-v2099.9 Attention, Initiative, and Background Cognition.
Next gate: v2100 operator-invoked Desktop Era 6 initiative gate.

## Completed portable capability

### v2001-v2025.9 Attention and Salience
- Added deterministic salience scoring across urgency, importance, novelty, emotional relevance, risk, deadline pressure, and operator priority.
- Added freshness/uncertainty penalties and anti-fixation penalties while exempting genuinely urgent, risky, or operator-priority work.
- Added restart-safe one-focus ownership with digest-bound defer/resume/cancel controls and exactly-once event replay.
- Reuses established attention-center evidence rather than creating a second attention store.

### v2026-v2050.9 Event Loop and Internal Scheduling Foundations
- Added a durable content-free background scheduler contract for read-only inspection, memory-consolidation review, plan review, and proposal preparation.
- Added operator-configurable enablement, quiet hours, interval jobs, priorities, bounded ticket budgets, wake/tick identity, foreground-load yielding, provider-availability awareness, and resource-pressure suppression.
- Added digest-bound pause/resume/cancel for jobs and digest-bound ticket outcome receipts with exactly-once lifecycle recording.
- Scheduler ticks prepare bounded work tickets only; they do not launch threads, processes, providers, tools, messages, source writes, or memory mutations.

### v2051-v2075.9 Proactive Communication Governance
- Added policy judgment over urgency, relevance, confidence, relationship relevance, operator priority, ignored cues, reminder state, completion summaries, and question need.
- Reuses the existing ProactiveCommunicationStore as the single retained queue/exactly-once delivery owner.
- Adds speak/wait/summarize/remind/ask decisions, cooldown/restraint after ignored cues, quiet-mode precedence, unread-message anti-stacking, and content-minimized batching.
- Browser policy may queue a reviewable candidate through existing boundaries but never claims delivery or new-turn authority.

### v2076-v2099.9 Resource and Concurrency Governance
- Added portable CPU, memory, disk, provider-concurrency, background-concurrency, thermal, and time budgets with priority classes.
- Added deterministic permit/degrade/suspend assessment from supplied measurements and cooperative logical suspension/resume of prepared background tickets.
- Integrated resource pressure directly into the Era 6 background-cycle preparation path so foreground load or critical pressure suppresses new background tickets.
- Does not sample or control OS processes in Browser; native sampling/process behavior is deferred to v2100.

## Production integration
- Added a single Era 6 coordination layer over the retained attention center, proactive queue, and existing ordinary-chat authority boundary.
- Ordinary chat can inspect attention/initiative state, background-cognition status, proactive queue state, and resource budgets through exact read-only controls.
- Compound read-only-plus-install/authority wording fails closed.
- Integrated background-cycle preparation can select focus, apply resource policy, and prepare a bounded scheduler ticket, but cannot execute the ticket.

## Defects and hardening during the campaign
1. Added explicit ticket lifecycle after the first scheduler implementation exposed a gap between ticket preparation and later outcome reconciliation.
2. Integrated resource assessment into the actual background-cycle path rather than leaving resource governance as an isolated helper.
3. Kept high-priority/urgent work exempt from anti-fixation so safety/urgent work is not suppressed merely because it remains important.
4. Historical retained tests that rely on obsolete README/version-authority text were classified against the untouched v2000.9 baseline rather than weakening them.

## Verification summary
- Era 6 focused: 76/76 passed.
- Selected current/affected retained verification: 514/514 passed.
- Combined selected current/affected total: 590/590 passed.
- Release metadata: 94/94 passed.
- Checkpoint registry: 118/118 passed.
- Compatibility registry migration: 100/100 passed.
- Release self-knowledge: 32/32 passed.
- Python compilation in memory: 4,210/4,210 passed before final packaging.

## Inherited historical debt
- v1108.9 persistent-initiative checkpoint: 7/8 on both candidate and untouched v2000.9 baseline; obsolete version-authority artifact expectation.
- v1191.9 responsiveness/background-work checkpoint fails on both candidate and untouched v2000.9 baseline at a hard-coded `Current source: v1191.9` README assertion.
- Browser quick verifier passed python-compile and version-inventory, then exceeded the command window during its large corrective suite. No complete quick-profile pass is claimed.

## Authority
No Browser step installed, promoted, certified, contacted a configured provider, changed a model, accessed private runtime content, started a native background process, delivered a proactive message, performed a destructive operation, or expanded standing authority.
