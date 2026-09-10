# Windows/Desktop Codex Handoff: v1192.9

## Candidate

Eidolon v1192.9 Bounded Evidence Compaction read-only checkpoint candidate.

## Review purpose

This is a bounded Windows/Desktop handoff, not the scheduled full Desktop Codex decision gate. The next full Desktop Codex and native-provider review remains v1200.

## Verify first

1. Verify the candidate archive SHA-256 supplied alongside the archive.
2. Extract beneath exactly one clean `Eidolon/` root.
3. Do not use an installed directory, an older source tree, or a reconstructed worktree.
4. Use neutral external runtime, bytecode, profile-output, and worktree paths that do not share the candidate-version cleanup prefix.

## Focused Windows checks

Run from the extracted `Eidolon/` root with Python 3.11 or the supported project interpreter:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = "."
python tools/v1192_9_evidence_compaction_checkpoint_tests.py
python tools/v1192_6_8_evidence_compaction_reliability_tests.py
python tools/v1192_3_5_evidence_compaction_review_tests.py
python tools/v1192_0_2_bounded_evidence_compaction_tests.py
python tools/v1191_9_responsiveness_background_work_checkpoint_tests.py
python tools/v1190_9_unified_experience_checkpoint_tests.py
python tools/v1189_9_persistent_supervised_developer_alpha_hardening_checkpoint_tests.py
python tools/v1150_1_source_only_runtime_boundary_tests.py
python eidolon.py evidence-compaction-checkpoint
```

Expected focused results:

- v1192.9 external suite: 383/383 PASS.
- v1192.6-v1192.8: 110/110 PASS.
- v1192.3-v1192.5: 73/73 PASS.
- v1192.0-v1192.2: 62/62 PASS.
- v1191.9: 176/176 PASS.
- v1190.9: 82/82 PASS.
- v1189.9: 72/72 PASS.
- Source-only boundary: 9/9 PASS.
- CLI checkpoint internal result: 159/159 PASS.

## Review observations

Confirm that:

- Nine evidence domains remain represented.
- Expansion reproduces every original evidence record exactly.
- Approve, reject, and defer remain presentation-only review decisions.
- Original evidence is preserved after every decision.
- Replay, stale snapshot/context/compaction, tamper, malformed lineage, private fields, and authority claims fail closed.
- No recovery, replacement, deletion, execution, approval consumption, provider/model contact, thread/process start, installation, promotion, publication, release, or authority expansion occurs.
- The API endpoint is GET-only: `/api/cognition/evidence-compaction-checkpoint`.
- The release-verification step is registered exactly once.

## Verifier note

The v1191.9 retained suite now checks that its historical current-source marker remains present rather than incorrectly requiring v1191.9 to remain the first current source forever. This preserves the suite's 176 checks while allowing later source versions.

## Known inherited debt

Do not treat the global quick/full profile as passed. Historical fixture overlap, checkpoint duplication, cleanup-prefix behavior, verifier ownership ambiguity, and performance-budget reconciliation remain v1193 work.

## Next development boundary

Proceed only to v1193.0-v1193.2 Verifier Ownership and Historical-Debt Foundations after accepting this checkpoint candidate.
