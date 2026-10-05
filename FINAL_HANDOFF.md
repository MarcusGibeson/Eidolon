# G-CAL1 Live Ollama Transport Handoff

Status: IMPLEMENTED_AND_OFFLINE_TESTED / GROK_REVIEW_INCOMPLETE.
This is not a reviewed execution adapter or execution-readiness certification.
No freeze candidate, activation, experimental authorization, merge or push was
created by this task.

## Commits and Scope

- Branch: `codex/gcal1-live-transport`.
- Base: `4fed0bae52e2e0d29ef023c89d8a3945fd535336`.
- Implementation: `23cde6bf28034dbc262bb4c4f68acd3a94b7ad49`.
- Implementation adds exactly four files:
  `.ai_pipeline/tasks/TASK-GCAL1-LIVE-TRANSPORT.md`,
  `tools/g_cal1_ollama_transport.py`,
  `tools/g_cal1_ollama_transport_tests.py`, and
  `docs/g_cal1_ollama_transport.md`.
- This handoff is a fifth new file, committed separately. Existing tracked
  source, science and historical evidence were not edited.

The generic pipeline checkout at `C:/Users/marcu/Eidolon` uses an older
infrastructure base that lacks G-CAL1. Implementation therefore used the actual
G-CAL1 checkout at `C:/Users/marcu/Eidolon-g4adj`, an isolated branch, and the
existing pipeline process logger with explicitly authorized Claude/Grok CLIs.
The full unmodified dispatcher was not run against its incompatible base.
The configured Claude path had become stale; installed Claude 2.1.286 was
located and verified without editing the pipeline configuration. Grok 1.0.41
was used for the attempted independent review.

## Adapter Interface

`OllamaLiveTransport(provider_binding, schedule, timeout_seconds=...,
start_position=1, connection_factory=None)` exposes `synthetic_only = False`.
Construction and import contact nothing. `verify_metadata()` explicitly checks
provider version, exact installed model manifest identity and the model blob
reference before generation. Its returned evidence supplies the provider receipt
fields required by the frozen live authority boundary.

Inject the instance as `Run.perform(row, transport)`. It accepts the original
wire `bytes` and copied frozen schedule row. It verifies call order, call ID,
request hash, exact request keys, model, options and scheduled seed before POST.
It sends those same bytes once to loopback Ollama `/api/generate`, using a fresh
connection, no request history, no retries, no redirects, no proxy, no repair
and no fallback. An attempt is consumed before transmission.

Success returns exactly `raw_output`, `provider_truncated`, and `receipt`.
The raw response is not cleaned or substituted. `done_reason=length` means
truncated; `stop` means untruncated. Unknown/missing truncation signals fail
closed. Timeout/error/missing results use the existing frozen failure kinds and
bind `call_id`, `request_sha256`, and `failure_kind`. Other exceptions use the
existing runner governance; control-flow exceptions propagate unchanged with
no fabricated receipt.

The blob content is not rehashed: identity is a provider-reported blob reference.
Sampling-option honoring remains UNATTESTED. Frozen configuration fields in
receipts are runtime declarations, not provider attestations. No real Ollama
behavior was verified in this task. The explicitly required timeout and its
per-socket-operation scope need binding in a future reviewed freeze. Resume
`start_position` must come from an already verified journal, not guesswork.

See `docs/g_cal1_ollama_transport.md` for exact interface and receipt limitations.

## Offline Validation

Required command:

```powershell
python -B -X utf8 tools/g_cal1_ollama_transport_tests.py
if ($LASTEXITCODE -ne 0) { throw 'Offline transport tests failed.' }
```

Independent parent replay in the original byte-preserved checkout:
524 passed, 0 failed, exit code 0. Its no-contact audit hook denies sockets and
subprocesses before tests; after the denial self-test, attempted socket/process
events were 0. Every HTTP response was scripted.

Coverage includes malformed envelopes/responses, missing/empty responses,
timeouts and provider errors; wrong call IDs/hashes; truncation; accidental
synthetic transport; retry/fallback/request/seed/model/version/config mutation;
fresh connections; receipt identity; process-control propagation; and immutable
binding copies. Counts include 179 adversarial checks, 92 call-binding checks,
78 retry checks and 15 process-control checks.

