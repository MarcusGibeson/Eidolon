# G-CAL1 Live Ollama Transport

Source: `tools/g_cal1_ollama_transport.py` (`g-cal1.ollama-live-transport.v1`).
Tests: `tools/g_cal1_ollama_transport_tests.py` (NO-PROVIDER).

This is plumbing only. The adapter does not authorize G-CAL1 execution, provider
metadata contact, a freeze change, or production integration. Importing or
constructing it contacts nothing. A live run still requires a future reviewed
active freeze and a separately authorized CAL grant accepted by
`g_cal1_lab.authority()`; the adapter itself grants no collection authority.

## Interface

```python
transport = OllamaLiveTransport(provider_binding, schedule, *, timeout_seconds,
                                start_position=1, connection_factory=None)
provider_receipts = transport.verify_metadata()   # explicit, once, before generation
run = Run(package, directory, run_id, mechanical=False, activation=...,
          authorization=..., provider_receipts=provider_receipts)
run.perform(row, transport)                       # calls transport(request_bytes, schedule_row)
```

- `synthetic_only = False`, so the adapter passes `transport_boundary` only in
  live mode. A mechanical `Run` rejects it before START.
- `provider_binding` has the shape of the frozen candidate `provider_binding`.
  It must be `ollama`. It must name a `provider_version` and list `models`, each
  with `model`, `manifest_digest` and `blob_sha256`. Its `generation_configuration`
  must retain `stream=false`, `think=false`, `fallback=false`, `retry_limit=0`,
  `repair_calls=0` and `fresh_session_per_call=true`. It must not claim
  provider-attested option honoring.
- `schedule` is the immutable frozen schedule. Both inputs are deep-copied as
  plain JSON at construction, and the copies are re-checked on every call.
- `timeout_seconds` is required. No frozen G-CAL1 timeout exists, so a future
  freeze must fix this value. It applies to each blocking socket operation, not
  to the total wall time of the call.
- `start_position` is for resuming from a verified checkpoint in a new process.
  The caller derives it from the verified journal (`len(run.attempted) + 1`).
  The adapter cannot prove that earlier positions were attempted. It records the
  value in every receipt and never serves an earlier position.
- `connection_factory(host, port, timeout)` exists solely for offline tests.
  When it is supplied, every receipt records
  `io = INJECTED_CONNECTION_FACTORY_OFFLINE_TEST_ONLY`. The default is
  `http.client.HTTPConnection('127.0.0.1', 11434, timeout=...)`, recorded as
  `STDLIB_HTTP_CLIENT_LOOPBACK`.

## Metadata verification (`verify_metadata`)

Exactly three kinds of request are made, each on a fresh connection that is
closed afterwards:

1. `GET /api/version`: `version` must equal the frozen `provider_version`.
2. `GET /api/tags`: each frozen model name must be listed exactly once, and its
   `digest` (the installed manifest digest) must equal `manifest_digest`.
3. `POST /api/show` with body `{"model":<name>}`: legacy bindings require one
   exact primary FROM reference. Explicit component bindings require the exact
   model/projector set and manifest role proof described below.

The multi-GB blob content is **not rehashed**. Explicit component bindings read
and hash the local manifest and verify its layer roles against the provider's
FROM set; legacy single-component bindings retain reference-only verification.
Receipts record `blob_content_rehashed: false`.

The adapter never issues pull, create, copy, delete, preload or `keep_alive`
requests. Any mismatch or exception disables the adapter permanently.
`KeyboardInterrupt`, `SystemExit` and other `BaseException`s propagate unchanged.

The returned dict carries the fields that `authority()` compares: `provider`,
`provider_version`, `models` and `generation_configuration`.
- `models` echoes the frozen entries after their provider-observable fields
  matched. Non-observable fields such as `tier` are not provider-attested.
- `generation_configuration` is the frozen configuration, not a provider report.
- It also includes the raw observation bodies (base64 and sha256).
- `internal_option_honoring: UNATTESTED`: accepted options do not prove
  provider-internal sampling behavior.

## Per-call contract (`transport(request_bytes, schedule_row)`)

Before any POST:
- the adapter must not be disabled, metadata must already be verified, and only
  one call may be in flight (a concurrent call is rejected, not queued);
