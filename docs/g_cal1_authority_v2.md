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

The bounded post-review repair adds `g_cal1_source_loader_v1.py`. The supported
authority entry is now its source-only bootstrap, not ordinary imports of these
two modules. The original implementation/review evidence remains historical.

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
   preparation. `Registry.candidate(timeout_seconds=..., provider_binding=...)`
   only returns an object; future production preparation now requires the explicit
   component binding described below.
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
   Obtain Registry, Package, LiveRun and OllamaLiveTransport from one verified
   runtime graph as described below; never mix ordinary-import or other-graph
   classes with it.
6. Inject that verified exact `OllamaLiveTransport` instance into `LiveRun` with
   activation_sha256 and grant_sha256. It requires synthetic_only=false. Production
   requires the exact frozen Package class and the adapter's standard-library
   loopback HTTP path, not an injected connection factory. A grant does not allow
   changing the transport, model, schedule, seed, wire bytes or timeout.

No step above is authorized or performed by the implementation task.

## Executable Identity

The candidate binds the transitive static repository Python import closure rooted
at the versioned authority consumer, live entrypoint, reviewed adapter and trusted
source loader: **18 modules after repair, previously 17**. The loader is explicitly
authority-critical because it determines which source bytes become executable
code. It includes the frozen kernel, contract, lock,
journal, scorer and imported normalization/semantic/contract dependencies. The
exact adapter SHA is additionally fixed to reviewed commit 9636b7e1, independently
of its commit-label field. Tests and documentation are review evidence, not
executable authority. Standard-library/runtime identity remains an environmental
dependency; it is not falsely represented as a repository source hash.

Every authorization rehashes the closure and requires ownership by the verified
private module graph. Source drift requires a new reviewed implementation
and future freeze, never an update of historical hashes. Historical activations
are validated against their own serialized bindings rather than claiming their
old executable bytes must equal a later version.
All 107 existing protected artifacts are carried unchanged in future candidates;
the original frozen manifest, candidate and six blocked-run files are additionally
checked as immutable predecessor evidence. No historical hash is rebound.

### Source-Only Bootstrap

The trusted first executable step is the explicitly selected trusted CPython
executable starting directly with **-I -S**, then CPython main-script execution
of the explicit reviewed loader source path. Only CPython and its interpreter-owned
standard library precede that loader. A supervised host may explicitly verify,
read and compile those loader bytes only within that same clean launch profile.
**Do not bootstrap by ordinary importing a cached loader**,
sys.path order, cache deletion, or -B. The trusted CPython/standard-library runtime
and the independently reviewed loader source are the bootstrap trust roots.

The loader validates its executing module code against compilation of its bound
source, snapshots all 18 canonical source paths, verifies every hash and the full
dependency closure, then compiles those exact immutable buffers. Its import hook
resolves repository dependencies only through that private graph, not sys.path,
sys.modules, importlib loaders or pyc files. Existing global/historical modules
are left untouched. Ordinary-import authority consumers lack the owned execution
context and fail closed, even when their source/path hashes are correct.

Its CLI accepts a separately reviewed source-inventory file and its exact SHA-256:

```text
<trusted-CPython-executable> -I -S <absolute-path-to-g_cal1_source_loader_v1.py> --inventory-file <reviewed-inventory.json> --inventory-sha256 <reviewed-digest>
```

This command only loads and attests code. It creates no candidate, activation,
grant or run and calls no provider. A supervised host using the same verified
bootstrap obtains classes from `VERIFIED_RUNTIME.module(...)`. An interactive
host may retain the graph; this is not an automatic execution loop. Future real
use still requires all distinct review/activation/grant actions above and the
same fixed provider and scientific configuration.

The initial flags are the startup boundary: -I ignores ambient PYTHONPATH,
PYTHONHOME, user-site and working-directory import precedence; -S prevents
automatic site/sitecustomize/usercustomize execution. Starting normally and then
re-executing an isolated interpreter is NOT a supported bootstrap. In-process
guards check CPython, `sys.flags.isolated == 1` and `sys.flags.no_site == 1`
before direct CLI loading, every VerifiedRuntime creation and source verification.
They reject unsafe authority but cannot undo hooks already executed during an
unsafe process startup. -B may prevent cache writes, not startup execution or
cache reads. It is optional housekeeping, never authority.

Future v2 candidates require `launch_profile` (g-cal1.clean-launch.v1): exact
CPython identity label, literal Boolean isolated_required/no_site_required=true,
the canonical tools/g_cal1_source_loader_v1.py entrypoint and its bound SHA-256,
authority-v2 version and source-loader version. Exact type validation rejects
integer Boolean substitutes. The execution digest is compact canonical JSON of
`{executable_sources: ..., launch_profile: ...}`, so review, activation and CAL
grant bindings seal both. Existing v1 artifacts remain unchanged; no replacement
authority has been created. The loader is already in the 18-source inventory,
so no new launcher or executable dependency is added by this bootstrap repair.

The CAL-grant validator now checks the complete exact field/type topology before
comparing values. `synthetic_evidence_allowed` must have Python type bool and be
literal False; numeric/string/container substitutes reject. Other declared grant
fields, including nested science binding and namespace Boolean, are also typed.
No unrelated candidate/review/activation schema was redesigned by this repair.

### Interpreter Library Import Boundary

