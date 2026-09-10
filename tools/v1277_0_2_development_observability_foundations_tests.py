from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1277_fixture import prepared_observability_chain
from development_observability_foundations import *
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory() as td:
 c=prepared_observability_chain(Path(td),now=100);o=c['observability'];oid=o['observability_id'];req(o['operation_status']=='created','created');req(validate_development_observability(o)['ok'],'valid');req(o['content_free'],'content_free');req(o['bounded_retention'],'bounded');req(o['current_phase']=='prepared','phase');req(o['next_required_authorization']=='v1265_exact_candidate_authorization','next_auth')
 for k in ['raw_prompt_persisted','raw_response_persisted','provider_payload_persisted','raw_path_persisted','raw_command_output_persisted']:req(o[k] is False,'privacy_'+k)
 for k,v in AUTHORITY_FLAGS.items():req(v is False,'authority_'+k)
 r=record_observability_event(oid,runtime_root=c['runtime'],event_code='phase_started',phase='candidate_execution',outcome='started',work_code='candidate_stage',elapsed_seconds=.25,detail_codes=['bounded_start'],lineage_marker='a'*64,now=101);req(r['operation_status']=='event_recorded','event');req(r['event']['elapsed_ms']==250,'ms');req(r['event_count_total']==1,'count')
 d=record_observability_event(oid,runtime_root=c['runtime'],event_code='phase_started',phase='candidate_execution',outcome='started',work_code='candidate_stage',lineage_marker='a'*64,now=102);req(d['duplicate_event_suppressed'],'dedupe');req(d['event_count_total']==1,'dedupe_count')
 s=build_harness_budget_signal(oid,runtime_root=c['runtime'],phase='verification_and_repair',predicted_seconds=121,budget_seconds=90,now=103);req(s['split_required'],'split');req(not s['global_timeout_increase_authorized'],'no_timeout_authority')
 for i in range(MAX_EVENTS+20):record_observability_event(oid,runtime_root=c['runtime'],event_code='progress_observed',phase='candidate_execution',outcome='observed',work_code='progress',detail_codes=['tick'],lineage_marker=f'{1000+i:064x}',now=200+i)
 f=load_development_observability(oid,runtime_root=c['runtime']);req(validate_development_observability(f)['ok'],'valid_final');req(len(f['events'])==MAX_EVENTS,'events_bound');req(f['event_count_total']>len(f['events']),'aggregate_survives');req(len(f['bounded_summaries'])<=MAX_SUMMARIES,'summary_bound')
 pub=public_development_observability(f);req(pub['content_free'],'public_content_free');req(pub['private_payloads_exposed'] is False,'no_private_public');req(len(pub['recent_events'])<=12,'recent_bound')
 for fn,label in [(lambda:record_observability_event(oid,runtime_root=c['runtime'],event_code='progress_observed',phase='bad phase'),'unsafe_phase'),(lambda:record_observability_event(oid,runtime_root=c['runtime'],event_code='progress_observed',phase='prepared',detail_codes=['secret=value']),'unsafe_detail'),(lambda:record_observability_event(oid,runtime_root=c['runtime'],event_code='progress_observed',phase='prepared',elapsed_seconds=-1),'negative_time'),(lambda:record_observability_event(oid,runtime_root=c['runtime'],event_code='bogus',phase='prepared'),'bogus_event')]:
  try:fn();raise AssertionError(label+'_accepted')
  except ValueError:C.append(label+'_rejected')
print(json.dumps({'ok':True,'suite':'v1277.0-2-development-observability-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