- `schedule_row` must equal the next frozen position exactly; repeated, skipped
  and earlier positions are rejected;
- `request_bytes` must be `bytes` whose sha256 equals the row's `request_sha256`;
- the request must parse as strict JSON (UTF-8, no duplicate keys, no
  non-finite numbers) with exactly the keys
  `model, system, prompt, stream, think, options`. There is no
  `context`/`messages`/`images`/`raw`/`template`/`format`/`keep_alive`, so no
  history or conversational carryover;
- `model` must equal the row model, `stream` and `think` must be `false`, and
  `options` must equal the frozen sampling options plus the row `seed`
  (compared as canonical bytes, so types are exact).

Any violation raises `TransportContractError` and disables the adapter.
`Run.perform` records that as `unreceipted`, which gives
`PROVIDER_FAILURE_WITHOUT_RECEIPT`. The attempt is consumed before the first
POST, so nothing re-enables it.

The POST sends the original request object (never reserialized) to
`/api/generate`. The only headers are `Content-Type: application/json` and
`Connection: close`, plus http.client's own `Host`, `Accept-Encoding: identity`
and `Content-Length`. The call uses a fresh connection, follows no redirects,
uses no proxy, and makes no retry, repair or fallback.

## Results

Success, which requires all of: HTTP 200; no non-identity `Content-Encoding`;
a strict-JSON object; no `error` key; `model` equal to the row model;
`done: true`; `response` a UTF-8-encodable string; `thinking` absent or empty;
and `done_reason` in `{stop, length}`.

```
{'raw_output': <response exactly>, 'provider_truncated': done_reason == 'length', 'receipt': {...}}
```

`raw_output` is never cleaned, repaired or substituted. Thinking text is never
used as an answer. Truncation comes only from `done_reason`. A missing, unknown
or non-string `done_reason` is a failure; the adapter never assumes the output
was untruncated.

Failures (`receipt` binds `call_id`, `request_sha256`, `failure_kind`, plus
`failure_reason`):

| kind | causes | frozen event |
|---|---|---|
| `timeout` | `TimeoutError` at connect, send, response or read | `PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT` |
| `error` | other `OSError`/`HTTPException`; non-200 status (including redirects); unsupported encoding; malformed JSON/root; `error` envelope; wrong or missing model; `done` not `true`; non-string response; non-encodable response; thinking returned; unusable truncation signal | `PROVIDER_ERROR_WITH_FAILURE_RECEIPT` |
| `missing` | `response` absent or `null` in an otherwise valid envelope | `MISSING_RESPONSE_WITH_FAILURE_RECEIPT` |

Other exceptions propagate, and `Run` maps them to `unreceipted`
(`PROVIDER_FAILURE_WITHOUT_RECEIPT`). Process-control exceptions propagate
unchanged with no receipt; `Run` then retains
`SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT`. No new lifecycle events exist.

An empty-string `response` in a complete envelope is preserved as `raw_output`
`""` and scored by the frozen scorer, which already defines empty output. It is
not reclassified as missing. Reviewers should confirm this reading.

Receipt evidence includes:
- schema and adapter versions, and `synthetic_only: false`;
- schedule position and start position, seed and model;
- the verified provider version and the sha256 of the metadata receipts;
- the endpoint and method;
- request bytes (base64 and length);
- POST transmission stage (`NOT_STARTED`/`STARTED`/`COMPLETED`) and connection
  evidence;
- HTTP status, reason and all response headers;
- the response entity body (base64, sha256 and length). This is the body after
  HTTP/1.1 transfer framing; the status line and headers are recorded parsed,
  not as wire bytes;
- selected scalar provider fields and the truncation basis.

Interrupted response reads. Once `getresponse()` has returned, a timeout or
transport error is still a `timeout`/`error` failure with the same frozen event,
and its receipt keeps exactly what was observed:
- `failure_stage` is `response_headers` or `response_body_read`. Before
  `getresponse()` returns, the stages stay `connect`/`send`/`response` with the
  original receipt shape;
- the HTTP status and reason; the headers if they were returned;
- once body reading started, the entity body made of every byte already returned
  (it may be empty). The body is read incrementally with `HTTPResponse.read1`,
  which does at most one socket read per call, so bytes received before a later
  timeout or reset are kept;
