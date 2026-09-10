from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from cognitive_coding_checkpoint import cognitive_coding_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=cognitive_coding_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1290.9','version');req(r['status']=='cognitive_coding_checkpoint_ready','status');req(all(r['checks'].values()),'checks');req(r['checks']['unfamiliar_multifile_fixture_benchmark'],'multifile');req(r['checks']['mistaken_assumption_revision_required'],'revision');req(r['checks']['intelligent_diagnostic_selection_required'],'diagnostics');req(r['checks']['focused_and_regression_verification_required'],'verification');req(r['checks']['product_quality_required'],'quality');req(r['checks']['existing_supervised_lineage_reused'],'lineage');req(r['checks']['native_windows_coding_validation_pending'],'native_pending');req(r['next']=='v1291 Independent Improvement Proposals' and r['v1291_started'] and r['checks']['v1291_transition_coherent'],'next_transition');req(r['read_only'] and not r['project_mutation_authorized'] and not r['release_authorized'],'readonly')
print(json.dumps({'ok':True,'suite':'v1290.9-cognitive-coding-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
