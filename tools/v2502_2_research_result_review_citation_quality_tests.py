from __future__ import annotations

"""Deterministic v2502.2 research-result review and citation-quality tests."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

runtime = tempfile.TemporaryDirectory(prefix="eidolon-v2502-2-")
os.environ["EIDOLON_DATA_DIR"] = runtime.name

import conversational_research_actions as bridge
import dashboard_chat_console as dashboard
from bounded_autonomous_web_research import BoundedResearchSessionStore
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


checks: list[str] = []


def require(value: object, name: str) -> None:
    if not value:
        raise AssertionError(name)
    checks.append(name)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


class EvidenceAdapter:
    search_calls = 0
    observe_calls = 0

    def describe(self):
        return {
            "adapter_code": "v2502.2-evidence-review-fixture",
            "read_only": True,
            "allowed_methods": ["GET", "HEAD"],
            "search_supported": True,
            "private_network_allowed": False,
            "redirect_revalidation_required": True,
            "credentials_allowed": False,
            "cookies_allowed": False,
            "uploads_allowed": False,
            "side_effects_allowed": False,
            "max_bytes_enforced": True,
            "timeout_enforced": True,
        }

    def search(self, query, *, limit, timeout_seconds):
        type(self).search_calls += 1
        query_number = type(self).search_calls
        return [
            {"url": f"https://official.example/support-q{query_number}?private=removed", "source_kind": "primary_official", "fetched_at": "2026-08-27T00:00:00+00:00"},
            {"url": f"https://mirror.example/duplicate-q{query_number}", "source_kind": "reputable_secondary", "fetched_at": "2026-08-27T00:00:00+00:00"},
            {"url": f"https://analysis.example/refute-q{query_number}", "source_kind": "reputable_secondary", "fetched_at": "2026-08-27T00:00:00+00:00"},
            {"url": f"https://failed.example/unavailable-q{query_number}", "source_kind": "unknown", "fetched_at": "2026-08-27T00:00:00+00:00"},
        ][:limit]

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        type(self).observe_calls += 1
        url = str(candidate.get("public_url") or "")
        if "failed.example" in url:
            raise RuntimeError("fixture_source_unavailable")
        claim = str(candidate.get("subquestion_id") or "rq1")
        if claim == "rq1":
            stance = "refutes" if "analysis.example" in url else "supports"
            fresh_enough = True
            evidence_key = "rq1-duplicate" if "official.example" in url or "mirror.example" in url else "rq1-refute"
        else:
            stance = "supports"
            fresh_enough = False
            evidence_key = f"{claim}-{candidate.get('host') or url}"
        citation_id = f"{claim}-{type(self).observe_calls}"
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
            "receipt_kind": "source_observation",
            "authoritative": True,
            "terminal": True,
            "operation_digest": digest(["operation", citation_id]),
            "terminal_result_digest": digest(["result", citation_id]),
            "source_observed": True,
            "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": claim,
            "stance": stance,
            "evidence_digest": digest(evidence_key),
            "citation_id": citation_id,
            "source_kind": candidate["source_kind"],
            "quality_score": candidate["quality_score"],
            "freshness_known": True,
            "fresh_enough": fresh_enough,
            "relevance_score": 0.92 if claim == "rq1" else 0.68,
            "observed_bytes": min(384, max_bytes),
        }
        row["receipt_digest"] = digest(row)
        return row


EvidenceAdapter.search_calls = 0
EvidenceAdapter.observe_calls = 0
store = BoundedResearchSessionStore(runtime.name)
private_objective = "Compare current public alpha evidence; explain historical public beta evidence"
created = store.create_session(
    "v2502.2:create",
    objective=private_objective,
    budget={"max_queries": 2, "max_candidates": 8, "max_observed_pages": 8, "max_total_bytes": 8192, "max_elapsed_seconds": 30},
)
session = dict(created.get("result") or {})
authorized = store.authorize_session(
    "v2502.2:authorize",
    session_id=session["session_id"],
    session_digest=session["session_digest"],
    public_query_confirmed=True,
)
executed = store.execute_session(
    "v2502.2:execute",
    session_id=session["session_id"],
    authorization_digest=str(dict(authorized.get("result") or {}).get("authorization_digest") or ""),
    adapter=EvidenceAdapter(),
)
require(executed.get("ok") is True, "bounded_research_fixture_completes")
result_payload = dict(executed.get("result") or {})
report = dict(result_payload.get("report") or {})
require(report.get("contract_version") == "v2502.2", "report_contract_advances_to_v2502_2")
require(bool(report.get("unresolved_disagreements")), "fresh_cross_source_contradiction_is_preserved")
require(bool(report.get("missing_evidence")), "stale_only_evidence_remains_a_gap")
require(int(report.get("source_failure_count") or 0) >= 1, "source_failure_count_reaches_report")
require(any(row.get("duplicate_evidence_count") for row in report.get("claim_assessments") or []), "duplicate_evidence_is_not_independent_confirmation")
require(all("quality_score" in row and "freshness" in row for row in report.get("citations") or []), "citation_quality_and_freshness_reach_report")

action_result = {
    "ok": True,
    "status": "bounded_research_completed",
    "session": dict(result_payload.get("session") or {}),
    "report": report,
    "report_digest": str(report.get("report_digest") or ""),
    "citation_count": int(report.get("citation_count") or 0),
}
action = {
    "id": "chat_action_v2502_2_fixture",
    "status": "completed",
    "function_name": "research_session_authorize_execute",
    "function_args": {"session_id": session["session_id"], "session_digest": session["session_digest"]},
    "result": action_result,
    "execution_mode": "direct_function",
    "risk_level": "low",
    "title": "Bounded read-only research",
    "summary": "Fixture summary",
}
request_counts = (EvidenceAdapter.search_calls, EvidenceAdapter.observe_calls)
review = bridge.conversational_research_review(action) or {}
require(review.get("report_digest") == report.get("report_digest"), "review_is_bound_to_exact_report_digest")
require(review.get("disagreement_count", 0) >= 1 and review.get("missing_evidence_count", 0) >= 1, "review_surfaces_conflict_and_gap_cues")
require(sum(dict(review.get("quality_counts") or {}).values()) == len(review.get("citations") or []), "quality_summary_matches_displayed_citations")
require(sum(dict(review.get("freshness_counts") or {}).values()) == len(review.get("citations") or []), "freshness_summary_matches_displayed_citations")
require(any(row.get("freshness") == "stale" for row in review.get("citations") or []), "stale_citation_is_visibly_classified")
require(request_counts == (EvidenceAdapter.search_calls, EvidenceAdapter.observe_calls), "review_projection_starts_no_external_request")

serialized_review = json.dumps(review, sort_keys=True)
require(private_objective not in serialized_review, "review_exposes_no_private_objective")
require("raw page fixture" not in serialized_review and review.get("raw_page_content_exposed") is False, "review_exposes_no_raw_page_content")
require(review.get("generated_prose_is_evidence") is False, "generated_prose_remains_distinct_from_evidence")
require(not any(review.get(key) for key in ("installation_authorized", "promotion_authorized", "authority_expanded")), "review_grants_no_additional_authority")

portal = dashboard._live_action_portal(action) or {}
require(dict(portal.get("research_review") or {}).get("review_digest") == review.get("review_digest"), "live_action_portal_projects_exact_review")
require(request_counts == (EvidenceAdapter.search_calls, EvidenceAdapter.observe_calls), "portal_rehydration_starts_no_external_request")
server_html = dashboard._render_research_review(portal)
require("data-research-review='true'" in server_html and "Review research evidence" in server_html, "server_renderer_exposes_bounded_review_surface")
require("Generated prose is synthesis, not evidence" in server_html and "Opening a citation is your explicit browser action" in server_html, "review_boundary_copy_is_explicit")

tampered = deepcopy(action)
tampered["result"]["report"]["citation_count"] = int(report.get("citation_count") or 0) + 1
require(bridge.conversational_research_review(tampered) is None, "tampered_report_digest_is_rejected")
pending = deepcopy(action)
pending["status"] = "running"
require(bridge.conversational_research_review(pending) is None, "nonterminal_report_is_not_presented_for_review")

source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
styles = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
require("renderResearchReview" in source and "data-research-review" in source, "dashboard_has_research_review_renderer")
require("chat-research-citations" in styles and "max-width:100%" in styles, "research_review_has_narrow_safe_styling")
rendered = dashboard.render_realtime_chat_panel(None)
scripts = re.findall(r"<script[^>]*>(.*?)</script>", rendered, flags=re.S | re.I)
node = shutil.which("node")
require(bool(scripts) and bool(node), "rendered_dashboard_script_and_node_are_available")
with tempfile.TemporaryDirectory(prefix="eidolon-v2502-2-js-") as js_root:
    for index, script in enumerate(scripts):
        script_path = Path(js_root) / f"dashboard-{index}.js"
        script_path.write_text(script, encoding="utf-8")
        checked = subprocess.run([str(node), "--check", str(script_path)], capture_output=True, text=True, timeout=30)
        require(checked.returncode == 0, f"rendered_dashboard_javascript_{index}_is_valid")

print(json.dumps({
    "suite": "v2502.2-research-result-review-citation-quality",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "search_request_count": EvidenceAdapter.search_calls,
    "observation_request_count": EvidenceAdapter.observe_calls,
    "review_network_request_count": 0,
    "raw_content_exposed": False,
    "authority_expanded": False,
}, sort_keys=True))
