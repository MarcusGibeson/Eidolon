from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1087c-')
import api_server
import conversation_daily_evaluation as evaluation
import conversation_evaluation_long_session as long_session
import conversation_evaluation_review_export as mod
import conversation_sessions as sessions
import post_review_development_verify as verify

def req(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not any(part in {'__pycache__','.git','.venv','venv'} for part in p.parts) and p.suffix!='.pyc': h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
def make_eval():
    session=sessions.create_conversation_session(title='Review export fixture')
    item=evaluation.start_daily_evaluation(session['id'],operator_confirmed=True)
    signals=list(long_session.REQUIRED_LONG_SESSION_SIGNALS)+['restart_resume','provider_outage','provider_return','generation_interruption','failed_retry','completed_regeneration','explicit_resend']
    item=evaluation.record_operator_observation(item['evaluation_id'],ratings={'continuity':5,'recovery':4},signals=signals,issue_domain='interface',severity='minor',reproducible=True,note='PRIVATE_EXPORT_SENTINEL',expected_revision=item['revision'],operator_confirmed=True)
    return evaluation.finish_daily_evaluation(item['evaluation_id'],state='completed',expected_revision=item['revision'],operator_confirmed=True)

def test_export_is_deterministic_and_hash_bound():
    item=make_eval(); first=mod.build_evaluation_review_export(item['evaluation_id']); second=mod.build_evaluation_review_export(item['evaluation_id'])
    req(first==second,'nondeterministic'); req(hashlib.sha256(first['document'].encode()).hexdigest()==first['document_sha256'],'hash mismatch')

def test_export_contains_bounded_review_evidence():
    item=make_eval(); report=mod.build_evaluation_review_export(item['evaluation_id']); review=report['review']
    req(review['long_session_status']=='complete' and review['restart_outage_status']=='complete','coverage')
    req(review['operator_review_required'] and review['release_decision']=='operator_only','operator authority')

def test_export_excludes_private_content():
    item=make_eval(); report=mod.build_evaluation_review_export(item['evaluation_id']); encoded=json.dumps(report)
    req('PRIVATE_EXPORT_SENTINEL' not in encoded,'note leaked'); req(not mod.evaluation_review_export_contains_private_fields(report),'private fields')
    for key in ('transcript_included','prompt_included','private_notes_included','memory_content_included','provider_payload_included','credentials_included','vectors_included','hidden_reasoning_included'): req(report['review'][key] is False,key)

def test_get_route_returns_client_download_without_server_write():
    item=make_eval(); before=tree_digest(); status,payload=api_server.handle_api_get('/api/conversation/evaluation-review-export',{'evaluation_id':[item['evaluation_id']]}); data=payload['data']
    req(status==200 and payload.get('ok') and data['client_download_ready'],'route'); req(not data['server_file_written'] and not data['writes_state'],'server write'); req(before==tree_digest(),'source mutation')

def test_export_cannot_certify_install_or_promote():
    item=make_eval(); report=mod.build_evaluation_review_export(item['evaluation_id'])
    req(not report['release_certified'] and not report['promotion_performed'] and not report['installation_performed'],'authority')
    req(not report['provider_invoked'],'provider')

def test_no_post_route_and_exact_registration():
    source=(ROOT/'conscious_agent'/'api_server.py').read_text(); post=source[source.index('def handle_api_post'):]
    req('parts == ["conversation", "evaluation-review-export"]' not in post,'POST route')
    names=[s.name for s in verify.SUITES]; req(names.count('v1087.8-evaluation-review-export')==1,'registration')

def test_filename_is_bounded_and_content_free():
    item=make_eval(); report=mod.build_evaluation_review_export(item['evaluation_id'])
    req(report['filename'].endswith('_privacy_safe_review.json'),'filename'); req('/' not in report['filename'] and '\\' not in report['filename'],'path injection')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1087.8-evaluation-review-export','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
