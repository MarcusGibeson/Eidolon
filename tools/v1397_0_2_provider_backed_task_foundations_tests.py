import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from representative_provider_backed_task import run_provider_backed_task
from v1397_test_support import *
passed=0
with tempfile.TemporaryDirectory() as td:
 r=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=local_provider,provider_use_authorized=True);require(r['ok'],'task');passed+=1
 t=r['provider_backed_task'];require(t['provider_called'] and t['provider_response_accepted'],'provider');passed+=1
 require(t['provider_configured_local'] and t['provider_endpoint_verified_loopback'] and t['remote_provider_contacted'] is False and t['private_project_content_transmitted'] is False,'privacy');passed+=1
 require(t['file_count']==3 and t['verification_exit_code']==0 and t['runnable_result_ready'],'result');passed+=1
 require(t['offline_fallback_available'] and not t['offline_fallback_used'],'fallback ready');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1397-foundations'})
