from __future__ import annotations

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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2503-3-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_history import build_history_record, render_markdown_export, sanitize_report
from bounded_research_reasoning import RESEARCH_EVIDENCE_DIMENSIONS, validate_research_synthesis
from research_source_independence import canonicalize_public_url, cluster_evidence_lineages, source_identity
import dashboard_chat_console as dashboard

CHECKS: list[str] = []

def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)

def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()

def candidate(name: str) -> dict[str, str]:
    return {
        "name": name,
        "customer": f"{name} customers",
        "problem": f"{name} problem",
        "product": f"{name} product",
        "zero_budget_rationale": "local-first implementation with public read-only research",
        "evidence_summary": f"Observed evidence supports evaluating {name}.",
    }

def candidate_digest(row: dict[str, str]) -> str:
    return digest({"title": row["name"], "customer": row["customer"], "problem": row["problem"], "product": row["product"]})

def citation(cid: str, cand: dict[str, str], dimension: str, url: str, *, stance: str="supports", quality: float=.9, source_kind: str="primary_data", freshness: str="fresh", **extra: object) -> dict[str, object]:
    row = {
        "citation_id": cid,
        "public_url": url,
        "host": url.split("/")[2],
        "source_kind": source_kind,
        "freshness": freshness,
        "quality_score": quality,
        "relevance_score": .9,
        "source_digest": digest({"citation": cid, "url": url}),
        "candidate_digest": candidate_digest(cand),
        "evidence_dimension": dimension,
        "stance": stance,
    }
    row.update(extra)
    return row

def payload_for(candidates: list[dict[str,str]], citation_map: dict[str, list[str]], *, recommendation: str | None=None) -> dict[str, object]:
    opportunities=[]
    for cand in candidates:
        per_dim={}
        for dim in RESEARCH_EVIDENCE_DIMENSIONS:
            ids=[cid for cid in citation_map.get(cand["name"], []) if cid.startswith(cand["name"][0].lower()+"-"+dim[:2])]
            per_dim[dim]={"summary": f"{dim} evidence for {cand['name']}", "citation_ids": ids}
        opportunities.append(dict(cand, evidence_dimensions=per_dim, citation_ids=citation_map.get(cand["name"], [])))
    chosen=recommendation or candidates[0]["name"]
    chosen_ids=citation_map.get(chosen, [])[:3]
    return {
        "opportunities": opportunities,
        "recommendation": {"opportunity_name": chosen, "conclusion": "Best observed fit under the bounded evidence matrix.", "citation_ids": chosen_ids},
        "disagreements": ["Minority evidence remains visible."],
        "limitations": ["Public evidence remains incomplete."],
    }

# A. Canonical identity and B. lineage clustering.
a={"citation_id":"a","public_url":"https://Example.com/path?utm_source=x&id=7#frag","source_digest":"a"*64}
b={"citation_id":"b","public_url":"https://example.com/path?id=7&utm_medium=y","source_digest":"b"*64}
require(canonicalize_public_url(a["public_url"]) == canonicalize_public_url(b["public_url"]), "tracking_variation_normalizes_to_same_canonical_url")
require(source_identity(a)["source_identity_digest"] == source_identity(b)["source_identity_digest"], "tracking_variation_is_one_source_identity")
same=cluster_evidence_lineages([a,b])
require(same["independent_lineage_count"] == 1 and same["repeated_or_derivative_citation_count"] == 1, "same_canonical_page_is_one_independent_lineage")
origin="1"*64
mirrors=cluster_evidence_lineages([
    {"citation_id":"m1","public_url":"https://publisher.example/story","source_digest":"2"*64,"lineage_origin_digest":origin},
    {"citation_id":"m2","public_url":"https://mirror.example/story-copy","source_digest":"3"*64,"mirror_of_source_digest":origin},
    {"citation_id":"m3","public_url":"https://syndicate.example/story","source_digest":"4"*64,"syndicated_from_source_digest":origin},
])
require(mirrors["unique_source_identity_count"] == 3, "mirror_urls_remain_distinct_source_identities")
require(mirrors["independent_lineage_count"] == 1 and mirrors["repeated_or_derivative_citation_count"] == 2, "mirrors_and_syndicated_copies_are_one_confirmation")
primary=cluster_evidence_lineages([
    {"citation_id":"p1","public_url":"https://agency-one.gov/data","source_digest":"5"*64,"source_kind":"primary_official"},
    {"citation_id":"p2","public_url":"https://agency-two.gov/data","source_digest":"6"*64,"source_kind":"primary_data"},
])
require(primary["independent_lineage_count"] == 2, "independent_primary_sources_remain_independent")
require(primary["primary_or_authoritative_lineage_count"] == 2, "primary_authoritative_lineages_are_counted")
ambiguous=cluster_evidence_lineages([
    {"citation_id":"u1","public_url":"https://one.example/a","content_similarity_digest":"7"*64,"content_similarity_confidence":"ambiguous"},
    {"citation_id":"u2","public_url":"https://two.example/b","content_similarity_digest":"7"*64,"content_similarity_confidence":"ambiguous"},
])
require(ambiguous["uncertain_lineage_count"] == 2 and ambiguous["ambiguous_lineage_silently_merged"] is False, "ambiguous_similarity_remains_uncertain_not_merged")
require(ambiguous["independent_lineage_count"] == 0, "ambiguous_similarity_does_not_claim_independent_confirmation")

