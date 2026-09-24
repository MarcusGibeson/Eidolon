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

Operational acceptance uses `g-route3.operational-validator.v1`. It is the G-ROUTE1 operational validator for
every profile except conversation, where it rejects only an affirmative first-person claim that an action
was carried out. The semantic evaluator is `g_route1_validators.py`, unchanged.

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
  execution-freeze binding, and `phase_a_attempts`: every Phase A run directory with its state, so a table
  cannot quietly come from the best of several attempts;
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

1. Phase A runs under its own authorization: `Authorize G-ROUTE3 phase A execution <freeze digest>`. The
   authorization is consumed on use by exclusive file creation. A second run under it is refused.
2. Phase A is scored and sealed, and reaches five-view terminal agreement.
3. The Phase A results are audited independently.
4. `freeze_table` writes the table **once**. A second write with different content is refused.
5. Phase B requires, before any provider contact:
   - the table exists and verifies;
   - its cells equal the cells in the sealed Phase A score, and the score digest matches;
   - it names this Phase A run, and discloses every Phase A attempt;
   - Phase A is `complete`, was not synthetic, and ran under this execution freeze;
   - the table is bound to this execution freeze;
   - a second authorization reads `Authorize G-ROUTE3 phase B execution <freeze digest> table <table digest>`,
     and it too is consumed on use.

   Verifying the execution freeze does not depend on the table being absent. Absence is checked only when
   the freeze is *written*, so the freeze stays valid once Phase A has produced a table.
6. The table file is inside Phase B's mutation guard, re-checked before every call and after scoring.
   Changing it mid-run stops the run `incomplete`.

If Phase A cannot produce a valid table, Phase B cannot launch.
