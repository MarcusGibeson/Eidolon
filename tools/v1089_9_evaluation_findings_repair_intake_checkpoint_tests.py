from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1089-9-runtime-")
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server, dashboard, release_metadata
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_checkpoint as checkpoint
import conversation_evaluation_finding_reproducibility as repro
import conversation_evaluation_finding_repair_candidates as repairs
import conversation_evaluation_finding_triage as triage
import post_review_development_verify as verify

PRIVATE_TITLE='PRIVATE_FINDING_TITLE_1089_9'; PRIVATE_DETAILS='PRIVATE_FINDING_DETAILS_1089_9'; PRIVATE_NOTE='PRIVATE_FINDING_NOTE_1089_9'; PRIVATE_REF='PRIVATE_PATCH_REFERENCE_1089_9'
def require(v,m):
 if not v: raise AssertionError(m)
def area(report,name):
 return next(row for row in report['areas'] if row['name']==name)
def source_digest():
 h=hashlib.sha256()
 for p in sorted(ROOT.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
   h.update(p.relative_to(ROOT).as_posix().encode()); h.update(b'\0'); h.update(p.read_bytes()); h.update(b'\0')
 return h.hexdigest()
def make_finding():
 s=create_conversation_session('Checkpoint finding session',select_session=False)
 e=daily.start_daily_evaluation(s['id'],operator_confirmed=True)
 e=daily.record_operator_observation(e['evaluation_id'],ratings={'continuity':3},issue_domain='interface',severity='minor',expected_revision=e['revision'],operator_confirmed=True)
 c=campaign.create_evaluation_campaign(campaign_label='PRIVATE_CAMPAIGN_1089_9',objective='PRIVATE_OBJECTIVE_1089_9',focus_areas=['conversation_quality'],target_evaluation_count=2,minimum_completed_evaluations=1,planned_duration_days=3,required_signals=[],operator_confirmed=True)
 c=enrollment.enroll_daily_evaluation(c['campaign_id'],e['evaluation_id'],expected_revision=c['revision'],operator_confirmed=True)
 f=finding.create_evaluation_finding(finding_title=PRIVATE_TITLE,finding_details=PRIVATE_DETAILS,issue_domain='interface',severity='major',campaign_id=c['campaign_id'],evaluation_id=e['evaluation_id'],operator_confirmed=True)
 return c,e,f

def enriched_finding():
 c,e,f=make_finding()
 r=repro.record_reproduction_attempt(f['finding_id'],outcome='reproduced',environment_kind='clean_restart',environment_label='PRIVATE_ENV_1089_9',note=PRIVATE_NOTE,evidence_digest='a'*64,expected_revision=f['revision'],operator_confirmed=True)
 latest=finding.load_evaluation_finding(f['finding_id'])
 refs=repairs.add_repair_candidate_reference(f['finding_id'],reference_kind='patch_candidate',reference_value=PRIVATE_REF,label='PRIVATE_LABEL_1089_9',expected_revision=latest['revision'],operator_confirmed=True)
 latest=finding.load_evaluation_finding(f['finding_id'])
 t=triage.start_evaluation_finding_triage(f['finding_id'],note=PRIVATE_NOTE,expected_revision=latest['revision'],operator_confirmed=True)
 latest=finding.load_evaluation_finding(f['finding_id'])
 triage.set_evaluation_finding_triage_disposition(f['finding_id'],disposition='repair_candidate_review',note=PRIVATE_NOTE,expected_revision=latest['revision'],operator_confirmed=True)
 return c,e,finding.load_evaluation_finding(f['finding_id'])

def test_checkpoint_contract_and_areas():
 r=checkpoint.build_evaluation_findings_checkpoint(); require(r['checkpoint_status']=='ready_for_operator_finding_review','status'); require(r['area_count']==checkpoint.CHECKPOINT_AREA_COUNT==15,'areas'); require(len(r['contract_digest'])==64 and len(r['areas_digest'])==64,'digests')
def test_campaign_checkpoint_foundation():
 r=checkpoint.build_evaluation_findings_checkpoint(); m=area(r,'operator_campaign_evaluation_foundation')['metrics']; require(m['checkpoint_status']=='ready_for_operator_campaign_evaluation' and m['area_count']==15,'campaign foundation')
def test_selected_finding_is_redacted():
 c,e,f=enriched_finding(); r=checkpoint.build_evaluation_findings_checkpoint(finding_id=f['finding_id'],campaign_id=c['campaign_id'],evaluation_id=e['evaluation_id']); encoded=json.dumps(r,sort_keys=True); require(r['selected_finding_status']=='available','selection'); require(PRIVATE_TITLE not in encoded and PRIVATE_DETAILS not in encoded and PRIVATE_NOTE not in encoded and PRIVATE_REF not in encoded,'private leak')
def test_missing_finding_is_bounded():
 r=checkpoint.build_evaluation_findings_checkpoint(finding_id='eval_finding_20200101T000000_aaaaaaaaaaaa'); require(r['selected_finding_status']=='not_found','missing')
def test_reproducibility_area_is_explicit():
 r=checkpoint.build_evaluation_findings_checkpoint(); m=area(r,'explicit_reproducibility_review')['metrics']; require(m['maximum_attempts']==24 and not m['automatic_rerun'] and not m['automatic_replay'],'repro contract')
def test_repair_reference_area_never_generates_patch():
 r=checkpoint.build_evaluation_findings_checkpoint(); m=area(r,'explicit_repair_candidate_references')['metrics']; require(m['maximum_references']==24 and not m['patch_generated'] and not m['patch_applied'],'repair boundary')
def test_aggregation_is_descriptive():
 make_finding(); r=checkpoint.build_evaluation_findings_checkpoint(); m=area(r,'privacy_safe_finding_aggregation')['metrics']; require(m['finding_count']>=1 and m['descriptive_counts_only'] and not m['findings_ranked'] and not m['priority_assigned'],'aggregation')
def test_triage_is_explicit():
 r=checkpoint.build_evaluation_findings_checkpoint(); m=area(r,'explicit_triage_and_dispositions')['metrics']; require('repair_candidate_review' in m['triage_dispositions'] and not m['automatic_triage'],'triage')
def test_comparison_declares_no_winner():
 _,_,a=make_finding(); _,_,b=make_finding(); r=checkpoint.build_evaluation_findings_checkpoint(comparison_finding_ids=[a['finding_id'],b['finding_id']]); m=area(r,'bounded_repair_intake_comparison')['metrics']; require(m['comparison_status']=='available' and m['compared_finding_count']==2,'comparison'); require(not m['findings_ranked'] and not m['winner_selected'] and not m['priority_assigned'] and not m['release_recommendation_produced'],'comparison authority')
def test_console_javascript_and_narrow_layout():
 r=checkpoint.build_evaluation_findings_checkpoint(); require(area(r,'operator_findings_console')['metrics']['read_routes_only_for_evidence'],'console'); html=dashboard.render_evaluation_findings_console(); require('@media(max-width:820px)' in html and 'grid-template-columns:1fr' in html,'narrow'); match=re.search(r'<script>(.*?)</script>',html,re.S); require(match,'script'); p=Path(tempfile.mkdtemp())/'findings.js'; p.write_text(match.group(1)); result=subprocess.run(['node','--check',str(p)],capture_output=True,text=True,timeout=30); require(result.returncode==0,result.stderr)
def test_review_export_is_client_side():
 _,_,f=enriched_finding(); r=checkpoint.build_evaluation_findings_checkpoint(finding_id=f['finding_id']); m=area(r,'privacy_safe_repair_intake_export')['metrics']; require(m['selected_export_status']=='available' and len(m['selected_document_sha256'])==64 and not m['server_file_written'],'export')
def test_long_session_window_contract():
 r=checkpoint.build_evaluation_findings_checkpoint(); m=area(r,'long_session_findings_windows')['metrics']; require(m['initial_window_limit']==80 and m['earlier_window_limit']==120 and m['maximum_findings']==256 and m['complete_finding_rows_only'],'window')
def test_existing_mutations_require_confirmation_and_revision():
 _,_,f=make_finding()
 try: finding.set_evaluation_finding_state(f['finding_id'],state='resolved',expected_revision=f['revision'],operator_confirmed=False)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('unconfirmed mutation')
 updated=finding.set_evaluation_finding_state(f['finding_id'],state='under_review',expected_revision=f['revision'],operator_confirmed=True)
 try: finding.set_evaluation_finding_state(f['finding_id'],state='resolved',expected_revision=f['revision'],operator_confirmed=True)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('stale revision')
 require(updated['revision']==f['revision']+1,'revision')
def test_checkpoint_is_provider_free_and_no_replay():
 r=checkpoint.build_evaluation_findings_checkpoint()
 for k in ('provider_invoked','embedding_provider_invoked','generation_invoked','automatic_provider_request','automatic_replay','automatic_resend'): require(r[k] is False,k)
 source=(AGENT/'conversation_evaluation_finding_checkpoint.py').read_text(); require('local_model' not in source and 'provider_readiness' not in source,'provider dependency')
def test_operator_authority_is_explicit():
 r=checkpoint.build_evaluation_findings_checkpoint(); m=area(r,'operator_authority_and_checkpoint_boundary')['metrics']; require(m['release_decision']=='operator_only' and m['repair_decision']=='operator_only','authority');
 for k in ('approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','model_management','provider_switching','generation_settings_changed','autonomous_prioritization','automatic_task_created','automatic_work_item_created','patch_generated','patch_reviewed','patch_applied','checkpoint_writes_state'): require(m[k] is False,k)
def test_api_get_route():
 _,_,f=make_finding(); status,payload=api_server.handle_api_get('/api/conversation/evaluation-findings-checkpoint',{'finding_id':[f['finding_id']]}); require(status==200 and payload['data']['type']=='desktop_alpha_evaluation_findings_repair_intake_checkpoint','GET')
def test_no_post_route():
 source=(AGENT/'api_server.py').read_text(); post=source[source.index('def handle_api_post'):]; require('parts == ["conversation", "evaluation-findings-checkpoint"]' not in post,'POST'); require('GET /api/conversation/evaluation-findings-checkpoint' in source,'index')
def test_private_detector():
 require(checkpoint.evaluation_findings_checkpoint_contains_private_fields({'private_note':'secret'}),'private missed'); require(checkpoint.evaluation_findings_checkpoint_contains_private_fields({'document':'secret'}),'document missed'); require(not checkpoint.evaluation_findings_checkpoint_contains_private_fields(checkpoint.build_evaluation_findings_checkpoint()),'false private')
def test_deterministic_and_immutable():
 before=source_digest(); a=checkpoint.build_evaluation_findings_checkpoint(); b=checkpoint.build_evaluation_findings_checkpoint(); after=source_digest(); require(a['contract_digest']==b['contract_digest'] and a['areas_digest']==b['areas_digest'],'determinism'); require(before==after,'source mutation')
def test_release_metadata_and_guides():
 require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.'))>=(1089,9),'version'); require(release_metadata.RUNTIME_VERSION_TAG==f"v{release_metadata.RUNTIME_VERSION}",'tag')
 for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
  text=(ROOT/name).read_text(); require('v1089.9' in text,f'{name} checkpoint'); require('v1088.9' in text,f'{name} campaign checkpoint')
def test_registration_is_exact_and_bounded():
 names=[s.name for s in verify.SUITES]; name='v1089.9-desktop-alpha-evaluation-findings-repair-intake-checkpoint'; require(names.count(name)==1,'registration'); require(names.index(name)<names.index('v1089.8-long-session-findings-ux'),'order'); historical=verify.SUITES[names.index(name):]; core=[s for s in historical if 'core' in s.profiles]; full=[s for s in historical if 'full' in s.profiles]; require(len(core)==92,f'historical core {len(core)}'); require(len(full)==109,f'historical full {len(full)}')
def test_source_only_privacy():
 forbidden={'data/projects.json','data/tasks.json','data/memories.json','data/conversations.json','data/conversation_evaluation_findings','.git','.venv','venv'}; relative={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')}; require(not(forbidden&relative),str(forbidden&relative))
 for p in ROOT.rglob('*'):
  rel=p.relative_to(ROOT); require('__pycache__' not in rel.parts,'cache'); require(p.suffix not in {'.pyc','.pyo','.zip'},f'artifact {rel}')

def test_checkpoint_top_level_boundaries():
 r=checkpoint.build_evaluation_findings_checkpoint(); require(r['read_only'] and r['content_free'] and r['redacted'] and not r['writes_state'],'top boundary');
 for k in ('automatic_finding_creation','automatic_reproduction','automatic_task_created','automatic_work_item_created','patch_generated','patch_reviewed','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified'): require(r[k] is False,k)

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for name,fn in TESTS:
  try: fn()
  except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
 report={'suite':'v1089.9-desktop-alpha-evaluation-findings-repair-intake-checkpoint','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
