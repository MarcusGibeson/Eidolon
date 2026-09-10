from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1270_fixture import prepared_chain,evidence,priority_context
from self_development_alpha_foundations import *
from isolated_self_modification_foundations import source_only_manifest,load_self_modification
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1270-found-') as td:
    b=Path(td);c=prepared_chain(b);r=c['campaign']
    req(r['phase']=='prepared','phase_prepared');req(r['improvement_proposed'] is True,'improvement_proposed');req(r['proposal_is_judgment_not_authority'] is True,'proposal_not_authority')
    req(r['selected_objective_code']=='investigate_test_signal:alpha_value_contract','selected_evidence_backed_improvement');req(bool(r['selected_strategy_code']),'alternative_plan_selected')
    req(r['candidate_materialized'] is True,'candidate_materialized');req(bool(r['candidate_operation_id']),'candidate_operation_bound');req(bool(r['candidate_authorization_phrase']),'exact_candidate_authorization_exposed')
    req(r['candidate_provider_executed'] is False,'provider_not_executed');req(r['tests_executed'] is False,'tests_not_executed');req(r['active_source_modified'] is False,'active_source_not_modified')
    req(source_only_manifest(c['source'])['source_manifest_digest']==c['before'],'source_immutable');req(validate_self_development_alpha_campaign(r)['ok'],'campaign_valid')
    restored=prepare_self_development_alpha_campaign(c['source'],external_evidence=evidence(),priority_context=priority_context(),runtime_root=c['runtime']);req(restored['campaign_id']==r['campaign_id'],'deterministic_campaign_id');req(restored['operation_status']=='restored','restart_restore')
    selfrec=load_self_modification(r['candidate_operation_id'],runtime_root=_stage_root(c['runtime'],'v1265'));req(selfrec['phase']=='prepared','v1265_still_prepared')
    for k,v in ALPHA_DENIED_AUTHORITY.items(): req(r[k] is v,k+'_denied')
print(json.dumps({'ok':True,'suite':'v1270.0-v1270.2-self-development-alpha-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
