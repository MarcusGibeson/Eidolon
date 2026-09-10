from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
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


def _worker_write(target: str, value: int, data_dir: str, queue) -> None:
    os.environ["EIDOLON_DATA_DIR"] = data_dir
    os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(Path(data_dir) / "locks")
    sys.path.insert(0, str(AGENT))
    from json_storage import write_json_atomic
    try:
        write_json_atomic(Path(target), {"writer": value}, expected_type=dict, coordination_timeout_seconds=5.0)
        queue.put({"ok": True, "value": value})
    except Exception as error:
        queue.put({"ok": False, "error": type(error).__name__})


def _worker_hold(target: str, data_dir: str, ready, release) -> None:
    os.environ["EIDOLON_DATA_DIR"] = data_dir
    os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(Path(data_dir) / "locks")
    sys.path.insert(0, str(AGENT))
    from metadata_mutation_coordination import metadata_mutation_lock
    with metadata_mutation_lock(Path(target), timeout_seconds=3.0):
        ready.set()
        release.wait(8.0)


def test_spawn_writers_share_one_cross_process_boundary() -> None:
    ctx = mp.get_context("spawn")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/"settings.json"; target.write_text('{"writer": -1}\n',encoding='utf-8')
        queue=ctx.Queue(); processes=[ctx.Process(target=_worker_write,args=(str(target),i,td,queue)) for i in range(6)]
        for p in processes: p.start()
        for p in processes: p.join(15); require(p.exitcode==0, f"writer failed: {p.exitcode}")
        results=[queue.get(timeout=2) for _ in processes]
        require(all(r["ok"] for r in results), "coordinated writer failed")
        value=json.loads(target.read_text(encoding='utf-8'))
        require(value.get("writer") in range(6), "final document malformed")
        require(not list(root.glob(".*.tmp")), "temporary files remained")
        require(not list((root/"locks").glob("*.lock")), "lock file remained")


def test_slow_live_owner_is_never_reclaimed_by_age() -> None:
    ctx=mp.get_context("spawn")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/"tasks.json"; target.write_text('{"version": 1}\n',encoding='utf-8')
        ready=ctx.Event(); release=ctx.Event(); holder=ctx.Process(target=_worker_hold,args=(str(target),td,ready,release)); holder.start()
        require(ready.wait(5), "holder did not acquire lock")
        os.environ["EIDOLON_METADATA_LOCK_DIR"]=str(root/"locks")
        from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
        start=time.monotonic()
        try:
            with metadata_mutation_lock(target,timeout_seconds=0.25):
                raise AssertionError("live owner was replaced")
        except MetadataMutationBusy as error:
            require(error.safe_retry and not error.uncertain_result, "busy result classification wrong")
        require(time.monotonic()-start >= 0.2, "lock did not wait bounded interval")
        require(holder.is_alive(), "slow owner was killed or treated as dead")
        release.set(); holder.join(5); require(holder.exitcode==0, "holder did not exit")


def test_dead_owner_is_reclaimed() -> None:
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/"settings.json"; target.write_text('{}\n',encoding='utf-8')
        os.environ["EIDOLON_METADATA_LOCK_DIR"]=str(root/"locks")
        from metadata_mutation_coordination import metadata_lock_path, metadata_mutation_lock
        lock=metadata_lock_path(target); lock.parent.mkdir(parents=True,exist_ok=True)
        lock.write_text(json.dumps({"pid":99999999,"owner_token":"a"*32,"target_digest":lock.stem})+'\n',encoding='utf-8')
        with metadata_mutation_lock(target,timeout_seconds=1.0) as state:
            require(state["reclaimed_dead_owner"], "dead owner not reclaimed")
        require(not lock.exists(), "reclaimed lock remained")


