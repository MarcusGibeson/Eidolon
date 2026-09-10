from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from operator_review_handoff_foundations import prepare_operator_review_handoff
from operator_review_handoff import record_operator_review_decision,build_v1269_review_handoff
from isolated_self_modification_foundations import source_only_manifest
from v1268_fixture import verified_chain
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1268-int-') as td:
    base=Path(td);chain=verified_chain(base);rt=base/'review';packet=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt)
    bad=record_operator_review_decision(packet['review_id'],packet_digest='0'*64,decision='approve_for_v1269_consideration',runtime_root=rt);req(bad['status']=='operator_review_packet_digest_mismatch','exact_packet_digest_required');req(build_v1269_review_handoff(packet['review_id'],runtime_root=rt)['ok'] is False,'no_handoff_before_valid_decision')
    decision=record_operator_review_decision(packet['review_id'],packet_digest=packet['record_digest'],decision='approve_for_v1269_consideration',runtime_root=rt);req(decision['ok'] and decision['eligible_for_v1269_consideration'],'approval_for_consideration_recorded');req(decision['decision_is_authority'] is False,'decision_not_authority');handoff=build_v1269_review_handoff(packet['review_id'],runtime_root=rt);req(handoff['ok'] and handoff['status']=='v1269_review_handoff_ready','v1269_handoff_ready');req(handoff['fresh_v1269_preflight_required'] and handoff['fresh_v1269_authorization_required'],'fresh_v1269_gate_required');req(handoff['self_update_authorized'] is False and handoff['source_application_authorized'] is False,'handoff_has_no_update_authority');req(source_only_manifest(chain['source'])['source_manifest_digest']==chain['active_digest'],'decision_never_changes_active_source')
    replay=record_operator_review_decision(packet['review_id'],packet_digest=packet['record_digest'],decision='approve_for_v1269_consideration',runtime_root=rt);req(replay['operation_status']=='restored','same_decision_idempotent');conflict=record_operator_review_decision(packet['review_id'],packet_digest=packet['record_digest'],decision='reject',runtime_root=rt);req(conflict['status']=='conflicting_operator_review_decision_rejected','conflicting_decision_rejected')
with tempfile.TemporaryDirectory(prefix='eidolon-v1268-defer-') as td:
    base=Path(td);chain=verified_chain(base);rt=base/'review';packet=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt);d=record_operator_review_decision(packet['review_id'],packet_digest=packet['record_digest'],decision='defer',runtime_root=rt);req(d['eligible_for_v1269_consideration'] is False,'defer_not_eligible');req(build_v1269_review_handoff(packet['review_id'],runtime_root=rt)['ok'] is False,'defer_blocks_v1269_handoff')
print(json.dumps({'ok':True,'suite':'v1268.3-v1268.5-operator-review-handoff-integration','passed':len(C),'failed':0,'checks':C,'active_source_modified':False},indent=2,sort_keys=True))
