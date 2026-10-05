# G-CAL1 Live Ollama Transport Implementation

## Task ID

TASK-GCAL1-LIVE-TRANSPORT

## Objective

Implement the smallest reusable injectable live Ollama transport for the frozen
G-CAL1 laboratory. This task implements plumbing only. It does not authorize
G-CAL1 execution, provider metadata contact, a freeze change, or production
integration. Claude/Grok implementation/review usage is explicitly authorized.

## Current Checkpoint / Base Expectations

Base commit: 4fed0bae52e2e0d29ef023c89d8a3945fd535336.
Implementation branch: codex/gcal1-live-transport.
The existing seven untracked G-EXTRACT1 corpus artifacts MUST remain untracked
and byte-identical. Do not demand a globally clean checkout or stage these files.
The existing PRECONTACT_BLOCKED G-CAL1 attempt is historical evidence, not a run
to resume. Do not change or reuse its authorization.

## Files / Subsystems in Scope

Add only:
- tools/g_cal1_ollama_transport.py
- tools/g_cal1_ollama_transport_tests.py
- docs/g_cal1_ollama_transport.md

The task file is supplied by the orchestrator and must also be committed.
FINAL_HANDOFF.md and immutable review/test evidence will be supplied separately
after review. Do not create or overwrite them during implementation.

## Protected Files / Artifacts

Every existing file is protected, including all G-CAL1, G-EXTRACT1 and G-ROUTE4
science, corpus, gold, requests, schedules, seeds, diagnostics, scorers, gates,
interpretation, frozen source, activation/pointer and historical evidence.
Do not change the pipeline infrastructure or its persistent configuration.

## Required Behavior

Read tools/g_cal1_lab.py, g_extract1_runner.py and g_extract1_journal.py first.
The actual interface is transport(request_bytes, schedule_row), passed as the
transport argument of Run.perform(row, transport).

Expose a callable OllamaLiveTransport with synthetic_only = False. Constructor
must not make provider contact. Explicit metadata verification must precede
live generation. Accept a frozen provider binding and immutable schedule; bind
every call to its exact row, call_id, request_sha256, model, seed and config.
Do not use the current active freeze as adapter-test authority.

Use the existing result contract:
- success: raw_output (str), provider_truncated (bool), receipt (plain dict);
- failure: failure = timeout/error/missing/unreceipted, receipt according to
  frozen failure_event. Valid receipts bind call_id, request_sha256 and
  failure_kind. Do not invent new lifecycle events.

Receipts may contain only truthful provider/runtime evidence. Preserve exact
request and raw HTTP response bytes or lossless encodings/digests. Do not use
thinking as a substitute for an absent response. No answer cleanup or repair.
Missing, malformed, wrong-model and provider-error envelopes cannot become
successful responses. Truncation must be derived from truthful provider fields;
do not silently assume untruncated when the signal is unusable/unknown.

No retries, repair calls, fallback, redirect following, request mutation,
replacement seeds, prompt transformation, parallel generation or conversational
carryover. Submit the original wire bytes, not reserialized JSON. A fresh
connection/session per call is required. Reject repeated calls, wrong schedule
positions and any attempt to change model/options. Consume the attempt before
the first POST; exceptions or failure must not permit retry. Preserve original
KeyboardInterrupt/SystemExit/other BaseException propagation; don't fabricate
provider receipts for process-control exceptions.

Use fixed loopback Ollama endpoint http://127.0.0.1:11434. Prefer stdlib HTTP
without proxies, retries or redirects. Permit an injectable HTTP connection
factory solely for offline tests. Metadata verification must match the frozen
provider version, installed model manifest digest and model blob identity.
If local manifest/blob references are inspected, say exactly what was checked;
do not falsely claim the multi-GB blob content was rehashed if it wasn't.

Verify request configuration against the frozen configuration, including all
options, seed, stream=false, think=false and lack of history. The binding retains
retry_limit=0, repair_calls=0, fallback=false, fresh_session_per_call=true.
Internal sampling-option honoring remains UNATTESTED; accepted options do not
prove provider-internal behavior. No automatic model loading or model pulling.

Keep the adapter experiment-neutral where practical, but don't add new runtime
abstractions or modify production Eidolon. Caller still needs a future reviewed
freeze and separately authorized run; the adapter grants no collection authority.

## Required Tests

All tests must be NO-PROVIDER: deny real sockets and use scripted/mocked HTTP
connections. Never contact Ollama, including version/tags metadata endpoints.
Test success, exact byte preservation, raw output preservation, call/request
receipt identity, fresh connections and one POST maximum per attempted call.

Adversarial vectors: malformed JSON/root/envelope/field types, missing response,
empty response, timeout, provider HTTP/error envelope, call_id mismatch, request
hash mismatch, truncation, accidental synthetic transport, retry, fallback,
request mutation, seed mutation, wrong model/version/config, failure without
usable receipt, and process-control exceptions.

Integration must exercise the ACTUAL frozen g_cal1_lab.Run in mechanical=False
mode with THIS adapter and mocked provider I/O. Use isolated temporary copies of
the authority/candidate namespace, a test-only package exposing the frozen
required structure and event catalog, and an explicit temporary test grant.
Never use, mutate, copy authority from, or claim execution authority via the
real current freeze/activation/blocked-run grant. No real scientific observation
may result. Prove missing/wrong authority rejects before transport, while the
temporary mocked integration passes the actual live authority/transport boundary
and journaling/scoring path. No existing protected source needs modification.

Tests must work in a detached review worktree without the seven untracked
corpus artifacts; do not import or instantiate the full primary Package merely
to obtain runtime authority. Use committed scientific data read-only as needed.

```powershell
python -B -X utf8 tools/g_cal1_ollama_transport_tests.py
if ($LASTEXITCODE -ne 0) { throw 'Offline transport tests failed.' }
```

## Forbidden Changes

No real provider/model/metadata calls. No second experimental run. No freeze
candidate, activation, authorization in the actual experiment, execution,
scientific mutation, rescore, threshold changes, production changes, push,
merge, deployment, autonomy or belief effects. Do not alter any existing file.

## Expected Deliverable

One implementation commit, the adapter, adversarial offline tests, interface
documentation and a concise implementation report with actual test counts,
zero-Ollama-contact evidence and any limitations. Scope limited to four files.
Use apply_patch for manual code edits. Stage explicit files only.

## Stop Conditions

Stop on any protected-byte change, real provider contact, test failure,
scientific ambiguity, unmet contract, or need to broaden scope. Preserve failure
evidence. Do not hide or bypass failures to obtain a favorable review.
