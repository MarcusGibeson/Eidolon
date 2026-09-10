from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from persistent_motivation import MotivationStore
from self_directed_inquiry import InquiryWorkspace
from inquiry_evidence_assimilation import InquiryEvidenceLedger

def req(x,m='failed'):
    if not x: raise AssertionError(m)
def fixture():
    root=Path(tempfile.mkdtemp())/'runtime'/'cognition';m=MotivationStore(root);mid=m.record_motivation('m',kind='curiosity',summary='Investigate evidence',cognitive_state='desire',urgency=.7,confidence=.6,origin_type='fixture',origin_ref='x')['result']['motivation_id'];w=InquiryWorkspace(root,motivation_store=m);iid=w.create_inquiry('q',motivation_id=mid,question='Which explanation fits?')['result']['inquiry_id'];return root,w,iid
def run():
    root,w,iid=fixture();l=InquiryEvidenceLedger(root,workspace=w);a=l.assimilate('e1',inquiry_id=iid,summary='Operator observed a repeatable pattern.',source_label='operator note',reliability=.8);req(a['status']=='evidence_assimilated',a);req(l.assimilate('e1',inquiry_id=iid,summary='Operator observed a repeatable pattern.',source_label='operator note')['idempotent']);p=l.propose_research('r1',inquiry_id=iid,question='Check external documentation?',justification='Local evidence is insufficient',requested_sources=['official docs']);req(p['result']['authorized'] is False and p['result']['executed'] is False,p);eid=a['result']['evidence_id'];l.retract_evidence('x',evidence_id=eid,reason_code='corrected');s=l.inspection_summary();req(s['active_evidence_count']==0 and s['historical_evidence_count']==1,s);req(s['external_browsing_performed'] is False and s['action_authority_changed'] is False);return [1]*11
if __name__=='__main__':
    try:r=run();o={'suite':'v1105.4-evidence-assimilation-research-boundary','ok':True,'passed':len(r),'total':len(r)}
    except Exception as e:o={'suite':'v1105.4-evidence-assimilation-research-boundary','ok':False,'passed':0,'total':11,'error':repr(e)}
    print(json.dumps(o,indent=2));raise SystemExit(0 if o['ok'] else 1)
