from __future__ import annotations
import hashlib, json
from conscious_agent.supervised_project_development_lineage import STAGES,create_project_stage_receipt,integrate_supervised_project_development
from conscious_agent.supervised_project_outcome_learning import *
from conscious_agent.supervised_project_outcome_learning_checkpoint import build_supervised_project_outcome_learning_checkpoint

def h(x):return hashlib.sha256(x.encode()).hexdigest()
def require(v,m,checks): checks.append((bool(v),m))
def main():
 checks=[];rows=[];prev=""
 for s in STAGES:
  r=create_project_stage_receipt(stage=s,status="completed",artifact_digest=h(s),previous_receipt_digest=prev,operator_review_digest=h(s+"r"));rows.append(r);prev=r["receipt_digest"]
 lineage=integrate_supervised_project_development(rows)
 mapping={"accepted":"retain_approach","rejected":"avoid_rejected_approach","failed":"strengthen_failure_checks","repaired":"retain_repair_pattern"}
 for outcome,code in mapping.items():
  p=create_project_result_presentation(lineage=lineage,outcome=outcome,operator_decision_digest=h(outcome),result_evidence_digest=h(outcome+"e"),rollback_available=True)
  l=create_accountable_outcome_learning(presentation=p,lesson_codes=[code],operator_learning_review_digest=h(outcome+"l"))
  for key in ("content_free","historical_truth_preserved"): require(l.get(key) is True,key,checks)
  for key in ("production_source_modified","sandbox_modified","execution_invoked","approval_created","authority_granted","source_application_authorized","release_authorized","autonomous_action_authorized"): require(l.get(key) is False,key,checks)
  require(p["status"]=="ready_for_operator_review","presentation",checks);require(l["status"]=="learning_recorded","learning",checks)
 require(create_project_result_presentation(lineage=lineage,outcome="other",operator_decision_digest=h("a"),result_evidence_digest=h("b"))["status"]=="blocked","unsupported",checks)
 tam=dict(lineage);tam["stage_count"]=8
 require(create_project_result_presentation(lineage=tam,outcome="accepted",operator_decision_digest=h("a"),result_evidence_digest=h("b"))["status"]=="blocked","tamper",checks)
 p=create_project_result_presentation(lineage=lineage,outcome="accepted",operator_decision_digest=h("a"),result_evidence_digest=h("b"))
 require(create_accountable_outcome_learning(presentation=p,lesson_codes=["strengthen_failure_checks"],operator_learning_review_digest=h("c"))["status"]=="blocked","mismatch",checks)
 require(create_accountable_outcome_learning(presentation=p,lesson_codes=["retain_approach","retain_approach"],operator_learning_review_digest=h("c"))["status"]=="blocked","duplicate",checks)
 cp=build_supervised_project_outcome_learning_checkpoint();require(cp["ok"],"checkpoint",checks)
 failed=[m for ok,m in checks if not ok];print(json.dumps({"ok":not failed,"passed":len(checks)-len(failed),"total":len(checks),"failed":failed},sort_keys=True));return 0 if not failed else 1
if __name__=="__main__":raise SystemExit(main())
