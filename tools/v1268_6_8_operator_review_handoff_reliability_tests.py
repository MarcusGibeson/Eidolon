from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from operator_review_handoff_foundations import prepare_operator_review_handoff,validate_operator_review_packet,_record_digest,_record_path,_write_json
from operator_review_handoff_reliability import validate_operator_review_freshness,inspect_operator_review_handoff_health,build_operator_review_handoff_operator_handoff
from isolated_self_modification_foundations import load_self_modification,source_only_manifest
from v1268_fixture import verified_chain
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1268-stale-') as td:
    base=Path(td);chain=verified_chain(base);rt=base/'review';p=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt);req(validate_operator_review_freshness(p['review_id'],chain['source'],self_modification_runtime_root=chain['sm'],runtime_root=rt)['ok'],'fresh_packet');(chain['source']/'README_NEXT_STEPS.md').write_text('drift\n');req(validate_operator_review_freshness(p['review_id'],chain['source'],self_modification_runtime_root=chain['sm'],runtime_root=rt)['status']=='operator_review_handoff_stale','active_source_drift_detected')
with tempfile.TemporaryDirectory(prefix='eidolon-v1268-candidate-') as td:
    base=Path(td);chain=verified_chain(base);rt=base/'review';p=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt);workspace=Path(load_self_modification(p['source_operation_id'],runtime_root=chain['sm'])['workspace_path']);(workspace/'conscious_agent/app.py').write_text('def value():\n    return 9\n');req(validate_operator_review_freshness(p['review_id'],chain['source'],self_modification_runtime_root=chain['sm'],runtime_root=rt)['candidate_fresh'] is False,'candidate_drift_detected')
with tempfile.TemporaryDirectory(prefix='eidolon-v1268-tamper-') as td:
    base=Path(td);chain=verified_chain(base);rt=base/'review';p=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt);raw=dict(p);raw['candidate_verified']=False;raw['record_digest']=_record_digest(raw);_write_json(_record_path(p['review_id'],rt),raw);req(validate_operator_review_packet(raw)['ok'] is False,'resealed_semantic_tamper_rejected')
health=inspect_operator_review_handoff_health(source_root=ROOT);req(health['ok'],'health_ready');h=build_operator_review_handoff_operator_handoff(source_root=ROOT);req(h['ok'] and h['next_bounded_unit']=='v1269 Governed Self-Update','handoff_ready');req('fresh_v1269_authorization_required' in h['review_boundaries'],'fresh_authorization_explicit');req('cross_process_review_decision_lock' in h['native_windows_review'],'windows_cross_process_review_explicit')
with tempfile.TemporaryDirectory(prefix='eidolon-v1268-long-') as td:
    deep=Path(td)
    for i in range(5):deep=deep/('seg_'+str(i)+'_'+'x'*30)
    deep.mkdir(parents=True);chain=verified_chain(deep);rt=deep/'review';p=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt);req(len(str(rt.resolve()))>180,'long_path_fixture');req(p['phase']=='review_ready','long_path_review_ready')
print(json.dumps({'ok':True,'suite':'v1268.6-v1268.8-operator-review-handoff-reliability','passed':len(C),'failed':0,'checks':C,'active_source_modified':False},indent=2,sort_keys=True))
