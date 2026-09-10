from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from bounded_development_campaigns import campaign_from_deliberation,apply_campaign_event,campaign_public_projection
from bounded_development_campaigns_foundations import DENIED_AUTHORITY
C=[]
def req(v,l):
 if not v: raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
def make(max_recovery=2):
 return campaign_from_deliberation({'disposition':'recommend_for_operator_review','recommended_proposal_id':'p1','recommended_proposal_digest':d('p')},objective_digest=d('obj'),operator_selection_digest=d('sel'),scope_paths=['conscious_agent/a.py','tools/test_a.py'],max_recovery_attempts=max_recovery,max_events=30)
def ev(s,kind,evidence='',strategy='',paths=(),outcome=''):
 return {'campaign_id':s['campaign_id'],'identity_digest':s['identity_digest'],'expected_last_event_digest':s['last_event_digest'],'kind':kind,'evidence_digest':evidence,'strategy_digest':strategy,'touched_paths':list(paths),'operator_review_outcome':outcome}
def apply(s,*a,**kw):
 r=apply_campaign_event(s,ev(s,*a,**kw));return r,r['state']
s=make();req(s['current_stage']=='prepared','prepared')
r,s=apply(s,'start_implementation');req(r['accepted'] and s['current_stage']=='implementation','start')
r,s=apply(s,'pause');req(s['paused'],'pause');blocked=apply_campaign_event(s,ev(s,'implementation_ready',d('i'),paths=['conscious_agent/a.py']));req(not blocked['ok'] and blocked['status']=='blocked_paused_campaign','paused_blocks')
r,s=apply(s,'resume');req(not s['paused'],'resume')
r,s=apply(s,'implementation_ready',d('impl'),d('strategy1'),['conscious_agent/a.py']);req(s['current_stage']=='verification','implementation_evidence')
# Replay exact already-recorded event is idempotent even though its expected predecessor is stale.
replay_event={'campaign_id':s['campaign_id'],'identity_digest':s['identity_digest'],'expected_last_event_digest':r['state']['event_digests'][-2] if len(r['state']['event_digests'])>1 else '', 'kind':'implementation_ready','evidence_digest':d('impl'),'strategy_digest':d('strategy1'),'touched_paths':['conscious_agent/a.py'],'operator_review_outcome':''}
rep=apply_campaign_event(s,replay_event);req(rep['duplicate_noop'] and rep['status']=='duplicate_event_noop','duplicate_noop')
# Verification failure enters bounded recovery and records failed strategy.
r,s=apply(s,'verification_fail',d('vf'),d('strategy1'),['tools/test_a.py']);req(s['current_stage']=='recovery' and s['recovery_attempts']==1,'recovery')
repeat=apply_campaign_event(s,ev(s,'recovery_ready',d('rr'),d('strategy1'),['conscious_agent/a.py']));req(repeat['status']=='blocked_repeated_failed_strategy','failed_strategy_not_repeated')
r,s=apply(s,'recovery_ready',d('rr2'),d('strategy2'),['conscious_agent/a.py']);req(s['current_stage']=='verification','recovery_ready')
r,s=apply(s,'verification_pass',d('vp'),d('strategy2'),['tools/test_a.py']);req(s['current_stage']=='quality_review','verification_pass')
r,s=apply(s,'quality_review_pass',d('qp'));req(s['current_stage']=='operator_review','quality_review')
r,s=apply(s,'operator_review_complete',d('op'),outcome='reviewed_no_apply');req(s['current_stage']=='complete' and s['completion_conditions_met'] and s['terminal'],'complete')
req(all(s[k] is False for k in DENIED_AUTHORITY),'complete_no_authority')
p=campaign_public_projection(s);req(p['scope_path_count']==2 and 'scope_path_digests' not in p and p['campaign_grants_authority'] is False,'projection')
# Out-of-scope change never mutates the state and requires new confirmation.
x=make();_,x=apply(x,'start_implementation');out=apply_campaign_event(x,ev(x,'implementation_ready',d('x'),paths=['outside.py']));req(out['status']=='blocked_scope_expansion' and out['new_requirement_confirmation_required'] and out['state']['event_sequence']==1,'scope_guard')
# Cancellation is terminal.
y=make();r,y=apply(y,'cancel');req(y['current_stage']=='cancelled' and y['terminal'],'cancel');req(apply_campaign_event(y,ev(y,'resume'))['status']=='blocked_terminal_campaign','terminal_immutable')
# Recovery budget is hard.
z=make(max_recovery=0);_,z=apply(z,'start_implementation');_,z=apply(z,'implementation_ready',d('zi'),d('zs'),['conscious_agent/a.py']);br=apply_campaign_event(z,ev(z,'verification_fail',d('zf'),d('zs'),['tools/test_a.py']));req(br['status']=='blocked_recovery_budget_exhausted','recovery_budget')
print(json.dumps({'ok':True,'suite':'v1293.3-v1293.5-bounded-development-campaigns-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
