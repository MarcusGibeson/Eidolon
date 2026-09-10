from __future__ import annotations
"""Evidence-backed architecture-improvement goal candidates.

This layer allows Eidolon to recognize architectural consolidation as a project
worth proposing. It cannot activate the goal, edit source, run tests, contact a
provider, approve work, or install a candidate. Goal activation remains an
operator-governed development action.
"""

import ast
import gc
from pathlib import Path
from typing import Any

from project_evidence_store import DENIED_AUTHORITY, atomic_json, digest, evidence_root, read_json, seal, valid
from repository_inventory import build_repository_inventory, load_repository_inventory
from symbol_graph import build_symbol_graph
from architecture_change_reasoning import build_architecture_change_assessment, load_architecture_change_assessment, build_refactor_migration_plan
from development_authority import validate_operator_authorization
from autonomous_developer_beta_v2400 import build_goal_to_candidate_contract, build_stage_evidence

CONTRACT_VERSION = "v2503.7.5"
MAX_CANDIDATES = 12
MAX_SCAN_BYTES = 8 * 1024 * 1024


def _candidate_path(candidate_id: str, runtime_root=None) -> Path:
    return evidence_root("architecture_project_goal", runtime_root) / "candidates" / f"{candidate_id}.json"


def _record_path(goal_id: str, runtime_root=None) -> Path:
    return evidence_root("architecture_project_goal", runtime_root) / "records" / f"{goal_id}.json"


def _metrics(path: Path) -> dict[str, int]:
    try:
        text = path.read_text(encoding="utf-8"); tree = ast.parse(text)
    except Exception:
        return {"line_count": 0, "top_level_symbol_count": 0}
    return {"line_count": text.count("\n") + (0 if not text else 1), "top_level_symbol_count": sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for x in tree.body)}


