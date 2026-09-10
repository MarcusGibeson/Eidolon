from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
import conversation_daily_evaluation_protocol as protocol
from conversation_readiness_checkpoint import build_conversation_readiness_checkpoint
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not any(part in {'__pycache__','.git','.venv','venv'} for part in p.parts) and p.suffix!='.pyc':
            h.update(p.relative_to(ROOT).as_posix().encode());h.update(p.read_bytes())
    return h.hexdigest()

def test_protocol_consumes_v1086_9_readiness_checkpoint():
    base=build_conversation_readiness_checkpoint(); report=protocol.build_daily_evaluation_protocol()
    require(report['protocol_status']=='ready','protocol not ready')
    require(report['readiness_checkpoint_status']=='ready_for_operator_evaluation','checkpoint status lost')
    require(report['readiness_contract_digest']==base['contract_digest'],'contract digest mismatch')
    require(report['readiness_areas_digest']==base['areas_digest'],'areas digest mismatch')
    require(report['readiness_area_count']==15,'readiness area count changed')

def test_protocol_defines_six_explicit_dimensions_and_bounded_scale():
    report=protocol.build_daily_evaluation_protocol()
    require(report['rating_dimensions']==['continuity','relevance','tone','responsiveness','recovery','usability'],'dimensions changed')
    require(report['rating_scale']=={'minimum':1,'maximum':5},'rating scale changed')

def test_protocol_bounds_observations_notes_states_and_signals():
    report=protocol.build_daily_evaluation_protocol()
    require(report['limits']=={'maximum_observations':64,'maximum_operator_note_chars':4000},'limits changed')
    require(report['evaluation_states']==['active','completed','aborted'],'states changed')
    require('provider_outage' in report['evaluation_signals'] and 'multi_tab' in report['evaluation_signals'],'daily signals missing')

def test_protocol_requires_operator_observation_and_confirmation():
    report=protocol.build_daily_evaluation_protocol()
    require(report['operator_observation_required'] and report['explicit_confirmation_required_for_mutation'],'operator boundary missing')
    require(report['private_notes_runtime_only'] and not report['transcript_content_required'],'privacy boundary wrong')

def test_protocol_has_no_autonomous_scoring_or_release_authority():
    report=protocol.build_daily_evaluation_protocol()
    for key in ('autonomous_scoring','automatic_promotion','automatic_release_certification','provider_invoked','embedding_provider_invoked','model_management','provider_switching','generation_settings_changed','approval_granted','rollback_authorized','installation_performed','promotion_performed','writes_state'):
        require(report[key] is False,f'authority escalated: {key}')

def test_protocol_is_content_free_and_redacted():
    report=protocol.build_daily_evaluation_protocol()
    require(report['read_only'] and report['content_free'] and report['redacted'],'public flags wrong')
    require(not protocol.daily_evaluation_protocol_contains_private_fields(report),'private field exposed')

def test_get_route_is_registered_and_provider_free():
    status,payload=api_server.handle_api_get('/api/conversation/daily-evaluation-protocol',{})
    require(status==200 and payload.get('ok'),'GET route failed')
    data=payload['data'];require(data['type']=='desktop_alpha_daily_evaluation_protocol','wrong payload type')
    require(not data['provider_invoked'] and not data['writes_state'],'GET route has side effects')

def test_protocol_has_no_post_mutation_route():
    source=(AGENT/'api_server.py').read_text(encoding='utf-8')
    post=source[source.index('def handle_api_post'):]
    require('parts == ["conversation", "daily-evaluation-protocol"]' not in post,'protocol POST route exists')

def test_protocol_build_preserves_source_tree():
    before=tree_digest();protocol.build_daily_evaluation_protocol();after=tree_digest();require(before==after,'protocol mutated source')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1087.0-daily-evaluation-protocol')==1,'suite registration not exact')
    require(names.index('v1087.0-daily-evaluation-protocol')<names.index('v1086.9-desktop-alpha-conversation-readiness-checkpoint'),'suite order wrong')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1087.0-daily-evaluation-protocol','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
