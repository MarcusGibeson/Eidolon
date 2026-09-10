from __future__ import annotations
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1253-3-5-')
checks=[]
def req(v): checks.append(bool(v)); assert v
launcher=(ROOT/'conscious_agent/chat_launcher.py').read_text(); runtime=(ROOT/'conscious_agent/conversation_runtime.py').read_text(); sm=(ROOT/'conscious_agent/self_maintenance.py').read_text(); dp=(ROOT/'conscious_agent/dashboard_performance.py').read_text()
# v1253.3: conversation runtime import moved behind actual message/retry paths.
run_pos=launcher.index('def run_chat'); runtime_pos=launcher.index('from conversation_runtime import',run_pos); input_pos=launcher.index('user_message = input',run_pos); req(runtime_pos>input_pos)
env=dict(os.environ); env['PYTHONDONTWRITEBYTECODE']='1'; env['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1253-launch-')
t0=time.perf_counter(); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'chat'],input='q\n',text=True,capture_output=True,cwd=ROOT,env=env,timeout=8); elapsed=time.perf_counter()-t0
req(p.returncode==0); req('Eidolon chat mode started.' in p.stdout); req(elapsed<5.5)
# Importing conversation runtime must not drag the lazy goal/planning stack in.
probe="import sys,conversation_runtime; print(','.join(n for n in ['internally_generated_goal_runtime','hierarchical_planning_runtime','plan_simulation_runtime','persistent_follow_through_runtime','goal_and_planning_alpha_runtime'] if n in sys.modules))"
p2=subprocess.run([sys.executable,'-c',probe],cwd=ROOT,env={**env,'PYTHONPATH':str(ROOT/'conscious_agent')},text=True,capture_output=True,timeout=10); req(p2.returncode==0); req(p2.stdout.strip()=='')
# v1253.4 extraction retains the historical wrapper seam.
req((ROOT/'conscious_agent/self_maintenance_attention_primitives.py').is_file()); req('from self_maintenance_attention_primitives import attention_score_task' in sm); req('from self_maintenance_attention_primitives import attention_budget_records' in sm)
from self_maintenance_attention_primitives import attention_budget_records,attention_score_task
req(len(attention_budget_records())==4)
score=attention_score_task({'task_id':'t','goal':'g','priority_score':80,'risk_score':10,'state':'queued','created_at':'2026-08-07T00:00:00'},'2026-08-07T00:00:00',age_seconds=lambda _:0); req(score['decision']=='candidate_focus'); req(score['attention_score']==77)
# v1253.5 first status route remains outside api_server.
import dashboard
req('api_server' not in sys.modules)
t=time.perf_counter(); status,payload=dashboard.dispatch_api('GET','/api/runtime-status',query={}); fast_ms=(time.perf_counter()-t)*1000
req(status==200 and payload['ok']); req(payload['read_only']); req(payload['runtime_mutation_performed'] is False); req('api_server' not in sys.modules); req(fast_ms<100.0)
from dashboard_performance import optimize_dashboard_html_assets
html=(ROOT/'conscious_agent/dashboard.py').read_text(encoding='utf-8'); req('/api/runtime-status' in optimize_dashboard_html_assets(html)); req("window.__eidolonFullStatusStarted" in dp)
r={'suite':'v1253.3-v1253.5-import-dependency-efficiency','ok':all(checks),'passed':sum(checks),'total':len(checks),'cold_launcher_seconds':round(elapsed,4),'fast_status_ms':round(fast_ms,3)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
