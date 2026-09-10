from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from operator_review_handoff_foundations import REVIEW_DENIED_AUTHORITY,prepare_operator_review_handoff,public_operator_review_packet,validate_operator_review_packet
from v1268_fixture import verified_chain
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1268-found-') as td:
    base=Path(td);chain=verified_chain(base);rt=base/'review'
    packet=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt)
    req(packet['phase']=='review_ready','review_ready');req(validate_operator_review_packet(packet)['ok'],'packet_valid');req(packet['candidate_verified'] is True,'candidate_verified');req(packet['changed_file_count']>=1,'changed_files_present');req(all(not r['content_exposed'] for r in packet['changed_files']),'diff_content_minimized');req(packet['verification']['passed'] is True,'verification_present');req(packet['risks'] and packet['unresolved_uncertainty'],'risks_and_uncertainty_present');req(packet['rollback_instructions']['active_rollback_needed_now'] is False,'no_active_rollback_needed');req(packet['operator_choices']==['approve_for_v1269_consideration','defer','reject'],'bounded_choices');req(packet['operator_decision_required'] is True,'operator_decision_required');req(packet['active_source_modified'] is False,'active_source_unchanged')
    restored=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=rt);req(restored['operation_status']=='restored' and restored['review_id']==packet['review_id'],'duplicate_prepare_idempotent')
    pub=public_operator_review_packet(packet);req('record_digest' not in pub and pub['content_minimized'],'public_packet_minimized')
    for k,v in REVIEW_DENIED_AUTHORITY.items(): req(packet[k] is v,f'{k}_denied')
print(json.dumps({'ok':True,'suite':'v1268.0-v1268.2-operator-review-handoff-foundations','passed':len(C),'failed':0,'checks':C,'active_source_modified':False},indent=2,sort_keys=True))
