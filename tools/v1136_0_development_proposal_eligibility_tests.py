import json, tempfile
from pathlib import Path
from conscious_agent.deficiency_signals import DeficiencySignalStore
from conscious_agent.deficiency_candidates import DeficiencyCandidateStore
from conscious_agent.deficiency_deliberation_sessions import DeficiencyDeliberationSessionStore
from conscious_agent.deficiency_arbitration import DeficiencyArbitrationStore
from conscious_agent.development_proposal_eligibility import DevelopmentProposalEligibilityStore
p=t=f=0
def check(name,fn):
 global p,t,f;t+=1
 try: fn();p+=1;print('PASS',name)
 except Exception as e:f+=1;print('FAIL',name,e)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition'; s=DeficiencySignalStore(r); x=s.register('s',origin_ids=['o'],source_categories=['failed_checkpoint'],deficiency_category='reliability_deficiency',component_ids=['component.alpha'],project_digest='p',scope_digest='q',evidence_ids=['e'],recurrence_count=3,reproducibility=.9,severity=.8,confidence=.9,uncertainty=.1)
 c=DeficiencyCandidateStore(r); cid=c.register('c',signal_ids=[x['result']['signal_id']])['result']['candidate_id']; ds=DeficiencyDeliberationSessionStore(r); sid=ds.open('d',candidate_id=cid)['session_id']; a=DeficiencyArbitrationStore(r); aid=a.arbitrate('a',session_id=sid,evidence_support=.9,impact_support=.8,feasibility_support=.8,verified_defect_evidence=True)['arbitration_id']; store=DevelopmentProposalEligibilityStore(r); out=store.register('p',arbitration_id=aid,proposal_category='reliability_repair',scope_component_ids=['component.alpha'],operator_review_required=False)
 check('verified eligibility',lambda: (_ for _ in ()).throw(AssertionError()) if out['state']!='eligible' else None)
 check('idempotent retry',lambda: (_ for _ in ()).throw(AssertionError()) if not store.register('p',arbitration_id=aid,proposal_category='reliability_repair',scope_component_ids=['component.alpha'])['idempotent'] else None)
 check('content free',lambda: (_ for _ in ()).throw(AssertionError()) if store.inspection_summary()['proposal_text_exposed'] else None)
 check('authority inert',lambda: (_ for _ in ()).throw(AssertionError()) if any(store.inspection_summary()['authority_boundary'].values()) else None)
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1136.0'})); raise SystemExit(0 if not f else 1)
