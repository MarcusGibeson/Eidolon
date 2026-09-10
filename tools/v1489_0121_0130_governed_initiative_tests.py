from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b13-'))
os.environ['EIDOLON_DATA_DIR']=str(R); os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(AGENT))
from governed_initiative_boundary import *
from conscious_agent.initiative_communication_restraint import InitiativeCommunicationRestraint
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 for k in ARTIFACT_CLASSES: ck('0121 artifact boundary '+k,classify_artifact(k)==k)
 private=decide_surface(artifact_class='internal_thought',novelty=.9,relevance=.9,confidence=.9,now_epoch=7200); ck('0122 background thought stays private',not private.surface_eligible and private.reason=='private_artifact_boundary',private.public_summary())
 low=decide_surface(artifact_class='suggestion',novelty=.4,relevance=.4,confidence=.9,now_epoch=7200); ck('0123 salience threshold blocks weak thought',not low.surface_eligible and low.reason=='below_salience_threshold',low.public_summary())
 cool=decide_surface(artifact_class='notification',novelty=.9,relevance=.9,confidence=.9,last_surface_epoch=7000,now_epoch=7200,cooldown_seconds=3600); ck('0124 cooldown blocks spam',not cool.surface_eligible and cool.reason=='cooldown_active',cool.public_summary())
 saved=preserved_unfinished_thought(thought_id='private-thought-id'); ck('0125 unfinished thought resumable not surfaced',saved['resume_allowed'] and not saved['surface_allowed'],saved)
 controls=operator_controls(muted=True,invited=False); ck('0126 operator inspect/dismiss/mute controls',controls['operator_can_inspect'] and controls['operator_can_dismiss'] and controls['operator_can_mute'] and not controls['autonomous_send_authority'],controls)
 guard=emotional_authority_guard(emotional_state='excited',requested_action='promote release'); ck('0127 emotion cannot broaden authority',not guard['command_authority_changed'] and not guard['release_authority_changed'],guard)
 loop=decide_surface(artifact_class='suggestion',novelty=.9,relevance=.9,confidence=.9,repetitive=True,now_epoch=7200); ck('0128 repetitive self-loop suppressed',not loop.surface_eligible and loop.reason=='repetitive_self_loop',loop.public_summary())
 # multi-hour simulated pacing: only first and one after cooldown may surface.
 outcomes=[]; last=None
 for hour in [0,.1,.5,1.1,1.2,2.3]:
  d=decide_surface(artifact_class='suggestion',novelty=.9,relevance=.9,confidence=.9,last_surface_epoch=last,now_epoch=hour*3600,cooldown_seconds=3600)
  outcomes.append(d.surface_eligible)
  if d.surface_eligible:last=hour*3600
 ck('0129 multi-hour pacing bounded',sum(outcomes)<=3 and outcomes[0] and outcomes[3],outcomes)
 # Existing restraint remains non-sending even when eligible.
 restraint=InitiativeCommunicationRestraint(R/'cognition'); snap=restraint.snapshot(); ck('0121 existing restraint cannot send/execute',not snap['authority_boundary']['can_send'] and not snap['authority_boundary']['can_execute'],snap['authority_boundary'])
 ck('0127 existing restraint cannot approve/promote',not snap['authority_boundary']['can_approve'] and not snap['authority_boundary']['can_promote'],snap['authority_boundary'])
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)
