from pathlib import Path
import tempfile
from conscious_agent.deficiency_signals import DeficiencySignalStore
from conscious_agent.deficiency_candidates import DeficiencyCandidateStore
from conscious_agent.deficiency_deliberation_sessions import DeficiencyDeliberationSessionStore
from conscious_agent.deficiency_arbitration import DeficiencyArbitrationStore
def session(root,s='a',rec=3,repro=.8,sev=.7,conf=.8,unc=.2):
 sid=DeficiencySignalStore(root).register('s-'+s,origin_ids=['o-'+s],source_categories=['failed_checkpoint'],deficiency_category='reliability_deficiency',component_ids=['component-'+s],project_digest='p',scope_digest='q',evidence_ids=['e-'+s],recurrence_count=rec,reproducibility=repro,severity=sev,confidence=conf,uncertainty=unc,verified_defect=True)['result']['signal_id']; cid=DeficiencyCandidateStore(root).register('c-'+s,signal_ids=[sid])['result']['candidate_id']; return DeficiencyDeliberationSessionStore(root).open('d-'+s,candidate_id=cid)['session_id']
def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); x=DeficiencyArbitrationStore(r).arbitrate('a',session_id=session(r),evidence_support=.9,impact_support=.8,feasibility_support=.7,verified_defect_evidence=True); assert x['outcome']=='verified_deficiency'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); x=DeficiencyArbitrationStore(r).arbitrate('b',session_id=session(r,'b'),evidence_support=.7,impact_support=.6); assert x['outcome']=='probable_deficiency'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); x=DeficiencyArbitrationStore(r).arbitrate('c',session_id=session(r,'c'),architectural_suspicion=True); assert x['outcome']=='architectural_suspicion_only'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); x=DeficiencyArbitrationStore(r).arbitrate('d',session_id=session(r,'d'),deliberate_no_deficiency=True); assert x['outcome']=='deliberate_no_deficiency'
 print('v1135.4 deficiency arbitration: 4/4 passed')
if __name__=='__main__': main()