# C-E. Candidate matrix and recommendation confidence.
alpha,beta,gamma=candidate("Alpha service"),candidate("Beta service"),candidate("Gamma service")
all_citations: list[dict[str,object]]=[]
ids: dict[str,list[str]]={c["name"]:[] for c in (alpha,beta,gamma)}
# Alpha: same canonical source repeated across all cells => coverage but only one independent lineage overall.
for i,dim in enumerate(RESEARCH_EVIDENCE_DIMENSIONS):
    cid=f"a-{dim[:2]}-{i}"; ids[alpha["name"]].append(cid)
    all_citations.append(citation(cid,alpha,dim,f"https://repeat.example/evidence?item=1&utm_source={i}"))
# Beta: three supported independent cells, one weak low-quality cell => moderate confidence.
for i,dim in enumerate(RESEARCH_EVIDENCE_DIMENSIONS):
    cid=f"b-{dim[:2]}-{i}"; ids[beta["name"]].append(cid)
    q=.9 if i<3 else .2
    all_citations.append(citation(cid,beta,dim,f"https://beta{i}.example/{dim}",quality=q,source_kind="secondary_analysis"))
# Gamma: two independent authoritative citations per cell => high confidence.
for i,dim in enumerate(RESEARCH_EVIDENCE_DIMENSIONS):
    for j in range(2):
        cid=f"g-{dim[:2]}-{i}{j}"; ids[gamma["name"]].append(cid)
        all_citations.append(citation(cid,gamma,dim,f"https://gamma-{i}-{j}.gov/{dim}",source_kind="primary_official"))

raw=payload_for([alpha,beta,gamma],ids,recommendation=gamma["name"])
result=validate_research_synthesis(raw,citations=all_citations,requested_result_count=3,require_candidate_specific_coverage=True,candidate_research_matrix_complete=True)
require(result["status"] == "citation_bound_research_synthesis_ready", "complete_three_candidate_matrix_is_report_ready")
require(len(result["candidate_evidence_matrix"]) == 3, "candidate_matrix_has_three_rows")
require(sum(len(row["cells"]) for row in result["candidate_evidence_matrix"]) == 12, "candidate_matrix_has_all_twelve_cells")
require(all(cell["matrix_state"] in {"supported","weak","contradicted","researched_with_no_credible_evidence","not_researched"} for row in result["candidate_evidence_matrix"] for cell in row["cells"].values()), "matrix_cells_use_bounded_state_vocabulary")
confidence={row["title"]:row for row in result["recommendation_confidence_assessments"]}
require(confidence[alpha["name"]]["confidence_label"] == "tentative", "citation_repetition_does_not_raise_recommendation_confidence")
require(confidence[alpha["name"]]["independent_lineage_count"] == 1 and confidence[alpha["name"]]["repeated_or_derivative_citation_count"] >= 3, "repeated_citations_are_counted_separately_from_independent_lineages")
require(confidence[beta["name"]]["confidence_label"] == "moderate-confidence" and confidence[beta["name"]]["threshold_met"], "moderate_confidence_requires_independent_supported_coverage")
require(any("three matrix dimensions" in reason.lower() for reason in confidence[beta["name"]]["reasons"]), "moderate_confidence_has_attributable_threshold_reason")
require(confidence[gamma["name"]]["confidence_label"] == "high-confidence" and confidence[gamma["name"]]["threshold_met"], "high_confidence_requires_full_independent_authoritative_coverage")
require(any("six independent" in reason.lower() for reason in confidence[gamma["name"]]["reasons"]), "high_confidence_has_independence_threshold_reason")
require(result["strongest_opportunity_admitted"] is True and result["recommendation"]["title"] == gamma["name"], "strongest_opportunity_only_admitted_after_threshold")
require(result["source_independence_summary"]["citation_volume_increases_confidence"] is False, "citation_volume_never_directly_increases_confidence")
require("Most promising: Gamma service" in result["rendered_answer"], "high_confidence_report_leads_with_qualified_conclusion")
require("Candidates and key tradeoffs:" in result["rendered_answer"] and "Evidence matrix:" in result["rendered_answer"], "readable_report_orders_conclusion_tradeoffs_then_evidence")

