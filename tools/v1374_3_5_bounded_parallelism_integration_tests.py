import sys,time,threading;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from bounded_parallelism import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1374_test_support import *
P=0;events=[];lock=threading.Lock()
def runner(t):
 with lock:events.append(('start',t,time.monotonic()))
 time.sleep(.16 if t!='write-a' else .02)
 with lock:events.append(('end',t,time.monotonic()))
 return {'done':t}
st=time.monotonic();r=run_bounded_parallel(campaign_record_digest=C,tasks=TASKS,runner=runner,max_parallel=2,cpu_budget=2,memory_budget_mb=128);elapsed=time.monotonic()-st;req(r['ok'],'run');P+=1
req(elapsed<.31,'concurrent reads/tests');P+=1
starts={t:x for k,t,x in events if k=='start'};ends={t:x for k,t,x in events if k=='end'};req(starts['write-a']>=max(ends['read-a'],ends['test-b']),'mutation after lane');P+=1
plan=build_bounded_parallel_plan(campaign_record_digest=C,tasks=TASKS,max_parallel=2,cpu_budget=2,memory_budget_mb=128)['parallel_plan'];c=process_ordinary_chat_development_turn('show parallel plan',project_state={'parallel_plan':plan});req(c.get('active') and c.get('ok'),'chat');P+=1
req(not c['action_executed'] and not c['execution_authority_created'],'chat safe');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1374-integration'})
