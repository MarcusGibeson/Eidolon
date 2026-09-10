import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from multi_day_continuity import *
from v1379_test_support import *
P0=0
r=capsule();req(r['ok'],'capsule');P0+=1
x=r['continuity_capsule'];req(x['completed_steps']==2 and x['remaining_steps']==3,'progress');P0+=1
req(x['chat_history_required'] is False and not x['raw_chat_persisted'],'chat independent');P0+=1
req(x['content_free'] and r['capsule_byte_count']<8192,'compact');P0+=1
req(not r['automatic_resume_authorized'] and not r['work_execution_authorized'],'authority');P0+=1
print({'ok':P0==5,'passed':P0,'total':5,'suite':'v1379-foundations'})
