# B7 run 1: FAIL (preserved)

`B7_RUN1_FAIL.json` is the first B7 run of the forked module, kept unchanged. 156 values compared, 3 differing; every
bound met; no finding. Both causes were defects in the new module, not in the corpus or the criterion:

1. `o3_entities.g4_entities` (697 frozen, 1139 forked) and `o3_entities.g3_entities_compared` (20 / 32): the carried
   G-ROUTE3 core had been retyped rather than copied, and the retyped entity detector lost the two literal backspace
   bytes that wrap the original's identifier pattern (its line 57; recorded in `sealed/O3_IDENTIFIER_DECISION.md`).
   The fork therefore was not byte-identical (N9) and its identifier branch matched where the frozen one never
   does. Fixed by copying the carried segments byte-for-byte from `tools/g_route3_independence.py`.
2. `conversation.gold_positions`: identical counts, but position keys were integers in the forked result and
   strings in the frozen (JSON) report. Fixed by emitting string keys.

No criterion, bound or frozen value was changed. Run 2 (`../B7_INDEPENDENCE_RECHECK.json`): PASS, 0 differing.
