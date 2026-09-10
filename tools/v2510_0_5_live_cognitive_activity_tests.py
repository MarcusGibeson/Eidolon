from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
checks=[]
def req(v,n): checks.append(n); assert v,n
cases=[
 {'event':'accepted','operation_id':'op1','message':'SECRET USER TEXT'},
 {'event':'meta','provider':'ollama','prompt':'PRIVATE PROMPT'},
 {'event':'status','stage':'governed_action','message':'RAW INTERNAL STATUS'},
 {'event':'action','action':{'arguments':{'secret':'x'}}},
 {'event':'action_result','execution':{'raw_output':'secret'}},
 {'event':'conversation_complete','result':{'success':True,'response':'secret answer'}},
 {'event':'saved','turn':{'user_message':'secret'}},
 {'event':'error','message':'sensitive stack trace'},
]
for idx,c in enumerate(cases):
    a=project_live_activity(c,operation_id='op1')
    req(a is not None,f'projected_{idx}')
    blob=str(a)
    req('SECRET USER TEXT' not in blob and 'PRIVATE PROMPT' not in blob and 'RAW INTERNAL STATUS' not in blob and 'secret answer' not in blob and 'sensitive stack trace' not in blob,f'content_minimized_{idx}')
    req(not a['hidden_reasoning_exposed'],f'no_hidden_reasoning_{idx}')
req(project_live_activity({'event':'delta','text':'assistant response'}) is None,'deltas_not_republished')
req(project_live_activity({'event':'keepalive'}) is None,'keepalive_ignored')
print({'ok':True,'passed':len(checks),'total':len(checks),'checks':checks})
