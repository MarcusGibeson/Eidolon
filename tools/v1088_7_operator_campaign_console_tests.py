from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1088c-console-')
import api_server
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_console as console
import dashboard
import post_review_development_verify as verify

def req(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not any(part in {'__pycache__','.git','.venv','venv'} for part in p.parts) and p.suffix!='.pyc': h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
def make_campaign():
    return campaign.create_evaluation_campaign(campaign_label='PRIVATE_CONSOLE_CAMPAIGN_LABEL',objective='PRIVATE_CONSOLE_CAMPAIGN_OBJECTIVE',focus_areas=['conversation_quality'],target_evaluation_count=2,minimum_completed_evaluations=1,planned_duration_days=5,required_signals=['consecutive_use'],operator_confirmed=True)

def test_console_without_selection_is_read_only():
    before=tree_digest(); report=console.build_evaluation_campaign_console_state()
    req(report['selection_status']=='none_selected' and report['campaign_count']==0,'empty state')
    req(not report['writes_state'] and report['content_free'] and report['redacted'],'boundary')
    req(before==tree_digest(),'source mutation')

def test_console_combines_redacted_campaign_evidence():
    camp=make_campaign(); report=console.build_evaluation_campaign_console_state(campaign_id=camp['campaign_id'])
    req(report['selection_status']=='available' and report['selected_campaign_id']==camp['campaign_id'],'selection')
    for key in ('protocol','selected_campaign','progress','issues','follow_ups','review'): req(report[key] is not None,f'missing {key}')
    encoded=json.dumps(report,sort_keys=True)
    req('PRIVATE_CONSOLE_CAMPAIGN_LABEL' not in encoded and 'PRIVATE_CONSOLE_CAMPAIGN_OBJECTIVE' not in encoded,'private plan leaked')

def test_console_campaign_list_is_bounded_and_redacted():
    for _ in range(3): make_campaign()
    report=console.build_evaluation_campaign_console_state()
    req(3 <= report['campaign_count'] <= report['maximum_campaign_rows']==64,'list count')
    req(all(not row['private_campaign_label_returned'] and not row['private_objective_returned'] for row in report['campaigns']),'plan returned')

def test_console_comparison_is_optional_and_descriptive():
    first=make_campaign(); second=make_campaign()
    report=console.build_evaluation_campaign_console_state(campaign_id=first['campaign_id'],comparison_campaign_ids=[first['campaign_id'],second['campaign_id']])
    req(report['comparison'] and report['comparison']['campaign_count']==2,'comparison missing')
    req(not report['comparison']['campaigns_ranked'] and not report['comparison']['winner_selected'],'ranking')

def test_api_get_console_route_is_provider_free():
    camp=make_campaign(); status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-console',{'campaign_id':[camp['campaign_id']]})
    data=payload['data']; req(status==200 and data['selection_status']=='available','route')
    req(not data['provider_invoked'] and not data['generation_invoked'],'provider')

def test_dashboard_has_explicit_controls_export_and_narrow_layout():
    html=dashboard.render_evaluation_campaign_console()
    for token in ("data-evaluation-campaign-console-version='v1088.7'",'/api/conversation/evaluation-campaign','operator_confirmed: true','window.confirm','start_review','set_review_disposition','/api/conversation/evaluation-campaign-review-export'):
        req(token in html,f'missing {token}')
    req('@media(max-width:820px)' in html and 'grid-template-columns:1fr' in html,'narrow layout')

def test_dashboard_javascript_has_valid_syntax():
    html=dashboard.render_evaluation_campaign_console(); match=re.search(r'<script>(.*?)</script>',html,re.S); req(match,'script missing')
    path=Path(tempfile.mkdtemp())/'campaign-console.js'; path.write_text(match.group(1),encoding='utf-8')
    result=subprocess.run(['node','--check',str(path)],capture_output=True,text=True,timeout=20)
    req(result.returncode==0,result.stderr)

def test_console_grants_no_tasks_priority_or_release_authority():
    camp=make_campaign(); report=console.build_evaluation_campaign_console_state(campaign_id=camp['campaign_id'])
    for key in ('automatic_task_created','autonomous_prioritization','release_recommendation_produced','provider_invoked','generation_invoked','automatic_replay','automatic_resend','installation_performed','promotion_performed','release_certified'):
        req(report[key] is False,f'authority {key}')

def test_dashboard_route_and_suite_registration_are_exact():
    source=(ROOT/'conscious_agent'/'dashboard.py').read_text()
    req(source.count('elif path == "/evaluation-campaign-console":')==1,'dashboard route')
    names=[s.name for s in verify.SUITES]; req(names.count('v1088.7-operator-campaign-console')==1,'registration')
    req(names.index('v1088.7-operator-campaign-console')<names.index('v1088.6-campaign-review-workflow'),'order')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1088.7-operator-campaign-console','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