The subsequent supervised repair removes ambient import-path authority for
standard-library dependencies. Before ordinary source imports, the loader uses
CPython's initialized builtin/frozen import machinery and frozen OS path helpers
to establish the interpreter library from `sys._stdlib_dir`, checked against
`sys.base_prefix`, plus its native extension directory. Unsupported interpreter
layouts fail closed. Site-packages, dist-packages and other resolved origins are
excluded even when present on sys.path.

During standard-library imports, an import-lock-scoped resolver uses only these
roots and builtin/frozen modules. It constrains transitive imports too and restores
the ambient import environment afterward. Newly loaded Python library code is
compiled from trusted-root source bytes rather than external bytecode caches.
Preloaded standard-library objects require module/spec identity and trusted
resolved origins; external Python function origins are rejected. Legitimate
library identities are retained for compatibility with frozen exception types.
Unchanged module identity signatures may be reused within that boundary; mutable
CPython internals, arbitrary monkeypatching and writes inside trusted interpreter
roots remain outside the declared runtime trust model.

Repository modules still come only from the private verified source graph. The
executable inventory remains 18 sources: only the bound loader hash changes in
this repair. No standard-library hash inventory or scientific refreeze is made.
The original failing external-copy probe and both interrupted Sol review records
remain immutable evidence. Mechanical validation is not independent approval.

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

`python -I -S -B tools/g_cal1_authority_v2_tests.py` constructs explicitly test-only
registries outside the repository, uses mocked HTTP and denies sockets/process
launches. Its local test package is read-only and science-equivalent to the frozen
package; production explicitly rejects that class. Simulated activation/review/
grant records are fixture data, not real operator/reviewer actions. Full mocked
run reports are marked MOCKED_LIVE_BOUNDARY_TEST with zero provider calls and zero
scientific observations. The existing reviewed transport suite remains unchanged.
The migration tests use the verified private graph, with only their HTTP factory
mocked. `python -I -S -B tools/g_cal1_source_loader_v1_tests.py` tests every dependency
hash, source/path drift, buffer-to-code correspondence, preloaded-module isolation,
and the exact Sol timestamp-valid pyc attack with an external cache prefix. -B is
used for test housekeeping only and is not credited as cache-read protection.

## Independent Review Handoff

For the mandatory post-repair review, inspect the single repair commit against
`9f3a30d05b75d6e9278ffe840404e830b918834d`, this document and the append-only
`preexecution/versioned_authority_v2/repair_01/REPAIR_VALIDATION_REPORT.json`.
The prior IMPLEMENTATION_VALIDATION_REPORT.json is unchanged historical evidence,
not certification of the repaired version.
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

### Clean-Startup Repair Handoff

The next bounded repair closes the demonstrated PYTHONPATH/sitecustomize startup
defect. Its additive report is `repair_03/REPAIR_VALIDATION_REPORT.json`; review
the repair against ee423980 without rewriting that commit or its failed bootstrap
packet. Both interrupted Sol stop records and the failed startup probe remain
historical evidence. Mechanical validation is not independent review approval.

The supported command now begins directly with the required -I -S profile.
No wrapper, normal-start/re-exec path, new executable source or automatic live
execution CLI is added. Test hosts explicitly add their fixture import directory
only after isolated startup; those ordinary imports never confer authority.
The private source graph and production class checks remain mandatory.

The closure assessment includes direct, transitive and conditional import nodes,
aliases, relative-import refusal and dynamic-loader sites. The G-EXTRACT1-only
`actual_reserve_profile` dynamic design-validator loader is not reachable from
G-CAL1: its sole caller is the reserve_replacements helper, the G-CAL1 Run does
not inherit the G-EXTRACT1 Run and imports neither helper, and G-CAL1 has no
reserve activation path. That exclusion is recorded explicitly, not counted
as a verified-source load. Read-only actual-package construction and all 80
request hashes provide additional live-path closure evidence without provider
contact or authority creation.
# Multicomponent Binding Extension (Pending Review)

The transport metadata repair prospectively extends each provider-model entry
with a typed `components` list, ordered model then optional projector. Existing
provider/version/model/manifest/primary blob/configuration values must project
exactly to the unchanged historical provider binding. Component roles are proved
by exact-digest local manifest layer media types; `/api/show` must expose exactly
the same blob set. This is not a scientific configuration change.

The candidate envelope remains `g-cal1.candidate.v2`. Future production candidate
preparation requires an explicitly supplied component-extended `provider_binding`;
there is no silent legacy fallback. This implementation task does not invoke that
preparation in production. Historical candidates continue to validate against
their original single-component binding and original transport source hash for
history replay only. Authorization still requires the complete source-only graph
to match the selected candidate, so the old active freeze rejects repaired code.

`reviewed_transport_commit` retains its original reviewed transport-lineage anchor;
it is not approval of the pending repair. Exact executable hashes, separate Sol
implementation review, future candidate-linked provenance/review evidence and
subsequent explicit activation are still mandatory. The component-aware transport
has a separate exact source pin; no branch label or historical commit label can
replace executable identity. Legacy bindings with repaired code are accepted only
inside explicitly test-only namespaces for historical regression fixtures, never
as a future production candidate.

The import closure remains 18 sources. Only the transport and authority resolver
executable hashes change; the frozen lab, manifest, loader, live entrypoint,
scientific contract, scorer and request rendering remain untouched. Production
authority artifacts and the stopped precontact attempt are preserved byte-exact.
The existing authority test now snapshots an already-existing production namespace
instead of assuming it is absent; no production authority is created in tests.
