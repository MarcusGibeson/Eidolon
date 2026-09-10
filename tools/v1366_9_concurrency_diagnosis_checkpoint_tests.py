from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1366_test_support import *
from concurrency_diagnosis import *
def main():
 P=0
 if 'checkpoint'=='foundations':
  for k,(ev,rep) in CASES.items():
   r=diagnose_concurrency(kind=k,events=ev,candidate_repairs=rep);req(r['ok'] and r['concurrency_diagnosis']['reproduced'] and r['concurrency_diagnosis']['repair_verified'],k);P+=1
 elif 'checkpoint'=='integration':
  for k,(ev,rep) in CASES.items():
   r=diagnose_concurrency(kind=k,events=ev,candidate_repairs=rep);v=r['concurrency_diagnosis'];req(v['deterministic_schedule'] and not v['selected_source_modified'] and not r['application_authorized'],k);P+=1
 elif 'checkpoint'=='reliability':
  req(not diagnose_concurrency(kind='bogus',events=[{'op':'x'}])['ok'],'kind');P+=1
  req(not diagnose_concurrency(kind='race',events=[])['ok'],'empty');P+=1
  ev,_=CASES['race'];r=diagnose_concurrency(kind='race',events=ev,candidate_repairs=['bogus']);req(r['concurrency_diagnosis']['reproduced'] and not r['concurrency_diagnosis']['repair_verified'],'unsupported');P+=1
  r=diagnose_concurrency(kind='race',events=[{'op':'read_modify_write','interleaved':False}],candidate_repairs=['serialized_transition']);req(r['status']=='not_reproduced','not reproduced');P+=1
  r=diagnose_concurrency(kind='duplicate_work',events=CASES['duplicate_work'][0],candidate_repairs=['idempotency_key','idempotency_key']);req(len(r['concurrency_diagnosis']['repair_trials'])==1,'dedupe');P+=1
  r=diagnose_concurrency(kind='stale_ownership',events=CASES['stale_ownership'][0],candidate_repairs=['generation_compare_and_swap']);req(r['concurrency_diagnosis']['before_violation_codes']==['stale_completion'],'class');P+=1
  req(not r['action_executed'],'read only');P+=1
 else:
  good=0
  for k,(ev,rep) in CASES.items():good+=int(diagnose_concurrency(kind=k,events=ev,candidate_repairs=rep)['concurrency_diagnosis']['repair_verified'])
  req(good==5,'all classes');P+=1
  from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
  rec=diagnose_concurrency(kind='race',events=CASES['race'][0],candidate_repairs=['serialized_transition'])['concurrency_diagnosis'];c=process_ordinary_chat_development_turn('show concurrency diagnosis',project_state={'concurrency_diagnosis':rec});req(c['active'] and c['ok'] and not c['action_executed'],'chat');P+=1
  req(rec['content_free'],'privacy');P+=1;req(not rec['source_mutation_authorized'],'authority');P+=1;req(rec['record_digest'],'digest');P+=1
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1366-checkpoint'})
if __name__=='__main__':main()