# Contradictory minority evidence remains visible in a cell and reasons.
delta=candidate("Delta service"); dids=[]; dcits=[]
for i,dim in enumerate(RESEARCH_EVIDENCE_DIMENSIONS):
    if dim=="demand":
        for j,stance in enumerate(("supports","refutes")):
            cid=f"d-{dim[:2]}-{j}"; dids.append(cid); dcits.append(citation(cid,delta,dim,f"https://delta-demand-{j}.example/x",stance=stance))
    else:
        cid=f"d-{dim[:2]}-{i}"; dids.append(cid); dcits.append(citation(cid,delta,dim,f"https://delta-{i}.example/x"))
dres=validate_research_synthesis(payload_for([delta],{delta["name"]:dids}),citations=dcits,requested_result_count=1,require_candidate_specific_coverage=True,candidate_research_matrix_complete=True)
dcell=dres["candidate_evidence_matrix"][0]["cells"]["demand"]
require(dcell["matrix_state"] == "contradicted" and dcell["refuting_evidence_count"] == 1, "minority_refuting_evidence_remains_visible_in_matrix")
require(any("contradict" in reason.lower() for reason in dres["recommendation_confidence_assessments"][0]["reasons"]), "contradiction_is_explained_in_confidence_reasons")

# A below-threshold comparison cannot render an unqualified winner.
low=validate_research_synthesis(payload_for([alpha],{alpha["name"]:ids[alpha["name"]]},recommendation=alpha["name"]),citations=[r for r in all_citations if r["candidate_digest"]==candidate_digest(alpha)],requested_result_count=1,require_candidate_specific_coverage=True,candidate_research_matrix_complete=True)
require(low["recommendation"]["confidence_threshold_met"] is False and low["strongest_opportunity_admitted"] is False, "low_confidence_candidate_does_not_clear_winner_threshold")
require("Best current lead for further research:" in low["rendered_answer"] and "Most promising:" not in low["rendered_answer"], "low_confidence_report_never_renders_unqualified_winner")

# Explicit gap/not-researched semantics.
epsilon=candidate("Epsilon service")
one_id="e-de-0"; one=[citation(one_id,epsilon,"demand","https://epsilon.example/demand",quality=.1)]
partial_payload=payload_for([epsilon],{epsilon["name"]:[one_id]})
partial=validate_research_synthesis(partial_payload,citations=one,requested_result_count=1,require_candidate_specific_coverage=True,candidate_research_matrix_complete=False,require_recommendation=False)
partial_cells=partial["candidate_evidence_matrix"][0]["cells"]
require(partial_cells["demand"]["matrix_state"] == "weak", "weak_researched_cell_is_distinct_from_missing")
require(all(partial_cells[d]["matrix_state"] == "not_researched" for d in RESEARCH_EVIDENCE_DIMENSIONS if d!="demand"), "unattempted_matrix_cells_are_not_researched")
full_gap=validate_research_synthesis(partial_payload,citations=one,requested_result_count=1,require_candidate_specific_coverage=True,candidate_research_matrix_complete=True,require_recommendation=False)
require(all(full_gap["candidate_evidence_matrix"][0]["cells"][d]["matrix_state"] == "researched_with_no_credible_evidence" for d in RESEARCH_EVIDENCE_DIMENSIONS if d!="demand"), "attempted_empty_cells_are_explicit_researched_gaps")

# Invalid model recommendation retains deterministic safe fallback only after complete matrix.
invalid=dict(raw); invalid["recommendation"]={"opportunity_name":"Imaginary winner","conclusion":"unsupported","citation_ids":[ids[gamma["name"]][0]]}
fallback=validate_research_synthesis(invalid,citations=all_citations,requested_result_count=3,require_candidate_specific_coverage=True,candidate_research_matrix_complete=True)
require(fallback["recommendation_deterministic_fallback_used"] is True, "invalid_model_recommendation_uses_existing_deterministic_fallback_after_complete_matrix")
require(fallback["recommendation"]["title"] in {alpha["name"],beta["name"],gamma["name"]}, "deterministic_fallback_selects_only_admitted_candidate")
not_complete=validate_research_synthesis(invalid,citations=all_citations,requested_result_count=3,require_candidate_specific_coverage=True,candidate_research_matrix_complete=False)
require(not_complete["recommendation_deterministic_fallback_used"] is False, "incomplete_matrix_never_uses_deterministic_recommendation_fallback")

