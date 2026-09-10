from __future__ import annotations
"""v1344 structured data/schema implementation over Phase 4 candidate execution.

JSON, YAML, TOML, and SQL source is parsed before and after a candidate-only
change. Compatibility evidence is content-minimized: field/table/column names
are reduced to counts and digests and are never persisted in public receipts.
SQL validation uses only an in-memory SQLite database after rejecting statements
that can address external files or change SQLite runtime configuration.
"""
import hashlib
import json
import re
import sqlite3
import time
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from workspace_isolation import create_disposable_workspace, cleanup_disposable_workspace
from structured_file_operations import read_candidate_file, patch_candidate_file
from typed_git_operations import stage_owned_changes, commit_owned_changes
from typed_process_operations import start_candidate_process, monitor_candidate_process
from tool_result_reconciliation import reconcile_tool_result

CONTRACT_VERSION = "v1344.8"
SUFFIXES = (".json", ".yaml", ".yml", ".toml", ".sql")
MAX_ANALYSIS_BYTES = 2 * 1024 * 1024
MAX_SHAPE_ENTRIES = 4096
MAX_PROCESS_WAIT_SECONDS = 45.0
REQUIRED_PRECONDITIONS = ("git", "file_read", "file_patch", "shell")
TERMINAL_PROCESS_STATES = {"completed", "failed", "cancelled", "interrupted", "uncertain"}
DATA_SCHEMA_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "source_mutation_authorized": False,
    "source_application_authorized": False,
    "dependency_installation_authorized": False,
    "database_mutation_authorized": False,
    "migration_application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "network_authorized": False,
    "independent_authority_granted": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase5_data_schema_implementation"


def _path(operation_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"dsimpl_[a-f0-9]{24}", str(operation_id or "")):
        raise ValueError("invalid_data_schema_implementation_id")
    return _root(runtime_root) / "records" / f"{operation_id}.json"


def _load(operation_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path(operation_id, runtime_root))
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    return row


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row.pop("record_digest", None)
    row["record_digest"] = digest(row)
    _atomic_json(_path(str(row["data_schema_implementation_id"]), runtime_root), row)
    return row


def _safe_relative(value: str) -> str:
    text = str(value or "").replace("\\", "/").strip()
    pure = PurePosixPath(text)
    if not text or pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("unsafe_data_schema_relative_path")
    if pure.suffix.lower() not in SUFFIXES:
        raise ValueError("structured_data_source_required")
    if any(part.casefold() in {".git", "data", "runtime", "private", "secrets", "credentials", "node_modules", ".venv", "venv", "__pycache__"} for part in pure.parts):
        raise ValueError("protected_data_schema_path")
    return pure.as_posix()


def _kind(value: Any) -> str:
    if value is None: return "null"
    if isinstance(value, bool): return "bool"
    if isinstance(value, int): return "int"
    if isinstance(value, float): return "float"
    if isinstance(value, str): return "str"
    if isinstance(value, dict): return "object"
    if isinstance(value, list): return "array"
    return type(value).__name__


def _shape(value: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    def walk(node: Any, path: str, depth: int) -> None:
        if len(out) >= MAX_SHAPE_ENTRIES:
            raise ValueError("structured_shape_budget_exceeded")
        out[path or "/"] = _kind(node)
        if depth >= 12:
            return
        if isinstance(node, dict):
            for key in sorted(node, key=lambda x: str(x)):
                token = hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:16]
                walk(node[key], f"{path}/{token}", depth + 1)
        elif isinstance(node, list):
            kinds = sorted({_kind(item) for item in node})
            out[f"{path}/[]"] = "|".join(kinds) if kinds else "empty"
            # Sample structural members, bounded and position-independent.
            for item in node[:16]:
                if isinstance(item, (dict, list)):
                    walk(item, f"{path}/[]/{hashlib.sha256(_kind(item).encode()).hexdigest()[:8]}", depth + 1)
    walk(value, "", 0)
    return out


def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise ValueError("yaml_parser_unavailable") from exc
    try:
        return yaml.safe_load(text)
    except Exception as exc:
        raise ValueError("yaml_syntax_invalid") from exc


