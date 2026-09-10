# Eidolon v1376.9 Partial-Result Retention Final Validation

This checkpoint extends **Phase 8: Durable Multi-Step Campaigns** with private retention of useful interrupted artifacts while keeping verification state explicit.

- Retention requires explicit retention authority and exact campaign/task/producer-evidence lineage.
- Artifact bytes are stored only beneath an explicit external runtime root; public evidence retains only content-free identity/content digests, byte counts, type, and unresolved verification digests.
- Every retained interrupted artifact is marked `partial_unverified` and `usable_as_verified_evidence: false` until later verification is independently completed.
- Exact-digest loading proves retained bytes survive interruption; duplicate retention converges idempotently.
- Tampered descriptors/blobs, stale expected digests, oversized artifacts, malformed types, and missing remaining checks fail closed.
- Ordinary-chat inspection never exposes private artifact bytes.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5. Retained release metadata passes 94/94 and checkpoint registry passes 118/118. No retained result grants application, project/source mutation, release, or independent authority.
