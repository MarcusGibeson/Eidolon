from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from operator_review_handoff_checkpoint import build_operator_review_handoff_checkpoint
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_operator_review_handoff_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint_ready');req(r['checkpoint_version']=='1268.9','checkpoint_version');req(r['status']=='operator_review_handoff_checkpoint_ready','checkpoint_status');d=r['details'];req(d['tests_executed'] is False and d['provider_contacted'] is False and d['commands_executed'] is False,'checkpoint_read_only');req(d['active_source_modified'] is False and d['candidate_workspace_modified'] is False,'checkpoint_no_mutation');req(d['next_bounded_unit']=='v1269 Governed Self-Update','next_unit_exact');req(d['self_update_authorized'] is False and d['source_application_authorized'] is False,'checkpoint_authority_denied');req('non_authorizing_operator_disposition' in d['review_contract'],'non_authorizing_disposition_recorded')
print(json.dumps({'ok':True,'suite':'v1268.9-operator-review-handoff-checkpoint','passed':len(C),'failed':0,'checks':C},indent=2,sort_keys=True))
