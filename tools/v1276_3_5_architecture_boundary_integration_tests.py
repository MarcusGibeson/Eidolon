from __future__ import annotations
import json,os,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from architecture_boundary_integration import build_architecture_boundary_integration_report
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_architecture_boundary_integration_report(ROOT)
req(r['ok'],'integration_ok');req(r['status']=='architecture_boundary_integration_ready','status');req(r['read_only'],'read_only')
for k,v in r['checks'].items():req(v,'check_'+k)
req(len(r['dashboard_panel_sha256'])==64,'panel_digest');req(r['parent_dispatch_ownership_preserved'],'parent_dispatch_ownership')
import api_server,dashboard,self_maintenance
req(api_server.dispatch_api.__module__=='api_server','api_dispatch_public_parent');req(dashboard.run_dashboard.__module__=='dashboard','dashboard_runtime_parent');req(self_maintenance.build_publish_approval_policy.__module__=='self_maintenance','maintenance_governance_parent')
print(json.dumps({'ok':True,'suite':'v1276.3-5-architecture-boundary-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
