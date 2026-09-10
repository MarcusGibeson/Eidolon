from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/"conscious_agent"
if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))

def require(condition: bool,message: str)->None:
    if not condition: raise AssertionError(message)

def write_bom(path:Path,value:object)->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'\xef\xbb\xbf'+json.dumps(value).encode())

def _interrupt(stage_name:str):
    def hook(stage:str)->None:
        if stage==stage_name: raise SystemExit(f"simulated termination at {stage}")
    return hook

def _simulate(stage:str, *, expected_after:str) -> None:
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); os.environ['EIDOLON_DATA_DIR']=td; os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'locks')
        target=root/'settings.json'; write_bom(target,{"safe_mode":"strict"}); original=target.read_bytes()
        from json_storage import apply_json_migration, preview_json_migration
        from metadata_migration_recovery import metadata_migration_recovery_status,recover_pending_metadata_migrations
        preview=preview_json_migration(target,expected_type=dict)
        try:
            apply_json_migration(target,preview_token=preview['preview_token'],operator_confirmed=True,expected_type=dict,backup_dir=root/'metadata_migration_backups'/'settings',recovery_dir=root/'metadata_migration_state',fault_hook=_interrupt(stage))
        except SystemExit: pass
        status=metadata_migration_recovery_status(data_dir=root); require(status['pending_operation_count']==1,f"{stage}: recovery state missing")
        denied=recover_pending_metadata_migrations(operator_confirmed=False,data_dir=root); require(denied['status']=='confirmation_required',f"{stage}: recovery lacked confirmation")
        result=recover_pending_metadata_migrations(operator_confirmed=True,data_dir=root); require(result['ok'] and result['recovered']==1,f"{stage}: recovery failed")
        if expected_after=='original': require(target.read_bytes()==original,f"{stage}: original not preserved")
        else: require(not target.read_bytes().startswith(b'\xef\xbb\xbf'),f"{stage}: canonical result not retained")
        require(metadata_migration_recovery_status(data_dir=root)['pending_operation_count']==0,f"{stage}: recovery record remained")

def test_recovery_before_backup_preserves_original()->None: _simulate('before_backup',expected_after='original')
def test_recovery_after_backup_preserves_original()->None: _simulate('after_backup',expected_after='original')
def test_recovery_before_replace_preserves_original()->None: _simulate('before_replace',expected_after='original')
def test_recovery_after_replace_verifies_canonical()->None: _simulate('after_replace_before_verify',expected_after='canonical')

def test_unknown_target_is_restored_from_verified_backup()->None:
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); os.environ['EIDOLON_DATA_DIR']=td; os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'locks')
        target=root/'tasks.json'; write_bom(target,{"version":1,"tasks":[]}); original=target.read_bytes()
        from json_storage import apply_json_migration,preview_json_migration
        from metadata_migration_recovery import recover_pending_metadata_migrations
        preview=preview_json_migration(target,expected_type=dict)
        try: apply_json_migration(target,preview_token=preview['preview_token'],operator_confirmed=True,expected_type=dict,backup_dir=root/'metadata_migration_backups'/'tasks',recovery_dir=root/'metadata_migration_state',fault_hook=_interrupt('after_backup'))
        except SystemExit: pass
        target.write_bytes(b'{"corrupt":')
        result=recover_pending_metadata_migrations(operator_confirmed=True,data_dir=root)
        require(result['ok'] and result['results'][0]['status']=='original_restored',"unknown target not restored")
        require(target.read_bytes()==original,"restored bytes differ")

def test_recovery_status_is_content_free()->None:
    from metadata_migration_recovery import begin_migration_recovery,metadata_migration_recovery_status
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'PRIVATE_PATH'/'settings.json'; target.parent.mkdir(); target.write_text('{}\n')
        begin_migration_recovery(target,original_sha256='a'*64,canonical_sha256='b'*64,expected_root_type='dict',data_dir=root)
        status=metadata_migration_recovery_status(data_dir=root); encoded=json.dumps(status)
        require(str(target) not in encoded and 'PRIVATE_PATH' not in encoded,"status leaked path")
        require(status['content_free'] and not status['source_mutated'],"status contract wrong")

