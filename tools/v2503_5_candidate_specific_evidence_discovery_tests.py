from __future__ import annotations

import json

import os
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2503-5-runtime-")

from bounded_autonomous_web_research import (
    CANDIDATE_FOLLOW_UP_SOURCES_PER_CELL,
    HARD_LIMITS,
    _select_candidate_follow_up_sources,
)
from bounded_research_reasoning import plan_candidate_evidence_follow_up
from bounded_research_reasoning import decompose_research_objective, plan_public_search_queries
from research_source_independence import source_evidence_role
from release_installation_preview import _target_inventory


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def source(url: str, *, host: str, quality: float, kind: str = "unknown") -> dict[str, object]:
    return {
        "public_url": url,
        "canonical_url": url,
        "host": host,
        "quality_score": quality,
        "source_kind": kind,
    }


selected, alternatives = _select_candidate_follow_up_sources(
    [
        source("https://generic.example/blog/best-tools", host="generic.example", quality=0.99),
        source("https://first.example/pricing", host="first.example", quality=0.70),
        source("https://second.example/plans", host="second.example", quality=0.65),
        source("https://third.example/pricing", host="third.example", quality=0.60),
    ],
    evidence_dimension="free_tier_feasibility",
)
require(CANDIDATE_FOLLOW_UP_SOURCES_PER_CELL == 2, "two_sources_are_reserved_per_candidate_matrix_cell")
require(len(selected) == 2, "two_candidate_specific_sources_are_selected")
require({row["host"] for row in selected} == {"first.example", "second.example"}, "role_compatible_sources_outrank_generic_listicles")
require(all(row["_candidate_role_supports_dimension"] for row in selected), "selected_sources_can_support_the_requested_dimension")
require(len({row["host"] for row in selected}) == 2, "selected_sources_use_distinct_hosts")
require(any(row["host"] == "generic.example" for row in alternatives), "unsupported_sources_remain_fallback_evidence_only")
require(not source_evidence_role(source("https://www.britannica.com/money/supply-and-demand", host="britannica.com", quality=0.9)).get("supportable_dimensions"), "generic_demand_definitions_are_not_evidence")

single = decompose_research_objective("Research Brand Deal Tracking for Content Creators demand")
single_query = plan_public_search_queries("Research Brand Deal Tracking for Content Creators demand", single, {"strategies": []}, max_queries=1)
require(single_query["ok"], "single_candidate_demand_query_is_planned")
require(bool({"creator", "creators"} & set(single_query["queries"][0]["query"].split())), "single_candidate_query_keeps_domain_context")
require("complaints" in single_query["queries"][0]["query"].split(), "single_candidate_query_requests_problem_evidence")

discovery = {
    "reasonable_inferences": [
        {
            "claim_code": "candidate-1",
            "title": "Quote follow-up tracker",
            "customer": "solo home service contractors",
            "problem": "open quotes miss timely follow-up deadlines",
            "product": "tracks quote status and follow-up dates",
            "evidence_strength": "weak",
            "evidence_dimensions": {},
        }
    ],
    "recommendation": {},
}
planned = plan_candidate_evidence_follow_up(
    discovery,
    remaining_query_budget=4,
    remaining_page_budget=4,
    remaining_failure_budget=4,
    max_followups=4,
)
demand = next(row for row in planned["queries"] if row["evidence_dimension"] == "demand")
require("quotes" in demand["query"].split(), "demand_query_retains_the_candidate_problem")
require("complaints" in demand["query"].split(), "demand_query_requests_experience_evidence")
require(HARD_LIMITS["max_observed_pages"] >= 28, "hard_page_limit_can_represent_the_independent_evidence_matrix")

inventory_root = Path(tempfile.mkdtemp(prefix="eidolon-target-inventory-"))
try:
    (inventory_root / "conscious_agent").mkdir(parents=True)
    (inventory_root / "conscious_agent" / "main.py").write_text("pass\n", encoding="utf-8")
    (inventory_root / ".venv" / "Scripts").mkdir(parents=True)
    (inventory_root / ".venv" / "Scripts" / "python.exe").write_bytes(b"runtime")
    inventory = _target_inventory(inventory_root)
    require([row["path"] for row in inventory["entries"]] == ["conscious_agent/main.py"], "target_inventory_excludes_external_runtime")
finally:
    shutil.rmtree(inventory_root, ignore_errors=True)

print(json.dumps({"ok": True, "checks": len(CHECKS), "check_names": CHECKS}, sort_keys=True))
