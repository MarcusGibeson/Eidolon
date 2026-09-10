from __future__ import annotations
"""v1285.3-v1285.5 integration with modern supervised planning evidence."""
import hashlib,json
from typing import Any,Mapping,Sequence
from hierarchical_goal_management_foundations import *
CONTRACT_VERSION="v1285.5"
def intent_digest_for_operator_contract(contract:Mapping[str,Any])->str:
 safe={"objective_code":str(contract.get("objective_code") or "unknown"),"acceptance_codes":sorted(str(x) for x in contract.get("acceptance_codes") or []),"scope_codes":sorted(str(x) for x in contract.get("scope_codes") or [])};return hashlib.sha256(json.dumps(safe,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def hierarchy_from_supervised_plan(plan:Mapping[str,Any],*,operator_contract:Mapping[str,Any])->dict[str,Any]:
 intent=intent_digest_for_operator_contract(operator_contract);milestones=list(plan.get("milestone_codes") or plan.get("phase_codes") or []);milestones=milestones or ["inspect_evidence","implement_candidate","verify_candidate","operator_review"];return build_goal_hierarchy(objective_code=str(operator_contract.get("objective_code") or plan.get("objective_code") or "development_objective"),original_intent_digest=intent,milestone_codes=milestones,acceptance_codes=operator_contract.get("acceptance_codes") or [],risk_codes=plan.get("risk_codes") or [])
def public_goal_hierarchy_summary(hierarchy:Mapping[str,Any])->dict[str,Any]:
 v=validate_goal_hierarchy(hierarchy);return {"ok":v.get("ok"),"objective_code":hierarchy.get("objective_code"),"milestone_count":hierarchy.get("milestone_count"),"hierarchy_depth":hierarchy.get("hierarchy_depth"),"acceptance_count":len(hierarchy.get("acceptance_codes") or []),"risk_count":len(hierarchy.get("risk_codes") or []),"original_intent_digest":hierarchy.get("original_intent_digest"),"raw_operator_request_exposed":False,"plan_activated":False,**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","intent_digest_for_operator_contract","hierarchy_from_supervised_plan","public_goal_hierarchy_summary","validate_goal_hierarchy","AUTHORITY_FLAGS"]
