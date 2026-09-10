from __future__ import annotations
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1'); os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1251-3-5-'))
import local_model
from local_model import LocalModelConfig, LocalModelClient, OllamaProvider
from response_time_runtime import trusted_action_acknowledgement, generation_token_budget
checks=[]
def req(v): checks.append(bool(v)); assert v
ack=trusted_action_acknowledgement({'grounding':{'capability_id':'run_diagnostics'}}); req('run diagnostics' in ack); req('Nothing has executed or been approved yet.' in ack)
cr=(ROOT/'conscious_agent/conversation_runtime.py').read_text(); req('first_visible_feedback' in cr); req('action_response_guarded' in cr); req('"event": "replace"' in cr); req('trusted_action_acknowledgement' in cr)
eid=(ROOT/'eidolon.py').read_text(); launch=(ROOT/'conscious_agent/chat_launcher.py').read_text(); req('chat_launcher.py' in eid); req('from main import' not in launch); req('stream_conversation_turn' in launch)
# Cold launcher benchmark with immediate quit. Loose bound allows slower CI while catching a return to the ~4s monolithic launcher.
env=dict(os.environ); env['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1251-launch-'); env['PYTHONDONTWRITEBYTECODE']='1'
t0=time.perf_counter(); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'chat'],input='q\n',text=True,capture_output=True,cwd=ROOT,env=env,timeout=8); elapsed=time.perf_counter()-t0
req(p.returncode==0); req('Eidolon chat mode started.' in p.stdout); req(elapsed<6.0)
config=LocalModelConfig(); a=local_model._shared_http_session(config); b=local_model._shared_http_session(config); req(a is b)
client1=LocalModelClient(config); client2=LocalModelClient(config); req(client1.provider.session is client2.provider.session); client1.close(); req(client2.provider.session is b); client2.close()
class Resp:
    def __init__(self,data): self._data=data; self.status_code=200; self.text=''
    def json(self): return self._data
    def close(self): pass
class Session:
    def request(self,*args,**kwargs): return Resp({'model':'qwen2.5:7b','response':'ok','done':True,'load_duration':10,'prompt_eval_count':123,'prompt_eval_duration':1_000,'eval_count':7,'eval_duration':2_000,'total_duration':3_010})
    def close(self): pass
provider=OllamaProvider(config,session=Session()); req(provider.generate('x')=='ok'); req(provider.last_metrics['prompt_eval_count']==123); req(provider.last_metrics['eval_count']==7)
req(generation_token_budget('Hi!',350)<350); req(generation_token_budget('Run diagnostics',350)<=192); req(generation_token_budget('Explain architecture comprehensively',350)==350)
r={'suite':'v1251.3-v1251.5-action-startup-provider-efficiency','ok':all(checks),'passed':sum(checks),'total':len(checks),'cold_launcher_seconds':round(elapsed,4)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