def test_dashboard_routes_keep_status_get_and_recovery_post()->None:
    text=(AGENT/'dashboard.py').read_text(encoding='utf-8'); do_post=text.index('    def do_POST')
    require(text.index('if path == "/api/metadata-migration/status"')<do_post,"status is not GET")
    require(text.index('if parsed.path == "/api/metadata-migration/recover"')>do_post,"recovery is not POST")
    require('operator_confirmed' in text[text.index('if parsed.path == "/api/metadata-migration/recover"'):][:800],"recovery confirmation missing")

def test_daily_use_surfaces_remain_present()->None:
    dashboard=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    for route in ['/api/dashboard-health','/api/conversation-runtime-health','/api/project-recovery-state','/api/dashboard-chat/coordination']:
        require(route in dashboard,f"daily-use route missing: {route}")
    require('metadata_migration_recovery' not in (AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8'),"migration recovery leaked into spoken conversation console")

def test_backups_are_bounded()->None:
    from metadata_migration_recovery import prune_target_backups
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        for i in range(8):
            p=root/f'settings.json.pre-utf8-migration-20260101T00000{i}Z-{i:012d}.bak'; p.write_text(str(i)); os.utime(p,(i+1,i+1))
        prune_target_backups(root,'settings.json',keep=5)
        require(len(list(root.glob('settings.json.pre-utf8-migration-*.bak')))==5,"backups not bounded")


def test_tampered_recovery_record_cannot_escape_runtime_root()->None:
    from metadata_migration_recovery import recovery_state_dir,recover_pending_metadata_migrations
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
        root=Path(td); external=Path(outside)/"victim.json"; external.write_text("ORIGINAL",encoding="utf-8")
        state=recovery_state_dir(data_dir=root); state.mkdir(parents=True)
        record={"type":"metadata_migration_recovery","schema_version":"1","operation_id":"a"*32,"target_path":str(external),"target_digest":"b"*64,"backup_path":"","original_sha256":"c"*64,"canonical_sha256":"d"*64,"expected_root_type":"dict","stage":"replacement_started","content_free":True,"local_private":True}
        (state/("a"*32+".json")).write_text(json.dumps(record),encoding="utf-8")
        result=recover_pending_metadata_migrations(operator_confirmed=True,data_dir=root)
        require(result["uncertain"]==1 and result["results"][0]["status"]=="unsafe_private_record","tampered record was not rejected")
        require(external.read_text(encoding="utf-8")=="ORIGINAL","external path was mutated")


def test_string_false_never_confirms_recovery()->None:
    from metadata_migration_recovery import begin_migration_recovery,recover_pending_metadata_migrations
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/"settings.json"; target.write_text("{}\n",encoding="utf-8")
        begin_migration_recovery(target,original_sha256="a"*64,canonical_sha256="b"*64,expected_root_type="dict",data_dir=root)
        result=recover_pending_metadata_migrations(operator_confirmed="false",data_dir=root)
        require(result["status"]=="confirmation_required","string false confirmed recovery")

def test_release_metadata_and_docs()->None:
    release=(AGENT/'release_metadata.py').read_text(); import re; match=re.search(r'RUNTIME_VERSION = "(\d+)\.(\d+)"',release); require(bool(match) and tuple(map(int,match.groups())) >= (1093,5),"runtime version regressed")
    require('v1093.5' in (ROOT/'README_RELEASE_HISTORY.md').read_text(),"history missing")
    require('v1093.6' in (ROOT/'README_NEXT_STEPS.md').read_text(),"next bundle missing")

def main()->int:
    tests=[test_recovery_before_backup_preserves_original,test_recovery_after_backup_preserves_original,test_recovery_before_replace_preserves_original,test_recovery_after_replace_verifies_canonical,test_unknown_target_is_restored_from_verified_backup,test_recovery_status_is_content_free,test_dashboard_routes_keep_status_get_and_recovery_post,test_daily_use_surfaces_remain_present,test_backups_are_bounded,test_tampered_recovery_record_cannot_escape_runtime_root,test_string_false_never_confirms_recovery,test_release_metadata_and_docs]
    failures=[]; passed=0
    for test in tests:
        try:test();passed+=1
        except Exception as error:failures.append(f"{test.__name__}: {type(error).__name__}: {error}")
    report={"version":"1093.5","suite":"migration-recovery-daily-use-hardening","passed":passed,"total":len(tests),"ok":passed==len(tests),"failures":failures}
    print(json.dumps(report,sort_keys=True));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
