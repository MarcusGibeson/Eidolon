from __future__ import annotations
import copy,json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from bounded_development_campaigns import campaign_from_deliberation,apply_campaign_event
from bounded_development_campaigns_foundations import DENIED_AUTHORITY,digest
from bounded_development_campaigns_reliability import assess_bounded_campaign_reliability
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
s=campaign_from_deliberation({'disposition':'recommend_for_operator_review','recommended_proposal_id':'p','recommended_proposal_digest':d('p')},objective_digest=d('o'),operator_selection_digest=d('s'),scope_paths=['a.py'],max_events=20,max_recovery_attempts=2)
def e(kind,evidence='',outcome=''):
 return {'campaign_id':s['campaign_id'],'identity_digest':s['identity_digest'],'expected_last_event_digest':s['last_event_digest'],'kind':kind,'evidence_digest':evidence,'touched_paths':[],'operator_review_outcome':outcome}
for kind,evidence,outcome in [('start_implementation','',''),('implementation_ready',d('i'),''),('verification_pass',d('v'),''),('quality_review_pass',d('q'),''),('operator_review_complete',d('r'),'accepted_for_campaign_completion')]:
 r=apply_campaign_event(s,e(kind,evidence,outcome));req(r['accepted'],kind);s=r['state']
req(assess_bounded_campaign_reliability([s])['ok'],'good_complete')
def tamper(base,mut):
 x=copy.deepcopy(base);mut(x);x['state_digest']=digest({k:v for k,v in x.items() if k!='state_digest'});return assess_bounded_campaign_reliability([x])
req(any('authority' in v for v in tamper(s,lambda x:x.__setitem__('release_authorized',True))['violations']),'authority_tamper')
req(any('false_completion' in v for v in tamper(s,lambda x:x.__setitem__('completion_conditions_met',False))['violations']),'false_completion')
req(any('event_budget' in v for v in tamper(s,lambda x:x.__setitem__('event_sequence',999))['violations']),'event_budget')
req(any('recovery_budget' in v for v in tamper(s,lambda x:x.__setitem__('recovery_attempts',99))['violations']),'recovery_budget')
req(any('duplicate_event' in v for v in tamper(s,lambda x:x.__setitem__('event_digests',tuple(x['event_digests'])+(x['event_digests'][0],)))['violations']),'duplicate_history')
req(any('selection_authority' in v for v in tamper(s,lambda x:x.__setitem__('selection_is_execution_authority',True))['violations']),'selection_authority')
r=assess_bounded_campaign_reliability([s,s]);req(r['ok'] and r['campaign_count']==2,'batch');req(r['native_windows_restart_and_multiprocess_validation_pending'],'native_pending');req(all(r[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1293.6-v1293.8-bounded-development-campaigns-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
