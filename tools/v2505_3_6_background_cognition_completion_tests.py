from __future__ import annotations
import json,sys,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.background_cognitive_runtime_v2505 import BackgroundCognitiveRuntime
checks=[]
def req(v,n):checks.append(n);assert v,n
class Clock:
 def __init__(self):self.t=datetime(2026,9,2,12,0,tzinfo=timezone.utc)
 def __call__(self):return self.t.isoformat().replace('+00:00','Z')
 def add(self,s):self.t+=timedelta(seconds=s)
with tempfile.TemporaryDirectory(prefix='eidolon-v2505-3-6-') as td:
 clock=Clock();rt=BackgroundCognitiveRuntime(Path(td),clock=clock);rt.configure('cfg',enabled=True,minimum_interval_seconds=5,max_cycles_per_hour=2)
 a=rt.tick('tick-a',new_experience=True,subject_ref='private experience');req(a['status']=='background_cognitive_work_opened','opened')
 try:rt.complete('bad',background_cycle_id=a['record']['background_cycle_id'],outcome_type='EXECUTE_TOOL');raise AssertionError('unsafe accepted')
 except ValueError:checks.append('unsafe_outcome_rejected')
 done=rt.complete('done-a',background_cycle_id=a['record']['background_cycle_id'],outcome_type='MEMORY_INTEGRATION_CANDIDATE',evidence_digests=['a'*64],changed_fields=['summary'],confidence=.8);req(done['record']['status']=='completed_with_candidate','candidate_recorded');req(not done['candidate_applied'],'candidate_not_applied')
 dup=rt.complete('done-a',background_cycle_id=a['record']['background_cycle_id'],outcome_type='MEMORY_INTEGRATION_CANDIDATE');req(dup['idempotent'],'completion_idempotent')
 clock.add(6);b=rt.tick('tick-b',new_experience=True,subject_ref='experience-2');req(b['status']=='background_cognitive_work_opened','second_opened');rt.complete('done-b',background_cycle_id=b['record']['background_cycle_id'],outcome_type='NO_DURABLE_CHANGE')
 clock.add(6);budget=rt.tick('tick-c',new_experience=True,subject_ref='experience-3');req('background_cycle_budget_exhausted' in budget['record']['suppression_reasons'],'hour_budget')
 final=rt.inspection_summary();req(final['open_cycle_count']==0,'no_open');req(not final['tool_executed'] and not final['source_mutated'],'no_tool_source');req(not final['hidden_reasoning_exposed'],'no_cot')
print(json.dumps({'ok':True,'contract':'v2505.3-v2505.6','passed':len(checks),'checks':checks},sort_keys=True))
