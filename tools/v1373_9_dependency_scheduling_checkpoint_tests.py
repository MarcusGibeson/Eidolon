import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from dependency_scheduling import *
from v1373_test_support import *
P=0;r=build_dependency_schedule(campaign_record_digest=C,tasks=TASKS);s=r['dependency_schedule'];req(r['ok'],'checkpoint');P+=1
req(s['ready_count']==2 and s['held_count']==1,'dispatchable');P+=1
req(s['critical_path_units']>0,'path');P+=1
req(s['content_free'] and s['read_only'],'evidence');P+=1
req(not r['project_mutation_authorized'] and not r['independent_authority_granted'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1373-checkpoint'})
