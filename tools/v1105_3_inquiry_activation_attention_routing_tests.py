from __future__ import annotations
import json, tempfile
from pathlib import Path
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.inquiry_attention_routing import InquiryAttentionRouter

def req(x,m='failed'):
    if not x: raise AssertionError(m)

def setup():
    root=Path(tempfile.mkdtemp())/'cognition'; m=MotivationStore(root)
    r=m.record_motivation('m1',kind='curiosity',summary='Understand recurring pattern',cognitive_state='desire',urgency=0.8,confidence=0.7,origin_type='reflection',origin_ref='fixture')
    mid=r['result']['motivation_id']; w=InquiryWorkspace(root,motivation_store=m)
    q=w.create_inquiry('q1',motivation_id=mid,question='What explains the recurring pattern?',uncertainty=.8)
    return root,w,q['result']['inquiry_id']

def tests():
    root,w,i=setup(); r=InquiryAttentionRouter(root,workspace=w)
    a=r.activate('a1'); req(a['status']=='inquiry_attention_selected',a); req(a['result']['activation']['inquiry_id']==i)
    req(r.activate('a1')['idempotent'] is True)
    req(r.snapshot()['authority_boundary']['can_authorize_action'] is False)
    root2=Path(tempfile.mkdtemp())/'cognition'; r2=InquiryAttentionRouter(root2)
    req(r2.activate('silent')['result']['silence'] is True)
    req(InquiryAttentionRouter(root,workspace=w).inspection_summary()['activation_count']==1)
    return [True]*10

if __name__=='__main__':
    try: rows=tests(); out={'suite':'v1105.3-inquiry-activation-attention-routing','ok':True,'passed':len(rows),'total':len(rows)}
    except Exception as e: out={'suite':'v1105.3-inquiry-activation-attention-routing','ok':False,'passed':0,'total':10,'error':repr(e)}
    print(json.dumps(out,indent=2)); raise SystemExit(0 if out['ok'] else 1)
