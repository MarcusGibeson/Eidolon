from __future__ import annotations

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

quick = set(release_verify.QUICK_STAGE_NAMES)
full = set(release_verify.FULL_STAGE_NAMES)

required_spine = {
    "python-compile",
    "version-inventory",
    "corrective-suite",
    "import-compatibility",
    "dashboard-http-probe",
    "release-integrity",
    "source-only-runtime-boundary",
}
require("quick-retains-attested-release-spine", required_spine <= quick)
require("quick-retains-latest-desktop-research-gate", "v2502.9-desktop-research-intelligence-gate" in quick)
require("quick-retains-current-version-regression", "v2503.4.30.2-training-anchor-integration" in quick)
require("full-retains-v2503-4-regression", "v2503.4-evidence-language-consistency-source-quality" in full)
require("full-retains-v2503-2-regression", "v2503.2-candidate-specific-evidence-follow-up" in full)
require("full-retains-v2503-3-regression", "v2503.3-source-independence-recommendation-confidence" in full)

retired_from_quick = {
    "v1300.9.1-desktop-checkpoint-coherence-repair",
    "v1450.9-desktop-alpha-checkpoint",
    "v2500.9.1-daily-use-conversation-grounding",
    "v2501.0-bounded-autonomous-web-research",
    "v2501.1-governed-public-web-research-adapter",
    "v2501.9-desktop-research-acceptance",
    "v2502.2-research-result-review-citation-quality",
    "v2502.7-source-strategy-adaptive-follow-up",
}
require("older-high-signal-gates-retired-from-quick", quick.isdisjoint(retired_from_quick))
require("older-high-signal-gates-preserved-in-full", retired_from_quick <= full)
require("full-superset-of-quick", quick <= full)
require("quick-stage-count-bounded", len(quick) <= 10)
require("quick-selector-rejects-retired-stage", not release_verify.stage_selected_for_profile("quick", "v1450.9-desktop-alpha-checkpoint"))
require("full-selector-keeps-retired-stage", release_verify.stage_selected_for_profile("full", "v1450.9-desktop-alpha-checkpoint"))
require("quick-selector-keeps-current-stage", release_verify.stage_selected_for_profile("quick", "v2503.4.30.2-training-anchor-integration"))
require("full-selector-keeps-v2503-4-stage", release_verify.stage_selected_for_profile("full", "v2503.4-evidence-language-consistency-source-quality"))
require("full-selector-keeps-v2503-3-stage", release_verify.stage_selected_for_profile("full", "v2503.3-source-independence-recommendation-confidence"))
require("full-selector-keeps-v2503-2-stage", release_verify.stage_selected_for_profile("full", "v2503.2-candidate-specific-evidence-follow-up"))

report = {
    "version": "2503.4",
    "status": "pass" if all(checks.values()) else "blocked",
    "ok": all(checks.values()),
    "passed": sum(checks.values()),
    "total": len(checks),
    "quick_stage_count": len(quick),
    "full_stage_count": len(full),
    "retired_from_quick_count": len(retired_from_quick),
    "checks": checks,
}
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if report["ok"] else 1)
