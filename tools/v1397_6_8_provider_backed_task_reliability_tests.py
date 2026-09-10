import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from representative_provider_backed_task import run_provider_backed_task
from v1397_test_support import *
passed=0
with tempfile.TemporaryDirectory() as td:
 r=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=local_provider,provider_use_authorized=False);t=r['provider_backed_task'];require(r['ok'] and not t['provider_called'] and t['offline_fallback_used'],'unauthorized fallback');passed+=1
with tempfile.TemporaryDirectory() as td:
 remote=dict(CONFIG,provider_class='local',privacy_tier='local_only',endpoint='https://example.com/v1');r=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=remote,provider_call=local_provider,provider_use_authorized=True);require(r['ok'] and r['provider_backed_task']['offline_fallback_used'] and not r['provider_backed_task']['provider_called'],'remote blocked');passed+=1
with tempfile.TemporaryDirectory() as td:
 def boom(_): raise RuntimeError('offline')
 r=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=boom,provider_use_authorized=True);require(r['ok'] and r['provider_backed_task']['offline_fallback_used'],'provider failure fallback');passed+=1
with tempfile.TemporaryDirectory() as td:
 r=run_provider_backed_task(request='make something',runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=local_provider,provider_use_authorized=True);require(not r['ok'] and not r['action_executed'],'unsupported');passed+=1
with tempfile.TemporaryDirectory() as td:
 r=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=local_provider,provider_use_authorized=True);d=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=local_provider,provider_use_authorized=True);require(r['ok'] and not d['ok'] and d['status']=='provider_backed_task_already_exists','duplicate');passed+=1
 require(not any('__pycache__' in p.parts or p.suffix=='.pyc' for p in Path(td).rglob('*')),'workspace bytecode');
with tempfile.TemporaryDirectory() as td:
 def bad(_): return {'label_prefix':'../../secret','empty_label':'x'}
 r=run_provider_backed_task(request=REQUEST,runtime_root=td,task_id=TASK_ID,provider_config=CONFIG,provider_call=bad,provider_use_authorized=True);require(r['ok'] and r['provider_backed_task']['offline_fallback_used'],'malformed response');passed+=1
 require(r['provider_backed_task']['workspace_path_exposed_in_evidence'] is False,'path privacy');passed+=1
print({'ok':passed==7,'passed':passed,'total':7,'suite':'v1397-reliability'})
