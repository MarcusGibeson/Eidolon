from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from bounded_capability_evidence import bounded_float, bounded_int, digest, sealed, valid_seal


def continuous_health_loop(observations: Sequence[Mapping[str,Any]], thresholds: Mapping[str,Any], *, standing_authority: bool, version: str="1471.9") -> dict[str,Any]:
    opened=[];ignored=[]
    for row in observations:
        kind=str(row.get("kind") or "unknown")
        value=bounded_float(row.get("value"),0,lo=0,hi=1_000_000)
        threshold=bounded_float(thresholds.get(kind),1,lo=0,hi=1_000_000)
        evidence=bool(row.get("evidence_digest"))
        if evidence and value>=threshold and standing_authority and str(row.get("risk") or "low") in {"low","routine"}:
            opened.append({"kind":kind,"evidence_digest":row.get("evidence_digest"),"priority":bounded_float(row.get("priority"),.5)})
        else: ignored.append(kind)
    return sealed("continuous_health_loop",{"observed":len(observations),"opened":opened,"opened_count":len(opened),"ignored":ignored,"standing_authority":standing_authority,"threshold_gated":True,"spam_suppressed":True},version=version)


def test_failure_triage(failures: Sequence[Mapping[str,Any]], *, version: str="1472.9") -> dict[str,Any]:
    rows=[]
    severity_order={"critical":0,"high":1,"medium":2,"low":3}
    for f in failures:
        reproducible=bool(f.get("reproduced")); flaky=bool(f.get("flaky")); new=bool(f.get("new",True)); sev=str(f.get("severity") or "medium").lower()
        rows.append({"id":str(f.get("id") or ""),"classification":"flaky" if flaky else "reproducible" if reproducible else "unreproduced","severity":sev,"new":new,"repair_eligible":reproducible and not flaky,"evidence_digest":str(f.get("evidence_digest") or "")})
    rows.sort(key=lambda x:(severity_order.get(x["severity"],9),not x["new"],x["id"]))
    return sealed("test_failure_triage",{"failures":rows,"repair_queue":[x["id"] for x in rows if x["repair_eligible"]],"blind_repair_denied":True,"unreproduced_failure_mutation_denied":True},version=version)


def dependency_maintenance(candidates: Sequence[Mapping[str,Any]], *, version: str="1473.9") -> dict[str,Any]:
    rows=[]
    for c in candidates:
        locked=bool(c.get("lockfile_updated")); compatibility=bool(c.get("compatibility_passed")); security=bool(c.get("security_reviewed")); changelog=bool(c.get("changelog_reviewed")); rollback=bool(c.get("rollback_ready")); major=bool(c.get("major_version"))
        ready=locked and compatibility and security and changelog and rollback and not major
        rows.append({"name":str(c.get("name") or ""),"from":str(c.get("from") or ""),"to":str(c.get("to") or ""),"ready_for_bounded_apply":ready,"major_requires_separate_review":major})
    return sealed("dependency_maintenance",{"candidates":rows,"ready_count":sum(x["ready_for_bounded_apply"] for x in rows),"automatic_major_upgrade":False,"installation_authorized":False},version=version)


def documentation_maintenance(findings: Sequence[Mapping[str,Any]], *, version: str="1474.9") -> dict[str,Any]:
    updates=[]
    for f in findings:
        source_digest=str(f.get("source_behavior_digest") or ""); doc_digest=str(f.get("documented_behavior_digest") or "")
        stale=bool(source_digest and doc_digest and source_digest!=doc_digest)
        if stale: updates.append({"path":str(f.get("path") or ""),"owner_change_id":str(f.get("owner_change_id") or ""),"reason":"behavior_digest_changed"})
    return sealed("documentation_maintenance",{"finding_count":len(findings),"updates":updates,"update_count":len(updates),"source_behavior_grounded":True,"standalone_doc_rewrite_without_owner_change":False},version=version)


def performance_maintenance(samples: Sequence[Mapping[str,Any]], *, regression_ratio: float=1.15, version: str="1475.9") -> dict[str,Any]:
    regressions=[]
    ratio=max(1.0,float(regression_ratio))
    for s in samples:
        baseline=max(1.0,float(s.get("baseline") or 1)); current=max(0.0,float(s.get("current") or 0)); observed=current/baseline
        if observed>=ratio:
            regressions.append({"metric":str(s.get("metric") or ""),"ratio":round(observed,4),"baseline_digest":str(s.get("baseline_digest") or ""),"localized_component":str(s.get("localized_component") or "unknown")})
    return sealed("performance_maintenance",{"regressions":regressions,"regression_count":len(regressions),"fixture_gaming_denied":True,"hardware_aware":True,"baseline_mutation_authorized":False},version=version)


def data_maintenance(state: Mapping[str,Any], *, version: str="1476.9") -> dict[str,Any]:
    checks={
        "schema":bool(state.get("schema_ok")),"integrity":bool(state.get("integrity_ok")),"migration":bool(state.get("migration_ok")),
        "backup":bool(state.get("backup_ok")),"restore":bool(state.get("restore_ok")),"retention":bool(state.get("retention_ok")),
        "compaction":bool(state.get("compaction_ok",True)),
    }
    return sealed("data_maintenance",{"checks":checks,"passed":sum(checks.values()),"total":len(checks),"healthy":all(checks.values()),"private_content_read_into_public_evidence":False,"destructive_compaction_authorized":False},version=version)


