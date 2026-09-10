# Eidolon v1256.0-v1256.9 Persistent Development Sessions Review

## Result

v1256 closes the continuity gap between the v1254 isolated-development pipeline and the v1255 controlled-application/rollback pipeline. A development request now has one deterministic durable session projection that can be reconstructed after process restart without replaying implementation work or inventing replacement authorization.

## Architecture

The implementation is deliberately layered over existing development records:

- `persistent_development_sessions_foundations.py` derives the durable session from v1254/v1255 sealed lineage.
- `persistent_development_sessions.py` supplies ordinary-chat status/resume controls and append-only deduplicated progress receipts.
- `persistent_development_sessions_reliability.py` supplies health inspection, metadata quarantine/reconstruction, reliable resume, and bounded operator handoff.
- `ordinary_chat_development_campaign.py` attaches/refreshed the session at existing proposal, execution, apply, and rollback boundaries.
- `persistent_development_sessions_checkpoint.py` provides the read-only v1256.9 consolidation surface.

No parallel provider runner, project mutator, application engine, or approval store was introduced.

## Bundle A: v1256.0-v1256.2

- Deterministic request-to-session identity and idempotent restoration.
- Requirements, plans, assumptions, workspace/review/application/rollback lineage preserved by digest.
- Attempt and verification summaries are content-minimized and omit raw provider/test output.
- Restart/cancellation restoration is durable.
- All execution/application/release authority remains false.
- Focused result: **49/49 passed**.

## Bundle B: v1256.3-v1256.5

- Ordinary conversational show/status/resume controls.
- Existing v1254 exact execution and v1255 exact apply/rollback authorizations are surfaced, never duplicated or silently consumed.
- Append-only progress event chain deduplicates identical state observations.
- End-to-end provider-backed fixture preserves failed and passing attempt evidence across a fresh process.
- Apply replay and rollback do not contact the provider again.
- Focused result: **42/42 passed**, provider calls exactly **2**.

## Bundle C: v1256.6-v1256.8

- Stale-source blocker before authorization resurfacing.
- Expired-lease recovery projection with original exact authorization.
- Corrupt index/session/event quarantine and authoritative-lineage reconstruction.
- Concurrent resume deduplication.
- Long-path and content-minimized handoff hardening.
- Focused result: **36/36 passed**.

## v1256.9 checkpoint

- Read-only checkpoint result: **40/40 passed**.
- Release/checkpoint metadata advanced through v1256.9.
- v1257 Diagnostic and Repair Reasoning is named only as the next bounded unit and has not been implemented.

## Retained regression evidence

- v1255.0-v1255.2: **44/44 passed**.
- v1255.3-v1255.5: **43/43 passed**.
- v1255.6-v1255.8: **50/50 passed** on its isolated rerun. A prior aggregate regression command hit its wall-clock limit before this heavy suite completed; no test failure was observed and the isolated suite is green.
- v1255.9 retained checkpoint: **31/31 passed** under later-source-compatible checkpoint assertions.
- v1254.9 retained checkpoint: **29/29 passed** under later-source-compatible checkpoint assertions.
- v1253.9.2 Windows coherence: **19/19 passed**.
- v1238.9 broader project/language adapters: **27/27 passed**.
- v1247.9 privacy/security checkpoint: **59/59 passed**.
- v1250.3 release metadata: **94/94 passed**.
- v1250.4 checkpoint registry: **118/118 passed**.

## Remaining limitations

- Native Windows cross-process lock behavior, actual NTFS junction/reparse cases, and real Windows long-path/process-restart behavior still require Desktop Codex validation.
- v1256 does not add new diagnostic reasoning. It records/restores blockers and evidence; v1257 owns causal diagnosis and focused repair reasoning.
- Resume does not grant execution, provider, test, application, rollback, installation, promotion, certification, release, permanent-approval, or independent authority.
- Raw provider payloads, raw test output, private project paths, secrets, and runtime content are not source-package artifacts.
