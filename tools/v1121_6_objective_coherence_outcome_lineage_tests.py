from pathlib import Path
import json,tempfile
from conscious_agent.objective_coherence_outcome_lineage import ObjectiveCoherenceOutcomeLineageStore
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=ObjectiveCoherenceOutcomeLineageStore(Path(td)); a=s.record("e1",objective_id="obj-1",session_id="s1",outcome="retain"); req(a["result"]["objectives_reprioritized"] is False); req(s.record("e1",objective_id="obj-1",session_id="s1",outcome="retain")["idempotent"]); req(s.record("e2",objective_id="obj-1",session_id="s1",outcome="retain")["status"]=="duplicate_outcome_suppressed"); b=s.record("e3",objective_id="obj-1",session_id="s2",outcome="reprioritization_candidate"); req(b["status"]=="objective_coherence_outcome_lineage_recorded"); ids=[x["outcome_id"] for x in s.snapshot()["outcomes"]]; req(len(ids)==2); req(s.supersede("e4",outcome_id=ids[0],successor_outcome_id=ids[1])["result"]["history_preserved"]); snap=s.snapshot(); req(snap["outcomes"][0]["state"]=="superseded"); req(len(snap["outcomes"][0]["history"])==2); i=s.inspection_summary(); req(i["history_preserved"] and not i["objectives_reprioritized"] and not i["objective_abandoned"]); req(not any(i["authority_boundary"].values()))
print(json.dumps({"passed":passed,"total":10,"suite":"v1121.6"}))
