from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090c-long-candidates-'); os.environ['PYTHONDONTWRITEBYTECODE']='1'
import api_server, dashboard, post_review_development_verify as verify
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_review as review
import repair_candidate_long_session as window

def require(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.suffix not in {'.pyc','.pyo'} and not any(x in p.parts for x in {'__pycache__','.git','.venv','venv'}): h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
_CACHE=None
def large_fixture():
    global _CACHE
    if _CACHE is not None:return _CACHE
    s=create_conversation_session('Long candidate window fixture',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); all_rows=[]
    remaining=205; finding_index=0
    while remaining:
        f=finding.create_evaluation_finding(finding_title=f'PRIVATE_LONG_CANDIDATE_FINDING_{finding_index:02d}',issue_domain='session_continuity',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True)
        revision=f['revision']; count=min(24,remaining)
        for index in range(count):
            serial=len(all_rows); kind='source_archive' if serial%2==0 else 'patch_artifact'; artifact=f'{serial+1:064X}'[-64:]
            r=registration.register_repair_candidate(f['finding_id'],candidate_kind=kind,artifact_sha256=artifact,label=f'PRIVATE_LONG_LABEL_{serial:03d}',private_reference=f'PRIVATE_LONG_REFERENCE_{serial:03d}',expected_revision=revision,operator_confirmed=True); revision=r['finding_revision']; c=r['candidates'][-1]; all_rows.append((f['finding_id'],c['candidate_id'],kind))
        remaining-=count; finding_index+=1
    _CACHE=(e['evaluation_id'],all_rows); return _CACHE

def test_initial_window_is_eighty_complete_rows():
    _,rows=large_fixture(); r=window.build_repair_candidate_window(); require(r['total_matching_candidates']==205,'total'); require(r['returned_count']==r['initial_window_limit']==80,'initial'); require(r['offset']==0 and r['next_offset']==80 and r['has_more'],'paging'); require(len({x['candidate_id'] for x in r['candidates']})==80,'rows')
def test_earlier_windows_are_one_hundred_twenty_then_remainder():
    large_fixture(); a=window.build_repair_candidate_window(); b=window.build_repair_candidate_window(offset=a['next_offset']); c=window.build_repair_candidate_window(offset=b['next_offset']); require(b['returned_count']==120 and b['next_offset']==200 and b['has_more'],'second'); require(c['returned_count']==5 and c['next_offset']==205 and not c['has_more'],'third'); combined=a['candidates']+b['candidates']+c['candidates']; require(len(combined)==205 and len({x['candidate_id'] for x in combined})==205,'coverage')
def test_order_and_digest_are_deterministic():
    large_fixture(); a=window.build_repair_candidate_window(); b=window.build_repair_candidate_window(); require(a==b,'deterministic'); keys=[(x['updated_at'],x['candidate_id'],x['finding_id']) for x in a['candidates']]; require(keys==sorted(keys,reverse=True),'order')
def test_filters_isolate_finding_kind_and_state():
    _,rows=large_fixture(); fid,cid,_=rows[0]; r=window.build_repair_candidate_window(finding_id=fid,candidate_kind='source_archive'); require(r['total_matching_candidates']>0 and all(x['finding_id']==fid and x['candidate_kind']=='source_archive' for x in r['candidates']),'filter')
    regs=registration.build_repair_candidate_registrations(fid); target=next(x for x in regs['candidates'] if x['candidate_id']==cid); rv=review.record_repair_candidate_review(fid,cid,review_area='artifact_integrity',review_outcome='reviewing',expected_revision=regs['finding_revision'],operator_confirmed=True); filtered=window.build_repair_candidate_window(finding_id=fid,review_state='reviewing'); require(any(x['candidate_id']==cid for x in filtered['candidates']),'state')
def test_window_excludes_private_content_and_authority():
    large_fixture(); r=window.build_repair_candidate_window(); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_LONG_LABEL_' not in encoded and 'PRIVATE_LONG_REFERENCE_' not in encoded,'private'); require(not window.repair_candidate_window_contains_private_fields(r),'fields')
    for key in ('provider_invoked','automatic_test_execution','automatic_task_created','automatic_work_item_created','autonomous_prioritization','candidate_ranked','winner_selected','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','writes_state'): require(r[key] is False,key)
def test_api_route_clamps_earlier_window():
    large_fixture(); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-window',{'offset':['80'],'limit':['999']}); d=payload['data']; require(status==200 and d['returned_count']==120 and d['limit']==d['earlier_window_limit'],'route')
def test_dashboard_integrates_load_earlier_without_overflow():
    html=dashboard.render_repair_candidate_review_console()
    for token in ("data-long-session-candidates-version='v1090.8'",'candidate-load-earlier','next_offset','has_more','offset = Number'): require(token in html,token)
    require('@media(max-width:820px)' in html and 'grid-template-columns:1fr' in html,'narrow')
def test_window_read_is_source_immutable():
    large_fixture(); before=tree_digest(); window.build_repair_candidate_window(offset=80); require(before==tree_digest(),'source')
def test_limits_are_explicit_and_bounded():
    require(window.INITIAL_CANDIDATE_WINDOW==80,'initial'); require(window.EARLIER_CANDIDATE_WINDOW==120,'earlier'); require(window.MAX_LONG_SESSION_CANDIDATES==512,'maximum'); large_fixture(); r=window.build_repair_candidate_window(offset=-10,limit=9999); require(r['offset']==0 and r['limit']==80,'bounds')
def test_route_and_suite_registration_are_exact():
    source=(ROOT/'conscious_agent/api_server.py').read_text(); require(source.count('parts == ["conversation", "repair-candidate-window"]')==1,'route'); post=source[source.index('def handle_api_post'):]; require('parts == ["conversation", "repair-candidate-window"]' not in post,'post'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.8-long-session-candidate-review')==1,'registration'); require(names.index('v1090.8-long-session-candidate-review')<names.index('v1090.7-candidate-review-export'),'order')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1090.8-long-session-candidate-review','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
