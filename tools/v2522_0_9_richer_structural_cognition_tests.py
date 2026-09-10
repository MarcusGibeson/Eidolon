from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.cognitive_state_delta_v2522 import compare_cognitive_frames
from conscious_agent.bounded_cognitive_episode_v2522 import build_bounded_cognitive_episode


def _frame(*, pressure=.1, uncertainty=.1, conflicts=0, contested=0, plans=1, due=0, demands=1, digest='a'*64):
    return {'ok':True,'frame_digest':digest,'projection':{
        'homeostasis':{'pressure':pressure,'uncertainty':uncertainty,'fragmentation':0.0,'recovery_margin':1.0},
        'demands':{'candidate_count':demands},'beliefs':{'active_conflict_count':conflicts,'contested_count':contested},
        'planning':{'active_count':plans},'continuity':{'due_subject_count':due},'initiative':{}}}

def main():
    checks=[]
    def ck(name,v): checks.append((name,bool(v)))
    a=_frame(); b=_frame(pressure=.4,uncertainty=.3,conflicts=1,digest='b'*64)
    d=compare_cognitive_frames(a,b)
    ck('delta_ok',d['ok']); ck('pressure_change','pressure' in d['meaningful_changes']); ck('conflict_change','belief_conflicts' in d['meaningful_changes'])
    ck('delta_minimized',not d['provider_contacted'] and not d['hidden_reasoning_exposed'])
    ep=build_bounded_cognitive_episode(b,previous_frame=a)
    ck('episode_ok',ep['ok']); ck('bounded',1 <= ep['step_count'] <= 3); ck('digest',len(ep['episode_digest'])==64)
    ck('no_provider',not ep['provider_contacted']); ck('no_action',not ep['tool_executed'] and not ep['message_sent']); ck('no_apply',not ep['candidate_applied'])
    ck('no_raw_reasoning',not ep['raw_reasoning_stored']); ck('delta_bound',ep['delta_digest']==d['delta_digest'])
    # Force belief path enough for chained step by explicit high conflict/uncertainty.
    c=_frame(pressure=0, uncertainty=1, conflicts=2, contested=2, demands=0, plans=0, digest='c'*64)
    ep2=build_bounded_cognitive_episode(c)
    ck('chained_or_bounded',ep2['step_count']>=1 and ep2['step_count']<=3)
    ck('unique_steps',len({x['operation'] for x in ep2['steps']})==ep2['step_count'])
    passed=sum(v for _,v in checks)
    print(f'v2522.0-9 richer structural cognition: {passed}/{len(checks)}')
    for n,v in checks: print(('PASS' if v else 'FAIL'), n)
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