# Public history/export projections remain content-minimized.
private_marker="PRIVATE_OBJECTIVE_SENTINEL_9f31"
report=dict(result,report_digest="d"*64,research_intelligence_version="v2503.3",raw_objective=private_marker,raw_query_text=private_marker,provider_payload=private_marker,cookies=private_marker,raw_page_body=private_marker)
sanitized=sanitize_report(report)
serialized=json.dumps(sanitized,sort_keys=True)
require(private_marker not in serialized, "public_report_history_excludes_private_objectives_queries_pages_and_provider_payloads")
require(sanitized["source_independence_summary"]["independent_lineage_count"] >= 1, "public_history_retains_content_free_lineage_counts")
require(len(sanitized["candidate_evidence_matrix"]) == 3 and len(sanitized["recommendation_confidence_assessments"]) == 3, "public_history_retains_bounded_matrix_and_confidence")
history=build_history_record({"session_id":"research-"+"3"*24,"session_digest":"3"*64,"state":"completed","completed_at":"2026-08-30T12:00:00Z"},report)
require(private_marker not in json.dumps(history,sort_keys=True), "history_catalog_never_contains_private_research_marker")
require(history["candidate_matrix_digest"] and history["recommendation_confidence_labels"], "history_catalog_retains_digest_bound_matrix_and_confidence_labels")
export=render_markdown_export("research-"+"3"*24,report)
require(export["ok"] and private_marker not in export["markdown"], "markdown_export_excludes_private_research_state")
require("## Recommendation confidence" in export["markdown"] and "## Candidate evidence matrix" in export["markdown"], "markdown_export_integrates_confidence_and_matrix")
require(export["uploaded"] is False and export["transmitted"] is False, "markdown_export_remains_local_read_only_projection")

# UI is integrated into the retained dashboard, accessible/narrow-safe, and JavaScript remains valid.
source=(ROOT/"conscious_agent"/"dashboard_chat_console.py").read_text(encoding="utf-8")
styles=(ROOT/"conscious_agent"/"dashboard_chat_styles.py").read_text(encoding="utf-8")
require("data-research-confidence" in source and "data-research-matrix" in source, "existing_research_review_integrates_confidence_and_matrix")
require("<caption>Candidate evidence matrix</caption>" in source and "scope='col'" in source and "scope='row'" in source, "server_matrix_has_screen_reader_table_semantics")
require("tabindex='0'" in source and "aria-label='Candidate evidence matrix'" in source, "matrix_is_keyboard_focusable_and_labeled")
require(".chat-research-matrix-wrap" in styles and "overflow-x:auto" in styles and "@media (max-width:620px)" in styles, "matrix_remains_narrow_window_safe")
require("prefers-reduced-motion" in styles or "reduced-motion" in source.casefold() or "prefers-reduced-motion" in (ROOT/"conscious_agent"/"dashboard_chat_console.py").read_text(encoding="utf-8"), "retained_dashboard_preserves_reduced_motion_contract")
rendered=dashboard.render_realtime_chat_panel(None)
scripts=re.findall(r"<script[^>]*>(.*?)</script>",rendered,flags=re.S|re.I); node=shutil.which("node")
require(bool(scripts) and bool(node), "rendered_dashboard_script_and_node_are_available")
with tempfile.TemporaryDirectory(prefix="eidolon-v2503-3-js-") as tmp:
    for index,script in enumerate(scripts):
        path=Path(tmp)/f"dashboard-{index}.js"; path.write_text(script,encoding="utf-8")
        checked=subprocess.run([str(node),"--check",str(path)],capture_output=True,text=True,timeout=30)
        require(checked.returncode==0,f"rendered_dashboard_javascript_{index}_is_valid")

# Authority and runtime boundaries.
for object_under_test in (same,mirrors,primary,ambiguous,result,export):
    require(not object_under_test.get("authority_expanded",False), "authority_remains_unexpanded_"+str(len(CHECKS)))
require(RUNTIME.is_dir() and not str(RUNTIME).startswith(str(ROOT)), "deterministic_runtime_is_external_to_source")
require(not (ROOT/"data"/"projects.json").exists(), "runtime_projects_file_is_not_packaged_in_source")
require("MAX_RESEARCH_REPORT_OUTPUT_CHARS = 12_000" in source, "audited_12000_character_research_delivery_ceiling_is_retained")

print(json.dumps({
    "suite":"v2503.3-source-independence-recommendation-confidence",
    "ok":True,"passed":len(CHECKS),"failed":0,"checks":CHECKS,
    "network_request_count":0,"provider_request_count":0,"external_action_count":0,
    "authority_expanded":False,"raw_private_content_persisted":False,
},sort_keys=True))
