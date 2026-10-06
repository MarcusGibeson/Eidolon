# G-CAL1 Versioned Authority Migration

Status: implementation prepared for independent Sol review. No replacement
candidate, activation, CAL grant, real run, or provider contact has been created.

## Boundary

The v1 lab has a fixed authority pointer and an implementation manifest that
predates the reviewed adapter. It cannot express transport-bound replacement
authority without changing protected bytes. It remains unchanged and available
for historical reconstruction. Its old activation is not authority for this
versioned entrypoint.

`g_cal1_authority_v2.Registry` and `g_cal1_live_v4.LiveRun` are additive. They reuse
the unchanged frozen lab's collection kernel, scoring, diagnostics, journal,
checkpoint verification, replay, terminal incidents and lock handling. There is
no automatic execution CLI and no monkeypatch of the historical authority path.
The versioned constructor and authority-boundary overrides replace only the
fixed v1 authority consumer.

## Append-Only Selection

Future production namespace: `experiments/G-CAL1-candidate/execution/authority_v2`.
It is **absent** during implementation. Reading an absent registry does not create
it and cannot authorize execution.

Immutable artifacts live in `candidates`, `reviews`, `activations`, and `grants`,
named by their actual compact sorted-key UTF-8 JSON SHA-256. Exclusive create,
flush and fsync are inherited from the frozen write-once helper. A candidate
publication alone grants no authority.

`transitions` uses the frozen sealed journal schema. Its first row is GENESIS
bound to the exact old pointer, activation and candidate hashes. Each
ACTIVATE_SUPERSEDING row identifies one new immutable activation and its exact
predecessor. All predecessor artifacts, review binding and unchanged science
binding are checked on replay. A failed publication can leave an inactive orphan;
only a complete validated transition selects authority. No mutable active pointer
is introduced; an ACTIVE_FREEZE.json in this namespace is rejected.

The current generation is the seal of its activation transition, not the latest
run-reservation row. Rollover changes it, invalidating older grants and resumptions.
Previous activations remain readable historical evidence; they are not current
authority for this entrypoint. The legacy pointer/activation status is never
rewritten to describe supersession.

## Future Separate Actions

1. Independent implementation review, then separately authorized candidate
   preparation. `Registry.candidate(timeout_seconds=...)` only returns an object.
   The operator must explicitly choose the positive per-blocking-socket-operation
   transport timeout before freeze; no default or scientific setting is invented.
2. Separate freeze review binds the exact candidate and execution digest. Its
   immutable review record requires PASS by Sol 6.1 for EXECUTION_FREEZE_REVIEW.
3. Separate explicit activation. `activate` requires an operator record with
   status EXPLICIT_OPERATOR_FREEZE_ACTIVATION bound to candidate, review and
   predecessor. It does not authorize CAL.
4. Separate fresh CAL grant. The immutable grant must bind exact activation,
   candidate, generation head, executable digest, science binding, phase CAL and
   unique run ID, with synthetic_evidence_allowed=false. No grant-builder API
   automatically supplies operator authority.
5. `Registry.authorize` is a local precontact gate. Pass it **before** explicitly
   calling the adapter's metadata verification. Nothing in this migration itself
   invokes metadata or generation. Provider version, model identity, manifest/blob
   evidence and generation configuration remain the existing frozen binding;
   internal option honoring remains UNATTESTED.
6. Inject that verified exact `OllamaLiveTransport` instance into `LiveRun` with
   activation_sha256 and grant_sha256. It requires synthetic_only=false. Production
   requires the exact frozen Package class and the adapter's standard-library
   loopback HTTP path, not an injected connection factory. A grant does not allow
   changing the transport, model, schedule, seed, wire bytes or timeout.

No step above is authorized or performed by the implementation task.

## Executable Identity