def _structured_facts(suffix: str, text: str) -> dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_ANALYSIS_BYTES:
        raise ValueError("structured_analysis_budget_exceeded")
    try:
        if suffix == ".json": value = json.loads(text); parser = "json_stdlib"
        elif suffix in {".yaml", ".yml"}: value = _load_yaml(text); parser = "yaml_safe_load"
        elif suffix == ".toml": value = tomllib.loads(text); parser = "tomllib_stdlib"
        else: raise ValueError("structured_format_required")
    except ValueError:
        raise
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("structured_syntax_invalid") from exc
    shape = _shape(value)
    return {
        "format": suffix.lstrip("."),
        "parser": parser,
        "syntax_valid": True,
        "shape_entry_count": len(shape),
        "shape_digest": digest(sorted(shape.items())),
        "shape": shape,
        "document_digest": hashlib.sha256(text.encode()).hexdigest(),
    }


def _sql_facts(text: str) -> dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_ANALYSIS_BYTES:
        raise ValueError("structured_analysis_budget_exceeded")
    # SQLite schema introspection must never gain filesystem or extension reach.
    forbidden = re.findall(r"\b(?:ATTACH|DETACH|VACUUM|PRAGMA|LOAD_EXTENSION)\b", text, flags=re.I)
    if forbidden:
        raise ValueError("unsafe_sql_schema_construct")
    allowed_prefixes = ("CREATE TABLE", "CREATE UNIQUE INDEX", "CREATE INDEX", "ALTER TABLE", "DROP TABLE", "DROP INDEX")
    statements = [part.strip() for part in text.split(";") if part.strip()]
    for statement in statements:
        normalized = re.sub(r"\s+", " ", statement).strip().upper()
        if not normalized.startswith(allowed_prefixes):
            raise ValueError("sql_schema_statement_not_allowed")
    db = sqlite3.connect(":memory:")
    try:
        db.executescript(text)
        table_rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        index_rows = db.execute("SELECT name,tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        tables: dict[str, dict[str, str]] = {}
        for (name,) in table_rows:
            cols = db.execute(f'PRAGMA table_info("{str(name).replace(chr(34), chr(34)*2)}")').fetchall()
            tables[str(name)] = {str(row[1]): str(row[2] or "").upper() for row in cols}
        indexes = {str(name): str(tbl) for name, tbl in index_rows}
    except sqlite3.DatabaseError as exc:
        raise ValueError("sql_schema_invalid") from exc
    finally:
        db.close()
    destructive = len(re.findall(r"\bDROP\s+(?:TABLE|INDEX|COLUMN)\b", text, flags=re.I))
    table_shape = {hashlib.sha256(k.encode()).hexdigest()[:16]: {hashlib.sha256(c.encode()).hexdigest()[:16]: t for c, t in sorted(v.items())} for k, v in sorted(tables.items())}
    index_shape = {hashlib.sha256(k.encode()).hexdigest()[:16]: hashlib.sha256(v.encode()).hexdigest()[:16] for k, v in sorted(indexes.items())}
    return {
        "format": "sql", "parser": "sqlite_memory_schema", "syntax_valid": True,
        "table_count": len(tables), "index_count": len(indexes), "destructive_statement_count": destructive,
        "table_shape": table_shape, "index_shape": index_shape,
        "shape_digest": digest({"tables": table_shape, "indexes": index_shape}),
        "document_digest": hashlib.sha256(text.encode()).hexdigest(),
    }


def _facts(relative_path: str, text: str) -> dict[str, Any]:
    suffix = PurePosixPath(relative_path).suffix.lower()
    return _sql_facts(text) if suffix == ".sql" else _structured_facts(suffix, text)


def _compatibility(relative_path: str, before: Mapping[str, Any], after: Mapping[str, Any], *, allow_breaking_schema_change: bool, allow_index_removal: bool, migration_change_declared: bool) -> dict[str, Any]:
    reasons: list[str] = []
    removed = changed_types = removed_indexes = 0
    migration_like = any("migration" in part.casefold() for part in PurePosixPath(relative_path).parts)
    if migration_like and before.get("document_digest") != after.get("document_digest") and not migration_change_declared:
        reasons.append("undeclared_migration_change")
    if before.get("format") == "sql":
        bt = dict(before.get("table_shape") or {}); at = dict(after.get("table_shape") or {})
        for table, cols in bt.items():
            if table not in at:
                removed += 1 + len(cols); continue
            acols = at[table]
            removed += len(set(cols) - set(acols))
            changed_types += sum(1 for col in set(cols) & set(acols) if cols[col] != acols[col])
        bi = set((before.get("index_shape") or {}).keys()); ai = set((after.get("index_shape") or {}).keys())
        removed_indexes = len(bi - ai)
        if (removed or changed_types) and not allow_breaking_schema_change:
            reasons.append("breaking_schema_change")
        if removed_indexes and not allow_index_removal:
            reasons.append("index_compatibility_regression")
    else:
        bs = dict(before.get("shape") or {}); a = dict(after.get("shape") or {})
        removed = len(set(bs) - set(a))
        changed_types = sum(1 for path in set(bs) & set(a) if bs[path] != a[path])
        if (removed or changed_types) and not allow_breaking_schema_change:
            reasons.append("breaking_schema_change")
    return {
        "compatible": not reasons, "reasons": reasons, "migration_like": migration_like,
        "removed_schema_entry_count": removed, "changed_type_count": changed_types,
        "removed_index_count": removed_indexes,
        "destructive_statement_delta": int(after.get("destructive_statement_count") or 0) - int(before.get("destructive_statement_count") or 0),
    }


def inspect_data_schema_project(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).resolve(strict=True)
    counts = {"json": 0, "yaml": 0, "toml": 0, "sql": 0}; invalid = migration = indexes = 0; files: list[Path] = []
    yaml_available = True
    try: import yaml  # type: ignore  # noqa: F401
    except Exception: yaml_available = False
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in SUFFIXES: continue
        rel = p.relative_to(root)
        if any(x in {".git", "data", "runtime", "private", "node_modules", "__pycache__"} for x in rel.parts): continue
        if p.stat().st_size > MAX_ANALYSIS_BYTES: continue
        files.append(p); key = "yaml" if p.suffix.lower() in {".yaml", ".yml"} else p.suffix.lower().lstrip("."); counts[key] += 1
        migration += int(any("migration" in x.casefold() for x in rel.parts))
        try:
            f = _facts(rel.as_posix(), p.read_text(encoding="utf-8")); indexes += int(f.get("index_count") or 0)
        except (OSError, UnicodeDecodeError, ValueError): invalid += 1
    out = {
        "contract_version": CONTRACT_VERSION, **{f"{k}_file_count": v for k, v in counts.items()},
        "migration_file_count": migration, "sql_index_count": indexes, "invalid_or_unsupported_file_count": invalid,
        "yaml_parser_available": yaml_available,
        "source_manifest_digest": digest([(p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),
        "inspection_only": True, "network_contacted": False, "database_contacted": False, **DATA_SCHEMA_DENIED_AUTHORITY,
    }
    out["inspection_digest"] = digest(out)
    return out


def _wait_process(process_id: str, *, workspace_digest: str, runtime_root=None) -> tuple[bool, dict[str, Any], str]:
    deadline = time.monotonic() + MAX_PROCESS_WAIT_SECONDS; observed: dict[str, Any] = {}
    while time.monotonic() < deadline:
        observed = monitor_candidate_process(process_id, runtime_root=runtime_root)
        state = (observed.get("process_operation") or {}).get("process_state")
        if state in TERMINAL_PROCESS_STATES: break
        time.sleep(0.05)
    proc = observed.get("process_operation") or {}
    passed = proc.get("process_state") == "completed" and proc.get("return_code") == 0 and not proc.get("timed_out") and not proc.get("log_limit_exceeded")
    recon = reconcile_tool_result(tool_code="shell", operation_id=process_id, wrapper_observation={"wrapper_status":"returned","reported_status":proc.get("process_state")}, current_workspace_digest=workspace_digest, runtime_root=runtime_root)
    return passed, proc, str((recon.get("reconciliation") or {}).get("reconciliation_id") or "")


def run_data_schema_implementation(*, source_root: str | Path, source_workspace_digest: str, active_grant: Mapping[str, Any], precondition_record_ids: Mapping[str, str], relative_path: str, expected_content_digest: str, patches: Sequence[Mapping[str, Any]], test_argv: Sequence[str], commit_message: str = "Update structured data schema", allow_breaking_schema_change: bool = False, allow_index_removal: bool = False, migration_change_declared: bool = False, runtime_root=None, now_unix: int | None = None, git_executable: str | None = None, cleanup_on_complete: bool = True) -> dict[str, Any]:
    try: rel = _safe_relative(relative_path)
    except ValueError as exc: return {"ok":False,"status":str(exc),"action_executed":False,**DATA_SCHEMA_DENIED_AUTHORITY}
    pres = {str(k):str(v) for k,v in precondition_record_ids.items()}
    if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):
        return {"ok":False,"status":"complete_data_schema_preconditions_required","action_executed":False,**DATA_SCHEMA_DENIED_AUTHORITY}
    spec = {"contract":CONTRACT_VERSION,"source":source_workspace_digest,"grant":active_grant.get("grant_digest"),"preconditions":pres,"path":hashlib.sha256(rel.encode()).hexdigest(),"expected":expected_content_digest,"patches":digest(patches),"tests":digest(list(test_argv)),"commit":hashlib.sha256(commit_message.encode()).hexdigest(),"flags":[allow_breaking_schema_change,allow_index_removal,migration_change_declared],"cleanup":cleanup_on_complete}
    op = "dsimpl_" + digest(spec)[:24]; existing = _load(op, runtime_root)
    if existing: return {"ok":existing.get("implementation_state")=="completed","status":"data_schema_implementation_already_exists","data_schema_implementation":public_data_schema_implementation(existing),"action_executed":False,**DATA_SCHEMA_DENIED_AUTHORITY}
    row = {"contract_version":CONTRACT_VERSION,"data_schema_implementation_id":op,"source_workspace_digest":source_workspace_digest,"implementation_state":"starting","failure_stage":"","workspace_id":"","file_operation_id":"","test_process_id":"","test_reconciliation_id":"","git_stage_operation_id":"","git_commit_operation_id":"","format":PurePosixPath(rel).suffix.lower().lstrip('.'),"compatibility_passed":False,"migration_like":any('migration' in x.casefold() for x in PurePosixPath(rel).parts),"workspace_cleaned":False,"host_recoverable":False,"action_executed":False,**DATA_SCHEMA_DENIED_AUTHORITY}; _save(row,runtime_root)
    wid = ""
    try:
        iso = create_disposable_workspace(source_root=source_root,source_workspace_digest=source_workspace_digest,active_grant=active_grant,precondition_record_id=pres["git"],mode="git_branch_worktree",retention_rule="retain_for_review",runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
        if not iso.get("ok") or not iso.get("workspace_created"): raise RuntimeError("workspace_isolation")
        wid = str(iso["workspace_id"]); row["workspace_id"] = wid; row["action_executed"] = True; _save(row,runtime_root)
        before_read = read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres["file_read"],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
        if not before_read.get("ok"): raise RuntimeError("data_schema_read_before")
        before_text = str(before_read.get("content") or ""); before = _facts(rel,before_text)
        if before.get("document_digest") != expected_content_digest: raise RuntimeError("stale_data_schema_content_digest")
        patched = patch_candidate_file(wid,rel,expected_content_digest=expected_content_digest,patches=patches,active_grant=active_grant,precondition_record_id=pres["file_patch"],runtime_root=runtime_root,now_unix=now_unix)
        if not patched.get("ok"): raise RuntimeError(str(patched.get("status") or "data_schema_patch_failed"))
        row["file_operation_id"] = str((patched.get("file_operation") or {}).get("operation_id") or ""); _save(row,runtime_root)
        after_read = read_candidate_file(wid,rel,active_grant=active_grant,precondition_record_id=pres["file_read"],runtime_root=runtime_root,now_unix=now_unix,include_content=True)
        if not after_read.get("ok"): raise RuntimeError("data_schema_read_after")
        try: after = _facts(rel,str(after_read.get("content") or ""))
        except ValueError as exc: raise RuntimeError(str(exc)) from exc
        comp = _compatibility(rel,before,after,allow_breaking_schema_change=allow_breaking_schema_change,allow_index_removal=allow_index_removal,migration_change_declared=migration_change_declared)
        row["compatibility_passed"] = bool(comp["compatible"]); row["compatibility_digest"] = digest(comp); _save(row,runtime_root)
        if not comp["compatible"]: raise RuntimeError(str(comp["reasons"][0]))
        start = start_candidate_process(wid,argv=list(test_argv),active_grant=active_grant,precondition_record_id=pres["shell"],runtime_root=runtime_root,now_unix=now_unix,timeout_seconds=30,max_log_bytes=256*1024,invocation_discriminator=f"v1344:{op}:tests")
        if not start.get("ok"): raise RuntimeError("data_schema_test_start_failed")
        pid = str((start.get("process_operation") or {}).get("process_operation_id") or ""); row["test_process_id"] = pid; _save(row,runtime_root)
        passed, _proc, recon = _wait_process(pid,workspace_digest=source_workspace_digest,runtime_root=runtime_root); row["test_reconciliation_id"] = recon; _save(row,runtime_root)
        if not passed: raise RuntimeError("data_schema_tests_failed")
        staged = stage_owned_changes(wid,owned_file_operation_ids=[row["file_operation_id"]],active_grant=active_grant,precondition_record_id=pres["git"],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
        if not staged.get("ok"): raise RuntimeError("data_schema_git_stage")
        row["git_stage_operation_id"] = str((staged.get("git_operation") or {}).get("operation_id") or ""); _save(row,runtime_root)
        committed = commit_owned_changes(wid,stage_operation_id=row["git_stage_operation_id"],commit_message=commit_message,active_grant=active_grant,precondition_record_id=pres["git"],runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable)
        if not committed.get("ok"): raise RuntimeError("data_schema_git_commit")
        row["git_commit_operation_id"] = str((committed.get("git_operation") or {}).get("operation_id") or ""); row["implementation_state"] = "verified_candidate"; _save(row,runtime_root)
    except Exception as exc:
        row["implementation_state"] = "failed"; row["failure_stage"] = str(exc); _save(row,runtime_root)
    finally:
        if wid and cleanup_on_complete:
            try: row["workspace_cleaned"] = cleanup_disposable_workspace(wid,active_grant=active_grant,discard_owned_changes=True,runtime_root=runtime_root,now_unix=now_unix,git_executable=git_executable).get("cleaned") is True
            except Exception: row["workspace_cleaned"] = False
        row["host_recoverable"] = bool(not cleanup_on_complete or row["workspace_cleaned"])
        if row["implementation_state"] == "verified_candidate" and row["host_recoverable"]: row["implementation_state"] = "completed"
        _save(row,runtime_root)
    ok = row["implementation_state"] == "completed"
    return {"ok":ok,"status":"data_schema_implementation_completed" if ok else "data_schema_implementation_failed","data_schema_implementation":public_data_schema_implementation(row),"action_executed":row["action_executed"] is True,**DATA_SCHEMA_DENIED_AUTHORITY}


def public_data_schema_implementation(row: Mapping[str, Any]) -> dict[str, Any]:
    if not row: return {}
    return {"contract_version":CONTRACT_VERSION,"data_schema_implementation_id":row.get("data_schema_implementation_id"),"source_workspace_digest":row.get("source_workspace_digest"),"implementation_state":row.get("implementation_state"),"failure_stage":row.get("failure_stage") or "","workspace_id":row.get("workspace_id") or "","file_operation_id":row.get("file_operation_id") or "","test_process_id":row.get("test_process_id") or "","test_reconciliation_id":row.get("test_reconciliation_id") or "","git_stage_operation_id":row.get("git_stage_operation_id") or "","git_commit_operation_id":row.get("git_commit_operation_id") or "","format":row.get("format") or "","compatibility_passed":row.get("compatibility_passed") is True,"migration_like":row.get("migration_like") is True,"workspace_cleaned":row.get("workspace_cleaned") is True,"host_recoverable":row.get("host_recoverable") is True,"candidate_only":True,"selected_source_content_modified":False,"raw_schema_content_exposed":False,"schema_identifiers_exposed":False,"database_contacted":False,"network_contacted":False,"action_executed":row.get("action_executed") is True,**DATA_SCHEMA_DENIED_AUTHORITY}


def load_data_schema_implementation(operation_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _load(operation_id,runtime_root); return public_data_schema_implementation(row) if row else {}


def process_data_schema_implementation_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show data schema implementation","inspect data schema implementation","show data schema checkpoint"}: return {"active":False}
    op = str((project_state or {}).get("data_schema_implementation_id") or ""); row = load_data_schema_implementation(op,runtime_root=runtime_root) if op else {}
    return {"active":True,"ok":bool(row),"status":"data_schema_implementation_found" if row else "data_schema_implementation_missing","data_schema_implementation":row,"action_executed":False,**DATA_SCHEMA_DENIED_AUTHORITY}


__all__ = ["CONTRACT_VERSION","REQUIRED_PRECONDITIONS","DATA_SCHEMA_DENIED_AUTHORITY","inspect_data_schema_project","run_data_schema_implementation","public_data_schema_implementation","load_data_schema_implementation","process_data_schema_implementation_control"]
