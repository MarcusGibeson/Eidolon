from pathlib import Path
import json,tempfile
from conscious_agent.identity_revision_lineage import IdentityRevisionLineageStore
from conscious_agent.self_model_stability_review import SelfModelStabilityReviewer
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); l=IdentityRevisionLineageStore(root); r=SelfModelStabilityReviewer(root); req(r.review(claim_id="none")["status"]=="insufficient_evidence")
 for n,out in enumerate(["retain","replace_candidate","retain"],1): l.record(f"e{n}",claim_id="claim-1",session_id=f"s{n}",outcome=out)
 x=r.review(claim_id="claim-1",operator_review_required=True); req(x["sample_size"]==3); req(x["identity_oscillation_detected"]); req(x["reversal_count"]==2); req(x["false_instability_suppressed"] is False); req(x["operator_review_proposal"]["applied"] is False); req(not x["identity_revised"] and not x["self_model_revised"]); req(not x["temporary_state_promoted"]); req(not x["approval_granted"] and not x["authorization_granted"] and not x["external_action_executed"]); req(r.inspection_summary()["contract_version"]=="v1120.7")
print(json.dumps({"passed":passed,"total":10,"suite":"v1120.7"}))
