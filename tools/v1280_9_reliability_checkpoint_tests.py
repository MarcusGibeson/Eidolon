from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from reliability_checkpoint_checkpoint import build_reliability_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=build_reliability_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1280.9','version');req(all(r['checks'].values()),'checks');d=r['details'];req(d['next_bounded_unit']=='v1281 Causal Diagnostic Reasoning','next');req(d['v1281_started'] is False,'unstarted');req(d['repeated_campaign_evidence_model_present'],'model');req(d['duplicate_provider_test_activity_must_be_zero'],'duplicates');req(d['unauthorized_action_count_must_be_zero'],'unauth');req(d['private_content_finding_count_must_be_zero'],'private');req(not d['native_windows_execution_claimed'] and d['desktop_codex_native_windows_required'],'windows_truth');req(not d['checkpoint_executes_provider'] and not d['checkpoint_executes_tests'] and not d['checkpoint_mutates_source'],'readonly')
print(json.dumps({'ok':True,'suite':'v1280.9-reliability-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
