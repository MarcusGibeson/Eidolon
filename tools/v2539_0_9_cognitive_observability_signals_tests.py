from __future__ import annotations
from conscious_agent.cognitive_observability_signals_v2539 import build_cognitive_observability_signals

def snap(**now):
    base={'pressure':0,'fragmentation':0,'uncertainty':0,'belief_conflicts':0,'due_continuity_subjects':0,'recovery_margin':1}
    base.update(now)
    return {'ok':True,'now':base,'recent_count':0}

def main():
    checks=[]
    quiet=build_cognitive_observability_signals(snap())
    checks += [quiet['overall']=='quiet',quiet['signals'][0]['code']=='quiet_state']
    high=build_cognitive_observability_signals(snap(pressure=.9,recovery_margin=.1,belief_conflicts=2,due_continuity_subjects=1))
    codes={r['code'] for r in high['signals']}
    checks += [high['overall']=='elevated','cognitive_load_elevated' in codes,'belief_conflict_present' in codes,'continuity_due' in codes,'recovery_margin_low' in codes]
    checks += [high['authority_boundary']['advisory_only'],not high['authority_boundary']['can_schedule_cognition'],not high['authority_boundary']['can_execute_action'],not high['authority_boundary']['medical_or_psychological_diagnosis']]
    checks += [all(not r['action_authorized'] and not r['state_mutated'] for r in high['signals'])]
    try:
        build_cognitive_observability_signals({}); checks.append(False)
    except ValueError: checks.append(True)
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
