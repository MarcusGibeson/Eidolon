# Eidolon v1255.0-v1255.9 Controlled Application and Rollback Review

## Finding

The v1254 isolated-development pipeline could produce a tested, reviewable candidate but deliberately had no authority to modify the selected project. v1255 closes that practical gap without reusing v1254 execution approval as application approval and without reviving the older global-staleness behavior that rejected safe unrelated operator edits.

## Implementation

### v1255.0-v1255.2

A reviewed v1254 result is transformed into an immutable controlled-application packet. It binds the exact request, inspection, execution, review, workspace, candidate manifest, and per-path baseline/candidate state. Conflict detection is path-selective: only paths the candidate intends to change can block application. Private backup contents are deliberately absent until the last pre-write boundary.

### v1255.3-v1255.5

Application requires an exact packet-digest phrase and is one-time. All candidate payloads and affected paths are preflighted, then a private affected-path backup is captured immediately before the first write. Create/modify/delete writes are performed with same-directory replacement semantics, followed by bounded live verification. Verification failure automatically restores the backed-up affected scope. Successful application creates rollback availability but not rollback authority; rollback requires another exact digest-bound phrase. Ordinary-chat controls reuse the existing development campaign instead of introducing a parallel product.

### v1255.6-v1255.8

The transaction is hardened against Windows case aliases, link/reparse substitutions, candidate workspace tampering, stale same-path source, cancellation, backup tampering, expired leases, interrupted partial application, interrupted partial rollback, concurrent duplicates, and post-apply operator edits. Recovery proceeds only from known baseline/candidate states and fails closed on unknown third states. Read-only health and operator handoff surfaces expose digests/state rather than project paths or backup contents.

### v1255.9

A read-only checkpoint consolidates the complete section, release metadata, registry selectors, retained behavioral evidence, and the boundary to v1256.

## Authority boundary

v1255 adds selected-project mutation only for one exact reviewed candidate under one exact operator authorization. It does not grant installation, promotion, certification, release, permanent approval, unrestricted shell/dependency installation, autonomous self-update, or independent authority. A successful application does not silently authorize rollback; rollback is separately approved.

## Remaining limitations

- Native Windows NTFS junction/reparse behavior and case-insensitive path collision behavior must be exercised on the Desktop Codex Windows host.
- Same-volume `os.replace` atomicity and interruption behavior should be rehearsed on the operator's actual Windows filesystem.
- v1255 is intentionally request-local. It does not yet persist a richer multi-stage development session across restarts; that belongs to v1256.
- Dependency installation and unrestricted shell execution remain outside the authority surface.
- Applying an Eidolon candidate to the active Eidolon installation is not an automatic self-update. Later governed self-update milestones remain separate.

## Result

The v1255 objective is met: explicitly authorized reviewed candidates can be applied, conflicting edits are detected without discarding unrelated operator changes, backups are captured at the correct boundary, installation is verified, and dependable separately authorized rollback/recovery is available.
