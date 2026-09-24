# G-ROUTE1 Live Mechanical Pilot Contract

This pilot is operational verification only. It is not part of the G-ROUTE1 scientific corpus, schedule, qualification matrix, or scorer.

- Synthetic fixture: `PX-ROUTE-MECHANICS-01`.
- Three model tiers are exercised.
- Each model receives two identical fresh-session requests with one seed and one identical request with a different seed.
- Intended generation calls: 9.
- Scientific retries and output-repair calls: 0.
- Pause occurs after the first durably persisted call.
- The paused model is released with a separate zero-token Ollama unload request where supported.
- Runtime artifacts are stored only under the `g_route1_mechanical_pilots` namespace.
- No scientific corpus, evaluator gold, qualification threshold, or production router is model input or pilot scoring input.
- Output comparison is mechanical. It does not establish semantic quality or prove that Ollama honored a seed internally.
- Belief effects and production routing remain disabled.

The pilot fails closed on execution-freeze drift, pilot-definition drift, model/config mismatch, provider fallback, duplicate or missing calls, corrupt checkpoints, append-only persistence failure, Activity lineage failure, or mutation-guard failure.
