# Eidolon v1269.0-v1269.9 Governed Self-Update Review

## Outcome
v1269 completes the governed self-update arc without creating standing or transferable self-update authority.

### v1269.0-v1269.2
- Consumes only an exact `approve_for_v1269_consideration` v1268 disposition.
- Revalidates the v1268 packet, decision receipt, active source, and disposable candidate.
- Binds one deterministic update packet to exact active/candidate manifests and reviewed changed paths.
- Defers private backup capture until immediately before the first authorized write.
- Requires a fresh exact update authorization.

### v1269.3-v1269.5
- Captures a private affected-path backup before the first write.
- Applies only reviewed paths and validates source/candidate digests before mutation.
- Requires the resulting source-only manifest to equal the reviewed candidate manifest.
- Requires fresh-process/restart-health evidence through a bounded verifier callback.
- Automatically restores the backup when application or health verification fails.
- Makes exact successful apply replay idempotent.
- Supports a separate exact authorization for rollback after a successful update.

### v1269.6-v1269.8
- Rejects stale active source, stale candidate, changed reviewed paths, ambiguous Windows names, links/reparse-like entries, and resealed candidate-digest tampering.
- Serializes duplicate update execution under the existing proposal lock.
- Recovers an expired running record only when affected paths are baseline/candidate known states and a valid private backup exists.
- Preserves unrelated drift by restoring only reviewed affected paths, then requires the full baseline manifest before retry.
- Exposes read-only health/recovery disposition and a native Windows/Desktop handoff.

### v1269.9
- Read-only Governed Self-Update checkpoint.
- v1270 remains separate.

## Practical full-tree probe
A source-only disposable active installation containing 3,362 files / 42,163,231 bytes was cloned from the v1269 development tree. A reviewed candidate added only `conscious_agent/v1269_update_probe.py`.

The exact v1269 authorization captured backup, applied that one path, matched the full candidate manifest, and launched a fresh child Python process that imported the updated source successfully. A separate exact rollback authorization then restored the original full-tree manifest. The development source used to build the release candidate remained unchanged.

## Authority boundary
v1268 approval is consideration only. v1269 exact authorization is one-time and packet-bound. Promotion, certification, release, permanent approval, and independent future self-update authority remain denied. Application remains separately governed by v1255.9.
