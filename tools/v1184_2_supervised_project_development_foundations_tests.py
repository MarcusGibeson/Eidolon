from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from conscious_agent.supervised_project_development_lineage import *
from conscious_agent.supervised_project_development_foundations_checkpoint import build_supervised_project_development_foundations_checkpoint
checks=[]
def req(v): checks.append(bool(v))
def h(v): return hashlib.sha256(v.encode()).hexdigest()
rows=[]; previous=""
for stage in STAGES:
    row=create_project_stage_receipt(stage=stage,status="completed",artifact_digest=h(stage),previous_receipt_digest=previous,operator_review_digest=h(stage+"review"),public_evidence_digest=h(stage+"evidence")); rows.append(row); previous=row["receipt_digest"]
    req(row["content_free"] is True); req(row["source_modified"] is False); req(row["execution_invoked"] is False); req(row["authority_granted"] is False)
for n in range(1,10):
    result=integrate_supervised_project_development(rows[:n]); req(result["error_count"]==0); req(result["stage_count"]==n); req(result["content_free"] is True); req(result["authority_granted"] is False); req(result["execution_invoked"] is False)
    req(result["complete_lineage"] is (n==9)); req(result["status"] == ("complete_review_required" if n==9 else "in_progress_review_required"))
complete=integrate_supervised_project_development(rows); public=supervised_project_development_public_summary(complete)
req(public["content_free"] is True); req("stage_receipt_digests" not in public); req(public["authority_granted"] is False)
for mutation, error in [
    ((2,"artifact_digest","x"*64),"invalid_artifact_digest"),
    ((2,"receipt_digest","0"*64),"tampered_receipt"),
    ((2,"previous_receipt_digest","f"*64),"lineage_link_mismatch"),
    ((2,"content_free",False),"privacy_contract_violation"),
    ((2,"source_modified",True),"authority_or_execution_expansion"),
    ((2,"execution_invoked",True),"authority_or_execution_expansion"),
    ((2,"authority_granted",True),"authority_or_execution_expansion"),
    ((2,"status","invented"),"unsupported_stage_status"),
]:
    bad=[dict(x) for x in rows[:3]]; i,k,v=mutation; bad[i][k]=v; req(error in integrate_supervised_project_development(bad)["errors"])
reordered=[rows[1],rows[0]]; req("stage_order_mismatch" in integrate_supervised_project_development(reordered)["errors"])
duplicate=[rows[0],dict(rows[0])]; req("duplicate_stage" in integrate_supervised_project_development(duplicate)["errors"])
req(integrate_supervised_project_development([])["status"]=="blocked")
req(integrate_supervised_project_development(rows+[rows[-1]])["status"]=="blocked")
report=build_supervised_project_development_foundations_checkpoint(source_root=ROOT,runtime_root=ROOT/"data")
for key in ("ok","read_only","content_free"): req(report[key] is True)
for key in ("production_source_modified","sandbox_modified","execution_invoked","provider_contacted","model_contacted","approval_created","authority_granted","source_application_authorized","release_authorized"): req(report[key] is False)
req(report["contract_version"]=="v1184.2"); req(report["desktop_verification_deferred_until_v1200"] is True)
text=json.dumps({"passed":sum(checks),"total":len(checks),"ok":all(checks)},sort_keys=True); print(text)
raise SystemExit(0 if all(checks) else 1)
