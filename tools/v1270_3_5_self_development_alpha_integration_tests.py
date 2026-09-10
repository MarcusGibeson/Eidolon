from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1270_fixture import prepared_chain,initial_provider,repair_provider
from self_development_alpha import *
from self_development_alpha_foundations import load_self_development_alpha_campaign
from isolated_self_modification_foundations import source_only_manifest
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1270-int-') as td:
    b=Path(td);c=prepared_chain(b);cid=c['campaign']['campaign_id'];initial=[];repairs=[]
    wrong=execute_self_development_alpha_candidate(cid,c['source'],runtime_root=c['runtime'],authorization_phrase='go ahead',provider=initial_provider(initial));req(wrong['status']=='isolated_self_modification_exact_authorization_required','generic_authorization_blocked');req(len(initial)==0,'no_provider_on_wrong_auth')
    stage=execute_self_development_alpha_candidate(cid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(initial));req(stage['phase']=='repair_authorization_required','repair_auth_required');req(len(initial)==1,'one_initial_provider_call');req(stage['selected_test_count']>=1,'tests_selected');req(stage['tests_executed'] is False,'tests_wait_for_exact_repair_auth')
    wrong2=execute_self_development_alpha_verification_and_review(cid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase='proceed',repair_provider=repair_provider(repairs));req(wrong2['status']=='iterative_self_repair_exact_authorization_required','generic_repair_authorization_blocked');req(len(repairs)==0,'no_repair_provider_on_wrong_auth')
    final=execute_self_development_alpha_verification_and_review(cid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs));req(final['phase']=='operator_review_required','review_ready');req(final['tests_executed'] is True,'trusted_tests_executed');req(final['repair_attempt_count']==1,'one_repair_attempt');req(len(repairs)==1,'one_repair_provider_call');req(bool(final['review_id']),'review_packet_bound');req(final['operator_decision']=='pending','operator_decision_pending');req(final['v1269_consideration_ready'] is False,'v1269_not_ready_before_review')
    req(source_only_manifest(c['source'])['source_manifest_digest']==c['before'],'active_source_unchanged')
    replay=execute_self_development_alpha_verification_and_review(cid,c['source'],runtime_root=c['runtime'],repair_authorization_phrase=stage['repair_authorization_phrase'],repair_provider=repair_provider(repairs));req(replay['operation_status']=='restored','review_replay_idempotent');req(len(repairs)==1,'no_duplicate_repair_provider')
    decided=record_self_development_alpha_review_decision(cid,runtime_root=c['runtime'],decision='approve_for_v1269_consideration');req(decided['phase']=='review_decided','review_decision_recorded');req(decided['v1269_consideration_ready'] is True,'v1269_consideration_ready');req(decided['self_update_authorized'] is False,'review_does_not_authorize_update');req(source_only_manifest(c['source'])['source_manifest_digest']==c['before'],'source_still_unchanged_after_review')
print(json.dumps({'ok':True,'suite':'v1270.3-v1270.5-self-development-alpha-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
