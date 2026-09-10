from pathlib import Path
import tempfile
from conscious_agent.sandbox_change_candidates import SandboxChangeCandidateStore,STATES
from conscious_agent.sandbox_change_eligibility import SandboxChangeEligibilityStore
from conscious_agent.json_storage import write_json_atomic
checks=[]
def check(n,v): checks.append((n,bool(v))); print(("PASS" if v else "FAIL"),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/"cognition"; e=SandboxChangeEligibilityStore(r); r.mkdir(parents=True,exist_ok=True); s=e._load(); s["eligibility_records"].append({"eligibility_id":"se-1","arbitration_id":"arb-1","test_plan_candidate_id":"tp-1","test_plan_eligibility_ids":["te-1"],"specification_candidate_ids":["sp-1"],"proposal_candidate_ids":["pr-1"],"deficiency_candidate_ids":["df-1"],"change_category":"source_repair","component_ids":["component:a"],"path_digests":["a"*64],"operation_categories":["modify_candidate_file"],"isolation_profile_id":"iso","resource_budget_id":"budget","project_digests":["pd"],"scope_digests":["sd"],"evidence_ids":["ev"],"estimated_cost":.4,"reversibility":.9,"containment_confidence":.9,"prerequisite_ids":[],"operator_review_required":False,"state":"eligible"}); write_json_atomic(e.path,s,expected_type=dict,sort_keys=True)
 st=SandboxChangeCandidateStore(r); x=st.register("c1",eligibility_ids=["se-1"]); check("active",x["state"]=="active"); row=st._load()["candidates"][0]; check("lineage",row["test_plan_candidate_ids"]==["tp-1"] and row["deficiency_candidate_ids"]==["df-1"]); check("scope",row["path_digests"] and row["operation_categories"]); check("no patch",not row["patch_text_digest"] and not row["sandbox_id"]); check("states",len(STATES)==11); check("authority inert",not any(st.inspection_summary()["authority_boundary"].values()))
assert all(v for _,v in checks); print(f"RESULT {sum(v for _,v in checks)}/{len(checks)}")
