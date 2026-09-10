from __future__ import annotations
import copy,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):sys.path.insert(0,str(p)) if str(p) not in sys.path else None
from unified_operator_dashboard import *
c=[];ck=lambda v:c.append(bool(v)); sts=['ready','awaiting_review','blocked','paused','failed','complete','stale','conflicted','unknown']; rec=[]
for i,s in enumerate(sts):rec.append({'record_id':f'r{i}','project_id':'a' if i%2==0 else 'b','session_id':f's{i}' if i<3 else '', 'panel_id':PANEL_IDS[i], 'status':s,'priority':100-i,'summary':'safe','source_path':'/private','provider_output':'secret','token':'x'})
x=build_unified_operator_dashboard_snapshot(rec);ck(not x['ok']);ck(x['status']=='unified_operator_dashboard_conflicted');ck(x['project_count']==2);ck(x['session_count']==3)
for s in sts:ck(x['status_counts'][s]==1)
blob=json.dumps(x,sort_keys=True)
for bad in ('/private','secret','"token"','source_path','provider_output'):ck(bad not in blob)
y=build_unified_operator_dashboard_snapshot(rec);ck(x['snapshot_digest']==y['snapshot_digest']);ck(x['records']==y['records'])
t=copy.deepcopy(x);t['records'][0]['status']='ready';z=filter_unified_operator_dashboard_snapshot(t);ck(not z['ok']);ck(z['status']=='unified_operator_dashboard_snapshot_tampered');ck(z['records']==[])
p=build_unified_operator_dashboard_snapshot([{'panel_id':'plans','status':'ready','available':False},{'panel_id':'quality','status':'ready','contradictory':True},{'panel_id':'resources','status':'ready','stale':True}]);ck([a['status'] for a in p['records']]==['conflicted','stale','unknown'])
i=build_unified_operator_dashboard_snapshot([{'panel_id':'../../x','status':'ready','summary':'x'*500,'priority':9999,'authority_state':'launch'}])['records'][0]
for v in (i['panel_id']=='benchmark',len(i['summary'])<=180,i['priority']==100,i['authority_state']=='none'):ck(v)
for k,e in AUTHORITY_FLAGS.items():ck(x.get(k) is e and p.get(k) is e)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