The candidate binds the transitive static repository Python import closure rooted
at the versioned authority consumer, live entrypoint and reviewed adapter: 17
modules in this implementation. It includes the frozen kernel, contract, lock,
journal, scorer and imported normalization/semantic/contract dependencies. The
exact adapter SHA is additionally fixed to reviewed commit 9636b7e1, independently
of its commit-label field. Tests and documentation are review evidence, not
executable authority. Standard-library/runtime identity remains an environmental
dependency; it is not falsely represented as a repository source hash.

Every authorization rehashes the closure and verifies imported-module origins
and the import-time inventory. Source drift requires a new reviewed implementation
and future freeze, never an update of historical hashes. Historical activations
are validated against their own serialized bindings rather than claiming their
old executable bytes must equal a later version.
All 107 existing protected artifacts are carried unchanged in future candidates;
the original frozen manifest, candidate and six blocked-run files are additionally
checked as immutable predecessor evidence. No historical hash is rebound.

## Run And Resume

RUN_RESERVED is an append-only transition binding the ID to its current activation
and grant before directory creation. IDs cannot be reused in a different directory
or after failed initialization. The blocked historical ID and every existing
legacy run directory are explicitly excluded. A crash after reservation consumes
the ID; manual clearing/reuse is not supported.

Collection holds the frozen per-run lock and the registry lock across authority
verification, START, the single transport attempt and its governed outcome.
Reconstruction uses the unchanged frozen replay. Resume requires the same
activation/grant/reservation and a verified original checkpoint before collection.
Caught integrity/control-flow exceptions remain terminal and persisted; the new
entrypoint does not relax the frozen omission or failure-receipt rules.
Checkpoint bindings also seal the activation/grant/generation authority digest.
Truthful adapter metadata receipts are preserved in write-once content-addressed
`provider_metadata` files in each future run. Fresh resume metadata can be retained
separately without rewriting RUN_CREATED or claiming sampling options were honored.

## Trust And Limitations

This is local operator-controlled artifact authority, not cryptographic identity
attestation of the human operator or reviewer. Review/authorization artifacts
must come from their separately authorized actions. Possession of arbitrary
filesystem-write or Python-monkeypatch access is outside this trust model; neither
this nor the legacy laboratory claims tamper-proof storage against such access.
Write-once APIs do not provide external anti-rollback hardware for deleted history.
The supported v4 path rejects stale authority; this task does not disable or
rewrite the protected legacy Python API.

## Offline Validation

`python -B tools/g_cal1_authority_v2_tests.py` constructs explicitly test-only
registries outside the repository, uses mocked HTTP and denies sockets/process
launches. Its local test package is read-only and science-equivalent to the frozen
package; production explicitly rejects that class. Simulated activation/review/
grant records are fixture data, not real operator/reviewer actions. Full mocked
run reports are marked MOCKED_LIVE_BOUNDARY_TEST with zero provider calls and zero
scientific observations. The existing reviewed transport suite remains unchanged.

## Independent Review Handoff

Review only the additive implementation commit against base
`9636b7e1fb1f5af05cb27ed29dfa6c9f5c63869c`, this document and
`preexecution/versioned_authority_v2/IMPLEMENTATION_VALIDATION_REPORT.json`.
Use Sol 6.1, with local/mock tests only. This task has prepared the packet; it has
not invoked a reviewer or claimed independent approval.

Preserve the existing two byte authorities: committed new source bytes and the
107 frozen runtime/package bytes. Do not normalize historical LF/CRLF differences
or infer scientific mutation from an already-reconciled storage representation.
The implementation report binds external full regression assertions, raw test
reports and three preserved external driver-setup failures. Those failures concern
temporary-path aliases and Windows local-process audit handling, not a product
finding; they must not be silently omitted or counted as successful checks.

A review PASS would not prepare or activate a replacement freeze and would not
authorize CAL. Candidate preparation, freeze review, explicit activation, and a
fresh activation-bound CAL authorization remain subsequent separate actions.
