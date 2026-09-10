from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import conversation_evaluation_campaign_protocol as protocol
import api_server
import post_review_development_verify as verify

def require(value,message):
    if not value: raise AssertionError(message)

def snapshot(path: Path):
    if not path.exists(): return {}
    return {p.relative_to(path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}

def test_protocol_consumes_verified_daily_evaluation_checkpoint():
    report=protocol.build_evaluation_campaign_protocol()
    require(report['protocol_status']=='ready','campaign protocol not ready')
    require(report['daily_evaluation_checkpoint_status']=='ready_for_operator_daily_evaluation','daily checkpoint not consumed')
    require(report['daily_evaluation_area_count']==15,'checkpoint area count drift')
    require(len(report['daily_evaluation_contract_digest'])==64 and len(report['daily_evaluation_areas_digest'])==64,'checkpoint digests missing')

def test_campaign_contract_is_bounded_and_explicit():
    report=protocol.build_evaluation_campaign_protocol(); limits=report['limits']
    require(report['campaign_states']==['planned','active','completed','aborted'],'campaign states changed')
    require(limits['maximum_campaign_evaluations']==32 and limits['maximum_campaign_duration_days']==30,'limits changed')
    require(report['campaign_launch_is_explicit'] and report['evaluation_creation_is_explicit'] and report['evaluation_enrollment_is_explicit'],'explicit boundaries missing')

def test_protocol_digest_is_deterministic():
    first=protocol.build_evaluation_campaign_protocol(); second=protocol.build_evaluation_campaign_protocol()
    require(first['campaign_contract_digest']==second['campaign_contract_digest'],'contract digest unstable')

def test_protocol_is_read_only_and_does_not_write_runtime_state():
    data=Path(os.environ['EIDOLON_DATA_DIR']); before=snapshot(data)
    report=protocol.build_evaluation_campaign_protocol(); after=snapshot(data)
    require(before==after and not report['writes_state'] and report['read_only'],'protocol wrote state')

def test_protocol_contains_no_private_content_fields():
    report=protocol.build_evaluation_campaign_protocol()
    require(not protocol.evaluation_campaign_protocol_contains_private_fields(report),'private field detected')
    serialized=json.dumps(report).lower()
    require('private campaign objective' not in serialized and 'transcript body' not in serialized,'private probe leaked')

def test_protocol_has_no_provider_or_release_authority():
    report=protocol.build_evaluation_campaign_protocol()
    for key in ('provider_invoked','embedding_provider_invoked','generation_invoked','model_management','provider_switching','generation_settings_changed','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','autonomous_scoring','automatic_campaign_launch','automatic_evaluation_creation','automatic_provider_request','automatic_replay','automatic_resend'):
        require(report[key] is False,f'authority escalated: {key}')
    require(report['release_decision']=='operator_only','operator release boundary missing')

def test_api_index_and_get_route_are_registered():
    index=api_server._api_index()['endpoints']
    require('GET /api/conversation/evaluation-campaign-protocol' in index,'protocol index route missing')
    status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-protocol',{})
    require(status==200 and payload['data']['type']=='desktop_alpha_operator_evaluation_campaign_protocol','protocol GET failed')

def test_no_get_route_mutates_campaign_state():
    source=(AGENT/'api_server.py').read_text(encoding='utf-8')
    get_section=source[source.index('def handle_api_get'):source.index('def handle_api_post')]
    require('create_evaluation_campaign(' not in get_section and 'enroll_daily_evaluation(' not in get_section,'GET route gained mutation')

def test_source_only_tree_has_no_campaign_runtime_data():
    require(not (ROOT/'data'/'conversation_evaluation_campaigns').exists(),'campaign runtime data packaged in source')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1088.0-operator-evaluation-campaign-protocol')==1,'suite registration not exact')
    require(names.index('v1088.0-operator-evaluation-campaign-protocol')<names.index('v1087.9-desktop-alpha-daily-evaluation-checkpoint'),'suite order wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1088.0-operator-evaluation-campaign-protocol','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
