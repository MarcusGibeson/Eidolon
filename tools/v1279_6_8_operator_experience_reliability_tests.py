from __future__ import annotations
import json,os,sys,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1279_fixture import prepared_operator_experience_chain
from operator_experience import build_operator_experience_snapshot,list_operator_experience_snapshots
from operator_experience_reliability import *
from operator_experience_foundations import validate_operator_experience_projection
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
h=inspect_operator_experience_health(source_root=ROOT);req(h['ok'],'health');req(all(h['checks'].values()),'health_checks');req(h['read_only'] and not h['active_source_modified'],'health_readonly')
hand=build_operator_experience_operator_handoff(source_root=ROOT);req(hand['ok'],'handoff');req(hand['next_bounded_unit']=='v1280 Reliability Checkpoint','next');req(hand['v1280_started'] is False,'next_unstarted');req('multi_tab_control_convergence' in hand['native_windows_review'],'windows_tabs')
panel=(ROOT/'conscious_agent/dashboard_operator_experience_panel.py').read_text();req('Authorization phrase is not exposed' in panel,'phrase_hidden_ui');req('Generic “go ahead”' in panel,'generic_warning');req('separately governed' in panel,'rollback_warning');req('Uncertainty' in panel and 'Review packet' in panel,'review_ui')
with tempfile.TemporaryDirectory() as td:
    c=prepared_operator_experience_chain(Path(td),now=100);oid=c['observability']['observability_id'];a=build_operator_experience_snapshot(oid,runtime_root=c['runtime']);b=build_operator_experience_snapshot(oid,runtime_root=c['runtime']);req(a['projection_digest']==b['projection_digest'],'restart_projection_stable');req(validate_operator_experience_projection(a)['ok'],'restart_valid');req(list_operator_experience_snapshots(runtime_root=c['runtime'])['snapshot_count']==1,'restart_list_stable')
with tempfile.TemporaryDirectory() as td:
    base=Path(td)
    while len(str(base))<285:base=base/('segment_'+'x'*28)
    base.mkdir(parents=True);c=prepared_operator_experience_chain(base,now=300);req(validate_operator_experience_projection(build_operator_experience_snapshot(c['observability']['observability_id'],runtime_root=c['runtime']))['ok'],'long_path_snapshot')
code="import sys;from pathlib import Path;sys.path[:0]=[str(Path(r'%s')),str(Path(r'%s')/'conscious_agent')];import operator_experience,operator_experience_reliability,dashboard_operator_experience_panel;print('ok')"%(ROOT,ROOT)
p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_process_import')
print(json.dumps({'ok':True,'suite':'v1279.6-8-operator-experience-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
