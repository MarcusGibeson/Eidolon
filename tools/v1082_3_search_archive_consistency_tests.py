from __future__ import annotations
import argparse, json, sys, tempfile, threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path.insert(0,str(AGENT))
import conversation_sessions as sessions
import post_review_development_verify as isolated_verify

def require(v,m):
    if not v: raise AssertionError(m)

class Store:
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='eidolon-v1082-3-'); root=Path(self.temp.name)/'sessions'
        self.orig=(sessions.CONVERSATION_SESSIONS_DIR,sessions.ACTIVE_SESSION_FILE,sessions.CONVERSATION_DRAFTS_DIR,sessions.CONVERSATION_DRAFT_CONFLICTS_DIR)
        sessions.CONVERSATION_SESSIONS_DIR=root; sessions.ACTIVE_SESSION_FILE=root/'active_session.json'; sessions.CONVERSATION_DRAFTS_DIR=root/'drafts'; sessions.CONVERSATION_DRAFT_CONFLICTS_DIR=root/'conflicts'; sessions.clear_conversation_search_cache()
    def close(self):
        (sessions.CONVERSATION_SESSIONS_DIR,sessions.ACTIVE_SESSION_FILE,sessions.CONVERSATION_DRAFTS_DIR,sessions.CONVERSATION_DRAFT_CONFLICTS_DIR)=self.orig; sessions.clear_conversation_search_cache(); self.temp.cleanup()

def seed():
    st=Store(); a=sessions.create_conversation_session('Alpha project'); b=sessions.create_conversation_session('Beta project')
    sessions.append_conversation_turn(a['id'],turn_id='a1',user_message='searchable alpha phrase',assistant_response='alpha reply',completion_state='completed',success=True)
    sessions.append_conversation_turn(b['id'],turn_id='b1',user_message='searchable beta phrase',assistant_response='beta reply',completion_state='completed',success=True)
    return st,a['id'],b['id']

def test_catalog_revision_changes_on_archive():
    st,a,b=seed()
    try:
        before=sessions.conversation_session_catalog_page('',include_archived=True)
        sessions.archive_conversation_session(a)
        after=sessions.conversation_session_catalog_page('',include_archived=True)
        require(before['catalog_revision']!=after['catalog_revision'],'archive did not advance catalog revision')
        require(after['snapshot_consistent'] is True and after['catalog_schema_version']=='2','catalog consistency metadata missing')
        row=next(x for x in after['items'] if x['id']==a); require(row['status']=='archived','archived row stale')
    finally: st.close()

def test_active_search_excludes_archived_immediately():
    st,a,b=seed()
    try:
        sessions.archive_conversation_session(a)
        page=sessions.conversation_session_catalog_page('alpha',include_archived=False)
        require(page['total']==0 and not page['items'],'active search returned archived session')
        page2=sessions.conversation_session_catalog_page('alpha',include_archived=True)
        require(page2['total']==1 and page2['items'][0]['status']=='archived','archived search lost session')
    finally: st.close()

def test_concurrent_search_archive_pages_are_self_consistent():
    st,a,b=seed(); pages=[]; gate=threading.Barrier(2)
    try:
        def searcher(): gate.wait(); pages.append(sessions.conversation_session_catalog_page('',include_archived=True))
        def archiver(): gate.wait(); sessions.archive_conversation_session(a)
        t1=threading.Thread(target=searcher); t2=threading.Thread(target=archiver); t1.start(); t2.start(); t1.join(); t2.join()
        page=pages[0]; require(page['snapshot_consistent'] is True,'concurrent page not marked consistent')
        statuses={x['id']:x['status'] for x in page['items']}; require(statuses[a] in {'active','archived'},'invalid mixed status')
        final=sessions.conversation_session_catalog_page('',include_archived=True); require(next(x for x in final['items'] if x['id']==a)['status']=='archived','final catalog missed archive')
    finally: st.close()

def test_out_of_range_page_normalizes_after_archive():
    st=Store()
    try:
        ids=[]
        for i in range(5): ids.append(sessions.create_conversation_session(f'Session {i}')['id'])
        page=sessions.conversation_session_catalog_page('',include_archived=False,offset=4,limit=2); require(page['offset']==4,'fixture page offset wrong')
        for sid in ids[:4]: sessions.archive_conversation_session(sid)
        page2=sessions.conversation_session_catalog_page('',include_archived=False,offset=4,limit=2)
        require(page2['offset']==0 and page2['shown']==1,'stale offset not normalized')
    finally: st.close()

def test_browser_discards_out_of_order_catalog_requests():
    src=(AGENT/'dashboard_chat_console.py').read_text()
    require('catalogRefreshSequence' in src and 'catalogRefreshController.abort()' in src,'catalog request sequencing absent')
    require('catalog_revision' in src and 'catalog_changed' in src,'catalog revision presentation absent')

def test_registration_and_metadata():
    core={x.name for x in isolated_verify.select_suites('core')}; require('v1082.3-search-archive-consistency' in core,'core registration missing')
    import release_metadata; version=tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')); require(version >= (1082,5),'runtime regressed below v1082.5')
    rel=(TOOLS/'release_verify.py').read_text(); require(rel.count('v1082_3_search_archive_consistency_tests.py')==1,'release registration count wrong')

def test_source_only_privacy():
    forbidden=['data/projects.json','data/tasks.json','data/memories.json','data/conversation_sessions/','data/dashboard_chat/','data/provider_recovery/']
    files=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    require(not [x for x in files if any(x==f or x.startswith(f) for f in forbidden)],'private runtime data present')

TESTS=[('catalog_revision_changes_on_archive',test_catalog_revision_changes_on_archive),('active_search_excludes_archived_immediately',test_active_search_excludes_archived_immediately),('concurrent_search_archive_pages_are_self_consistent',test_concurrent_search_archive_pages_are_self_consistent),('out_of_range_page_normalizes_after_archive',test_out_of_range_page_normalizes_after_archive),('browser_discards_out_of_order_catalog_requests',test_browser_discards_out_of_order_catalog_requests),('registration_and_metadata',test_registration_and_metadata),('source_only_privacy',test_source_only_privacy)]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); argparse.ArgumentParser
    checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1082.3-search-archive-consistency','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
