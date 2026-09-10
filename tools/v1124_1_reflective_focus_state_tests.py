from pathlib import Path
import tempfile
from conscious_agent.reflective_focus_state import ReflectiveFocusStateStore

def main():
 checks=[]
 def ck(n,o): checks.append((n,bool(o)))
 with tempfile.TemporaryDirectory() as td:
  s=ReflectiveFocusStateStore(Path(td))
  r=s.record('e1',attention_id='a1',focus_budget=99,interruptible=True,recovery_compatible=True)
  ck('focus recorded',r['status']=='reflective_focus_state_recorded')
  d=s.record('e1',attention_id='a1')
  ck('event idempotency',d['idempotent'])
  snap=s.snapshot(); row=snap['focus_states'][0]
  ck('budget bounded',row['focus_budget']==8)
  ck('interruptibility preserved',row['interruptible'])
  ck('recovery compatibility preserved',row['recovery_compatible'])
  x=s.record('e2',attention_id='a1',focus_budget=8,interruptible=True,recovery_compatible=True)
  ck('semantic duplicate suppression',x['status']=='duplicate_focus_state_suppressed')
  y=s.record('e3',attention_id='a1',state='interrupted',predecessor_focus_id=r['focus_id'])
  ck('interruption lineage',y['status']=='reflective_focus_state_recorded')
  ck('restart continuity',ReflectiveFocusStateStore(Path(td)).inspection_summary()['focus_count']==2)
  info=s.inspection_summary(); ck('reflection separation',not info['reflection_created'])
  ck('external authority separation',not info['message_sent'] and not info['external_action_executed'])
 for n,o in checks: print(('PASS' if o else 'FAIL')+': '+n)
 print(f'{sum(o for _,o in checks)}/{len(checks)}'); return 0 if all(o for _,o in checks) else 1
if __name__=='__main__': raise SystemExit(main())
