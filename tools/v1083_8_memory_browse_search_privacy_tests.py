from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from memory_browse import browse_relationship_memories

def main():
 checks=[]
 def ck(n,c,d=''): checks.append({'name':n,'status':'pass' if c else 'fail','detail':d})
 rows=[]
 for i in range(130):
  rows.append({'record_key':f'id:{i}','id':str(i),'type':'preference','category':'preference','label':'Preference','content':f'coffee preference {i}','importance':'medium','state':'active','created_at':f'2026-07-{(i%20)+1:02d}','updated_at':'','operator_curated':True,'temporal_state':'','retention_confirmed':bool(i%2),'provenance':{'origin':'operator_explicit'},'private_receipt':'secret'})
 rows.append({'record_key':'id:deleted','state':'deleted','content':'deleted secret'})
 report=browse_relationship_memories(query='coffee',filters={'memory_type':'preference','provenance_state':'operator_explicit'},page=2,page_size=25,records=rows)
 ck('read only',report['read_only'])
 ck('bounded pagination',len(report['records'])==25 and report['page']==2 and report['has_more'])
 ck('privacy fields filtered',all('private_receipt' not in r and 'vector' not in r for r in report['records']))
 ck('deleted hidden',all(r['record_key']!='id:deleted' for r in report['records']))
 ck('offline available',report['offline_available'] and not report['provider_invoked'])
 source=(ROOT/'conscious_agent'/'dashboard_chat_console.py').read_text()
 ck('narrow layout retained','@media (max-width:' in source)
 ck('rendered javascript present','<script>' in source and '</script>' in source)
 passed=sum(c['status']=='pass' for c in checks); print(json.dumps({'suite':'v1083.8-memory-browse-search-privacy','ok':passed==len(checks),'status':'pass' if passed==len(checks) else 'fail','passed':passed,'total':len(checks),'checks':checks})); return 0 if passed==len(checks) else 1
if __name__=='__main__': raise SystemExit(main())
