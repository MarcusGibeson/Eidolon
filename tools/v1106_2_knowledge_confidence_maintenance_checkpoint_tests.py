from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.knowledge_confidence_checkpoint import build_knowledge_confidence_checkpoint
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.inquiry_residual_lineage import InquiryResidualLineage
from conscious_agent.inquiry_evidence_assimilation import InquiryEvidenceLedger
from conscious_agent.cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage

def req(v,d='failed'):
 if not v:raise AssertionError(d)
def fix():
 b=Path(tempfile.mkdtemp());r=b/'runtime'/'cognition';s=b/'source';s.mkdir();m=MotivationStore(r);mid=m.record_motivation('m',kind='curiosity',summary='confidence',cognitive_state='desire',urgency=.8,confidence=.8,origin_type='fixture',origin_ref='v1106.2')['result']['motivation_id'];w=InquiryWorkspace(r,motivation_store=m);p=w.create_inquiry('p',motivation_id=mid,question='Parent?',uncertainty=.9)['result']['inquiry_id'];c=InquiryResidualLineage(r,workspace=w).create_child('c',parent_inquiry_id=p,residual_question='Child?')['result']['child_inquiry_id'];l=InquiryEvidenceLedger(r,workspace=w);e=l.assimilate('e',inquiry_id=p,summary='fact',source_label='operator',reliability=.9,supports='supports')['result']['evidence_id'];CrossInquiryEvidenceLineage(r,workspace=w,ledger=l).link('x',evidence_id=e,target_inquiry_id=c);return b,r,s

def tests():
 out=[]
 def run(n,f):
  try:f();out.append({'name':n,'status':'pass'})
  except Exception as e:out.append({'name':n,'status':'fail','detail':repr(e)})
 def empty_read_only():
  b=Path(tempfile.mkdtemp());r=b/'runtime'/'cognition';s=b/'source';s.mkdir();before=list(b.rglob('*'));q=build_knowledge_confidence_checkpoint(r,source_root=s);after=list(b.rglob('*'));req([str(x) for x in before]==[str(x) for x in after] and q['runtime_mutated'] is False)
 def aggregate():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['summary']['residual_lineage_link_count']==1 and q['summary']['cross_inquiry_evidence_link_count']==1)
 def uncertainty_review():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['summary']['inquiry_review_candidate_count']>=1)
 def checks():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(len(q['checks'])==12 and all(x['status'] in {'pass','pending_desktop'} for x in q['checks']))
 def provider():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['provider_contacted'] is False)
 def browse():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['external_browsing_performed'] is False)
 def authority():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['action_authority_changed'] is False and q['external_action_executed'] is False)
 def privacy():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['hidden_reasoning_exposed'] is False)
 def epistemic():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['consciousness_claimed'] is False and q['epistemic_status'].endswith('not_proven'))
 def restart():
  b,r,s=fix();a=build_knowledge_confidence_checkpoint(r,source_root=s)['summary'];z=build_knowledge_confidence_checkpoint(r,source_root=s)['summary'];req(a==z)
 def external_runtime():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(next(x for x in q['checks'] if x['id']=='runtime_separation')['status']=='pass')
 def certification():
  b,r,s=fix();q=build_knowledge_confidence_checkpoint(r,source_root=s);req(q['release_certified'] is False and q['release_promoted'] is False)
 for n,f in [('empty_read_only',empty_read_only),('aggregate',aggregate),('uncertainty_review',uncertainty_review),('checks',checks),('provider',provider),('browse',browse),('authority',authority),('privacy',privacy),('epistemic',epistemic),('restart',restart),('external_runtime',external_runtime),('certification',certification)]:run(n,f)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');p.parse_args();rows=tests();x={'passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows};print(json.dumps(x,indent=2));raise SystemExit(0 if x['passed']==x['total'] else 1)
