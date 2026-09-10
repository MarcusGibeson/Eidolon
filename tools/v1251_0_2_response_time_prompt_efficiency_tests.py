from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1'); os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1251-0-2-'))
from response_time_runtime import *
from response_time_efficiency import response_time_contract
checks=[]
def req(v): checks.append(bool(v)); assert v

def sec(n=1400): return {'prompt_section':'<x>'+('x'*n)+'</x>'}
base=dict(action_projection={},development_campaign={},cognitive=sec(),conversation_policy=sec(),conversation_discourse=sec(),memory_retrieval=sec(),natural_continuity=sec(),natural_follow_up=sec(),governed_speech=sec(),daily_companion=sec())
for msg,lane in [('Hi!','social'),('Tell me about this','ordinary'),('Make a roadmap','planning'),('Build a Python tool','development')]:
    prompt,diag=build_compact_cognitive_projection(msg,**base); req(diag['lane']==lane); req(len(prompt)<=3200); req(diag['estimated_projection_tokens']<=800); req(diag['internal_cognition_preserved']); req(diag['model_facing_projection_compacted']); req(diag['approval_granted'] is False)
social,sdiag=build_compact_cognitive_projection('Hi!',**base); ordinary,odiag=build_compact_cognitive_projection('Tell me about this',**base)
req(len(social)<len(ordinary)); req('planning' not in sdiag['included_sections']); req('cognition' not in sdiag['included_sections']); req('cognition' in odiag['included_sections'])
req(generation_token_budget('Hi!',350)==96); req(generation_token_budget('Thanks!',350)==96); req(generation_token_budget('Explain this in detail',350)==350); req(generation_token_budget('Brief question',350)==192); req(generation_token_budget('Explain this in detail',80)==80)
m=provider_metrics_public({'load_duration_ns':1,'prompt_eval_count':100,'prompt_eval_duration_ns':2_000_000_000,'eval_count':50,'eval_duration_ns':1_000_000_000,'total_duration_ns':3_000_000_000,'prompt':'secret','response':'secret'})
req(m['generation_tokens_per_second']==50.0); req('prompt' not in m and 'response' not in m); req(m['content_free'] is True)
contract=response_time_contract(source_root=ROOT); req(contract['ok']); req(contract['ordinary_projection_estimated_tokens']<=800); req(contract['social_projection_estimated_tokens']<=600); req(contract['passed']==contract['total'])
r={'suite':'v1251.0-v1251.2-response-time-prompt-efficiency','ok':all(checks),'passed':sum(checks),'total':len(checks)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
