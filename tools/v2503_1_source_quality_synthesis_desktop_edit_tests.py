from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2503-1-runtime-")

from bounded_research_history import sanitize_report
from bounded_research_reasoning import validate_research_synthesis


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


CITATIONS = [
    {
        "citation_id": f"web-{index:016x}",
        "public_url": f"https://source{index}.example/evidence",
        "source_kind": "unknown",
        "quality_score": 0.3,
        "relevance_score": 0.8,
        "freshness": "unknown",
        "source_digest": str(index) * 64,
    }
    for index in range(1, 7)
]


generic = validate_research_synthesis(
    {
        "findings": [
            {"title": "Micro-SaaS strategy", "conclusion": "Validate quickly.", "citation_ids": ["web-0000000000000001"]},
            {"title": "Pricing framework", "conclusion": "Charge monthly.", "citation_ids": ["web-0000000000000002"]},
            {"title": "Opportunity ideas", "conclusion": "Pick a niche.", "citation_ids": ["web-0000000000000003"]},
        ],
        "recommendation": {
            "title": "Micro-SaaS strategy",
            "conclusion": "It is broad advice.",
            "citation_ids": ["web-0000000000000001"],
        },
    },
    citations=CITATIONS,
    requested_result_count=3,
)
require(not generic["ok"], "generic_strategy_rows_fail_the_concrete_opportunity_contract")
require(not generic["rendered_answer"], "rejected_generic_strategy_is_not_presented")
require(len(generic["missing_evidence"]) == 2, "rejection_names_result_and_recommendation_gaps")


opportunities = [
    {
        "name": "Amazon seller research tracker",
        "customer": "independent Amazon private-label sellers",
        "problem": "product research evidence is scattered across repeated manual checks",
        "product": "records candidate products and compares operator-entered demand signals",
        "zero_budget_rationale": "starts with local storage and manual public-data entry",
        "evidence_summary": "The supplied sources describe recurring product-research work.",
        "citation_ids": ["web-0000000000000001", "web-0000000000000002"],
        "uncertainties": ["The sources do not establish willingness to pay."],
    },
    {
        "name": "Copywriter lead follow-up board",
        "customer": "freelance copywriters",
        "problem": "small prospect lists lose follow-up context",
        "product": "tracks manually entered leads, next steps, and reply status",
        "zero_budget_rationale": "needs only a local database and browser UI",
        "evidence_summary": "The supplied sources describe lead follow-up as repeated work.",
        "citation_ids": ["web-0000000000000003", "web-0000000000000004"],
        "uncertainties": ["Competitive alternatives were not measured."],
    },
    {
        "name": "Creator brand-deal tracker",
        "customer": "small independent content creators",
        "problem": "brand conversations and deliverables are tracked informally",
        "product": "tracks outreach, deliverables, deadlines, and payment status",
        "zero_budget_rationale": "the first version uses local storage without paid APIs",
        "evidence_summary": "The supplied sources identify brand-deal administration as recurring work.",
        "citation_ids": ["web-0000000000000005", "web-0000000000000006"],
        "uncertainties": ["The evidence comes from low-authority list articles."],
    },
]

mismatched = validate_research_synthesis(
    {
        "opportunities": opportunities,
        "recommendation": {
            "opportunity_name": "Generic SaaS strategy",
            "conclusion": "It sounds flexible.",
            "citation_ids": ["web-0000000000000001"],
        },
    },
    citations=CITATIONS,
    requested_result_count=3,
)
require(not mismatched["ok"], "recommendation_must_select_an_admitted_opportunity")

valid = validate_research_synthesis(
    {
        "opportunities": opportunities,
        "recommendation": {
            "opportunity_name": "Copywriter lead follow-up board",
            "conclusion": "It has the narrowest build and clearest manually operated first version.",
            "citation_ids": ["web-0000000000000003", "web-0000000000000004"],
        },
        "disagreements": ["List articles disagree about which niche has the strongest demand."],
        "limitations": ["No primary market data or pre-sales evidence was observed."],
    },
    citations=CITATIONS,
    requested_result_count=3,
)
require(valid["ok"], "three_concrete_citation_bound_opportunities_are_admitted")
require(len(valid["reasonable_inferences"]) == 4, "three_opportunities_and_one_recommendation_are_retained")
require(all(row["evidence_strength"] == "weak" for row in valid["reasonable_inferences"][:3]), "low_quality_sources_are_labeled_weak")
require("Best current lead for further research: Copywriter lead follow-up board" in valid["rendered_answer"], "weak_evidence_cannot_render_as_unqualified_winner")
require("Customer:" in valid["rendered_answer"] and "Zero-budget basis:" in valid["rendered_answer"], "rendered_results_explain_buyer_problem_product_and_feasibility")
require("validated" not in valid["rendered_answer"].casefold(), "weak_list_evidence_is_not_called_validated")

sanitized = sanitize_report({
    **valid,
    "session_id": "research-" + "a" * 24,
    "session_digest": "b" * 64,
    "report_digest": "c" * 64,
    "research_intelligence_version": "v2503.1",
    "requested_result_count": 3,
    "synthesis_status": "citation_bound_research_synthesis_ready",
    "provider_contacted": True,
    "provider_request_count": 1,
    "private_objective_sent_to_provider": False,
})
require(not sanitized["provider_contacted"], "history_inspection_itself_remains_provider_free")
require(sanitized["synthesis_provider_contacted"], "historical_report_preserves_truthful_synthesis_provider_contact")
require(sanitized["synthesis_provider_request_count"] == 1, "historical_report_preserves_synthesis_request_count")
require(sanitized["requested_result_count"] == 3, "historical_report_preserves_requested_result_count")
require(sanitized["research_intelligence_version"] == "v2503.1", "historical_report_preserves_research_intelligence_version")

desktop_source = (AGENT / "desktop_shell.py").read_text(encoding="utf-8")
require('edit_menu.add_command(label="Cut"' in desktop_source, "desktop_context_menu_exposes_cut")
require('edit_menu.add_command(label="Copy"' in desktop_source, "desktop_context_menu_exposes_copy")
require('edit_menu.add_command(label="Paste"' in desktop_source, "desktop_context_menu_exposes_paste")
require('edit_menu.add_command(label="Select all"' in desktop_source, "desktop_context_menu_exposes_select_all")
require('text_widget.bind("<Button-3>", show_edit_menu)' in desktop_source, "desktop_right_click_opens_edit_menu")
require('text_widget.bind("<Shift-F10>", show_edit_menu)' in desktop_source, "desktop_keyboard_context_menu_remains_accessible")
require('widget is composer and str(widget.cget("state")) != "disabled"' in desktop_source, "paste_and_cut_are_limited_to_editable_composer")

print(json.dumps({
    "suite": "v2503.1-source-quality-synthesis-desktop-edit",
    "ok": True,
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "network_request_count": 0,
    "provider_request_count": 0,
    "authority_expanded": False,
    "runtime_mutated": False,
}, sort_keys=True))
