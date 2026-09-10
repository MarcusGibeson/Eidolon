from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from hermetic_verification_runtime import (  # noqa: E402
    AUTHORITY_FLAGS,
    CONTRACT_VERSION,
    IGNORED_DIRECTORY_NAMES,
    IGNORED_FILE_SUFFIXES,
    atomic_write_json,
    build_hermetic_environment,
    copy_clean_source_snapshot,
    hermetic_runtime_contract,
    run_bounded_command,
    scan_forbidden_runtime_entries,
    source_signature,
    validate_external_path,
)

checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


contract = hermetic_runtime_contract()
require(contract["ok"] is True)
require(contract["contract_version"] == CONTRACT_VERSION == "v1250.2")
require(contract["bytecode_disabled"] is True)
require(contract["clean_external_snapshot_required"] is True)
require(contract["runtime_paths_external_to_source_required"] is True)
require(contract["shell_execution_forbidden"] is True)
require(contract["bounded_process_group_timeout"] is True)
require(contract["partial_receipts_external_to_source_required"] is True)
require(contract["source_immutability_required"] is True)
require(contract["repository_size_thresholds_used"] is False)
require("data" in contract["ignored_directory_names"])
require("__pycache__" in contract["ignored_directory_names"])
require(".pyc" in contract["ignored_file_suffixes"])
require(len(contract["contract_digest"]) == 64)

