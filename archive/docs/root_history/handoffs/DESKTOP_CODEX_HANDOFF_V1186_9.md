# Desktop Codex Handoff: Eidolon v1186.9

## Candidate

Archive: `Eidolon_v1186_9_durable_campaign_continuation_checkpoint_source_candidate.zip`

The archive SHA-256 is supplied in the adjacent `.sha256` sidecar after final packaging. Treat the archive as immutable input and verify its digest before extraction.

## Verified state

v1186.9 consolidates durable campaign storage, restoration review, source-drift reconciliation, resume eligibility, lease-backed resumed-session materialization, restart reconciliation, and operator-reviewed lease release into one source-discovered checkpoint.

Current deterministic results:

- v1186.9 internal checkpoint: 222/222 PASS.
- v1186.9 external suite: 137/137 PASS.
- v1186 retained bundles: 21/21, 14/14, and 23/23 PASS.
- v1185.9: 131/131 PASS.
- v1184.9: 125/125 PASS.
- v1183.9: 113/113 PASS.
- v1182.9 through v1179.9 retained checkpoints: PASS.
- v1174.9: 90/90 PASS plus repaired-baseline review PASS.
- Conversation runtime: 35/35 PASS.
- Source-only boundary: 9/9 PASS.
- External compilation: 2,039 Python files PASS.

The quick profile is BLOCKED: 88/113 steps passed, with 24 inherited historical blocks and one 60.148-second performance-budget overrun. All current v1186 steps passed. Source writes and deletes were both zero, and runtime cleanup passed.

## Review boundaries

Do not infer campaign execution, provider reconnection, automatic resume, source application, installation, promotion, certification, publication, release, or autonomous authority. Temporary runtime fixtures are not production campaign data.

## Next bounded unit

v1187.0-v1187.2: **Bounded Campaign Work Execution Foundations**.

Recommended objectives:

- Accept one exact execution-eligible resumed-session handoff and its lease/restart lineage.
- Require a separate explicit operator execution admission.
- Bind one bounded selected work item, exact source baseline, resource budgets, rollback plan, stopping conditions, and result-evidence contract.
- Permit only an allowlisted isolated execution adapter.
- Measure actual elapsed time, disk change, token/provider budget, and cancellation state.
- Produce content-free execution receipts without exposing source, prompts, provider payloads, stdout, stderr, or private reasoning.
- Keep execution admission, execution, result review, source application, promotion, certification, and release authority separate.
- Do not make Eidolon autonomous.

Desktop Codex and native-provider review remain scheduled for v1200.