Actual frozen `g_cal1_lab.Run` integration runs with `mechanical=False` using
mocked HTTP, a test-only package binding and an isolated temporary authority
namespace. It exercises rejection before contact, START/COMPLETE/FAILURE,
scoring, terminal failures, checkpoint, restart, verified resume and replay.
Neither the current activation nor the historical blocked grant supplies test
authority. Reading frozen provider-binding values does not grant authority.

Claude additionally reported 524/0 in a detached checkout without the seven
untracked artifacts when checked out with `core.autocrlf=false`. This is a
producer report, not a substitute for the unfinished independent Grok review.
The existing pipeline infrastructure tests also passed 22/22.

## Independent Grok Review: No Verdict

Grok reviewed exact implementation commit `23cde6bf` in an isolated sparse
detached checkout. The review process exited 1 after reaching its configured
20-turn limit. It did NOT return `PIPELINE_VERDICT: PASS`, `REVISE`, or `BLOCKED`.
Consequently no favorable review verdict is claimed.

The review test command exited 1 during test-package initialization, before the
adapter checks: global `core.autocrlf=true` converted an unchanged historical
dependency to CRLF in the new checkout. The pinned file is
`experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json`:

- Expected SHA-256: `41c04df59d3ae465dc1094c5e15562fd7ea52c7f20e9d83f7f7ade9d9acbddd5`.
- Temporary checkout SHA-256: `e052802f7cdff3516518ed40231437c973ab3b09ea559580408028e878d2c293`.

The parent independently reproduced this hash difference. The original
checkout still has the pinned bytes and passes. The digest check was not
weakened, the failed review was preserved, and no automatic second Grok request
or implementation workaround was made.

Next review should use a new byte-preserving detached checkout with a per-command
`core.autocrlf=false` setting and sufficient bounded review turns. Do not change
global configuration or rewrite frozen artifacts. Continue read-only review of
the same implementation commit, run the offline command, and obtain an actual
Grok verdict before claiming this task complete. No Ollama check or experiment
is needed or authorized by that review.

## Preservation and Governance

The 107-file starting digest baseline comprises the 99 candidate-bound files,
the two existing G-CAL1 activation/pointer files and the six files of the
historical PRECONTACT_BLOCKED run. Reverification found 107/107 unchanged.
All seven unrelated untracked G-EXTRACT1 corpus artifacts are included in the
baseline and remain byte-identical and untracked.

- Ollama metadata contacts: 0.
- G-CAL1 provider/model generation calls: 0.
- New real runs or experimental observations: 0.
- Current freeze/candidate/activation changed or used as test authority: false.
- Corpus, gold, request, schedule, seed, scorer, diagnostic and interpretation
  changes: 0.
- G-EXTRACT1 remains closed valid negative; G-ROUTE4 remains closed failed.
- Autonomy: false. Belief effects: none.
- Claude/Grok cloud development/review usage was explicitly authorized and did
  occur; the zero-call statements refer to Ollama and experiment execution.

## Hashes and Local Evidence

Implementation working-tree SHA-256:

| File | SHA-256 |
| --- | --- |
| `tools/g_cal1_ollama_transport.py` | `1a939f2804652c1ea8085c71a8e0e91d2cb58a37242a4029771a2f8eed71d1cb` |
| `tools/g_cal1_ollama_transport_tests.py` | `f0463fbabdb527da2acf5ef1e90722cbeb2a5070d2a416ae72907b62cc12657c` |
| `docs/g_cal1_ollama_transport.md` | `ab8c8f0bf7cbf3ff9d8c094d7af994da6fee8312ae95c51973756ebb02d0ccaf` |
| `.ai_pipeline/tasks/TASK-GCAL1-LIVE-TRANSPORT.md` | `e0aeb5af3900ca28fc275ce79001f9263930708864722833f8be22cfe773955d` |

Preserved local evidence directory:
`C:/Users/marcu/G-CAL1-live-transport-20261005-b458ca0e/`.

| Evidence | SHA-256 |
| --- | --- |
| `parent-offline-tests.txt` | `5e7de3217d1146124a86e6c37a07c48435e7314740f339c9175fe4b3bb8344c7` |
| `claude-implementation.txt` | `ebaca8cfd94339fbbc043a710606e9e31f778c1253c35760e448a2329b491c36` |
| `grok-review.txt` | `02ae32921f776afd2fafd815e5e90df19edcb3f9b06e39d7326241192044c756` |
| `PROTECTED_BASELINE.json` | `a5755976a24ab7c11a676f53c79140eeebe217387b61ebd3186ee80420aa84cd` |

Do not activate or execute G-CAL1 from this handoff.
