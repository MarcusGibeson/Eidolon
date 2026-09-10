from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path:sys.path.insert(0,str(AGENT))

def require(condition: bool,message: str)->None:
    if not condition:raise AssertionError(message)

def seed(path:Path,value:object)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding='utf-8')

def test_healthy_state_is_content_free_and_conversation_available()->None:
    from metadata_recovery_state import build_metadata_recovery_state
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);seed(root/'settings.json',{'secret':'PRIVATE'}) ;os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'locks')
        state=build_metadata_recovery_state(data_dir=root);encoded=json.dumps(state)
        require(state['status']=='healthy' and state['controls']['ordinary_conversation_available'],'healthy state incorrect')
        require('PRIVATE' not in encoded and str(root) not in encoded,'state leaked payload/path')

def test_live_owner_reports_busy_without_eviction()->None:
    from metadata_mutation_coordination import metadata_mutation_lock
    from metadata_recovery_state import build_metadata_recovery_state
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);target=root/'settings.json';seed(target,{'a':1});os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'locks')
        with metadata_mutation_lock(target):
            state=build_metadata_recovery_state(data_dir=root)
            require(state['status']=='busy' and not state['controls']['metadata_mutations_enabled'],'busy state incorrect')

def test_pending_record_reports_recovery_required()->None:
    from metadata_migration_recovery import begin_migration_recovery
    from metadata_recovery_state import build_metadata_recovery_state
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);target=root/'settings.json';seed(target,{'a':1});begin_migration_recovery(target,original_sha256='a'*64,canonical_sha256='b'*64,expected_root_type='dict',data_dir=root)
        state=build_metadata_recovery_state(data_dir=root)
        require(state['status']=='recovery_required' and state['controls']['confirmed_recovery_available'],'pending recovery hidden'); require(state['summary']['recovery_required_count']==1,'pending recovery double counted')

def test_invalid_private_record_reports_uncertain()->None:
    from metadata_migration_recovery import recovery_state_dir
    from metadata_recovery_state import build_metadata_recovery_state
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);directory=recovery_state_dir(data_dir=root);directory.mkdir(parents=True);(directory/'bad.json').write_text('{',encoding='utf-8')
        state=build_metadata_recovery_state(data_dir=root)
        require(state['status']=='uncertain' and state['controls']['operator_review_required'],'invalid state not uncertain')

def test_confirmed_duplicate_cleanup_reports_safely_recovered()->None:
    from metadata_recovery_state import reconcile_metadata_recovery_state
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);target=root/'settings.json';seed(target,{'a':1});temp=root/'.settings.json.transaction-1-dead.tmp';temp.write_bytes(target.read_bytes());os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'locks')
        denied=reconcile_metadata_recovery_state(operator_confirmed=False,data_dir=root)
        require(denied['status']=='confirmation_required' and temp.exists(),'unconfirmed cleanup mutated')
        state=reconcile_metadata_recovery_state(operator_confirmed=True,data_dir=root)
        require(state['status']=='safely_recovered' and state['removed']==1 and not temp.exists(),'safe cleanup status incorrect')

def test_dashboard_keeps_status_get_and_cleanup_post()->None:
    text=(AGENT/'dashboard.py').read_text(encoding='utf-8');do_post=text.index('    def do_POST')
    require(text.index('if path == "/api/metadata-recovery-state"') < do_post,'status is not GET')
    require(text.index('if parsed.path == "/api/metadata-recovery/reconcile"') > do_post,'cleanup is not POST')
    require('operator_confirmed=body.get("operator_confirmed") is True' in text,'literal confirmation missing')

def test_chat_panel_is_async_accessible_and_provider_free()->None:
    console=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8');styles=(AGENT/'dashboard_chat_styles.py').read_text(encoding='utf-8')
    require("id='chat-metadata-recovery'" in console and "role='status'" in console and "aria-live='polite'" in console,'accessible panel missing')
    require("fetch('/api/metadata-recovery-state'" in console and 'window.setTimeout(refreshMetadataRecoveryState, 0)' in console,'async status missing')
    require('contact a provider' in console and 'chat-metadata-recovery button:focus-visible' in styles and '@media(max-width:700px)' in styles,'provider-free or responsive UX missing')

def test_dashboard_style_module_imports_and_contains_panel_css()->None:
    import importlib
    module=importlib.import_module('dashboard_chat_styles')
    require('.chat-metadata-recovery{' in module.COMPANION_CHAT_STYLES,'metadata recovery CSS not inside stylesheet contract')

def test_repeated_save_stale_preview_and_invalid_file_preserve_state()->None:
    from json_storage import write_json_atomic
    from metadata_migration import preview_metadata_migration,apply_metadata_migration
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);target=root/'settings.json';target.write_bytes(b'\xef\xbb\xbf'+b'{"a":1}');os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'locks')
        preview=preview_metadata_migration('settings','settings.json',data_dir=root)
        for value in range(2,7):write_json_atomic(target,{'a':value},expected_type=dict)
        stale=apply_metadata_migration('settings','settings.json',preview_token=preview['preview_token'],operator_confirmed=True,data_dir=root)
        require(stale['status']=='stale_or_mismatched_preview' and json.loads(target.read_text())['a']==6,'stale preview or repeated saves failed')
        invalid=root/'tasks.json';invalid.write_text('{broken',encoding='utf-8');before=invalid.read_bytes()
        from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts
        inspect_orphaned_metadata_artifacts(data_dir=root)
        require(invalid.read_bytes()==before,'invalid file was rewritten')

def test_release_metadata_and_docs()->None:
    import re
    release=(AGENT/'release_metadata.py').read_text();match=re.search(r'RUNTIME_VERSION = "(\d+)\.(\d+)"',release)
    require(bool(match) and tuple(map(int,match.groups())) >= (1093,8),'runtime version regressed')
    require('v1093.8' in (ROOT/'README_RELEASE_HISTORY.md').read_text(),'history missing')
    require('v1093.9' in (ROOT/'README_NEXT_STEPS.md').read_text(),'checkpoint missing')

def main()->int:
    tests=[test_healthy_state_is_content_free_and_conversation_available,test_live_owner_reports_busy_without_eviction,test_pending_record_reports_recovery_required,test_invalid_private_record_reports_uncertain,test_confirmed_duplicate_cleanup_reports_safely_recovered,test_dashboard_keeps_status_get_and_cleanup_post,test_chat_panel_is_async_accessible_and_provider_free,test_dashboard_style_module_imports_and_contains_panel_css,test_repeated_save_stale_preview_and_invalid_file_preserve_state,test_release_metadata_and_docs]
    failures=[];passed=0
    for test in tests:
        try:test();passed+=1
        except Exception as error:failures.append(f'{test.__name__}: {type(error).__name__}: {error}')
    report={'version':'1093.8','suite':'daily-use-metadata-recovery-hardening','passed':passed,'total':len(tests),'ok':passed==len(tests),'failures':failures}
    print(json.dumps(report,sort_keys=True));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
