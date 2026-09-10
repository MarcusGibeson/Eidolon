from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'): sys.path.insert(0,str(p)) if str(p) not in sys.path else None
from unified_operator_dashboard import *
c=[]; ck=lambda v:c.append(bool(v)); r=dashboard_panel_registry(); s=build_unified_operator_dashboard_snapshot()
for v in (r['ok'],r['panel_count']==14,len(r['panels'])==14,r['content_free'],r['read_only'],bool(r['registry_digest']),s['ok'],s['record_count']==14,s['project_count']==1,s['panel_count']==14,s['read_only'],s['content_free'],s['private_fields_suppressed'],not s['opening_record_mutates_state'],not s['filtering_mutates_state'],not s['sorting_mutates_state'],s['cross_project_records_kept_separate'],bool(s['snapshot_digest'])):ck(v)
for k,e in AUTHORITY_FLAGS.items():ck(r.get(k) is e and s.get(k) is e)
for p in r['panels']:
 for v in (p['panel_id'] in PANEL_IDS,bool(p['title']),p['get_path'].startswith('/api/'),p['read_only'],not p['mutation_controls_present']):ck(v)
for a,b in [('ready','ready'),('admissible','ready'),('pending review','awaiting_review'),('missing-evidence','blocked'),('recovered to paused','paused'),('rejected','failed'),('sealed','complete'),('expired','stale'),('tampered','conflicted'),('nonsense','unknown')]:ck(normalize_dashboard_status(a)==b)
ck(normalize_dashboard_status('ready',stale=True)=='stale');ck(normalize_dashboard_status('ready',contradictory=True)=='conflicted');ck(normalize_dashboard_status('ready',available=False)=='unknown')
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
