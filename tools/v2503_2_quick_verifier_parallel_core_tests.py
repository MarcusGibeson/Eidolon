from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import release_verify  # noqa: E402

checks: dict[str, bool] = {}

def require(name: str, value: object) -> None:
    checks[name] = bool(value)
    assert checks[name], name

parallel = tuple(release_verify.QUICK_PARALLEL_CORE_STAGE_NAMES)
require("parallel-core-is-exactly-four-stages", parallel == (
    "python-compile",
    "version-inventory",
    "corrective-suite",
    "import-compatibility",
))
require("parallel-core-is-subset-of-quick", set(parallel) <= set(release_verify.QUICK_STAGE_NAMES))
require("current-v2502-9-gate-selected-by-quick", release_verify.stage_selected_for_profile("quick", "v2502.9-desktop-research-intelligence-gate"))
require("current-v2503-4-30-2-gate-selected-by-quick", release_verify.stage_selected_for_profile("quick", "v2503.4.30.2-training-anchor-integration"))
require("retained-v2503-4-gate-selected-by-full", release_verify.stage_selected_for_profile("full", "v2503.4-evidence-language-consistency-source-quality"))
require("retained-v2503-3-gate-selected-by-full", release_verify.stage_selected_for_profile("full", "v2503.3-source-independence-recommendation-confidence"))
require("retained-v2503-2-gate-selected-by-full", release_verify.stage_selected_for_profile("full", "v2503.2-candidate-specific-evidence-follow-up"))
source = inspect.getsource(release_verify.build_verification)
require("quick-core-uses-thread-pool", "ThreadPoolExecutor(max_workers=len(quick_parallel_specs))" in source)
require("parallel-completions-rehash-source", 'payload["source_after"] = source_snapshot_digest(ROOT)' in source)
require("full-remains-sequential", 'if profile == "quick":\n            quick_parallel_specs' in source)
require("focused-suite-loop-admits-quick", 'profiles=("quick", "full")' in source)
require("final-whole-tree-immutability-retained", "source_snapshot_after = _source_tree_snapshot()" in source)
require("quick-budget-is-six-minutes", 'performance_budget_seconds = 360 if profile == "quick" else 1800' in source)

report = {
    "version": "2503.2",
    "status": "pass" if all(checks.values()) else "blocked",
    "ok": all(checks.values()),
    "passed": sum(checks.values()),
    "total": len(checks),
    "parallel_core_stage_count": len(parallel),
    "checks": checks,
}
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if report["ok"] else 1)
