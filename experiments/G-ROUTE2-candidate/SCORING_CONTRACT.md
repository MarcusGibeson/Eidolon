# G-ROUTE2 scoring contract

Contract: `g-route2.scorer.v1`. Frozen before model contact.
Implementation: `tools/g_route2_scorer.py`.

## Units

24 fixtures, 6 task classes, 4 risk classes, 3 tiers, 3 repeats, 72 qualification cells, 216 calls.
Ambiguity diagnostics do not exist in this corpus; their denominator is zero and excluded.

## Both contracts, always

Every JSON-profile output is scored twice from the same bytes:

* **raw contract** — the G-ROUTE1 transport rule, no wrapper tolerated;
* **normalized contract** — after transport canonicalization.

Both matrices are reported in full. **Qualification is decided under the normalized contract**; the
raw matrix is reported beside it so formatting and reasoning effects stay separable within one
sample. `conversation.v1` is unaffected by transport and its two contracts are identical by
construction.

## Reported metrics

Raw structural validity; normalized structural validity; normalization rate overall, by outcome and
by tier; operational acceptance; semantic correctness; false-clean count; validator-detected
semantic failures; validator-missed semantic failures; safe-to-stop correctness; unsafe early-stop
count; unsafe early stops that required normalization; useful admission; escalation frequency; final
simulated tier distribution; no-qualified-model rate; per-tier latency, token counts and
tokens-per-second.

## Qualification

A cell qualifies only when all three scheduled observations exist, all three are operationally
accepted under the normalized contract, all three pass the frozen evaluator, no false-clean occurs,
no infrastructure failure occurs and no returned-model mismatch occurs.

Missing data cannot pass. Aggregate performance cannot override a hard failure. Structural validity
alone can never qualify a cell. There is no global model leaderboard and no averaging across task
classes. Selection is the cheapest qualified tier, and only after qualification is established under
this contract. R4 is evidence-only.

## Safe-to-stop scoring

For each of the 72 fixture-repeats the ladder `small → mid → large` is walked and the first tier
where `safe_to_stop_escalation` holds is the stop.

* **useful admission** — a stop whose answer passes the frozen evaluator;
* **unsafe early stop** — a stop whose answer fails it;
* **no_qualified_model** — no tier was safe to stop.

Gold is used here and nowhere else. The routing policy never sees it.

## Gates

Frozen in `thresholds.json` before contact: zero infrastructure crashes from model-produced output;
zero unsafe terminal acceptance attributable solely to normalization; normalization never changes a
semantic value; normalization decisions reproducible deterministically; unsafe early stops at most
5% of stops; useful admission at least 25% of fixture-repeats; qualification requires complete
observations; no cell passes on missing data; no vacuous pass; no qualification from structural
validity alone.
