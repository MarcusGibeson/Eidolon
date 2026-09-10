from __future__ import annotations
"""v1148.7 content-free privacy/security reliability review."""
import hashlib, json
from pathlib import Path
from privacy_security_continuity import build_privacy_security_continuity_inspection
from privacy_security_bounded_execution import build_privacy_security_bounded_execution_inspection
from privacy_security_findings_receipts import build_privacy_security_findings_receipts_inspection
CONTRACT_VERSION="v1148.7"
def _digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def build_privacy_security_reliability(runtime_root=None):
 c=build_privacy_security_continuity_inspection(runtime_root);e=build_privacy_security_bounded_execution_inspection(runtime_root);f=build_privacy_security_findings_receipts_inspection(runtime_root)
 cr=c.get("recent_records",[]);er=e.get("recent_records",[]);fr=f.get("recent_records",[])
 unresolved=sum(x.get("state") in {"review_required","recovery_failed"} for x in er+fr)
 recurrence=sum(int(x.get("repeated_finding_count") or 0) for x in cr)
 drift=sum(bool(x.get("drift_detected")) for x in cr)
 orphan=sum(int(x.get("orphan_finding_count") or 0) for x in cr)
 recovered=sum(x.get("state")=="recovered" for x in fr);contained=sum(x.get("state")=="contained" for x in fr)
 issue_count=unresolved+recurrence+drift+orphan
 score=max(0,100-issue_count*10);uncertainty=min(100,issue_count*8+(10 if not cr else 0));classification="reliable" if score>=90 and uncertainty<=10 else "review_required"
 report={"contract_version":CONTRACT_VERSION,"review_id":f"privacy-security-reliability:{len(cr)}","continuity_record_count":len(cr),"execution_count":len(er),"finding_count":len(fr),"unresolved_count":unresolved,"repeated_finding_count":recurrence,"drift_count":drift,"orphan_finding_count":orphan,"contained_count":contained,"recovered_count":recovered,"reliability_score":score,"uncertainty":uncertainty,"classification":classification,"operator_visible_state":"ready" if classification=="reliable" else "attention","raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"runtime_mutated":False,"source_modified":False,"read_only":True};report["structural_digest"]=_digest(report);return report
