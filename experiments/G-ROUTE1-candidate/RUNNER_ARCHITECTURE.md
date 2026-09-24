# G-ROUTE1 Execution Architecture

The execution path is:

fixture freeze verification -> exact model/config preflight -> frozen balanced schedule -> minimal request construction -> one fresh provider session -> raw append-only persistence -> gold-blind operational validation -> isolated coding evidence where required -> frozen evaluator-only validation -> checkpoint -> qualification scoring -> simulated escalation -> terminal receipt.

The provider boundary has no implicit retry or fallback. Live execution has no CLI and requires a separate one-shot authorization bound to the final execution-freeze digest. Synthetic tests can inject a deterministic provider stub but cannot authorize a live run.

Production adaptive routing is not imported or invoked. G-ROUTE1 only estimates how the frozen ladder `7B -> 14B -> 27B -> no_qualified_model` would behave.
