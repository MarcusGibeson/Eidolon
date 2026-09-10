from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from persistent_motivation import MotivationStore
from self_directed_inquiry import InquiryWorkspace
from proactive_communication import ProactiveCommunicationStore
from inquiry_conversation_continuity import InquiryConversationBridge

def req(x,m='failed'):
    if not x:raise AssertionError(m)
def fixture():
    root=Path(tempfile.mkdtemp())/'runtime'/'cognition';m=MotivationStore(root);mid=m.record_motivation('m',kind='curiosity',summary='Why does this pattern recur?',cognitive_state='desire',urgency=.9,confidence=.7,origin_type='fixture',origin_ref='x')['result']['motivation_id'];w=InquiryWorkspace(root,motivation_store=m);iid=w.create_inquiry('q',motivation_id=mid,question='What distinguishes the explanations?',uncertainty=.9)['result']['inquiry_id'];w.add_progress('p',inquiry_id=iid,conclusion='One explanation now fits more evidence.',uncertainty_after=.7);c=ProactiveCommunicationStore(root,motivation_store=m);return root,w,c,iid
def run():
    root,w,c,iid=fixture();b=InquiryConversationBridge(root,workspace=w,communication=c,epoch_clock=lambda:2000000000.0);r=b.consider('x',inquiry_id=iid);req(r['result']['decision']=='communicate',r);req(c.unread_messages(),c.snapshot());req(b.consider('x',inquiry_id=iid)['idempotent']);root2,w2,c2,i2=fixture();c2.set_preferences('quiet',quiet_indefinite=True);b2=InquiryConversationBridge(root2,workspace=w2,communication=c2,epoch_clock=lambda:2000000000.0);q=b2.consider('q',inquiry_id=i2);req(q['result']['decision']=='silence',q);req(q['result']['action_authorized'] is False);req(b.inspection_summary()['action_authority_changed'] is False);return [1]*12
if __name__=='__main__':
    try:r=run();o={'suite':'v1105.5-inquiry-conversation-continuity','ok':True,'passed':len(r),'total':len(r)}
    except Exception as e:o={'suite':'v1105.5-inquiry-conversation-continuity','ok':False,'passed':0,'total':12,'error':repr(e)}
    print(json.dumps(o,indent=2));raise SystemExit(0 if o['ok'] else 1)
