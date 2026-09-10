from __future__ import annotations
import concurrent.futures,hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from coding_alpha_reliability import inspect_coding_alpha_health,build_coding_alpha_operator_handoff
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from natural_language_action_routing import build_natural_language_action_projection
from isolated_coding_execution import load_isolated_coding_execution
from controlled_application_rollback_foundations import prepare_controlled_application
from v1260_test_support import CodingAlphaProvider,make_project,tree_signature
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def turn(text,session,runtime,project=None,provider=None):
    kw={'session_id':session,'runtime_root':runtime,'node_executable':'node'}
    if project is not None: kw['project_state']={'id':'calc','name':'Calculator','path':str(project)}
    if provider is not None: kw['provider_generate']=provider
    return process_ordinary_chat_development_turn(text,action_projection=build_natural_language_action_projection(text),**kw)
def prepared(base:Path,session='rel'):
    runtime=base/'runtime'; project=make_project(base); original=tree_signature(project); text='Build me a complete responsive accessible calculator webpage.'
    c=turn(text,session,runtime,project); p=c['proposal']; a=turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",session,runtime); return runtime,project,original,a
# stale source blocks application before authorization consumption
with tempfile.TemporaryDirectory(prefix='eid-v1260-stale-') as d:
    runtime,project,original,a=prepared(Path(d)); rid=a['isolated_coding_request_id']; provider=CodingAlphaProvider(); e=turn(a['isolated_coding_execution']['authorization_phrase'],'rel',runtime,provider=provider); req(e['event']=='isolated_coding_execution_completed','stale_fixture_execution_ready')
    (project/'index.html').write_text('<!doctype html><p>operator edit</p>',encoding='utf-8'); before=tree_signature(project)
    blocked=turn(f'Prepare controlled application for request {rid}.','rel',runtime); req('conflict' in blocked['event'] or 'stale' in blocked['event'],'operator_conflict_blocks_application_preparation')
    req(tree_signature(project)==before,'conflict_block_changes_nothing')
# provider outage fails isolated and never touches project
with tempfile.TemporaryDirectory(prefix='eid-v1260-provider-') as d:
    runtime,project,original,a=prepared(Path(d),'outage'); rid=a['isolated_coding_request_id']
    def outage(_): raise RuntimeError('provider unavailable')
    r=turn(a['isolated_coding_execution']['authorization_phrase'],'outage',runtime,provider=outage)
    req(r['event']!='isolated_coding_execution_completed','provider_outage_fails_closed'); req(tree_signature(project)==original,'provider_outage_preserves_project')
# exact execution replay is idempotent and no duplicate provider calls
with tempfile.TemporaryDirectory(prefix='eid-v1260-replay-') as d:
    runtime,project,original,a=prepared(Path(d),'replay'); provider=CodingAlphaProvider(); phrase=a['isolated_coding_execution']['authorization_phrase']
    r1=turn(phrase,'replay',runtime,provider=provider); req(r1['event']=='isolated_coding_execution_completed','replay_fixture_first_execution_passes'); calls=provider.calls
    r2=turn(phrase,'replay',runtime,provider=provider); req(r2['event']=='isolated_coding_execution_completed','exact_execution_replay_returns_terminal_result'); req(provider.calls==calls,'exact_execution_replay_no_provider_call')
# concurrent generic authorization remains inert
with tempfile.TemporaryDirectory(prefix='eid-v1260-generic-race-') as d:
    runtime=Path(d)/'runtime'; project=make_project(Path(d)); created=turn('Build me a complete responsive accessible calculator webpage.','race',runtime,project)
    def go(_): return turn('Go ahead.','race',runtime)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: rows=list(pool.map(go,range(8)))
    req(all(r['event']=='generic_authorization_blocked' for r in rows),'concurrent_generic_authorization_all_blocked')
    req(created['proposal']['approval_consumed'] is False,'generic_race_does_not_change_original_public_proposal')
# cancellation before execution prevents work
with tempfile.TemporaryDirectory(prefix='eid-v1260-cancel-') as d:
    runtime=Path(d)/'runtime'; project=make_project(Path(d)); original=tree_signature(project); c=turn('Build me a complete responsive accessible calculator webpage.','cancel',runtime,project)
    x=turn('Cancel that development proposal.','cancel',runtime); req(x['event']=='conversational_cancellation_applied','conversational_cancel_applied'); req(tree_signature(project)==original,'cancel_no_project_mutation')
health=inspect_coding_alpha_health(source_root=ROOT); req(health['ok'] and all(health['checks'].values()),'read_only_health_passes'); req(health['read_only'] and health['native_windows_validation']=='desktop_review_required','health_honest_about_native_windows')
h=build_coding_alpha_operator_handoff(source_root=ROOT); req(h['ok'] and h['operator_review_required'],'operator_handoff_ready'); req(len(h['desktop_focus'])>=8,'desktop_focus_complete'); req(h['release_authorized'] is False and h['independent_authority_granted'] is False,'handoff_grants_no_release_authority')
print(json.dumps({'ok':True,'suite':'v1260.6-v1260.8-coding-alpha-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'native_windows_multi_process_validation':'desktop_review_required','release_authorized':False},indent=2,sort_keys=True))
