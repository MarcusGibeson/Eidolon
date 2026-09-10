from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
from autonomy_benchmark_v2400 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
matrix=build_autonomy_matrix()
req(matrix['ok'] and matrix['matrix']['expand_own_authority']=='prohibited','self_authority_expansion_prohibited')
req(matrix['matrix']['install_candidate']=='review_required','installation_remains_review_required')
restrict=build_autonomy_matrix({'execute_local_tool':'prohibited'})
req(restrict['ok'] and restrict['matrix']['execute_local_tool']=='prohibited','matrix_can_be_more_restrictive')
expand=build_autonomy_matrix({'expand_own_authority':'independent'})
req(not expand['ok'] and 'authority_expansion_override_rejected' in expand['errors'],'matrix_cannot_expand_authority')
D='a'*64
freeze=freeze_benchmark_claims(source_manifest_digest=D,capability_claims=[{'claim_code':'portable_goal_to_candidate','status':'verified_portable','evidence_digest':'1'*64},{'claim_code':'windows_long_soak','status':'deferred_native','evidence_digest':'2'*64}],known_limitations=['native_benchmark_pending'],deferred_local_evidence=['windows_soak'])
req(freeze['ok'] and len(freeze['claims'])==2,'claims_frozen_with_evidence')
req(freeze['browser_cannot_certify_native_claims'],'native_claims_not_certified')
privacy=freeze_benchmark_claims(source_manifest_digest=D,capability_claims=[],known_limitations=['C:/private/path'],deferred_local_evidence=['operator notes here'])
req(privacy['rejected_inventory_text_count']==2 and privacy['known_limitations']==[],'free_form_inventory_text_rejected')
bad=freeze_benchmark_claims(source_manifest_digest=D,capability_claims=[{'claim_code':'magic','status':'verified_portable','evidence_digest':'bad'}],known_limitations=[],deferred_local_evidence=[])
req(not bad['ok'] and bad['rejected_claim_count']==1,'unsupported_claim_evidence_rejected')
fixture=build_benchmark_fixture(fixture_id='f1',scenario_codes=['goal_to_candidate','quiet_background','authority_refusal'],expected_boundary_codes=['review_install','no_secret_access'])
req(fixture['ok'] and fixture['deterministic'],'deterministic_fixture_ready')
score=score_portable_benchmark(fixture=fixture,outcomes=[{'scenario_code':'goal_to_candidate','passed':True,'evidence_digest':'3'*64},{'scenario_code':'quiet_background','passed':True,'evidence_digest':'4'*64},{'scenario_code':'authority_refusal','passed':True,'evidence_digest':'5'*64}])
req(score['ok'] and score['pass_rate']==1.0,'portable_benchmark_scored')
req(score['native_certification_required'],'portable_score_not_native_certification')
incomplete=score_portable_benchmark(fixture=fixture,outcomes=[{'scenario_code':'goal_to_candidate','passed':True,'evidence_digest':'3'*64}])
req(not incomplete['ok'] and incomplete['status']=='portable_benchmark_incomplete','incomplete_fixture_not_passed')
dup=score_portable_benchmark(fixture=fixture,outcomes=[{'scenario_code':'goal_to_candidate','passed':True,'evidence_digest':'3'*64},{'scenario_code':'goal_to_candidate','passed':True,'evidence_digest':'4'*64}])
req(not dup['ok'] and dup['malformed_outcome_count']>0,'duplicate_scenario_rejected')
packet=assemble_v2500_gate_packet(claim_freeze=freeze,autonomy_matrix=matrix,portable_score=score,release_packet_digest='6'*64)
req(packet['ok'] and packet['status']=='v2500_desktop_gate_packet_ready','v2500_gate_packet_ready')
req(packet['operator_decision_required'] and packet['next_research_roadmap_required'],'benchmark_requires_operator_and_next_roadmap')
req('native_windows_long_soak' in packet['required_desktop_evidence'],'native_soak_explicitly_deferred')
req(all(not packet[k] for k in ('benchmark_certified','native_evidence_collected','operator_benchmark_completed','installation_authorized','promotion_authorized','authority_expanded')),'benchmark_packet_non_certifying')
print(json.dumps({'suite':'v2499.9-autonomy-benchmark-prep','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
