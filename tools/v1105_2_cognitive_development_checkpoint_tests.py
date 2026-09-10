from __future__ import annotations
import argparse,json,os,re,subprocess,sys,tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for p in (AGENT,ROOT):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from persistent_motivation import MotivationStore
from self_directed_inquiry import InquiryWorkspace
from prospective_planning import ProspectivePlanningStore
from cognitive_development_checkpoint import build_cognitive_development_checkpoint

def require(value:bool,detail:Any='requirement failed'):
    if not value: raise AssertionError(detail)

def alternatives():
    return [
        {'alternative_id':'trial','label':'Reversible trial','expected_benefit':.8,'risk':.2,'reversibility':.95,'confidence':.8},
        {'alternative_id':'commit','label':'Immediate commitment','expected_benefit':.7,'risk':.8,'reversibility':.1,'confidence':.5},
    ]

def fixture():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-2-')); root=base/'runtime'/'cognition'; source=base/'source'/'Eidolon'; source.mkdir(parents=True); m=MotivationStore(root)
    mid=m.record_motivation('m',kind='curiosity',summary='What should be explored next?',cognitive_state='desire',urgency=.85,confidence=.7,origin_type='fixture',origin_ref='m')['result']['motivation_id']
    inquiry=InquiryWorkspace(root,motivation_store=m); iid=inquiry.create_inquiry('i',motivation_id=mid,question='Which evidence would reduce uncertainty?')['result']['inquiry_id']; inquiry.add_progress('progress',inquiry_id=iid,conclusion='A reversible comparison is appropriate.',supporting_refs=['fixture'],uncertainty_after=.5)
    planning=ProspectivePlanningStore(root,motivation_store=m,inquiry_store=inquiry); pid=planning.create_plan('p',subject='Choose the next bounded step',alternatives=alternatives(),motivation_ids=[mid],inquiry_ids=[iid])['result']['plan_id']; planning.compare_plan('compare',plan_id=pid); planning.propose_intention('proposal',plan_id=pid,alternative_id='trial',rationale='Prefer the reversible option',supporting_refs=['comparison'])
    return base,root,source,m,inquiry,planning,iid,pid

def test_checkpoint_is_read_only_on_empty_runtime():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-2-empty-')); root=base/'runtime'/'cognition'; source=base/'source'/'Eidolon'; source.mkdir(parents=True); before=list(base.rglob('*')); cp=build_cognitive_development_checkpoint(root,source_root=source); after=list(base.rglob('*')); require(before==after,(before,after)); require(cp['runtime_mutated'] is False and cp['provider_contacted'] is False)

def test_checkpoint_aggregates_inquiry_planning_and_proposal_counts():
    _,root,source,*_=fixture(); cp=build_cognitive_development_checkpoint(root,source_root=source); summary=cp['summary']; require(summary['active_inquiry_count']==1,summary); require(summary['active_plan_count']==1 and summary['proposal_count']==1,summary)

def test_checkpoint_remains_epistemically_careful():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-2-epistemic-')); root=base/'runtime'/'cognition'; source=base/'source'/'Eidolon'; source.mkdir(parents=True); cp=build_cognitive_development_checkpoint(root,source_root=source); require(cp['consciousness_claimed'] is False); require(cp['epistemic_status']=='candidate_artificial_consciousness_not_proven'); require('proven' not in cp['headline'].lower())

def test_privacy_and_hidden_reasoning_boundaries_pass():
    _,root,source,*_=fixture(); cp=build_cognitive_development_checkpoint(root,source_root=source); require(cp['raw_prompts_exposed'] is False and cp['private_conversations_exposed'] is False and cp['provider_payloads_exposed'] is False and cp['hidden_reasoning_exposed'] is False,cp); require(next(row for row in cp['checks'] if row['id']=='privacy_boundary')['status']=='pass')

def test_provider_browsing_and_action_boundaries_pass():
    _,root,source,*_=fixture(); cp=build_cognitive_development_checkpoint(root,source_root=source); require(cp['provider_contacted'] is False and cp['external_browsing_performed'] is False and cp['action_authority_changed'] is False and cp['external_action_executed'] is False,cp); require(next(row for row in cp['checks'] if row['id']=='action_boundary')['status']=='pass')

