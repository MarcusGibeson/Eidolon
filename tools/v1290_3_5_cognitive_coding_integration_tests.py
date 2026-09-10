from __future__ import annotations
import json,sys,tempfile
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cognitive_coding_foundations import create_cognitive_coding_campaign,record_assumption_revision,select_discriminating_diagnostics,continuity_event,DENIED_AUTHORITY,digest
from cognitive_coding import build_cognitive_coding_result,public_cognitive_coding_result
from v1290_test_support import write_fixture,project_manifest,run,normalization_probe,apply_solution,quality_evidence
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1290-unfamiliar-') as td:
 root=Path(td);write_fixture(root);before=project_manifest(root)
 baseline=run(root,'-m','unittest','discover','-s','tests');req(not baseline['passed'],'unfamiliar_fixture_starts_failing')
 campaign=create_cognitive_coding_campaign(objective_digest=digest({'requirement':'normalize codes and aggregate duplicate invoice totals'}),project_manifest_digest=before['digest'],project_file_count=before['file_count'],initial_assumptions=[{'assumption_code':'aggregation_only','evidence_digest':baseline['stderr_digest']}])
 selected=select_discriminating_diagnostics(campaign,[{'probe_code':'normalization_behavior','distinguishes':['aggregation_only','normalization_and_aggregation'],'cost':5,'information_gain':95},{'probe_code':'rerun_everything','distinguishes':['aggregation_only','normalization_and_aggregation'],'cost':90,'information_gain':25}]);req(selected[0]['probe_code']=='normalization_behavior','intelligent_probe_selected')
 probe=normalization_probe(root);req(probe['passed'] and probe['supports_combined_defect'],'probe_falsifies_initial_assumption')
 revision=record_assumption_revision(campaign,assumption_code='aggregation_only',outcome='revised',contradicting_evidence_digest=probe['observed_value_digest'],replacement_assumption_code='normalization_and_aggregation');req(revision['outcome']=='revised','mistaken_assumption_revised')
 ev1=continuity_event(campaign,stage='diagnosis',evidence_digest=revision['revision_digest']);changed=apply_solution(root);after=project_manifest(root);req(len(changed)==2 and before['digest']!=after['digest'],'actual_multifile_change')
 ev2=continuity_event(campaign,stage='verification',evidence_digest=after['digest'],previous_event_digest=ev1['event_digest']);req(ev2['previous_event_digest']==ev1['event_digest'],'continuity_preserved')
 focused=run(root,'-m','unittest','tests.test_summary.SummaryTests.test_normalized_aggregation');regression=run(root,'-m','unittest','discover','-s','tests');req(focused['passed'],'focused_test_passes');req(regression['passed'],'regression_passes')
 # Actual CLI walkthrough: output is text/JSON, help has semantic labels, no color-only state.
 help_run=run(root,'-m','invoice.cli','--help');req(help_run['passed'],'operator_walkthrough_help_passes')
 result=build_cognitive_coding_result(campaign,assumption_revisions=[revision],diagnostic_results=[{'probe_code':'normalization_behavior','observed':True,'distinguishes':['aggregation_only','normalization_and_aggregation'],'evidence_digest':probe['observed_value_digest']}],changed_paths=changed,verification_results=[{'tier':'focused','passed':True,'result_digest':focused['stdout_digest']},{'tier':'regression','passed':True,'result_digest':regression['stdout_digest']}],quality_evidence=quality_evidence(before['digest']))
 req(result['ok'],'benchmark_complete');req(result['status']=='cognitive_coding_benchmark_complete','status');req(result['changed_path_count']==2,'two_changed_paths');req(result['assumption_revision_count']==1,'revision_count');req(result['quality_disposition']=='operator_ready_candidate','polished_quality_candidate');req(all(result['checks'].values()),'completion_checks');req(result['release_ready_claimed'] is False and result['completion_is_authorization'] is False,'not_release_or_authority')
 pub=public_cognitive_coding_result(result);req(pub['content_free'],'public_content_free');req(all(pub[k] is False for k in DENIED_AUTHORITY),'public_no_authority')
 # Without revision or without regression, completion must fail.
 no_revision=build_cognitive_coding_result(campaign,assumption_revisions=[],diagnostic_results=[{'observed':True,'distinguishes':['a','b']}],changed_paths=changed,verification_results=[{'tier':'focused','passed':True},{'tier':'regression','passed':True}],quality_evidence=quality_evidence(before['digest']))
 req(not no_revision['ok'] and not no_revision['checks']['mistaken_assumption_revised'],'revision_mandatory')
 no_reg=build_cognitive_coding_result(campaign,assumption_revisions=[revision],diagnostic_results=[{'observed':True,'distinguishes':['a','b']}],changed_paths=changed,verification_results=[{'tier':'focused','passed':True}],quality_evidence=quality_evidence(before['digest']))
 req(not no_reg['ok'] and not no_reg['checks']['regression_verification_passed'],'regression_mandatory')
print(json.dumps({'ok':True,'suite':'v1290.3-v1290.5-cognitive-coding-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
