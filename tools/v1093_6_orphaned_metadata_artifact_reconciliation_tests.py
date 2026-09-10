from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def seed(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_idle_inventory_is_content_free() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); seed(root/'settings.json', {'safe_mode':'strict'})
        os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'metadata_mutation_locks')
        result=inspect_orphaned_metadata_artifacts(data_dir=root)
        require(result['status']=='healthy' and result['artifact_count']==0, 'idle inventory incorrect')
        require(result['content_free'] and not result['absolute_path_returned'], 'inventory leaked paths')


def test_live_owner_is_preserved() -> None:
    from metadata_mutation_coordination import metadata_mutation_lock
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; seed(target, {'a':1})
        os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'metadata_mutation_locks')
        with metadata_mutation_lock(target):
            state=inspect_orphaned_metadata_artifacts(data_dir=root)
            require(state['status']=='busy' and state['counts'].get('busy')==1, 'live owner not classified')
            cleaned=reconcile_orphaned_metadata_artifacts(operator_confirmed=True, data_dir=root)
            require(cleaned['status']=='busy' and cleaned['removed']==0, 'live owner was removed')


def test_dead_exact_owner_is_safe_cleanup() -> None:
    from metadata_mutation_coordination import metadata_lock_path
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts
    import hashlib
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; seed(target, {'a':1})
        os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'metadata_mutation_locks')
        lock=metadata_lock_path(target); lock.parent.mkdir(parents=True)
        digest=hashlib.sha256(str(target.resolve()).encode()).hexdigest()
        lock.write_text(json.dumps({'pid':99999999,'owner_token':'a'*32,'target_digest':digest}),encoding='utf-8')
        state=inspect_orphaned_metadata_artifacts(data_dir=root)
        require(state['counts'].get('safe_cleanup')==1, 'dead exact owner not safe cleanup')
        denied=reconcile_orphaned_metadata_artifacts(operator_confirmed=False,data_dir=root)
        require(denied['status']=='confirmation_required' and lock.exists(), 'unconfirmed cleanup mutated')
        done=reconcile_orphaned_metadata_artifacts(operator_confirmed=True,data_dir=root)
        require(done['removed']==1 and not lock.exists(), 'dead lock not removed')


def test_duplicate_temp_is_only_safe_temp_cleanup() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; seed(target, {'a':1})
        os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'metadata_mutation_locks')
        duplicate=root/'.settings.json.transaction-1-dead.tmp'; duplicate.write_bytes(target.read_bytes())
        other=root/'.settings.json.transaction-2-live.tmp'; seed(other, {'a':2})
        state=inspect_orphaned_metadata_artifacts(data_dir=root)
        require(state['counts'].get('safe_cleanup')==1 and state['counts'].get('operator_review')==1, 'temp classification unsafe')
        done=reconcile_orphaned_metadata_artifacts(operator_confirmed=True,data_dir=root)
        require(not duplicate.exists() and other.exists() and done['removed']==1, 'cleanup deleted uncertain temp')


def test_recovery_record_requires_recovery_not_cleanup() -> None:
    from metadata_migration_recovery import begin_migration_recovery
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; seed(target, {'a':1})
        begin_migration_recovery(target, original_sha256='a'*64, canonical_sha256='b'*64, expected_root_type='dict', data_dir=root)
        state=inspect_orphaned_metadata_artifacts(data_dir=root)
        require(state['status']=='recovery_required' and state['counts'].get('recovery_required')==1, 'recovery record misclassified')


def test_verified_backup_is_not_deleted_by_age() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; seed(target, {'a':2})
        backup=root/'metadata_migration_backups'/'settings'/'settings.json.pre-utf8-migration-old.bak'; seed(backup, {'a':1})
        os.utime(backup,(1,1))
        state=inspect_orphaned_metadata_artifacts(data_dir=root)
        require(state['counts'].get('verified_backup')==1, 'verified backup not detected')
        reconcile_orphaned_metadata_artifacts(operator_confirmed=True,data_dir=root)
        require(backup.exists(), 'backup deleted merely because old')


def test_unmatched_private_artifacts_require_operator_review() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); os.environ['EIDOLON_METADATA_LOCK_DIR']=str(root/'metadata_mutation_locks')
        locks=root/'metadata_mutation_locks'; locks.mkdir(parents=True)
        unknown=locks/('f'*64+'.lock'); unknown.write_text(json.dumps({'pid':99999999,'owner_token':'a'*32,'target_digest':'f'*64}),encoding='utf-8')
        temp=root/'.deleted.json.transaction-1-orphan.tmp'; seed(temp, {'a':1})
        state=inspect_orphaned_metadata_artifacts(data_dir=root)
        require(state['status']=='uncertain' and state['counts'].get('operator_review')==2,'unmatched artifacts not surfaced')
        reconcile_orphaned_metadata_artifacts(operator_confirmed=True,data_dir=root)
        require(unknown.exists() and temp.exists(),'unmatched artifacts were deleted')

def test_duplicate_backup_name_is_never_bound_by_guess() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        first=root/'conversation_navigation'/'one'/'state.json'; second=root/'conversation_navigation'/'two'/'state.json'
        seed(first, {'a':1}); seed(second, {'a':1})
        backup=root/'metadata_migration_backups'/'conversation_navigation'/'state.json.pre-utf8-migration-old.bak'; seed(backup, {'a':1})
        state=inspect_orphaned_metadata_artifacts(data_dir=root)
        row=next(row for row in state['rows'] if row['artifact_type']=='migration_backup')
        require(row['status']=='operator_review' and not row['safe_cleanup'],'ambiguous backup name was guessed')

def test_rows_never_return_paths_or_payloads() -> None:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); seed(root/'settings.json', {'secret':'PRIVATE_PAYLOAD'})
        result=inspect_orphaned_metadata_artifacts(data_dir=root)
        encoded=json.dumps(result)
        require(str(root) not in encoded and 'PRIVATE_PAYLOAD' not in encoded, 'artifact status leaked content')


def test_release_metadata_and_docs() -> None:
    import re
    release=(AGENT/'release_metadata.py').read_text(encoding='utf-8')
    match=re.search(r'RUNTIME_VERSION = "(\d+)\.(\d+)"',release)
    require(bool(match) and tuple(map(int,match.groups())) >= (1093,6),'runtime version regressed')
    require('v1093.6' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'history missing')
    require('v1093.7' in (ROOT/'README_NEXT_STEPS.md').read_text(encoding='utf-8'),'next step missing')


def main() -> int:
    tests=[test_idle_inventory_is_content_free,test_live_owner_is_preserved,test_dead_exact_owner_is_safe_cleanup,test_duplicate_temp_is_only_safe_temp_cleanup,test_recovery_record_requires_recovery_not_cleanup,test_verified_backup_is_not_deleted_by_age,test_unmatched_private_artifacts_require_operator_review,test_duplicate_backup_name_is_never_bound_by_guess,test_rows_never_return_paths_or_payloads,test_release_metadata_and_docs]
    failures=[]; passed=0
    for test in tests:
        try: test(); passed+=1
        except Exception as error: failures.append(f'{test.__name__}: {type(error).__name__}: {error}')
    report={'version':'1093.6','suite':'orphaned-metadata-artifact-reconciliation','passed':passed,'total':len(tests),'ok':passed==len(tests),'failures':failures}
    print(json.dumps(report,sort_keys=True)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
