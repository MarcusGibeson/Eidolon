from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from memory_reconciliation import detect_memory_conflicts, apply_reconciliation

def main():
    checks=[]
    def ck(name, cond, detail=''): checks.append({'name':name,'status':'pass' if cond else 'fail','detail':detail})
    memories=[
      {'id':'a','type':'preference','content':'Marcus likes black coffee','created_at':'2026-01-01'},
      {'id':'b','type':'preference','content':'Marcus likes black coffee','created_at':'2026-02-01'},
      {'id':'c','type':'preference','content':'Marcus does not like black coffee','created_at':'2026-03-01'},
      {'id':'d','type':'nickname','content':'Marc','created_at':'2026-01-01'},
      {'id':'e','type':'nickname','content':'Marcus','created_at':'2026-02-01'},
    ]
    evidence=detect_memory_conflicts(memories); kinds={e['kind'] for e in evidence}
    ck('exact duplicate detection','exact_duplicate' in kinds)
    ck('contradiction separated','contradiction' in kinds)
    ck('singleton conflict','singleton_conflict' in kinds)
    conflict=next(e for e in evidence if e['kind']=='exact_duplicate')
    ck('classification read only', memories[0].get('use_in_conversation') is None and not conflict['automatic_mutation'])
    first=apply_reconciliation(memories, conflict,'mark_superseded'); second=apply_reconciliation(memories, conflict,'mark_superseded')
    ck('explicit-only reconciliation',first['changed'] and memories[0]['use_in_conversation'] is False)
    ck('idempotent reload replay',not second['changed'] and second['idempotent_replay'])
    ck('provider-free evidence',all(not e['provider_invoked'] for e in evidence))
    passed=sum(c['status']=='pass' for c in checks); print(json.dumps({'suite':'v1083.6-memory-conflict-reconciliation','ok':passed==len(checks),'status':'pass' if passed==len(checks) else 'fail','passed':passed,'total':len(checks),'checks':checks}))
    return 0 if passed==len(checks) else 1
if __name__=='__main__': raise SystemExit(main())