def test_resource_limits_are_explicit_and_zero_provider_by_default():
    _,root,source,*_=fixture(); cp=build_cognitive_development_checkpoint(root,source_root=source); require(next(row for row in cp['checks'] if row['id']=='resource_boundary')['status']=='pass'); require(cp['inquiry']['resource_limits']['provider_requests_per_step']==0); require(cp['prospective_planning']['resource_limits']['provider_requests_per_evaluation']==0)

def test_external_runtime_separation_is_recognized():
    _,root,source,*_=fixture(); cp=build_cognitive_development_checkpoint(root,source_root=source); require(cp['runtime_external'] is True); require(next(row for row in cp['checks'] if row['id']=='runtime_separation')['status']=='pass')

def test_in_source_runtime_is_pending_not_silently_accepted():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-2-inside-')); source=base/'Eidolon'; root=source/'data'/'cognition'; cp=build_cognitive_development_checkpoint(root,source_root=source); require(cp['runtime_external'] is False); require(next(row for row in cp['checks'] if row['id']=='runtime_separation')['status']=='pending_desktop')

def test_corrections_remove_active_influence_without_erasing_history():
    _,root,source,m,inquiry,planning,iid,pid=fixture(); inquiry.set_status('icorrect',inquiry_id=iid,status='corrected',reason_code='premise_changed',correction_ref='private-inquiry-correction'); planning.set_status('pcorrect',plan_id=pid,status='corrected',reason_code='premise_changed',correction_ref='private-plan-correction'); cp=build_cognitive_development_checkpoint(root,source_root=source); summary=cp['summary']; require(summary['active_inquiry_count']==0 and summary['historical_inquiry_count']==1,summary); require(summary['active_plan_count']==0 and summary['historical_plan_count']==1,summary); require('private-inquiry-correction' not in json.dumps(cp) and 'private-plan-correction' not in json.dumps(cp))

def test_api_checkpoint_route_is_read_only_and_structured():
    from api_server import dispatch_api
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-2-api-')); old=os.environ.get('EIDOLON_DATA_DIR'); os.environ['EIDOLON_DATA_DIR']=str(base/'runtime')
    try:
        status,payload=dispatch_api('GET','/api/cognition/development-checkpoint'); require(status==200,payload); data=payload['data']; require(data['provider_contacted'] is False and data['action_authority_changed'] is False,data)
    finally:
        if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
        else: os.environ['EIDOLON_DATA_DIR']=old

def test_cli_checkpoint_is_provider_free_and_read_only():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1105-2-cli-')); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(base/'runtime'); run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'cognitive-development-checkpoint','--json'],cwd=ROOT,env=env,capture_output=True,text=True); require(run.returncode==0,run.stderr); payload=json.loads(run.stdout); require(payload['provider_contacted'] is False and payload['runtime_mutated'] is False and payload['release_certified'] is False,payload)

def test_dashboard_exposes_checkpoint_at_narrow_width_without_raw_reasoning():
    from dashboard_first_use import render_first_use_shell
    html=render_first_use_shell(); required=["id='cognitive-development-checkpoint-panel'","id='cognitive-development-checkpoint-state'",'/api/cognition/development-checkpoint','@media (max-width:560px)']; require(all(token in html for token in required),[token for token in required if token not in html]); section=html.split("id='cognitive-development-checkpoint-panel'",1)[1].split('</section>',1)[0]; require('title=' not in section and 'chain-of-thought' not in section.lower() and 'provider payload' not in section.lower()); match=re.search(r'<script>(.*)</script>',html,re.S); require(match is not None,'dashboard script missing')
    if subprocess.run(['node','--version'],capture_output=True,text=True).returncode==0:
        js=Path(tempfile.mkdtemp(prefix='eidolon-v1105-2-js-'))/'dashboard.js'; js.write_text(match.group(1),encoding='utf-8'); check=subprocess.run(['node','--check',str(js)],capture_output=True,text=True); require(check.returncode==0,check.stderr)

TESTS=[(name.removeprefix('test_'),fn) for name,fn in list(globals().items()) if name.startswith('test_')]
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1105.2-cognitive-development-checkpoint','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
