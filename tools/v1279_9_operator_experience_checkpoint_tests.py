from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from operator_experience_checkpoint import build_operator_experience_checkpoint
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_operator_experience_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1279.9','version');req(r['status']=='operator_experience_checkpoint_ready','status');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1280 Reliability Checkpoint','next');req(d['v1280_started'] is False,'unstarted');req(d['dashboard_presents_plan_diff_tests_progress'],'core_ui');req(d['dashboard_presents_exact_authorization_without_granting_it'],'authority_ui');req(d['dashboard_presents_rollback_as_separately_governed'],'rollback_ui');req(d['generic_approval_remains_non_authorizing'],'generic');req(not d['checkpoint_executes_provider'] and not d['checkpoint_executes_commands'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly')
print(json.dumps({'ok':True,'suite':'v1279.9-operator-experience-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