with tempfile.TemporaryDirectory(prefix="eidolon-v1250-2-fixture-") as temp_text:
    temp = Path(temp_text)
    source = temp / "source"
    source.mkdir()
    (source / "pkg").mkdir()
    (source / "pkg" / "demo.py").write_text("VALUE = 7\n", encoding="utf-8")
    (source / "runner.py").write_text(
        "import json\nfrom pkg.demo import VALUE\nprint(json.dumps({'ok': VALUE == 7, 'value': VALUE}))\n",
        encoding="utf-8",
    )
    (source / "slow.py").write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    (source / "fail.py").write_text("import sys\nprint('{\"ok\": false}')\nsys.exit(3)\n", encoding="utf-8")
    (source / "data").mkdir()
    (source / "data" / "private.json").write_text('{"secret":"not copied"}', encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "junk.pyc").write_bytes(b"junk")
    (source / ".git").mkdir()
    (source / ".git" / "config").write_text("git", encoding="utf-8")
    (source / "loose.pyc").write_bytes(b"junk")

    before = source_signature(source)
    again = source_signature(source)
    require(before == again)
    require(before["file_count"] == 4)
    require(before["byte_count"] > 0)
    require(len(before["tree_digest"]) == 64)
    require(validate_external_path(temp / "receipt.json", source_root=source)["ok"] is True)
    require(validate_external_path(source / "receipt.json", source_root=source)["ok"] is False)

    runtime = temp / "runtime"
    snapshot = temp / "snapshot"
    receipt = copy_clean_source_snapshot(source_root=source, snapshot_root=snapshot)
    require(receipt["ok"] is True)
    require(receipt["contract_version"] == "v1250.2")
    require(receipt["snapshot_external_to_source"] is True)
    require(receipt["read_only_authoritative_source"] is True)
    require(receipt["copied_file_count"] == 4)
    require((snapshot / "runner.py").is_file())
    require((snapshot / "pkg/demo.py").is_file())
    require(not (snapshot / "data").exists())
    require(not (snapshot / "__pycache__").exists())
    require(not (snapshot / ".git").exists())
    require(not (snapshot / "loose.pyc").exists())
    require(receipt["source_signature"] == before)
    require(receipt["snapshot_signature"] == source_signature(snapshot))
    require(len(receipt["snapshot_receipt_digest"]) == 64)

    env = build_hermetic_environment(runtime_root=runtime, source_root=source, base_env={"PATH": os.environ.get("PATH", "")})
    require(env["PYTHONDONTWRITEBYTECODE"] == "1")
    require(env["EIDOLON_VERIFICATION_HERMETIC"] == "1")
    require(Path(env["EIDOLON_DATA_DIR"]).is_relative_to(runtime.resolve()))
    require(Path(env["PYTHONPYCACHEPREFIX"]).is_relative_to(runtime.resolve()))
    require(Path(env["TMPDIR"]).is_relative_to(runtime.resolve()))
    require(not Path(env["EIDOLON_DATA_DIR"]).is_relative_to(source.resolve()))
    env["PYTHONPATH"] = str(snapshot)

    command = run_bounded_command(
        [sys.executable, "runner.py"],
        cwd=snapshot,
        env=env,
        timeout_seconds=5,
    )
    require(command.ok is True)
    require(command.status == "passed")
    require(command.returncode == 0)
    require(command.timed_out is False)
    require(command.stdout_byte_count > 0)
    require(command.stderr_byte_count == 0)
    require(command.parsed_json == {"ok": True, "value": 7})
    require(len(command.stdout_sha256) == 64)
    require(len(command.stderr_sha256) == 64)
    require(len(command.command_digest) == 64)
    require(command.process_group_terminated is False)
    require(scan_forbidden_runtime_entries(snapshot)["ok"] is True)
    require(not any(path.name == "__pycache__" for path in snapshot.rglob("*")))
    require(source_signature(source) == before)

    failed = run_bounded_command(
        [sys.executable, "fail.py"],
        cwd=snapshot,
        env=env,
        timeout_seconds=5,
    )
    require(failed.ok is False)
    require(failed.status == "failed")
    require(failed.returncode == 3)
    require(failed.parsed_json == {"ok": False})

    timed = run_bounded_command(
        [sys.executable, "slow.py"],
        cwd=snapshot,
        env=env,
        timeout_seconds=0.25,
    )
    require(timed.ok is False)
    require(timed.status == "timeout")
    require(timed.timed_out is True)
    require(timed.process_group_terminated is True)
    require(timed.elapsed_seconds < 3)

    payload = {"ok": True, "contract_version": "v1250.2", "release_authorized": False}
    outside_receipt = temp / "receipts" / "verification.json"
    written = atomic_write_json(outside_receipt, payload, source_root=source)
    require(written["ok"] is True)
    require(written["status"] == "receipt_written")
    require(outside_receipt.is_file())
    require(json.loads(outside_receipt.read_text(encoding="utf-8")) == payload)
    require(len(written["receipt_sha256"]) == 64)
    require(written["receipt_byte_count"] == outside_receipt.stat().st_size)

    blocked = atomic_write_json(source / "receipt.json", payload, source_root=source)
    require(blocked["ok"] is False)
    require(blocked["status"] == "receipt_path_inside_source_blocked")
    require(not (source / "receipt.json").exists())

    debris = temp / "debris"
    (debris / "data").mkdir(parents=True)
    (debris / "__pycache__").mkdir()
    (debris / "__pycache__" / "x.pyc").write_bytes(b"x")
    debris_report = scan_forbidden_runtime_entries(debris)
    require(debris_report["ok"] is False)
    require(debris_report["status"] == "runtime_debris_detected")
    require(debris_report["forbidden_entry_count"] == 3)
    require({row["reason"] for row in debris_report["forbidden_entries"]} == {"forbidden_runtime_directory", "forbidden_bytecode_file"})
    require(all(len(row["relative_path_digest"]) == 64 for row in debris_report["forbidden_entries"]))

    (source / "pkg/demo.py").write_text("VALUE = 8\n", encoding="utf-8")
    changed = source_signature(source)
    require(changed["tree_digest"] != before["tree_digest"])
    require(changed["file_count"] == before["file_count"])

    try:
        build_hermetic_environment(runtime_root=source / "runtime", source_root=source)
    except ValueError as exc:
        require(str(exc) == "runtime_root_must_be_outside_source")
    else:
        require(False)

    try:
        copy_clean_source_snapshot(source_root=source, snapshot_root=source / "snapshot")
    except ValueError as exc:
        require(str(exc) == "snapshot_root_must_be_outside_source")
    else:
        require(False)

    try:
        run_bounded_command([], cwd=snapshot, env=env, timeout_seconds=1)
    except ValueError as exc:
        require(str(exc) == "command_must_be_nonempty_string_sequence")
    else:
        require(False)

    try:
        run_bounded_command([sys.executable, "runner.py"], cwd=snapshot, env=env, timeout_seconds=0)
    except ValueError as exc:
        require(str(exc) == "timeout_seconds_must_be_positive")
    else:
        require(False)

module_text = (ROOT / "conscious_agent/hermetic_verification_runtime.py").read_text(encoding="utf-8")
require("shell=False" in module_text)
require("os.killpg" in module_text)
require("taskkill" in module_text)
require("PYTHONDONTWRITEBYTECODE" in module_text)
require("repository_size_thresholds_used" in module_text)
require("source_file_count >" not in module_text)
require("python_file_count >" not in module_text)

for key, expected in AUTHORITY_FLAGS.items():
    require(contract.get(key) is expected)

result = {
    "suite": "v1250.2-hermetic-verification-runtime",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
