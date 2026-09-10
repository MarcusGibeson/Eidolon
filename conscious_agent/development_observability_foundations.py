from __future__ import annotations
"""v1277.0-v1277.2 bounded, privacy-safe development observability foundations."""
import hashlib,json,os,re,tempfile,time
from pathlib import Path
from typing import Any,Iterable,Mapping
from ordinary_chat_development_campaign import _proposal_lock
from self_development_alpha_foundations import _runtime_root,load_self_development_alpha_campaign,validate_self_development_alpha_campaign
from long_running_work_sessions_foundations import AUTHORITY_FLAGS as LONG_AUTH,load_long_running_work_session,validate_long_running_work_session
SCHEMA_VERSION='1';CONTRACT_VERSION='v1277.2';MAX_RECORD_BYTES=4*1024*1024;MAX_EVENTS=64;MAX_SUMMARIES=10;MAX_MARKERS=96;MAX_DETAILS=12;MAX_SECONDS=86400
EVENT_CODES=frozenset({'phase_started','phase_attempted','phase_completed','phase_blocked','authorization_required','retry_observed','retry_suppressed','failure_observed','recovery_observed','ownership_observed','environment_evidence_observed','provider_outage','provider_return','budget_split_required','paused','resumed','interrupted','cancelled','restart_observed','progress_observed'})
OUTCOMES=frozenset({'started','attempted','completed','blocked','observed','suppressed','cancelled'})
AUTHORITY_FLAGS={**LONG_AUTH,'observability_is_execution_authority':False,'observability_is_provider_authority':False,'observability_is_test_authority':False,'observability_is_retry_authority':False,'observability_is_update_authority':False,'observability_is_application_authority':False,'observability_is_rollback_authority':False,'observability_is_release_authority':False,'performance_signal_is_timeout_authority':False,'authorization_status_is_authorization':False}
_OID=re.compile(r'^observability_[a-f0-9]{24}$');_SAFE=re.compile(r'^[a-z0-9][a-z0-9_.:-]{0,95}$');_HEX=re.compile(r'^[a-f0-9]{64}$')
_ALLOWED_EVENT_KEYS=frozenset({'event_code','phase','outcome','work_code','elapsed_ms','phase_budget_ms','detail_codes','recorded_at','lineage_marker','content_free','event_digest'})
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def observability_id_for_session(session_id:str,campaign_id:str,source_manifest_digest:str)->str:return 'observability_'+hashlib.sha256(f'{session_id}:{campaign_id}:{source_manifest_digest}:v1277'.encode()).hexdigest()[:24]
def _root(runtime_root):return _runtime_root(runtime_root)/'development_observability'
def _path(oid,runtime_root):
    if not _OID.fullmatch(str(oid or '')):raise ValueError('invalid_development_observability_id')
    return _root(runtime_root)/'records'/f'{oid}.json'
def _read(p:Path):
    if not p.exists():return {}
    if p.stat().st_size>MAX_RECORD_BYTES:raise ValueError('development_observability_record_too_large')
    v=json.loads(p.read_text());
    if not isinstance(v,dict):raise ValueError('development_observability_record_invalid')
    return v
