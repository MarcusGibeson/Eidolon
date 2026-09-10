from pathlib import Path
import json,tempfile
from conscious_agent.identity_revision_lineage import IdentityRevisionLineageStore
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=IdentityRevisionLineageStore(Path(td)); a=s.record("e1",claim_id="claim-1",session_id="session-1",outcome="retain",claim_type="identity_claim"); req(a["result"]["identity_revised"] is False); req(s.record("e1",claim_id="claim-1",session_id="session-1",outcome="retain",claim_type="identity_claim")["idempotent"]); req(s.record("e2",claim_id="claim-1",session_id="session-1",outcome="retain",claim_type="identity_claim")["status"]=="duplicate_revision_suppressed"); b=s.record("e3",claim_id="claim-1",session_id="session-2",outcome="weaken"); req(b["status"]=="identity_revision_lineage_recorded"); ids=[x["revision_id"] for x in s.snapshot()["revisions"]]; req(len(ids)==2); req(s.supersede("e4",revision_id=ids[0],successor_revision_id=ids[1])["result"]["history_preserved"]); snap=s.snapshot(); req(snap["revisions"][0]["state"]=="superseded"); req(len(snap["revisions"][0]["history"])==2); i=s.inspection_summary(); req(i["history_preserved"] and not i["identity_revised"] and not i["self_model_revised"]); req(not any(i["authority_boundary"].values()))
print(json.dumps({"passed":passed,"total":10,"suite":"v1120.6"}))