def discover_architecture_goal_candidates(source_root: str | Path, *, runtime_root=None, now_unix: int | None = None) -> dict[str, Any]:
    root = Path(source_root).resolve()
    symbol_pub = build_symbol_graph(root, runtime_root=runtime_root, now_unix=now_unix)["symbol_graph"]
    wid = str(symbol_pub["workspace_digest"]); inv = load_repository_inventory(wid, runtime_root=runtime_root, include_private=True)
    inv_pub = {"workspace_digest": wid, "source_manifest_digest": symbol_pub.get("source_manifest_digest")}
    python_rows = [row for row in (inv.get("files") or []) if str(row.get("suffix") or "") == ".py" and not bool(row.get("test")) and int(row.get("size_bytes") or 0) <= MAX_SCAN_BYTES]
    python_rows.sort(key=lambda row: (-int(row.get("size_bytes") or 0), str(row.get("relative_path") or "")))
    triage_rows = python_rows[:48]
    prelim: list[tuple[int, str, dict[str, int]]] = []
    for row in triage_rows:
        rel = str(row.get("relative_path") or ""); m = _metrics(root / rel); lines = int(m["line_count"]); symbols = int(m["top_level_symbol_count"])
        if lines < 800 and symbols < 80: continue
        score = min(100, lines // 250 + symbols // 12); prelim.append((score, rel, m))
    prelim.sort(key=lambda x: (-x[0], x[1]))

    candidates = []
    selected_prelim = prelim[:MAX_CANDIDATES]
    # The private inventory can be large. Release triage-only structures before
    # loading retained model/symbol evidence for the deeper assessment so full
    # repository discovery does not double its peak working set.
    del python_rows, triage_rows, inv
    gc.collect()
    assessed = build_architecture_change_assessment(root, [rel for _, rel, _ in selected_prelim], runtime_root=runtime_root, now_unix=now_unix, evidence_workspace_digest=wid) if selected_prelim else {}
    aid = str((assessed.get("assessment") or {}).get("analysis_id") or "")
    private = load_architecture_change_assessment(aid, runtime_root=runtime_root, include_private=True) if aid else {}
    findings_by_path = {str(x.get("target_path")): x for x in private.get("findings") or []}
    for triage_score, rel, m in selected_prelim:
        finding = findings_by_path.get(rel, {})
        responsibilities = [x for x in finding.get("responsibilities") or [] if float(x.get("score") or 0) >= 0.42]
        reasons = []
        if int(m.get("line_count") or 0) >= 1500: reasons.append("large_module")
        if int(m.get("line_count") or 0) >= 5000: reasons.append("very_large_module")
        if int(m.get("top_level_symbol_count") or 0) >= 150: reasons.append("high_top_level_symbol_count")
        if len(responsibilities) >= 4: reasons.append("mixed_responsibility_evidence")
        if int(finding.get("filename_bound_consumer_count") or 0): reasons.append("source_filename_contracts")
        if int(finding.get("transitive_importer_count") or 0) >= 20: reasons.append("broad_change_blast_radius")
        if len(reasons) < 2: continue
        candidate_id = "architecture-goal-candidate-" + digest({"workspace": wid, "manifest": inv_pub.get("source_manifest_digest"), "path": rel, "reasons": reasons})[:20]
        candidate_row = {
            "candidate_id": candidate_id, "target_path": rel, "target_path_digest": digest(rel), "triage_score": triage_score,
            "line_count": int(m.get("line_count") or 0), "top_level_symbol_count": int(m.get("top_level_symbol_count") or 0), "responsibility_count": len(responsibilities),
            "responsibilities": [x.get("responsibility") for x in responsibilities[:10]], "suggested_owner": finding.get("suggested_owner"), "risk": finding.get("risk"),
            "risk_reasons": list(finding.get("risk_reasons") or []), "architecture_reasons": reasons, "direct_importer_count": int(finding.get("direct_importer_count") or 0),
            "transitive_importer_count": int(finding.get("transitive_importer_count") or 0), "filename_bound_consumer_count": int(finding.get("filename_bound_consumer_count") or 0),
            "candidate_test_count": int(finding.get("candidate_test_count") or 0), "dependency_cycle_count": int(private.get("dependency_cycle_count") or 0),
            "in_dependency_cycle": bool(finding.get("in_dependency_cycle")), "analysis_id": aid, "candidate_only": True, "auto_selected": False, "goal_activated": False,
        }
        atomic_json(_candidate_path(candidate_id, runtime_root), seal({"contract_version": CONTRACT_VERSION, "workspace_digest": wid, "source_manifest_digest": inv_pub.get("source_manifest_digest"), **candidate_row}))
        candidates.append(candidate_row)
    candidates.sort(key=lambda x: (-int(x.get("triage_score") or 0), -int(x.get("line_count") or 0), str(x.get("target_path"))))
    return {"ok": True, "status": "architecture_goal_candidates_available" if candidates else "no_architecture_goal_candidates", "workspace_digest": wid,
            "source_manifest_digest": inv_pub.get("source_manifest_digest"), "candidate_count": len(candidates), "candidates": candidates, "automatic_selection_performed": False,
            "goal_activated": False, "source_modified": False, "provider_contacted": False, "action_executed": False, **DENIED_AUTHORITY}


def prepare_architecture_project_goal(source_root: str | Path, candidate_id: str, *, runtime_root=None) -> dict[str, Any]:
    candidate_record = read_json(_candidate_path(str(candidate_id), runtime_root))
    if not candidate_record or not valid(candidate_record):
        return {"ok": False, "status": "architecture_goal_candidate_not_found", "goal_activated": False, "action_executed": False, **DENIED_AUTHORITY}
    current = build_repository_inventory(Path(source_root).resolve(), runtime_root=runtime_root)["inventory"]
    if str(candidate_record.get("workspace_digest") or "") != str(current.get("workspace_digest") or "") or str(candidate_record.get("source_manifest_digest") or "") != str(current.get("source_manifest_digest") or ""):
        return {"ok": False, "status": "architecture_goal_candidate_stale", "goal_activated": False, "action_executed": False, **DENIED_AUTHORITY}
    c = {k: v for k, v in candidate_record.items() if k not in {"record_digest", "contract_version", "workspace_digest", "source_manifest_digest"}}
    discovery = {"workspace_digest": current.get("workspace_digest"), "source_manifest_digest": current.get("source_manifest_digest")}
    plan_result = build_refactor_migration_plan(source_root, [c["target_path"]], objective="reduce architectural fragmentation while preserving behavior and governance", runtime_root=runtime_root, analysis_id=str(c.get("analysis_id") or ""))
    plan = plan_result.get("plan") or {}; goal_id = "architecture-project-goal-" + digest({"candidate": c["candidate_id"], "analysis": c["analysis_id"], "plan": plan.get("plan_id")})[:24]
    acceptance = {"behavior_preserved": True, "governance_authority_unchanged": True, "legacy_compatibility_explicit": True, "focused_tests_required": True,
                  "combined_regression_required": True, "source_only_checkpoint_required": True, "target_line_count_should_decrease": int(c["line_count"]),
                  "target_top_level_symbol_count_should_decrease": int(c["top_level_symbol_count"]), "baseline_dependency_cycle_count": int(c.get("dependency_cycle_count") or 0),
                  "new_dependency_cycles_allowed": 0, "unexplained_regressions_allowed": 0}
    goal_evidence_digest = digest({"candidate_id": c["candidate_id"], "analysis_id": c["analysis_id"], "migration_plan_id": plan.get("plan_id"), "acceptance_criteria": acceptance})
    row = seal({"contract_version": CONTRACT_VERSION, "goal_id": goal_id, "goal_evidence_digest": goal_evidence_digest, "candidate_id": c["candidate_id"], "workspace_digest": discovery.get("workspace_digest"),
                "source_manifest_digest": discovery.get("source_manifest_digest"), "target_path": c["target_path"], "target_path_digest": c["target_path_digest"],
                "objective": "Reduce architectural fragmentation around the selected hotspot while preserving behavior, compatibility, privacy, rollback, and operator authority.",
                "architecture_reasons": c["architecture_reasons"], "risk": c["risk"], "risk_reasons": c["risk_reasons"], "analysis_id": c["analysis_id"], "migration_plan_id": plan.get("plan_id"),
                "acceptance_criteria": acceptance, "goal_activated": False, "operator_selection_required": True, "operator_authorization_required_before_mutation": True,
                "source_modified": False, "tests_executed": False, "provider_contacted": False, "action_executed": False, **DENIED_AUTHORITY})
    atomic_json(_record_path(goal_id, runtime_root), row)
    return {"ok": True, "status": "architecture_project_goal_ready_for_operator_review", "goal": public_architecture_project_goal(row), "action_executed": False, **DENIED_AUTHORITY}


def public_architecture_project_goal(row: dict[str, Any]) -> dict[str, Any]:
    return {"contract_version": CONTRACT_VERSION, "goal_id": row.get("goal_id"), "goal_evidence_digest": row.get("goal_evidence_digest"), "candidate_id": row.get("candidate_id"),
            "workspace_digest": row.get("workspace_digest"), "source_manifest_digest": row.get("source_manifest_digest"), "target_path_digest": row.get("target_path_digest"),
            "architecture_reasons": list(row.get("architecture_reasons") or []), "risk": row.get("risk"), "risk_reasons": list(row.get("risk_reasons") or []), "analysis_id": row.get("analysis_id"),
            "migration_plan_id": row.get("migration_plan_id"), "acceptance_criteria": dict(row.get("acceptance_criteria") or {}), "goal_activated": False, "operator_selection_required": True,
            "operator_authorization_required_before_mutation": True, "source_modified": False, "tests_executed": False, "source_paths_exposed": False, "action_executed": False, **DENIED_AUTHORITY}


def load_architecture_project_goal(goal_id: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_record_path(str(goal_id), runtime_root)); return (row if include_private else public_architecture_project_goal(row)) if row and valid(row) else {}


def prepare_architecture_autonomous_developer_bridge(goal_id: str, *, operator_selection_receipt: dict[str, Any] | None, runtime_root=None) -> dict[str, Any]:
    goal = load_architecture_project_goal(goal_id, runtime_root=runtime_root, include_private=True)
    if not goal:
        return {"ok": False, "status": "architecture_goal_not_found", "campaign_started": False, "action_executed": False, **DENIED_AUTHORITY}
    goal_digest = str(goal.get("goal_evidence_digest") or "")
    auth = validate_operator_authorization(operator_selection_receipt, stage="candidate_selection", subject_id=str(goal_id), subject_digest=goal_digest)
    if not auth.get("ok"):
        return {"ok": False, "status": "exact_operator_goal_selection_required", "campaign_started": False, "action_executed": False, **DENIED_AUTHORITY}
    contract = build_goal_to_candidate_contract(goal_id=str(goal_id), goal_digest=goal_digest, baseline_source_digest=str(goal.get("source_manifest_digest") or ""), scope_digest=digest(str(goal.get("target_path") or "")))
    architecture_artifact_digest = digest({"goal_evidence_digest": goal_digest, "analysis_id": goal.get("analysis_id"), "migration_plan_id": goal.get("migration_plan_id"), "acceptance_criteria": goal.get("acceptance_criteria")})
    stage_evidence = build_stage_evidence(stage="architecture", artifact_digest=architecture_artifact_digest, owner="deep_project_understanding")
    return {"ok": bool(contract.get("ok")) and bool(stage_evidence.get("ok")), "status": "architecture_developer_bridge_ready", "goal_id": str(goal_id), "goal_evidence_digest": goal_digest,
            "operator_selection_authorization_id": auth.get("authorization_id"), "operator_selection_receipt_digest": auth.get("receipt_digest"), "developer_contract": contract,
            "architecture_stage_evidence": stage_evidence, "campaign_started": False, "workspace_prepared": False, "implementation_executed": False, "tests_executed": False,
            "source_modified": False, "candidate_installed": False, "candidate_promoted": False, "provider_contacted": False, "action_executed": False, **DENIED_AUTHORITY}


__all__ = ["CONTRACT_VERSION", "discover_architecture_goal_candidates", "prepare_architecture_project_goal", "public_architecture_project_goal", "load_architecture_project_goal", "prepare_architecture_autonomous_developer_bridge"]
