from __future__ import annotations
import json,os,sys,tempfile,shutil,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from architecture_boundary_reliability import *
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_architecture_boundary_reliability_report(ROOT)
req(r['ok'],'reliability_ok');req(r['target_digests_unchanged'],'no_source_mutation');req(r['read_only'],'read_only')
for k,v in r['checks'].items():req(v,'check_'+k)
for i,row in enumerate(r['spawn_results']):req(row['returncode']==0,f'spawn_{i}')
# Long-path parse proof for extracted modules without changing source.
with tempfile.TemporaryDirectory() as td:
    deep=Path(td)/('x'*80)/('y'*80)/('z'*80);deep.mkdir(parents=True)
    for rel in ('conscious_agent/release_evidence_boundary.py','conscious_agent/dashboard_development_campaign_panel.py','conscious_agent/api_request_boundary.py'):
        src=ROOT/rel;dst=deep/src.name;shutil.copy2(src,dst);ast.parse(dst.read_text('utf-8'));C.append('long_path_parse_'+src.stem)
print(json.dumps({'ok':True,'suite':'v1276.6-8-architecture-boundary-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
