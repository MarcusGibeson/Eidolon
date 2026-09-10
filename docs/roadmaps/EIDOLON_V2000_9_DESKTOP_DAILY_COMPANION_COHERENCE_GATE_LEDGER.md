# Eidolon v2000.9 Desktop Daily-Companion Coherence Gate Ledger

Status: Desktop-reviewed source-only checkpoint; unpromoted and not installed.

## Input identity

- Candidate ZIP SHA-256: `4406159396cecdbf08186f577bc8017fc9d7a6e97a14b4b479adb6a807df6045`
- Archive shape: one `Eidolon/` root; 5,290 entries; no packaged private runtime data, project registry, cache, bytecode, or Git metadata.
- Cumulative diff from v1900.9: 14 added, 12 modified, 0 deleted files.
- The actual file-level diff matched every declared path and SHA-256 in the candidate manifest with no missing, extra, or mismatched entries.

## Windows and native evidence

- Focused Era 5 suites: 116/116 passed after repair.
- Affected retained suites: 668/668 passed.
- Fresh compilation covered 4,171 cache targets without writing bytecode into source.
- Twelve concurrent Windows processes produced twelve successful affective-state updates and exactly twelve revisions. A fresh process restored the same content-free state; no message content or authority effect was present.
- Configured Ollama readiness, generation, streaming, and 768-dimensional embeddings passed without installing, deleting, or switching models. The configuration digest matched between readiness and native smoke.
- Native conversation completed 12/12 scenarios. Average quality was 99%, with 11 passes and one non-blocking response-shape warning. Provider requests, messages, actions, and persistent conversation mutations had zero duplicates; no automatic provider fallback or switching occurred.

## Desktop repair

The Era 5 output audit looked for a flat `response_plan.max_questions` field, while live runtime projections provide `discourse.response_plan.maximum_questions`. It also converted a valid zero-question limit into one. The repaired audit reads both projection shapes, preserves zero, bounds malformed values safely, and has regressions for nested and legacy zero-question plans.

## Remaining limitations

- The configured 7B model still has one non-blocking native response-shape warning despite a 99% average quality score.
- Output audits detect and report quality risks; they deliberately do not rewrite a response or retry the provider automatically.
- Relationship continuity candidates cannot start unsolicited turns. Era 6 must add paced attention and initiative governance before background cognition can become useful without becoming noisy.
- This gate is not installation, promotion, certification, model-management, destructive-operation, or independent authority.

## Next bounded unit

`v2001.0 - Attention and Salience foundations`
