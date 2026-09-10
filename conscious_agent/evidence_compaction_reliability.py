from __future__ import annotations
"""v1192.6-v1192.8 reliability and privacy hardening for compacted evidence."""
import hashlib, json, re
from collections.abc import Mapping
from typing import Any
CONTRACT_VERSION='v1192.8'; DIGEST_RE=re.compile(r'^[0-9a-f]{64}$'); ID_RE=re.compile(r'^[A-Za-z0-9._:-]{8,128}$')
EVENTS={'interruption','restart','stale_compaction','replay','privacy','tamper','outage','recovery_review'}
ACTIONS={'preserve','defer','rebuild_required','reject','review_required'}
MAX_BYTES=262144
FORBIDDEN={'prompt','conversation','memory','secret','raw_source','raw_patch','stdout','stderr','provider_payload','private_reasoning','content','text','release_authority'}
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _is_digest(v:object)->bool:return bool(DIGEST_RE.fullmatch(str(v or '').lower()))
def _forbidden(v:object)->bool:
    if isinstance(v,Mapping): return any(str(k).lower() in FORBIDDEN or _forbidden(x) for k,x in v.items())
    if isinstance(v,(list,tuple)): return any(_forbidden(x) for x in v)
    return False
def create_reliability_record(*,record_id:str,event_type:str,action:str,compaction_digest:str,terminal_evidence_digest:str,snapshot_digest:str,context_digest:str,review_digest:str,sequence:int,previous_record_digest:str='')->dict[str,Any]:
    row={'contract_version':CONTRACT_VERSION,'record_id':str(record_id or ''),'event_type':str(event_type or ''),'action':str(action or ''),'compaction_digest':str(compaction_digest or '').lower(),'terminal_evidence_digest':str(terminal_evidence_digest or '').lower(),'snapshot_digest':str(snapshot_digest or '').lower(),'context_digest':str(context_digest or '').lower(),'review_digest':str(review_digest or '').lower(),'sequence':int(sequence),'previous_record_digest':str(previous_record_digest or '').lower(),'content_free':True,'automatic_recovery':False,'replacement_performed':False,'deletion_performed':False,'execution_invoked':False,'authority_granted':False}
    row['record_digest']=_digest(row); return row
def assess_compaction_reliability(*,records:list[Mapping[str,Any]],current_compaction_digest:str,current_terminal_evidence_digest:str,current_snapshot_digest:str,current_context_digest:str)->dict[str,Any]:
    errors=[]; rows=[dict(x) for x in records]
    if len(json.dumps(rows,sort_keys=True,default=str).encode())>MAX_BYTES: errors.append('oversized_contract')
    if not rows: errors.append('empty_records')
    if _forbidden(rows): errors.append('private_or_authority_content_present')
    ids=[]; seqs=[]; prev=''
    for i,row in enumerate(rows):
        claimed=str(row.pop('record_digest','')).lower()
        if not _is_digest(claimed) or claimed!=_digest(row): errors.append(f'tampered_record:{i}')
        row['record_digest']=claimed; ids.append(row.get('record_id')); seqs.append(row.get('sequence'))
        if not ID_RE.fullmatch(str(row.get('record_id') or '')): errors.append(f'invalid_record_id:{i}')
        if row.get('event_type') not in EVENTS: errors.append(f'unsupported_event_type:{i}')
        if row.get('action') not in ACTIONS: errors.append(f'unsupported_action:{i}')
        for f in ('compaction_digest','terminal_evidence_digest','snapshot_digest','context_digest','review_digest'):
            if not _is_digest(row.get(f)): errors.append(f'invalid_{f}:{i}')
        if i==0:
            if row.get('previous_record_digest') not in ('',None): errors.append('broken_lineage:0')
        elif row.get('previous_record_digest')!=prev: errors.append(f'broken_lineage:{i}')
        prev=claimed
        if row.get('sequence')!=i: errors.append(f'invalid_sequence:{i}')
        if row.get('compaction_digest')!=str(current_compaction_digest or '').lower(): errors.append(f'stale_compaction:{i}')
        if row.get('terminal_evidence_digest')!=str(current_terminal_evidence_digest or '').lower(): errors.append(f'stale_terminal_evidence:{i}')
        if row.get('snapshot_digest')!=str(current_snapshot_digest or '').lower(): errors.append(f'stale_snapshot:{i}')
        if row.get('context_digest')!=str(current_context_digest or '').lower(): errors.append(f'stale_context:{i}')
        for f in ('automatic_recovery','replacement_performed','deletion_performed','execution_invoked','authority_granted'):
            if row.get(f) is not False: errors.append(f'hidden_mutation_or_authority_claim:{i}')
        if row.get('content_free') is not True: errors.append(f'privacy_contract_violation:{i}')
    if len(ids)!=len(set(ids)): errors.append('duplicate_record_id')
    if len(seqs)!=len(set(seqs)): errors.append('duplicate_sequence')
    replay=len({r.get('review_digest') for r in rows})!=len(rows)
    if replay: errors.append('replay_detected')
    errors=sorted(set(errors)); ok=not errors
    out={'contract_version':CONTRACT_VERSION,'ok':ok,'status':'reliability_verified' if ok else 'blocked','errors':errors,'error_count':len(errors),'record_count':len(rows),'interruption_count':sum(r.get('event_type')=='interruption' for r in rows),'restart_count':sum(r.get('event_type')=='restart' for r in rows),'replay_detected':replay,'original_evidence_preserved':True,'content_free':True,'automatic_recovery':False,'replacement_performed':False,'deletion_performed':False,'execution_invoked':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'runtime_modified':False,'authority_granted':False}
    out['result_digest']=_digest(out); return out
def public_reliability_summary(result:Mapping[str,Any])->dict[str,Any]:
    return {k:result.get(k) for k in ('contract_version','ok','status','record_count','interruption_count','restart_count','replay_detected','original_evidence_preserved','content_free','automatic_recovery','replacement_performed','deletion_performed','execution_invoked','authority_granted')}
