from __future__ import annotations
import json, sys, tempfile, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from conversation_context import _memory_candidates
from relationship_memory_curation import correct_relationship_memory
import memory

def main():
 checks=[]
 def ck(n,c,d=''): checks.append({'name':n,'status':'pass' if c else 'fail','detail':d})
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'memories.json'; memory.MEMORY_FILE=path
  original={'id':'fact1','type':'personal_fact','content':'Marcus lives in Toledo','status':'active','relationship_eligible':True,'use_in_conversation':True}
  stale={'id':'fact2','type':'personal_fact','content':'Marcus lives in Toledo','status':'active'}
  path.write_text(json.dumps([original,stale]))
  result=correct_relationship_memory('id:fact1','Marcus lives in Cleveland')
  rows=json.loads(path.read_text()); corrected=rows[0]
  ck('correction lineage',bool(corrected.get('correction_lineage')) and corrected['correction_lineage'][-1]['previous_content']=='Marcus lives in Toledo')
  ck('original transcript untouched',result['raw_conversation_history_changed'] is False)
  candidates=_memory_candidates(rows,'Where does Marcus live?'); texts=[m.get('content') for m,_ in candidates]
  ck('superseded prompt suppression','Marcus lives in Toledo' not in texts)
  ck('corrected prompt use','Marcus lives in Cleveland' in texts)
  ck('stale reintroduction prevented',len([t for t in texts if 'Toledo' in str(t)])==0)
  ck('provider not invoked',corrected['correction_lineage'][-1]['provider_invoked'] is False)
 passed=sum(c['status']=='pass' for c in checks); print(json.dumps({'suite':'v1083.7-user-correction-propagation','ok':passed==len(checks),'status':'pass' if passed==len(checks) else 'fail','passed':passed,'total':len(checks),'checks':checks})); return 0 if passed==len(checks) else 1
if __name__=='__main__': raise SystemExit(main())