def test_preview_becomes_stale_after_other_process_save() -> None:
    ctx=mp.get_context("spawn")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/"settings.json"; target.write_bytes(b'\xef\xbb\xbf{"value": 1}')
        os.environ["EIDOLON_DATA_DIR"]=td; os.environ["EIDOLON_METADATA_LOCK_DIR"]=str(root/"locks")
        from metadata_migration import apply_metadata_migration, preview_metadata_migration
        preview=preview_metadata_migration("settings","settings.json",data_dir=root)
        queue=ctx.Queue(); p=ctx.Process(target=_worker_write,args=(str(target),2,td,queue)); p.start(); p.join(10); require(p.exitcode==0 and queue.get()["ok"],"competing save failed")
        result=apply_metadata_migration("settings","settings.json",preview_token=preview["preview_token"],operator_confirmed=True,data_dir=root)
        require(result["status"]=="stale_or_mismatched_preview", "concurrent save did not stale preview")


def test_migration_returns_safe_retry_while_live_save_owner_exists() -> None:
    ctx=mp.get_context("spawn")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/"settings.json"; target.write_bytes(b'\xef\xbb\xbf{"value": 1}')
        ready=ctx.Event(); release=ctx.Event(); holder=ctx.Process(target=_worker_hold,args=(str(target),td,ready,release)); holder.start(); require(ready.wait(5),"holder missing")
        os.environ["EIDOLON_DATA_DIR"]=td; os.environ["EIDOLON_METADATA_LOCK_DIR"]=str(root/"locks")
        from json_storage import apply_json_migration, preview_json_migration
        preview=preview_json_migration(target,expected_type=dict)
        result=apply_json_migration(target,preview_token=preview["preview_token"],operator_confirmed=True,expected_type=dict,backup_dir=root/"backups",coordination_timeout_seconds=0.2)
        require(result["status"]=="mutation_busy" and result["safe_retry"] and not result["uncertain_result"],"busy migration classification wrong")
        require(target.read_bytes().startswith(b'\xef\xbb\xbf'),"busy migration mutated target")
        release.set(); holder.join(5)


def test_lock_records_are_private_and_content_free() -> None:
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); target=root/"private"/"settings.json"; target.parent.mkdir(); target.write_text('{}\n')
        os.environ["EIDOLON_METADATA_LOCK_DIR"]=str(root/"locks")
        from metadata_mutation_coordination import metadata_lock_path, metadata_mutation_lock
        with metadata_mutation_lock(target):
            text=metadata_lock_path(target).read_text(encoding='utf-8')
            require(str(target) not in text and 'settings.json' not in text, "lock leaked path")
            value=json.loads(text); require(value["content_free"] and value["local_private"],"private lock contract missing")


def test_release_metadata_and_docs() -> None:
    release=(AGENT/"release_metadata.py").read_text(encoding='utf-8')
    import re
    match = re.search(r'RUNTIME_VERSION = "(\d+)\.(\d+)"', release)
    require(bool(match) and tuple(map(int, match.groups())) >= (1093, 4), "runtime version regressed")
    require("v1093.4" in (ROOT/"README_RELEASE_HISTORY.md").read_text(encoding='utf-8'),"history missing")
    require("Next bounded work" in (ROOT/"README.md").read_text(encoding='utf-8') or "Continue only with" in (ROOT/"README_NEXT_STEPS.md").read_text(encoding='utf-8'),"next bounded work missing")


def main() -> int:
    tests=[test_spawn_writers_share_one_cross_process_boundary,test_slow_live_owner_is_never_reclaimed_by_age,test_dead_owner_is_reclaimed,test_preview_becomes_stale_after_other_process_save,test_migration_returns_safe_retry_while_live_save_owner_exists,test_lock_records_are_private_and_content_free,test_release_metadata_and_docs]
    failures=[]; passed=0
    for test in tests:
        try: test(); passed+=1
        except Exception as error: failures.append(f"{test.__name__}: {type(error).__name__}: {error}")
    report={"version":"1093.4","suite":"cross-process-metadata-mutation-coordination","passed":passed,"total":len(tests),"ok":passed==len(tests),"failures":failures,"start_method":"spawn"}
    print(json.dumps(report,sort_keys=True)); return 0 if report["ok"] else 1
if __name__=="__main__": raise SystemExit(main())