def _write(p:Path,row:Mapping[str,Any]):
    data=(json.dumps(dict(row),indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode()
    if len(data)>MAX_RECORD_BYTES:raise ValueError('development_observability_record_too_large')
    p.parent.mkdir(parents=True,exist_ok=True);tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',delete=False,dir=p.parent,suffix='.tmp') as h:h.write(data);h.flush();os.fsync(h.fileno());tmp=Path(h.name)
        os.replace(tmp,p);tmp=None
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)
def _record_digest(row):return _digest({k:v for k,v in row.items() if k not in {'record_digest','operation_status'}})
def _seal(row):o=dict(row);o['record_digest']=_record_digest(o);return o
def _event_digest(row):return _digest({k:v for k,v in row.items() if k!='event_digest'})
def _seal_event(row):o=dict(row);o['event_digest']=_event_digest(o);return o
def _safe(v,field,allow_empty=False):
    t=str(v or '').strip().lower()
    if allow_empty and not t:return ''
    if not _SAFE.fullmatch(t):raise ValueError(f'invalid_observability_{field}_code')
    return t
def _codes(values):
    rows=[]
    for v in values or ():
        t=_safe(v,'detail')
        if t not in rows:rows.append(t)
    return rows[-MAX_DETAILS:]
def _ms(seconds,field):
    v=float(seconds or 0)
    if v<0 or v>MAX_SECONDS:raise ValueError(f'observability_{field}_seconds_out_of_bounds')
    return int(round(v*1000))
def _summary(row,events):
    recent=events[-8:]
    return {'summary_version':'1','event_count_total':int(row.get('event_count_total') or 0),'retained_event_count':len(events),'latest_phase':str(recent[-1].get('phase') if recent else row.get('current_phase') or 'prepared'),'latest_event_code':str(recent[-1].get('event_code') if recent else 'progress_observed'),'failure_count_total':int(row.get('failure_count_total') or 0),'retry_count_total':int(row.get('retry_count_total') or 0),'recovery_count_total':int(row.get('recovery_count_total') or 0),'budget_split_count_total':int(row.get('budget_split_count_total') or 0),'aggregate_event_counts':dict(row.get('aggregate_event_counts') or {}),'recent_event_digests':[str(x.get('event_digest') or '') for x in recent],'content_free':True}
def validate_development_observability(row):
    digest_ok=bool(row.get('record_digest')) and row.get('record_digest')==_record_digest(row);events=list(row.get('events') or []);summaries=list(row.get('bounded_summaries') or []);markers=list(row.get('lineage_markers') or [])
    events_ok=len(events)<=MAX_EVENTS and all(set(e).issubset(_ALLOWED_EVENT_KEYS) and e.get('event_code') in EVENT_CODES and e.get('outcome') in OUTCOMES and bool(_SAFE.fullmatch(str(e.get('phase') or ''))) and (not e.get('work_code') or bool(_SAFE.fullmatch(str(e.get('work_code'))))) and int(e.get('elapsed_ms') or 0)>=0 and int(e.get('phase_budget_ms') or 0)>=0 and len(e.get('detail_codes') or [])<=MAX_DETAILS and all(_SAFE.fullmatch(str(c or '')) for c in e.get('detail_codes') or []) and (not e.get('lineage_marker') or bool(_HEX.fullmatch(str(e.get('lineage_marker'))))) and e.get('content_free') is True and e.get('event_digest')==_event_digest(e) for e in events)
    semantic=bool(_OID.fullmatch(str(row.get('observability_id') or ''))) and str(row.get('session_id') or '').startswith('longwork_') and str(row.get('campaign_id') or '').startswith('selfalpha_') and bool(_HEX.fullmatch(str(row.get('source_manifest_digest') or ''))) and row.get('content_free') is True and row.get('raw_prompt_persisted') is False and row.get('raw_response_persisted') is False and row.get('provider_payload_persisted') is False and row.get('raw_path_persisted') is False and row.get('raw_command_output_persisted') is False and row.get('active_source_modified') is False and int(row.get('event_count_total') or 0)>=len(events)
    auth=all(row.get(k) is v for k,v in AUTHORITY_FLAGS.items());ok=digest_ok and events_ok and len(summaries)<=MAX_SUMMARIES and all(x.get('content_free') is True for x in summaries) and len(markers)<=MAX_MARKERS and all(_HEX.fullmatch(str(x or '')) for x in markers) and auth and semantic
    return {'ok':ok,'status':'development_observability_valid' if ok else 'development_observability_invalid','digest_valid':digest_ok,'events_valid':events_ok,'authority_contained':auth,'semantic_valid':semantic}
def prepare_development_observability(session_id,*,runtime_root,now=None):
    runtime=_runtime_root(runtime_root);s=load_long_running_work_session(session_id,runtime_root=runtime)
    if not s or not validate_long_running_work_session(s).get('ok'):raise ValueError('valid_v1271_long_running_work_session_required')
    cid=str(s.get('campaign_id') or '');c=load_self_development_alpha_campaign(cid,runtime_root=runtime)
    if not c or not validate_self_development_alpha_campaign(c).get('ok'):raise ValueError('valid_v1270_self_development_campaign_required')
    sd=str(c.get('source_manifest_digest') or '');oid=observability_id_for_session(session_id,cid,sd);p=_path(oid,runtime);clock=float(time.time() if now is None else now)
    with _proposal_lock('devc_'+session_id.split('_',1)[1],runtime):
        old=_read(p)
        if old:
            if not validate_development_observability(old).get('ok'):raise ValueError('stored_development_observability_invalid')
            return {**old,'operation_status':'restored'}
        row=_seal({'ok':True,'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'status':'development_observability_prepared','observability_id':oid,'session_id':session_id,'campaign_id':cid,'source_manifest_digest':sd,'current_phase':str(s.get('current_phase') or 'prepared'),'next_required_authorization':str(s.get('next_required_authorization') or 'operator_reconciliation'),'events':[],'bounded_summaries':[],'lineage_markers':[],'aggregate_event_counts':{},'event_count_total':0,'failure_count_total':0,'retry_count_total':0,'recovery_count_total':0,'budget_split_count_total':0,'created_at':clock,'updated_at':clock,'content_free':True,'bounded_retention':True,'aggregate_counts_survive_compaction':True,'raw_prompt_persisted':False,'raw_response_persisted':False,'provider_payload_persisted':False,'raw_path_persisted':False,'raw_command_output_persisted':False,'active_source_modified':False,**AUTHORITY_FLAGS});_write(p,row);return {**row,'operation_status':'created'}
def load_development_observability(oid,*,runtime_root):return _read(_path(oid,runtime_root))
def record_observability_event(oid,*,runtime_root,event_code,phase,outcome='observed',work_code='',elapsed_seconds=0.0,phase_budget_seconds=0.0,detail_codes=(),lineage_marker='',next_required_authorization=None,now=None):
    if event_code not in EVENT_CODES:raise ValueError('invalid_observability_event_code')
    if outcome not in OUTCOMES:raise ValueError('invalid_observability_outcome')
    phase=_safe(phase,'phase');work=_safe(work_code,'work',True);details=_codes(detail_codes);marker=str(lineage_marker or '')
    if marker and not _HEX.fullmatch(marker):raise ValueError('invalid_observability_lineage_marker')
    auth=None if next_required_authorization is None else _safe(next_required_authorization,'authorization');runtime=_runtime_root(runtime_root);clock=float(time.time() if now is None else now)
    with _proposal_lock('devc_'+oid.split('_',1)[1],runtime):
        row=load_development_observability(oid,runtime_root=runtime)
        if not validate_development_observability(row).get('ok'):raise ValueError('valid_development_observability_required')
        markers=list(row.get('lineage_markers') or [])
        if marker and marker in markers:return {**row,'operation_status':'duplicate_event_suppressed','duplicate_event_suppressed':True}
        e=_seal_event({'event_code':event_code,'phase':phase,'outcome':outcome,'work_code':work,'elapsed_ms':_ms(elapsed_seconds,'elapsed'),'phase_budget_ms':_ms(phase_budget_seconds,'phase_budget'),'detail_codes':details,'recorded_at':clock,'lineage_marker':marker,'content_free':True});events=(list(row.get('events') or [])+[e])[-MAX_EVENTS:];agg=dict(row.get('aggregate_event_counts') or {});agg[event_code]=int(agg.get(event_code) or 0)+1;u=dict(row);u.update({'events':events,'aggregate_event_counts':dict(sorted(agg.items())),'event_count_total':int(row.get('event_count_total') or 0)+1,'failure_count_total':int(row.get('failure_count_total') or 0)+(1 if event_code=='failure_observed' or outcome=='blocked' else 0),'retry_count_total':int(row.get('retry_count_total') or 0)+(1 if event_code=='retry_observed' else 0),'recovery_count_total':int(row.get('recovery_count_total') or 0)+(1 if event_code in {'recovery_observed','restart_observed'} else 0),'budget_split_count_total':int(row.get('budget_split_count_total') or 0)+(1 if event_code=='budget_split_required' else 0),'current_phase':phase,'next_required_authorization':auth if auth is not None else row.get('next_required_authorization'),'updated_at':clock})
        if marker:markers.append(marker);u['lineage_markers']=markers[-MAX_MARKERS:]
        sums=list(row.get('bounded_summaries') or []);sums.append(_summary(u,events));u['bounded_summaries']=sums[-MAX_SUMMARIES:];u=_seal(u);_write(_path(oid,runtime),u);return {**u,'operation_status':'event_recorded','event':e}
def build_harness_budget_signal(oid,*,runtime_root,phase,predicted_seconds,budget_seconds,now=None):
    p=float(predicted_seconds);b=float(budget_seconds)
    if p<0 or b<=0 or p>MAX_SECONDS or b>MAX_SECONDS:raise ValueError('invalid_observability_harness_budget')
    over=p>b
    if over:row=record_observability_event(oid,runtime_root=runtime_root,event_code='budget_split_required',phase=phase,outcome='blocked',elapsed_seconds=p,phase_budget_seconds=b,detail_codes=['split_harness','do_not_raise_global_timeout'],lineage_marker=_digest({'signal':'harness_budget_split_required','phase':phase,'predicted_ms':int(p*1000),'budget_ms':int(b*1000)}),now=now)
    else:row=load_development_observability(oid,runtime_root=runtime_root)
    return {'ok':True,'status':'harness_budget_split_required' if over else 'harness_budget_within_limit','predicted_seconds':p,'budget_seconds':b,'monolithic_run_within_budget':not over,'global_timeout_increase_authorized':False,'split_required':over,'observability_record_digest':row.get('record_digest'),**AUTHORITY_FLAGS}
def public_development_observability(row):
    v=validate_development_observability(row);ev=list(row.get('events') or [])
    return {'ok':v.get('ok') is True,'status':'development_observability_operator_status' if v.get('ok') else 'development_observability_invalid','observability_id':row.get('observability_id'),'session_id':row.get('session_id'),'campaign_id':row.get('campaign_id'),'current_phase':row.get('current_phase'),'next_required_authorization':row.get('next_required_authorization'),'event_count_total':int(row.get('event_count_total') or 0),'retained_event_count':len(ev),'failure_count_total':int(row.get('failure_count_total') or 0),'retry_count_total':int(row.get('retry_count_total') or 0),'recovery_count_total':int(row.get('recovery_count_total') or 0),'budget_split_count_total':int(row.get('budget_split_count_total') or 0),'aggregate_event_counts':dict(row.get('aggregate_event_counts') or {}),'recent_events':[{'event_code':x.get('event_code'),'phase':x.get('phase'),'outcome':x.get('outcome'),'elapsed_ms':x.get('elapsed_ms'),'phase_budget_ms':x.get('phase_budget_ms'),'detail_codes':list(x.get('detail_codes') or [])} for x in ev[-12:]],'bounded_retention':True,'content_free':True,'private_payloads_exposed':False,'active_source_modified':False,**AUTHORITY_FLAGS}
__all__=['CONTRACT_VERSION','AUTHORITY_FLAGS','MAX_EVENTS','MAX_SUMMARIES','EVENT_CODES','observability_id_for_session','prepare_development_observability','load_development_observability','validate_development_observability','record_observability_event','build_harness_budget_signal','public_development_observability']
