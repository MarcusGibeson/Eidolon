from __future__ import annotations
import json, os, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1'); os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1251-6-8-'))
from dashboard_performance import optimize_dashboard_html_assets, load_dashboard_asset, prewarm_api_runtime_async, prewarm_status
from dashboard_first_use import render_first_use_shell
from runtime_projection_cache import cached_read_only_projection, clear_projection_cache, cache_status
checks=[]
def req(v): checks.append(bool(v)); assert v
html='<!doctype html><html><head><style>'+('x'*60000)+'</style></head><body><script>(function () {'+('y'*5000)+'</script></body></html>'; opt=optimize_dashboard_html_assets(html)
req(len(opt)<len(html)-50000); req("/assets/dashboard.css?v=1396.9-r3" in opt); req("/assets/dashboard.js?v=1396.9-r3" in opt); req('<style>' not in opt)
first_use=optimize_dashboard_html_assets(render_first_use_shell()); req("data-first-use-shell='v1101'" in first_use); req("#conversation-log { min-height:48vh; max-height:58vh; overflow:auto;" in first_use); req("/assets/dashboard.css?v=1396.9-r3" not in first_use)
css=load_dashboard_asset('dashboard.css'); js=load_dashboard_asset('dashboard.js'); req(css is not None and css[0].startswith('text/css') and len(css[1])>10000); req(js is not None and 'javascript' in js[0] and len(js[1])>100); req(load_dashboard_asset('../secret') is None)
clear_projection_cache(); count={'n':0}
def builder(): count['n']+=1; return {'n':count['n'],'rows':[1,2,3]}
a=cached_read_only_projection('probe',builder,ttl_seconds=5); b=cached_read_only_projection('probe',builder,ttl_seconds=5); req(count['n']==1); req(a==b); b['rows'].append(4); c=cached_read_only_projection('probe',builder,ttl_seconds=5); req(c['rows']==[1,2,3]); req(cache_status()['entry_count']>=1); clear_projection_cache(); req(cache_status()['entry_count']==0)
state=prewarm_api_runtime_async(); req(state['started'] is True); deadline=time.time()+15
while not prewarm_status()['completed'] and time.time()<deadline: time.sleep(.02)
status=prewarm_status(); req(status['completed'] is True); req(status['failed'] is False); req(int(status['duration_ms'])<15000); req(status['provider_contacted'] is False); req(status['runtime_mutation_performed'] is False)
dash=(ROOT/'conscious_agent/dashboard.py').read_text(encoding='utf-8'); api=(ROOT/'conscious_agent/api_server.py').read_text(encoding='utf-8'); req('/assets/dashboard.css' in dash); req('/assets/dashboard.js' in dash); req('prewarm_api_runtime_async' in dash); req('cached_read_only_projection' in api); req('def _build_status_payload_uncached' in api)
r={'suite':'v1251.6-v1251.8-dashboard-response-time','ok':all(checks),'passed':sum(checks),'total':len(checks)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