- an `IncompleteRead.partial` is stored losslessly in `exception_partial_*`
  fields. It is not spliced into the body, because `http.client` may put
  chunk-framing bytes there;
- an EOF before the declared `Content-Length` (`http.client` returns `b''`
  here, not an exception) is an `error` with
  `eof_before_declared_content_length` and `content_length_remaining`;
- `response_capture.state` is `INTERRUPTED_INCOMPLETE`. The exception type,
  message and errno are recorded.
Unavailable metadata and bytes are left out; nothing is filled in. Partial bytes
are never classified or parsed as a response.

## Limitations

- Offline tests only. No real provider behavior has been observed by this task.
  The Ollama envelope fields relied on (`model`, `response`, `done`,
  `done_reason`, `thinking`, `error`, tags `digest`, show `modelfile`) are
  assumptions to confirm during a separately authorized metadata check.
- Ollama may load the model on demand while serving the single generate POST.
  The adapter issues no explicit load request.
- `timeout_seconds` and its per-operation scope are not part of any freeze.
- Blob content is not rehashed (see above).
- Integration tests use a test-only package and a temporary authority namespace
  carrying a `test_only` binding marker. The real activation, pointer and CAL
  grant are never parsed, copied or used as authority; they are only hashed,
  together with the rest of the G-CAL1 tree, to prove they are unchanged. The
  committed candidate is read only to get the frozen `provider_binding` values.
# Prospective Multicomponent Metadata Repair

This repair is implementation only and awaits independent Sol review. It creates
no freeze candidate, activation, CAL grant, reservation, or execution authority.
The old candidate/activation and the blocked intent
`G-CAL1-CAL-20261006T063011Z-706d0b9fa5764a64` remain unchanged. That intent and grant
must not be reused. Existing active authority pins older executable hashes and
cannot authorize this repaired transport.

The preserved `/api/show` response contains two FROM directives. The exact local
manifest SHA-256 is `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`,
matching the recorded `/api/tags` digest. Its layer media types identify:

| Role | Component SHA-256 |
| --- | --- |
| model | `f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d` |
| projector | `ac3714bfdddeca31351f2752bf1a63f266f4df87c0b68c895e44945ca704448e` |

The remaining layers are license and parameters; the manifest also identifies a
Docker config object. No other executable model component is present. Blob content
was not rehashed; component identities/roles are manifest-derived, not guessed
from FROM order, model name, or model_info. Raw manifest and preserved HTTP response
bytes are retained in `preexecution/multicomponent_metadata_repair/provider_evidence`.

Transport version v2 adds a prospective per-model `components` field, with exact
entries `{role, sha256}`. The versioned semantics are
`g-cal1.ollama-model-components.v1`; binding order is model first, then optional
projector. Duplicate roles/hashes, unknown roles, invalid hashes and a primary
component inconsistent with the existing `blob_sha256` are rejected. Legacy input
without components still requires exactly one FROM reference and does not imply
projector coverage.

For explicit components the adapter requires all of the following:

1. Exact existing provider/version/name and `/api/tags` manifest digest.
2. Exact raw local manifest digest at the default local Ollama registry path.
3. Complete model/projector composition and roles matching that manifest.
4. Exact FROM component set, without duplicates, malformed references or extras.

FROM order is not role authority and may vary. Each directive must contain one
complete, unquoted, whitespace-free blob path/reference; unsupported syntax fails
closed. The local manifest supports only schemaVersion 2 and declared model,
projector and recognized non-executable metadata layer types. Unknown layer types
fail closed. This version does not infer alternate OLLAMA_MODELS locations or pull
missing manifests. A missing/inconsistent local manifest blocks verification.

Metadata receipts v2 preserve every verified component, its role source, manifest
bytes/hash/path and the actual FROM order. They do not claim blob-content rehashing
or internal sampling-option honoring. Internal option honoring remains UNATTESTED.
Generation/wire/session/retry behavior is unchanged. Tests use scripted HTTP and
temporary manifest files, with socket contact denied.

`component_provider_binding(binding, manifest_bytes)` is an offline prospective
binding constructor, not a candidate or authority action. A future independently
reviewed replacement freeze must bind the new executable inventory and explicit
component binding; the old candidate must never be rewritten to cover a projector.
