from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):sys.path.insert(0,str(p)) if str(p) not in sys.path else None
from unified_operator_dashboard import *
c=[];ck=lambda v:c.append(bool(v)); rec=[{'record_id':'q','project_id':'a','panel_id':'work_queue','status':'awaiting_review','priority':80},{'record_id':'s','project_id':'a','session_id':'s1','panel_id':'sessions','status':'paused','authority_state':'consumed'},{'record_id':'d','project_id':'b','panel_id':'dependencies','status':'blocked','blocker_count':2},{'record_id':'o','project_id':'b','panel_id':'outcomes','status':'complete'}];s=build_unified_operator_dashboard_snapshot(rec)
for v in (s['ok'],s['record_count']==4,s['project_count']==2,s['session_count']==1,s['authority_summary']['consumed']==1,s['status_counts']['paused']==1,s['status_counts']['blocked']==1):ck(v)
for x,n in ((filter_unified_operator_dashboard_snapshot(s,project_id='a'),2),(filter_unified_operator_dashboard_snapshot(s,panel_id='dependencies'),1),(filter_unified_operator_dashboard_snapshot(s,status='complete'),1)):
 for v in (x['ok'],x['record_count']==n,x['read_only'],x['content_free'],bool(x['filter_digest'])):ck(v)
h=render_unified_operator_dashboard_html(s)
for t in ('Unified Operator Dashboard','command-deck operator-console','dashboard-card','GET-only consolidated inspection','/api/cognition/'):ck(t in h)
for t,a in [('show unified operator dashboard',True),('show unified operator dashboard registry!',True),('mutate dashboard',False)]:ck(process_unified_operator_dashboard_control(t)['active'] is a)
for x in s['records']:
 for v in (bool(x['record_id']),bool(x['project_id']),x['panel_id'] in PANEL_IDS,x['status'] in STATUS_ORDER,bool(x['record_digest']),bool(x['safe_next_action'])):ck(v)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