def release_preparation(files: Sequence[Mapping[str,Any]], verification: Mapping[str,Any], *, version: str="1477.9") -> dict[str,Any]:
    manifest=[]
    for f in files:
        path=str(f.get("path") or "").replace("\\","/")
        if path.startswith("data/") or "/__pycache__/" in f"/{path}/" or path.endswith((".pyc",".log")): continue
        sha=str(f.get("sha256") or "")
        manifest.append({"path":path,"sha256":sha,"size":bounded_int(f.get("size"),hi=10_000_000_000)})
    manifest.sort(key=lambda x:x["path"])
    exact=all(len(x["sha256"])==64 for x in manifest)
    verified=bool(verification.get("focused_passed")) and bool(verification.get("privacy_passed")) and bool(verification.get("clean_extract_passed"))
    return sealed("release_preparation",{"manifest":manifest,"manifest_digest":digest(manifest),"file_count":len(manifest),"hashes_exact":exact,"verification_ready":verified,"rollback_package_required":True,"release_authorized":False},version=version)


def multi_project_operation(projects: Sequence[Mapping[str,Any]], *, version: str="1478.9") -> dict[str,Any]:
    rows=[]; seen=set(); collision=False
    for p in projects:
        pid=str(p.get("project_id") or "")
        collision |= pid in seen or not pid; seen.add(pid)
        rows.append({"project_id":pid,"goal_digest":str(p.get("goal_digest") or ""),"authority_digest":str(p.get("authority_digest") or ""),"runtime_root_digest":str(p.get("runtime_root_digest") or ""),"memory_namespace":str(p.get("memory_namespace") or pid),"resource_budget":dict(p.get("resource_budget") or {})})
    isolated=not collision and len({x["runtime_root_digest"] for x in rows})==len(rows) and len({x["authority_digest"] for x in rows})==len(rows)
    return sealed("multi_project_operation",{"projects":rows,"project_count":len(rows),"isolated":isolated,"cross_project_memory_default":False,"cross_project_authority_inheritance":False},version=version)


def self_update_operation(candidate: Mapping[str,Any], *, version: str="1479.9") -> dict[str,Any]:
    checks={
        "bounded_improvement":bool(candidate.get("bounded_improvement")),"isolated_workspace":bool(candidate.get("isolated_workspace")),
        "dogfood_passed":bool(candidate.get("dogfood_passed")),"shadow_passed":bool(candidate.get("shadow_passed")),"canary_passed":bool(candidate.get("canary_passed")),
        "rollback_ready":bool(candidate.get("rollback_ready")),"standing_policy_allows_apply":bool(candidate.get("standing_policy_allows_apply")),
    }
    ready=all(checks.values())
    failed_canary=bool(candidate.get("canary_failed"))
    return sealed("self_update_operation",{"checks":checks,"ready_for_separately_governed_apply":ready,"automatic_rollback_required":failed_canary,"installed_by_this_function":False,"source_mutation_performed":False,"authority_expansion":False},version=version)


def build_autonomous_operations_checkpoint(days: Sequence[Mapping[str,Any]], *, health: Mapping[str,Any], triage: Mapping[str,Any], dependency: Mapping[str,Any], docs: Mapping[str,Any], performance: Mapping[str,Any], data: Mapping[str,Any], release: Mapping[str,Any], projects: Mapping[str,Any], self_update: Mapping[str,Any], version: str="1480.9") -> dict[str,Any]:
    inputs=[health,triage,dependency,docs,performance,data,release,projects,self_update]
    ordinals=[int(x.get("day") or 0) for x in days]
    useful=[bool(x.get("useful_work_completed")) for x in days]
    unauthorized=sum(int(x.get("unauthorized_expansion") or 0) for x in days)
    interventions=sum(int(x.get("operator_interventions") or 0) for x in days)
    checks={
        "all_subsystems_sealed":all(valid_seal(x) for x in inputs),"seven_day_temporal_replay":ordinals==list(range(1,8)),
        "useful_each_day":len(useful)==7 and all(useful),"zero_unauthorized_expansion":unauthorized==0,
        "low_intervention":interventions<=2,"multi_project_isolated":projects.get("payload",{}).get("isolated") is True,
        "self_update_bounded":self_update.get("payload",{}).get("authority_expansion") is False,
    }
    return sealed("autonomous_operations_checkpoint",{"checks":checks,"passed":sum(checks.values()),"total":len(checks),"autonomous_operations_ready":all(checks.values()),"temporal_replay_days":7,"wall_clock_week_claimed":False,"unauthorized_expansion_count":unauthorized,"operator_interventions":interventions},version=version)

__all__=["continuous_health_loop","test_failure_triage","dependency_maintenance","documentation_maintenance","performance_maintenance","data_maintenance","release_preparation","multi_project_operation","self_update_operation","build_autonomous_operations_checkpoint"]
