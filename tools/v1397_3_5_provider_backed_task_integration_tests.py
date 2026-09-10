import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from representative_provider_backed_task import run_provider_backed_task,process_provider_backed_task_control
from v1397_test_support import *
passed=0
with tempfile.TemporaryDirectory() as td:
 r=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=local_provider,provider_use_authorized=True);t=r['provider_backed_task']
 require(t['feature_behavior']=={'label_prefix':'gamma','empty_label':'none'},'provider plan applied');passed+=1
 require(len(t['payload_digest'])==64 and len(t['provider_id_digest'])==64,'evidence digests');passed+=1
 c=process_provider_backed_task_control('show provider backed task',project_state={'provider_backed_task':t});require(c['active'] and c['ok'] and not c['action_executed'],'inspection');passed+=1
 require(not t['remote_provider_contacted'] and not t['remote_provider_contact_authorized'],'local only');passed+=1
 require(not t['eidolon_source_mutation_authorized'] and not t['release_authorized'],'authority');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1397-integration'})
