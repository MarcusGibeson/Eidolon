import json,tempfile
from pathlib import Path
from conscious_agent.deficiency_signals import DeficiencySignalStore
from conscious_agent.deficiency_candidates import DeficiencyCandidateStore
from conscious_agent.deficiency_deliberation_sessions import DeficiencyDeliberationSessionStore
from conscious_agent.deficiency_arbitration import DeficiencyArbitrationStore
from conscious_agent.development_proposal_eligibility import DevelopmentProposalEligibilityStore
from conscious_agent.development_proposal_candidates import DevelopmentProposalCandidateStore
p=t=f=0
def check(n,v):
 global p,t,f;t+=1
 if v:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition'; sig=DeficiencySignalStore(r).register('s',origin_ids=['o'],source_categories=['operator_confirmed_problem'],deficiency_category='usability_deficiency',component_ids=['ui.panel'],project_digest='p',scope_digest='s',evidence_ids=['e'],recurrence_count=2,reproducibility=.8,confidence=.9,uncertainty=.1)
 dc=DeficiencyCandidateStore(r).register('c',signal_ids=[sig['result']['signal_id']])['result']['candidate_id']; sid=DeficiencyDeliberationSessionStore(r).open('d',candidate_id=dc)['session_id']; aid=DeficiencyArbitrationStore(r).arbitrate('a',session_id=sid,evidence_support=.9,impact_support=.8,feasibility_support=.7,verified_defect_evidence=True)['arbitration_id']; eid=DevelopmentProposalEligibilityStore(r).register('e',arbitration_id=aid,proposal_category='usability_repair',scope_component_ids=['ui.panel'],operator_review_required=True)['eligibility_id']; store=DevelopmentProposalCandidateStore(r); out=store.register('p',eligibility_ids=[eid]); check('candidate created',out['state']=='requires_operator_review'); check('overlap merged',store.register('p2',eligibility_ids=[eid])['status']=='proposal_candidate_overlap_merged'); row=store.inspection_summary()['recent_candidates'][0]; check('exact lineage',row['eligibility_ids']==[eid] and row['arbitration_ids']==[aid]); check('no proposal text',not row['proposal_text_digest']); check('authority inert',not any(store.inspection_summary()['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1136.1'})); raise SystemExit(0 if not f else 1)
