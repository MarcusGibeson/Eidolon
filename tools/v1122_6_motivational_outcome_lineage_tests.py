from pathlib import Path
import json,tempfile
from conscious_agent.motivational_outcome_lineage import MotivationalOutcomeLineageStore
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 s=MotivationalOutcomeLineageStore(Path(td)); a=s.record('e1',drive_id='d1',session_id='s1',outcome='retain_drive'); req(a['status']=='motivational_outcome_lineage_recorded'); req(s.record('e1',drive_id='d1',session_id='s1',outcome='retain_drive')['idempotent']); req(s.record('e2',drive_id='d1',session_id='s1',outcome='retain_drive')['status']=='duplicate_outcome_suppressed'); b=s.record('e3',drive_id='d1',session_id='s2',outcome='decay_transient_urgency'); req(b['status']=='motivational_outcome_lineage_recorded'); ids=[x['outcome_id'] for x in s.snapshot()['outcomes']]; req(len(ids)==2); req(s.supersede('e4',outcome_id=ids[0],successor_outcome_id=ids[1])['result']['history_preserved']); snap=s.snapshot(); req(snap['outcomes'][0]['state']=='superseded'); req(len(snap['outcomes'][0]['history'])==2); i=s.inspection_summary(); req(i['history_preserved'] and not i['attention_selected'] and not i['initiative_created']); req(not any(i['authority_boundary'].values()))
print(json.dumps({'passed':passed,'total':10,'suite':'v1122.6'}))
