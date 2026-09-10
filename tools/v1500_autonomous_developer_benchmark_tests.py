from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=tempfile.mkdtemp(prefix='eidolon-v1500-');os.environ['EIDOLON_DATA_DIR']=R;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.autonomous_developer_v1500 import REQUIRED_CAPABILITIES,capability_receipt,build_autonomous_developer_benchmark,final_candidate_boundary
from conscious_agent.dynamic_improvement_eligibility import harden_dynamic_discovery
from conscious_agent.dynamic_candidate_quality import compare_dynamic_candidates
from conscious_agent.dynamic_implementation_planning import build_evidence_bound_plan
from conscious_agent.generalized_isolated_coding import apply_structured_edits
from conscious_agent.bounded_failure_diagnosis import diagnose_candidate_failure
from conscious_agent.verification_intelligence import verification_plan,evaluate_verification
from conscious_agent.governed_candidate_review import build_review_packet
from conscious_agent.continuous_development_campaign import new_campaign,apply_campaign_event
from conscious_agent.development_authority import issue_operator_authorization,private_scope_digest
from conscious_agent.windows_certification_protocol import REQUIRED_NATIVE_CHECKS,build_windows_certification_protocol,seal_windows_receipt,evaluate_windows_receipts
from conscious_agent.v1489_product_capability_integration import integrate_v1489_product_capabilities
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 # A compact end-to-end deterministic benchmark over an unfamiliar synthetic candidate.
 discovery={'discovery_digest':'d','candidates':[{'candidate_id':'cand','evidence_digest':'e'*64,'source_module':'conscious_agent/sample.py','source_symbols':['alpha','beta'],'proposed_destination_module':'conscious_agent/sample_helpers.py','estimated_dependency_count':2,'test_reference_file_count':3,'reversibility_classification':'high_reversible','eligible_for_later_planning':True,'rejection_codes':[]}]}
 hard=harden_dynamic_discovery(discovery);cmp=compare_dynamic_candidates(hard);selected=hard['eligible_candidates'][0]
 ck('benchmark discovery reaches eligible deterministic candidate',hard['eligible_count']==1,hard)
 ck('benchmark quality comparison ranks without selecting',cmp['top_candidate_id']=='cand' and not cmp['selection_made'],cmp)
 select_phrase='Select dynamic candidate cand.';select_receipt=issue_operator_authorization(stage='candidate_selection',subject_id='cand',subject_digest=selected['eligibility_digest'],explicit_operator_text=select_phrase,expected_operator_text=select_phrase)
 plan=build_evidence_bound_plan(selected,operator_selection_receipt=select_receipt,available_test_files=['tools/sample_tests.py']);ck('benchmark requires explicit selection before plan',plan['plan_created'] and plan['operator_selected'],plan)
 w=Path(R)/'workspace';(w/'conscious_agent').mkdir(parents=True);(w/'conscious_agent'/'sample.py').write_text('def alpha():\n    return 1\n\ndef beta():\n    return 2\n',encoding='utf-8')
 edits=[{'path':'conscious_agent/sample.py','action':'modify','replacements':[{'find':'return 1','replace':'return helper()'}]},{'path':'conscious_agent/sample_helpers.py','action':'create','content':'def helper():\n    return 1\n'}]
 implement_phrase='Implement candidate cand in benchmark workspace.';workspace_receipt=issue_operator_authorization(stage='workspace_implementation',subject_id='cand',subject_digest=plan['plan_digest'],scope_digest=private_scope_digest(str(w.resolve())),explicit_operator_text=implement_phrase,expected_operator_text=implement_phrase)
 change=apply_structured_edits(w,plan,edits,workspace_authorization_receipt=workspace_receipt);ck('benchmark coding stays inside authorized workspace',change['status']=='workspace_changed' and not change['active_source_modified'],change)
 diagnosis=diagnose_candidate_failure([{'status':'failed','reason':'assertion failed','passed':False}],attempt=1);ck('benchmark can diagnose bounded repair without retrying',diagnosis['repair_attempt_may_be_prepared'] and not diagnosis['automatic_retry_allowed'],diagnosis)
 vp=verification_plan(changed_files=change['changed_files'],candidate_test_files=['tools/sample_tests.py']);vr=evaluate_verification(vp,[{'suite':'python_compile','passed':True},{'suite':'source_immutability','passed':True},{'suite':'source_only_privacy','passed':True},{'suite':'tools/sample_tests.py','passed':True},{'suite':'focused_behavioral','passed':True},{'suite':'retained_architecture','passed':True}]);ck('benchmark verification intelligence accepts complete required receipts',vr['verification_passed'],vr)
 review=build_review_packet(plan=plan,change_receipt=change,verification=vr,source_manifest_digest='e'*64,rollback_digest='f'*64);ck('benchmark review packet is ready but non-installing',review['review_ready'] and not review['installation_executed'],review)
 campaign=new_campaign(campaign_id='camp',candidate_id='cand',baseline_source_digest='a'*64);r=apply_campaign_event(campaign,{'event_id':'1','action':'record_comparison','current_source_digest':'a'*64,'evidence_digest':'1'*64});campaign=r['state'];r=apply_campaign_event(campaign,{'event_id':'2','action':'operator_select','current_source_digest':'a'*64,'evidence_digest':selected['eligibility_digest'],'operator_authorization_receipt':select_receipt});campaign=r['state'];ck('benchmark campaign requires operator selection and stays deterministic',campaign['stage']=='operator_selected',campaign)
 # Production path: dynamic discovery can be turned into a proposal only by an exact operator command.
 dyn=Path(R)/'dynamic-source';(dyn/'conscious_agent').mkdir(parents=True);(dyn/'tools').mkdir()
 (dyn/'conscious_agent'/'__init__.py').write_text('',encoding='utf-8')
 (dyn/'paths.py').write_text('DATA_DIR=None\nROOT_DIR=None\ndef path_reference(x): return x\n',encoding='utf-8')
 (dyn/'conscious_agent'/'sample.py').write_text('from paths import DATA_DIR, ROOT_DIR, path_reference\n\nSTATE = 1\n\ndef alpha_queue():\n    return STATE\n\ndef beta_queue():\n    return alpha_queue() + STATE\n',encoding='utf-8')
 for name in ('v1489_product_capability_integration_tests.py','v1489_generic_self_development_execution_tests.py','v1489_symbol_level_refactoring_tests.py'):
     (dyn/'tools'/name).write_text("from pathlib import Path\nimport sys\nroot=Path(__file__).resolve().parents[1]\nsys.path.insert(0,str(root))\nsys.path.insert(0,str(root/'conscious_agent'))\nfrom conscious_agent.sample import alpha_queue,beta_queue\nassert alpha_queue()==1 and beta_queue()==2\n",encoding='utf-8')
 inspected=integrate_v1489_product_capabilities('Inspect your own project and propose one improvement.',{},source_root=dyn)
 quality=inspected.get('v1491_dynamic_candidate_quality') or {};ordered=quality.get('ordered_comparison') or []
 ck('production self-inspection exposes ranked review evidence without selection',bool(ordered) and not quality.get('selection_made') and not inspected.get('source_modified'),quality)
 top=ordered[0];command=f"Create dynamic self-development proposal {top['candidate_id']} evidence {str(top['evidence_digest'])[:16]}."
 created=integrate_v1489_product_capabilities(command,{},source_root=dyn)
 ck('exact operator command creates supervised dynamic proposal only',created.get('event')=='dynamic_self_development_proposal_created' and not created.get('provider_contacted') and not created.get('source_modified'),created)
 proposal=created.get('self_development_proposal') or {}
 ck('dynamic proposal binds exact discovered symbols and remains unprepared',proposal.get('source_symbols') and not proposal.get('isolated_workspace_created') and not proposal.get('installation_authorized'),proposal)
 ck('dynamic proposal enters durable planned campaign',proposal.get('development_plan_digest') and proposal.get('development_campaign',{}).get('stage')=='planned',proposal)
 replay=integrate_v1489_product_capabilities(command,{},source_root=dyn)
 ck('dynamic proposal creation is idempotent for same evidence',replay.get('event')=='dynamic_self_development_proposal_reused' and replay.get('self_development_proposal',{}).get('proposal_id')==proposal.get('proposal_id'),replay)
 prepare=integrate_v1489_product_capabilities(str(proposal.get('isolated_preparation_phrase') or ''),{},source_root=dyn)
 ck('exact operator preparation creates only disposable workspace',prepare.get('event')=='isolated_self_development_prepared' and not prepare.get('source_modified') and not prepare.get('provider_contacted'),prepare)
 ck('workspace preparation advances durable campaign',prepare.get('self_development_proposal',{}).get('development_campaign',{}).get('stage')=='workspace_authorized',prepare)
 implement_phrase=f"Implement isolated self-development proposal {proposal['proposal_id']} digest {str(proposal['proposal_digest'])[:16]}."
 implemented=integrate_v1489_product_capabilities(implement_phrase,{},source_root=dyn)
 ck('dynamic exact-symbol implementation reaches review ready provider-free',implemented.get('event')=='isolated_self_development_implementation_review_ready' and not implemented.get('provider_contacted') and not implemented.get('source_modified'),implemented)
 done=implemented.get('self_development_proposal') or {};ck('dynamic implementation remains uninstalled and unpromoted',done.get('state')=='isolated_implementation_review_ready' and not done.get('installation_authorized') and not done.get('promotion_authorized'),done)
 ck('implementation verification and review reach durable review-ready stage',done.get('development_campaign',{}).get('stage')=='review_ready' and done.get('verification_digest') and done.get('review_digest'),done)
 ck('authoritative synthetic source remains unchanged by dynamic implementation',not (dyn/'conscious_agent'/str(top.get('proposed_destination_module') or '').split('/')[-1]).exists(),top)
 receipts=[capability_receipt(name,passed=True,evidence_digest=(f'{i:x}'*64)[:64],evidence_source='integrated_benchmark',executed=True) for i,name in enumerate(REQUIRED_CAPABILITIES,1)]
 bench=build_autonomous_developer_benchmark(receipts)
 ck('all deterministic v1500 capabilities produce browser review candidate',bench['deterministic_benchmark_passed'] and bench['browser_review_candidate_ready'] and bench['score_percent']==100.0,bench)
 ck('missing Windows/operator gates block promotion decision',not bench['promotion_decision_ready'] and not bench['promotion_executed'] and not bench['independent_authority_granted'],bench)
 protocol=build_windows_certification_protocol(candidate_zip_sha256='a'*64,source_manifest_sha256='b'*64)
 windows=evaluate_windows_receipts(protocol,[seal_windows_receipt(protocol,check=name,passed=True,platform='Windows',execution_digest='c'*64) for name in REQUIRED_NATIVE_CHECKS])
 review_phrase='Accept v1500 benchmark review.';review_receipt=issue_operator_authorization(stage='operator_review',subject_id='v1500',subject_digest=bench['deterministic_evidence_digest'],explicit_operator_text=review_phrase,expected_operator_text=review_phrase)
 gated=build_autonomous_developer_benchmark(receipts,windows_evidence=windows,operator_review_receipt=review_receipt);ck('external gates only make decision ready, never auto-promote',gated['promotion_decision_ready'] and not gated['promotion_executed'] and not gated['certification_granted'],gated)
 boundary=final_candidate_boundary(bench);ck('final boundary permits package/review but never automatic install promotion',boundary['candidate_may_be_packaged'] and not boundary['candidate_may_be_installed_automatically'] and not boundary['candidate_may_be_promoted_automatically'],boundary)
 missing=build_autonomous_developer_benchmark(receipts[:-1]);ck('missing capability fails benchmark honestly',not missing['deterministic_benchmark_passed'] and REQUIRED_CAPABILITIES[-1] in missing['missing_capabilities'],missing)
 forged=build_autonomous_developer_benchmark([{'capability':name,'passed':True} for name in REQUIRED_CAPABILITIES]);ck('self-asserted capability rows cannot pass benchmark',not forged['deterministic_benchmark_passed'] and forged['invalid_capability_receipt_count']==len(REQUIRED_CAPABILITIES),forged)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1500-autonomous-developer-benchmark','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
