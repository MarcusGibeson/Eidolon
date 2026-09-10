from __future__ import annotations
import json, os, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1253-0-2-')
from critical_path_runtime import build_critical_path_decision,critical_path_public_receipt
from goal_planning_bundle import deferred_goal_planning_stub
from work_coalescing import TurnWorkCache
from bounded_internal_maintenance import enqueue_internal_maintenance,internal_maintenance_status,schedule_post_turn_housekeeping
checks=[]
def req(v): checks.append(bool(v)); assert v
ordinary=SimpleNamespace(lane='social',planning_relevant=False,development_relevant=False,action_relevant=False)
decision=build_critical_path_decision('Hi!',relevance=ordinary,action_projection={},development_campaign={})
req(decision.goal_planning_deferred); req(not decision.goal_planning_pre_provider); req(decision.memory_retrieval_pre_provider); req(decision.response_policy_pre_provider)
receipt=critical_path_public_receipt(decision,pre_provider_ms=12); req(receipt['pre_provider_ms']==12); req(receipt['provider_contact_authorized'] is False); req(receipt['independent_authority_granted'] is False)
planning=SimpleNamespace(lane='planning',planning_relevant=True,development_relevant=False,action_relevant=False)
req(build_critical_path_decision('plan this',relevance=planning).goal_planning_pre_provider)
action=SimpleNamespace(lane='action',planning_relevant=False,development_relevant=False,action_relevant=True)
req(build_critical_path_decision('run diagnostics',relevance=action).goal_planning_pre_provider)
stub=deferred_goal_planning_stub(); req(stub['deferred_stub']); req(stub['goal_and_planning_alpha_projection']['prompt_section']==''); req(stub['goal_and_planning_alpha_projection']['policy']['action_execution_authorized'] is False)
calls={'n':0}
def build(): calls['n']+=1; return {'nested':{'value':calls['n']}}
cache=TurnWorkCache(); a=cache.get('x',build); a['nested']['value']=99; b=cache.get('x',build); req(calls['n']==1); req(b=={'nested':{'value':1}}); req(cache.receipt()['coalesced_hits']==1); req(cache.receipt()['turn_local_only'])
try: enqueue_internal_maintenance('provider_call'); req(False)
except ValueError: req(True)
post=schedule_post_turn_housekeeping('session-test'); req(post['ok']); req(all(row['content_free'] for row in post['receipts'])); req(all(row['authority_granted'] is False for row in post['receipts']))
status=internal_maintenance_status(); req(status['max_pending']==64); req(status['allowed_kinds']==['persistent_index_health_sample','projection_cache_prune']); req(status['provider_contact_authorized'] is False); req(status['tool_execution_authorized'] is False); req(status['project_mutation_authorized'] is False)
source=(ROOT/'conscious_agent/conversation_runtime.py').read_text(encoding='utf-8'); req('_complete_deferred_goal_planning' in source); req('schedule_post_turn_housekeeping' in source); req('TurnWorkCache' in source)
# The heavy planning stack must not be eagerly imported by conversation_runtime.
import subprocess
env=dict(os.environ); env['PYTHONPATH']=str(ROOT/'conscious_agent')
probe="import sys,conversation_runtime; print(int(any(n in sys.modules for n in ['internally_generated_goal_runtime','hierarchical_planning_runtime','plan_simulation_runtime','persistent_follow_through_runtime','goal_and_planning_alpha_runtime'])))"
p=subprocess.run([sys.executable,'-c',probe],cwd=ROOT,env=env,text=True,capture_output=True,timeout=10); req(p.returncode==0); req(p.stdout.strip()=='0')
r={'suite':'v1253.0-v1253.2-critical-path-work-efficiency','ok':all(checks),'passed':sum(checks),'total':len(checks)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
