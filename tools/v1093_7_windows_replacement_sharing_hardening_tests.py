from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))


def require(condition: bool, message: str) -> None:
    if not condition: raise AssertionError(message)


def test_permission_sharing_retries_are_bounded() -> None:
    import json_storage
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; target.write_text('{"a":1}',encoding='utf-8')
        real=json_storage.os.replace; calls={'n':0}
        def flaky(src,dst):
            calls['n']+=1
            if calls['n']<3: raise PermissionError('sharing')
            return real(src,dst)
        json_storage.os.replace=flaky
        try: json_storage.write_json_atomic(target,{'a':2},expected_type=dict,replace_retries=4,retry_delay_seconds=0)
        finally: json_storage.os.replace=real
        require(calls['n']==3 and json.loads(target.read_text())['a']==2,'bounded sharing retry failed')


def test_error_after_visible_replace_is_verified_as_success() -> None:
    import json_storage
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; target.write_text('{"a":1}',encoding='utf-8')
        real=json_storage.os.replace; calls={'n':0}
        def after(src,dst):
            calls['n']+=1; real(src,dst); raise PermissionError('filter reported late')
        json_storage.os.replace=after
        try: json_storage.write_json_atomic(target,{'a':2},expected_type=dict,replace_retries=1)
        finally: json_storage.os.replace=real
        require(json.loads(target.read_text())['a']==2,'visible replacement treated as failure')


def test_corrupt_post_replace_result_restores_original() -> None:
    import json_storage
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; original=b'{"a":1}' ; target.write_bytes(original)
        real=json_storage.os.replace; calls={'n':0}
        def corrupt(src,dst):
            calls['n']+=1
            if calls['n']==1:
                Path(dst).write_bytes(b'corrupt'); Path(src).unlink(missing_ok=True); return
            return real(src,dst)
        json_storage.os.replace=corrupt
        try:
            try: json_storage.write_json_atomic(target,{'a':2},expected_type=dict,replace_retries=1)
            except json_storage.AtomicJsonWriteError as error:
                require(error.original_restored and not error.uncertain_result,'corrupt replacement not classified restored')
            else: raise AssertionError('corrupt replacement unexpectedly succeeded')
        finally: json_storage.os.replace=real
        require(target.read_bytes()==original,'prior valid target not restored')


def test_nonretryable_pre_replace_failure_preserves_original() -> None:
    import json_storage
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; original=b'{"a":1}'; target.write_bytes(original)
        real=json_storage.os.replace
        def denied(src,dst): raise OSError(22,'invalid')
        json_storage.os.replace=denied
        try:
            try: json_storage.write_json_atomic(target,{'a':2},expected_type=dict,replace_retries=5)
            except json_storage.AtomicJsonWriteError as error:
                require(error.status=='replace_blocked' and not error.safe_retry and not error.uncertain_result,'nonretryable failure misclassified')
            else: raise AssertionError('nonretryable failure succeeded')
        finally: json_storage.os.replace=real
        require(target.read_bytes()==original,'pre-replace failure changed target')


def test_windows_error_codes_are_the_only_extra_retry_class() -> None:
    import json_storage
    sharing=OSError('sharing'); sharing.winerror=32
    denied=OSError('denied'); denied.winerror=5
    unknown=OSError('unknown'); unknown.winerror=1234
    require(json_storage._replace_error_safe_to_retry(sharing),'winerror 32 not retryable')
    require(json_storage._replace_error_safe_to_retry(denied),'winerror 5 not retryable')
    require(not json_storage._replace_error_safe_to_retry(unknown),'unknown Windows error retried')


def _hold(target: str, lock_dir: str, ready, release) -> None:
    os.environ['EIDOLON_METADATA_LOCK_DIR']=lock_dir
    sys.path.insert(0,str(AGENT))
    from metadata_mutation_coordination import metadata_mutation_lock
    with metadata_mutation_lock(Path(target),timeout_seconds=2):
        ready.set(); release.wait(5)


def test_spawn_live_owner_returns_safe_busy() -> None:
    from json_storage import write_json_atomic
    from metadata_mutation_coordination import MetadataMutationBusy
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'; target.write_text('{"a":1}',encoding='utf-8')
        lock_dir=str(root/'locks'); os.environ['EIDOLON_METADATA_LOCK_DIR']=lock_dir
        ctx=mp.get_context('spawn'); ready=ctx.Event(); release=ctx.Event(); process=ctx.Process(target=_hold,args=(str(target),lock_dir,ready,release)); process.start()
        try:
            require(ready.wait(5),'spawn owner not ready')
            try: write_json_atomic(target,{'a':2},expected_type=dict,coordination_timeout_seconds=.1)
            except MetadataMutationBusy as error: require(error.safe_retry and not error.uncertain_result,'busy classification wrong')
            else: raise AssertionError('live owner was replaced')
        finally:
            release.set(); process.join(5)
            if process.is_alive(): process.kill(); process.join()
        require(json.loads(target.read_text())['a']==1,'busy writer changed target')


def test_directory_fsync_remains_optional() -> None:
    import json_storage
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/'settings.json'
        real_open=json_storage.os.open
        def optional(path,flags,*args):
            if Path(path)==target.parent and flags==json_storage.os.O_RDONLY: raise OSError('unsupported directory sync')
            return real_open(path,flags,*args)
        json_storage.os.open=optional
        try: json_storage.write_json_atomic(target,{'a':1},expected_type=dict)
        finally: json_storage.os.open=real_open
        require(json.loads(target.read_text())['a']==1,'optional directory sync blocked save')


def test_release_metadata_and_docs() -> None:
    import re
    release=(AGENT/'release_metadata.py').read_text(encoding='utf-8'); match=re.search(r'RUNTIME_VERSION = "(\d+)\.(\d+)"',release)
    require(bool(match) and tuple(map(int,match.groups())) >= (1093,7),'version regressed')
    require('v1093.7' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'),'history missing')
    require('v1093.8' in (ROOT/'README_NEXT_STEPS.md').read_text(encoding='utf-8'),'next missing')


def main() -> int:
    tests=[test_permission_sharing_retries_are_bounded,test_error_after_visible_replace_is_verified_as_success,test_corrupt_post_replace_result_restores_original,test_nonretryable_pre_replace_failure_preserves_original,test_windows_error_codes_are_the_only_extra_retry_class,test_spawn_live_owner_returns_safe_busy,test_directory_fsync_remains_optional,test_release_metadata_and_docs]
    failures=[];passed=0
    for test in tests:
        try:test();passed+=1
        except Exception as error:failures.append(f'{test.__name__}: {type(error).__name__}: {error}')
    report={'version':'1093.7','suite':'windows-replacement-sharing-hardening','passed':passed,'total':len(tests),'ok':passed==len(tests),'failures':failures}
    print(json.dumps(report,sort_keys=True));return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
