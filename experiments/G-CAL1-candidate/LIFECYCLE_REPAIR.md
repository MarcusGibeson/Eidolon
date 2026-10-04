# G-CAL1 lifecycle repair (science unchanged)

This prospective implementation revision closes the four blocked audit paths.
It does not change any design, fixture, gold, allocation, request, seed, schedule,
contamination rule/result, interpretation, generation setting or historical file.

## Operation ordering

Every collection, checkpoint, resume verification and authority-bearing report
acquires an OS-backed exclusive per-run file lock before inspecting authoritative
incidents/journal. The namespace is derived from the normalized absolute run
directory and shared across processes. Windows byte-range locking (or POSIX flock)
holds a handle through synchronization, operability checks and durable closure or
incident retention. A competing operation waits; timeout fails closed. Lock files
are transient coordination state outside the experiment directory and never part
of authority or deterministic evidence. The lock grants no execution permission.

Under the lock, complete journal/checkpoint/scorer replay reconstructs position and
state. An incident from any object is terminal for all objects. A stale checkpoint
cannot verify after journal advancement. Guarded integrity errors are persisted
before releasing the lock, not by a wrapper running afterwards.

## START-to-close boundary

The entire durable START through COMPLETE/FAILURE region catches BaseException,
not merely the transport invocation. If durable closure cannot be established,
the existing SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT INVALID incident is
persisted with phase/cell before the original exception propagates. No provider
receipt is fabricated. If append already committed COMPLETE before interruption,
the durable tail establishes closure: no false omission is recorded, and the next
operation replays that COMPLETE before using position/state. Ordinary transport
Exceptions still produce the existing unreceipted FAILURE lifecycle.

## Cached science and callback aliases

Canonical bytes of all authority-bearing package caches are bound at verified
load and compared before use, alongside the protected source hashes. This includes
the schedule, entire canonical member/fixture/request/gold set, design/baseline,
manifest/pins and bindings. A callback receives a detached schedule row including
detached generation configuration. Scoring uses a detached frozen member and a
post-return package verification. This protects the public mutation/alias boundary;
it does not purport to sandbox arbitrary malicious Python code with process access.

## Synthetic-only mechanical boundary

Mechanical collection requires `synthetic_only is True`, before START or transport.
Unmarked, false, numeric/truthy markers, unmarked wrappers and provider-like adapters
are rejected. Real collection still requires an explicit false transport marker,
an independently active G-CAL1 freeze and a distinct exact CAL phase/run/binding grant.
Positive markers are trusted declarations for local test stubs, not proof that an
arbitrarily malicious callable cannot make a network request. The pilot additionally
denies socket network operations. No provider adapter is imported or invoked.

The old blocked candidate and audits remain unchanged. Any replacement is candidate
only, with separate independent audit, freeze review, activation and execution
authorization still required. Closed G-EXTRACT1 and G-ROUTE4 remain immutable.
