import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from dependency_scheduling import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1373_test_support import *
P=0;r=build_dependency_schedule(campaign_record_digest=C,tasks=TASKS,max_ready=1);s=r['dependency_schedule'];req(len(s['selected_ready_tasks'])==1,'cap');P+=1
c=process_ordinary_chat_development_turn('show dependency schedule',project_state={'dependency_schedule':s});req(c.get('active') and c.get('ok'),'chat');P+=1
req(c['dependency_schedule']['record_digest']==s['record_digest'],'projection');P+=1
req(not c['action_executed'] and not c['task_execution_authorized'],'readonly');P+=1
req(s['critical_path_units']>=7,'critical');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1373-integration'})
