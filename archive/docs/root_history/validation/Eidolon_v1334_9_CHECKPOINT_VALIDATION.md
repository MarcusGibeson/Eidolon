# Eidolon v1334.9 File Operations Checkpoint Validation

This checkpoint adds structured candidate-workspace file operations on top of v1333 isolation.

## Completed behavior

- Supports candidate `read`, `patch`, `move`, and `generated_update` operations.
- Every operation resolves a workspace-relative path beneath the exact sealed v1333 candidate root, rejects links/reparse boundaries and protected runtime/private paths, and never writes the selected source.
- Reads require an active exact standing grant plus a sealed satisfied `file_read` precondition. Writes require the same workspace-bound standing grant plus a sealed satisfied `file_patch` precondition.
- Patches use optimistic exact content digests, deterministic structured text or line-range patches, atomic replacement, mode preservation, supported UTF-8/UTF-8-BOM/UTF-16 BOM preservation, and dominant newline preservation.
- Moves require an exact source digest and an absent destination. Generated updates require either exact existing-content lineage or an explicit expected-absent contract.
- Duplicate mutation requests converge to the prior sealed operation only when current candidate content matches the recorded postcondition; otherwise they fail as conflicts.
- Evidence receipts persist path/content digests and encoding/newline classes, never raw paths or file content. Immediate file contents are returned only to an explicitly requesting internal read caller and are not persisted in the receipt.
- Ordinary chat can inspect a receipt but performs no file operation.

## Focused deterministic evidence

- v1334.0-v1334.2 foundations: 5/5
- v1334.3-v1334.5 integration: 5/5
- v1334.6-v1334.8 reliability/adversarial: 5/5
- v1334.9 checkpoint: 5/5
- retained v1250.3 release metadata: 94/94
- retained v1250.4 checkpoint registry: 118/118

The integration fixtures exercise CRLF and UTF-8 BOM preservation, line-range and text patching, safe moves, generated files, stale-write prevention, duplicate convergence, symlink rejection where supported, tamper rejection, and selected-source immutability.

## Authority and platform boundary

The active grant authorizes only the exact candidate file operation. No command/provider contact, selected-source application, installation, release, protected action, or persistent independent authority is granted. Native Windows reparse/newline/encoding behavior remains subject to the later native Windows review gate.
