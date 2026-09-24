# G-ROUTE3 qualification contract

Contract: `g-route3.qualification.v1` · implementation `tools/g_route3_qualification.py`

## Criteria, per task class × risk class × model tier

Qualification is decided on Corpus A alone, under the normalized transport contract, from 2 distinct
fixtures × 2 repeats = **4 observations per cell**.

| Verdict | Condition |
|---|---|
| `qualified` | exactly 2 distinct fixtures × 2 repeats, all complete; all 4 operationally accepted; all 4 pass the frozen evaluator; 0 false-clean; 0 infrastructure failures; 0 returned-model mismatches |
| `not_qualified` | evidence complete in exactly that shape, and any of the above fails |
| `insufficient_evidence` | any other shape (3 + 1, one fixture four times, five observations), or any infrastructure failure or model mismatch |

An infrastructure failure includes a coding-sandbox host failure. Only model-caused coding errors (bad JSON,
a syntax error, a whitelist denial, a timeout of the candidate) count as failed evidence. Any other sandbox
exception is charged to infrastructure and stops the run `incomplete`.

Operational acceptance uses `g-route3.operational-validator.v2`, and correctness uses `g-route3.semantics.v1`.
Both are the G-ROUTE1 checks except in two profiles:

- **conversation**: the disclosed two-line frame (Answer, and Actions taken written exactly as `none`);
- **coding**: `old` is compared ignoring trailing newlines.

A coding timeout counts against the model only if the unchanged source runs in time on the same host;
otherwise it is an infrastructure failure.

`insufficient_evidence` is never operationally qualified. There is no aggregate score, no global
leaderboard, and no qualification from structural validity, formatting or model size. A missing
observation cannot pass, and an empty cell is `insufficient_evidence`, never `qualified`.

## Sample size

Four observations is pilot scale, and the table says so on every cell. Each cell carries
`failure_rate_upper_95`, the one-sided exact binomial bound on its true failure rate. At 0 failures in 4
this is **0.527**. The budget of 288 calls for A and 144 for B was chosen so that both corpora could be
built to the derivability rule with two independent problems per cell. More repeats of the same problem
would tighten the bound without making it more representative, so distinct fixtures were preferred.

Corpus B is the real check. If pilot-scale qualification predicts nothing, Corpus B shows it.

## Table format

`QUALIFICATION_TABLE.json`, schema `g-route3.qualification-table.v1`:

- `source` — corpus A digest, gold A digest, Phase A run id, sealed Phase A score digest, thresholds digest,
  execution-freeze binding, and `phase_a_attempts`: every authorized Phase A attempt from the fixed
  authorization ledger, so a table cannot quietly come from the best of several attempts;
- `audit` — the independent audit of the Phase A results. It must read `READY` and is bound to an audit
  document by path and sha256. A bare statement is not an audit, and editing the document afterwards
  invalidates the table;
- `cells` — 72 rows with verdict, observation counts, semantic passes, false-cleans, infrastructure failures
  and the failure-rate bound;
- `routing_lookup` — for each `task|risk`, the qualified tiers in cost order;
- `corpus_b_consulted: false`, `immutable: true`, `evidence_scale: "pilot"`;
- `table_sha256` — digest of everything above.

`verify_table` recomputes the digest, confirms that the lookup is exactly what the cells imply, re-checks the
audit document's digest, and rejects any table not derived from Corpus A alone or lacking a `READY` audit.
Internal consistency is not enough. Phase B also checks the table against the sealed Phase A run, below.

## The hard A → table → B boundary

1. Phase A runs under its own numbered authorization:
   `Authorize G-ROUTE3 phase A execution <freeze digest> attempt <n>`, with n = 1 for the first attempt.

   - The run starts only through the launcher, `tools/g_route3_launch.py`. The launcher builds the Ollama
     provider itself and reads the operator's verbatim sentence. The authorized path refuses any other
     provider type and any override of the guarded root.
   - The authorization has an exact key set.
   - It is consumed by exclusive creation in the fixed ledger `authorization_ledger/`. This happens only
     once the run exists and holds its lease.
   - Another run under the same authorization is refused. The same run may resume only with its own run id,
     its own run root and `--resume`.
   - **Attempt policy:** attempt n+1 is authorized only if every earlier attempt ended incomplete, failed or
     cancelled. The first complete run is the result, so a best-of-N choice is impossible.
   - A stuck attempt can be closed only by an explicit abandon (`--abandon A --reason …`). Its reason is
     recorded.
   - Every attempt is disclosed in the table with its run root, outcome and reason.
2. Phase A is scored and sealed, and reaches five-view terminal agreement.
3. The Phase A results are audited independently.
4. `freeze_table` writes the table **once**. A second write with different content is refused.
5. Phase B requires, before any provider contact:
   - the table exists and verifies;
   - its cells equal the cells **re-derived from the sealed Phase A call records**, and also equal the sealed
     score;
   - the call records cover all 288 scheduled calls in order;
   - the sealed terminal receipt chains to the call records and to the score;
   - it names this Phase A run. That run appears in the authorization ledger at the same run root, and it is
     the only complete Phase A attempt. The table also discloses every Phase A attempt;
   - every call record agrees with the receipt on the synthetic flag. Each record of an authorized run also
     carries the provider's own raw body, and the envelope, model, output and request body are all consistent
     with it;
   - the unsealed run manifest also reads `complete`;
   - Phase A is `complete`, and, **according to the sealed receipt** (never the unsealed run manifest), it
     was not synthetic, ran under this execution freeze, and ran with today's guarded dependencies;
   - the table is bound to this execution freeze, and its corpus, gold and threshold digests match;
   - the audit document names the run and the score digest, and is not itself a frozen artifact;
   - a second authorization reads
     `Authorize G-ROUTE3 phase B execution <freeze digest> table <table digest> attempt <n>`, names the Phase
     A run, and is consumed in the ledger.

   An authorized Phase A run must also meet these conditions:

   - Every call record and the receipt carry its attempt number and authorization digest, and these match
     the ledger.
   - The hash-chained ledger agrees exactly with the run directories under the fixed run root.
   - The fixed endpoint and the model receipts were recorded and still verify.
   - The run's git anchor file matches its sealed receipt.

   **Threat model: an honest operator with tamper-evident records.** These checks stop cheap tampering:

   - a deleted or edited ledger entry;
   - a replayed sentence;
   - an unrecorded run;
   - a relabelled run;
   - a redirected endpoint.

   Local seals carry no secret. So the following are out of scope for the code, and are countered by the git
   anchor commits the launcher makes at each consumption and each completion:

   - a deliberate adversary who runs a fake model server;
   - a second checkout;
   - consistently rewriting sealed files and the anchor history.

   **Model output cannot crash collection.** Any exception in normalization, validation, evaluation or
   triggers is recorded as a failure of that output. Output that cannot be serialized is recorded without
   its parsed copy. Lone surrogates are replaced before sealing. So a malformed answer can never block Phase
   A from completing.

   **Interrupted finalization.** A run killed after its receipt was sealed is finished by `--resume`. An
   attempt that already holds every call record cannot be abandoned.

   Verifying the execution freeze does not depend on the table being absent. Absence is checked only when
   the freeze is *written*, so the freeze stays valid once Phase A has produced a table.
6. The table file is inside Phase B's mutation guard, re-checked before every call and after scoring.
   Changing it mid-run stops the run `incomplete`.

If Phase A cannot produce a valid table, Phase B cannot launch.
