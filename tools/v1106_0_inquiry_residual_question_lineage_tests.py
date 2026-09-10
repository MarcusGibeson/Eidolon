from __future__ import annotations
import argparse, json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.inquiry_residual_lineage import InquiryResidualLineage

def req(v,d='failed'):
    if not v: raise AssertionError(d)

def fixture():
    root=Path(tempfile.mkdtemp())/'runtime'/'cognition'; m=MotivationStore(root); mid=m.record_motivation('m',kind='curiosity',summary='lineage',cognitive_state='desire',urgency=.8,confidence=.8,origin_type='fixture',origin_ref='v1106.0')['result']['motivation_id']; w=InquiryWorkspace(root,motivation_store=m); pid=w.create_inquiry('p',motivation_id=mid,question='Parent?',uncertainty=.8)['result']['inquiry_id']; return root,w,pid

def tests():
    out=[]
    def run(name,fn):
        try: fn(); out.append({'name':name,'status':'pass'})
        except Exception as e: out.append({'name':name,'status':'fail','detail':repr(e)})
    def create():
        r,w,p=fixture(); x=InquiryResidualLineage(r,workspace=w).create_child('c',parent_inquiry_id=p,residual_question='Child?'); req(x['result']['created']); req(len(w.snapshot()['inquiries'])==2)
    def duplicate():
        r,w,p=fixture(); s=InquiryResidualLineage(r,workspace=w); a=s.create_child('a',parent_inquiry_id=p,residual_question='Child?'); b=s.create_child('b',parent_inquiry_id=p,residual_question='Child?'); req(a['result']['child_inquiry_id']==b['result']['child_inquiry_id'])
    def retry():
        r,w,p=fixture(); s=InquiryResidualLineage(r,workspace=w); a=s.create_child('same',parent_inquiry_id=p,residual_question='Child?'); b=s.create_child('same',parent_inquiry_id=p,residual_question='Child?'); req(b['idempotent'])
    def persistence():
        r,w,p=fixture(); InquiryResidualLineage(r,workspace=w).create_child('c',parent_inquiry_id=p,residual_question='Child?'); req(InquiryResidualLineage(r,workspace=w).inspection_summary()['active_link_count']==1)
    def provenance():
        r,w,p=fixture(); s=InquiryResidualLineage(r,workspace=w); s.create_child('c',parent_inquiry_id=p,residual_question='Child?'); req(s.snapshot()['links'][0]['provenance']['parent_question_digest'])
    def retract():
        r,w,p=fixture(); s=InquiryResidualLineage(r,workspace=w); lid=s.create_child('c',parent_inquiry_id=p,residual_question='Child?')['result']['link_id']; s.retract_link('r',link_id=lid,reason_code='corrected'); q=s.inspection_summary(); req(q['active_link_count']==0 and q['historical_link_count']==1)
    def budget():
        r,w,p=fixture(); s=InquiryResidualLineage(r,workspace=w); s._load()['resource_limits']
        for i in range(5): s.create_child(f'c{i}',parent_inquiry_id=p,residual_question=f'Child {i}?')
        try: s.create_child('overflow',parent_inquiry_id=p,residual_question='Overflow?'); raise AssertionError('not blocked')
        except ValueError: pass
    def authority():
        r,w,p=fixture(); q=InquiryResidualLineage(r,workspace=w).inspection_summary(); req(q['authority_boundary']['can_authorize_action'] is False and q['external_browsing_performed'] is False)
    def missing_parent():
        r,w,_=fixture();
        try: InquiryResidualLineage(r,workspace=w).create_child('c',parent_inquiry_id='missing',residual_question='Child?'); raise AssertionError('not blocked')
        except KeyError: pass
    def clean_summary():
        r,w,p=fixture(); q=InquiryResidualLineage(r,workspace=w).inspection_summary(); req(q['provider_contacted'] is False and q['hidden_reasoning_exposed'] is False)
    for n,f in [('create',create),('duplicate',duplicate),('retry',retry),('persistence',persistence),('provenance',provenance),('retract',retract),('budget',budget),('authority',authority),('missing_parent',missing_parent),('clean_summary',clean_summary)]: run(n,f)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');a=p.parse_args();rows=tests();payload={'passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows};print(json.dumps(payload,indent=2));raise SystemExit(0 if payload['passed']==payload['total'] else 1)
