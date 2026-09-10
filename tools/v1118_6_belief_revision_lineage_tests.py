from pathlib import Path
import tempfile
from conscious_agent.belief_revision_lineage import BeliefRevisionLineageStore
p=f=0
def req(x):
 global p,f;p+=bool(x);f+=not bool(x)
with tempfile.TemporaryDirectory() as td:
 s=BeliefRevisionLineageStore(Path(td)); a=s.record('e1',belief_id='b1',session_id='s1',outcome='retain');req(a['ok']);rid=a['result']['revision_id'];req(not a['result']['belief_mutated']);req(s.record('e1',belief_id='b1',session_id='s1',outcome='retain')['idempotent']);req(s.record('e2',belief_id='b1',session_id='s1',outcome='retain')['status']=='duplicate_revision_suppressed');b=s.record('e3',belief_id='b1',session_id='s2',outcome='weaken',predecessor_revision_id=rid);req(b['ok']);rid2=b['result']['revision_id'];z=s.supersede('e4',revision_id=rid,successor_revision_id=rid2);req(z['result']['history_preserved']);snap=s.snapshot();req(len(snap['revisions'])==2);req(snap['revisions'][0]['state']=='superseded');i=s.inspection_summary();req(i['history_preserved'] and not i['belief_mutated']);req(not any(i['authority_boundary'].values()))
print(f'v1118.6 belief revision lineage: {p}/10 passed');raise SystemExit(0 if f==0 and p==10 else 1)
