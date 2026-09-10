from __future__ import annotations
"""Bounded browser-document and JavaScript validation for isolated workspaces.

v1201.6-v1201.8 executes only allowlisted validation adapters against the exact
external workspace revision. It grants no apply, source, model, provider, or
release authority and exposes no filenames, paths, source, stdout, or stderr.
"""
import hashlib
import os
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_implementation_workspace import _record_path, _workspace_root, _verify_record
from isolated_workspace_preview import _preview_path
from structured_development_generation import _safe_relative

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1201.8"
MAX_HTML_BYTES = 1024 * 1024
MAX_JS_FILE_BYTES = 512 * 1024
MAX_JS_FILES = 24
MAX_JS_TOTAL_BYTES = 2 * 1024 * 1024
COMMAND_TIMEOUT_SECONDS = 8


class _BrowserFacts(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tag_count = 0
        self.has_title = False
        self.has_viewport = False
        self.ids: list[str] = []
        self.assets: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_count += 1
        values = dict(attrs)
        if tag == "title":
            self.has_title = True
        if tag == "meta" and str(values.get("name") or "").lower() == "viewport":
            self.has_viewport = True
        if values.get("id"):
            self.ids.append(str(values["id"]))
        value = values.get("src") if tag in {"script", "img"} else values.get("href") if tag == "link" else None
        if value and not str(value).startswith(("http:", "https:", "//", "data:", "#")):
            clean = str(value).split("?", 1)[0].split("#", 1)[0]
            self.assets.append(clean)
            if tag == "script":
                self.scripts.append(clean)


def _validation_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "validation" / pid / f"revision-{int(rev)}.json"


def _load_bound_records(pid: str, rev: int, runtime_root=None):
    workspace = _read_json(_record_path(pid, rev, runtime_root))
    preview = _read_json(_preview_path(pid, rev, runtime_root))
    if not workspace:
        return None, None, None
    root = _workspace_root(pid, rev, str(workspace.get("generation_digest") or ""), runtime_root)
    return workspace, preview, root


def _record_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("validation_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "validation_digest"}))


def _diagnostic_digest(*parts: str) -> str:
    text = "\n".join(str(part or "")[:4096] for part in parts)
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _browser_adapter(root: Path, workspace: Mapping[str, Any], preview: Mapping[str, Any] | None) -> dict[str, Any]:
    names = {str(row.get("relative_path") or "") for row in workspace.get("files") or []}
    entry = str((preview or {}).get("entrypoint") or "")
    if not entry:
        entry = next((name for name in ("index.html", "index.htm") if name in names), "")
    if not entry:
        return {"adapter": "browser_document", "status": "not_applicable", "passed": True, "reason_code": "html_entrypoint_not_planned"}
    try:
        entry_rel = _safe_relative(entry)
    except ValueError:
        return {"adapter": "browser_document", "status": "failed", "passed": False, "reason_code": "entrypoint_path_rejected"}
    path = root / entry_rel
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_HTML_BYTES:
        return {"adapter": "browser_document", "status": "failed", "passed": False, "reason_code": "entrypoint_unavailable_or_oversized"}
    try:
        text = path.read_text(encoding="utf-8")
        parser = _BrowserFacts()
        parser.feed(text)
        parser.close()
    except (UnicodeError, OSError, ValueError) as error:
        return {"adapter": "browser_document", "status": "failed", "passed": False, "reason_code": "html_parse_failed", "diagnostic_digest": _diagnostic_digest(type(error).__name__)}
    missing: list[str] = []
    rejected: list[str] = []
    for asset in parser.assets:
        try:
            rel = _safe_relative(unquote(asset))
        except ValueError:
            rejected.append(hashlib.sha256(asset.encode()).hexdigest())
            continue
        target = root / rel
        try:
            resolved = target.resolve(strict=True)
        except OSError:
            missing.append(hashlib.sha256(rel.encode()).hexdigest())
            continue
        if root.resolve() not in resolved.parents or resolved.is_symlink() or not resolved.is_file():
            rejected.append(hashlib.sha256(rel.encode()).hexdigest())
    duplicate_ids = len(parser.ids) - len(set(parser.ids))
    failures = int(not parser.has_title) + int(not parser.has_viewport) + len(missing) + len(rejected) + duplicate_ids
    return {
        "adapter": "browser_document",
        "status": "passed" if failures == 0 else "failed",
        "passed": failures == 0,
        "entrypoint_digest": hashlib.sha256(entry.encode()).hexdigest(),
        "tag_count": parser.tag_count,
        "asset_count": len(parser.assets),
        "script_reference_count": len(parser.scripts),
        "missing_asset_count": len(missing),
        "missing_asset_digests": sorted(missing),
        "rejected_asset_count": len(rejected),
        "rejected_asset_digests": sorted(rejected),
        "duplicate_id_count": duplicate_ids,
        "has_title": parser.has_title,
        "has_viewport": parser.has_viewport,
    }


def _javascript_adapter(root: Path, workspace: Mapping[str, Any], *, node_executable: str | None = None) -> dict[str, Any]:
    rows = [row for row in workspace.get("files") or [] if Path(str(row.get("relative_path") or "")).suffix.lower() in {".js", ".mjs", ".cjs"}]
    if not rows:
        return {"adapter": "javascript_syntax", "status": "not_applicable", "passed": True, "file_count": 0, "command_count": 0}
    if len(rows) > MAX_JS_FILES or sum(int(row.get("size_bytes") or 0) for row in rows) > MAX_JS_TOTAL_BYTES:
        return {"adapter": "javascript_syntax", "status": "failed", "passed": False, "reason_code": "javascript_budget_exceeded", "file_count": len(rows), "command_count": 0}
    node = node_executable or shutil.which("node")
    if not node:
        return {"adapter": "javascript_syntax", "status": "unsupported", "passed": False, "reason_code": "node_unavailable", "file_count": len(rows), "command_count": 0}
    results: list[dict[str, Any]] = []
    minimal_env = {"PATH": os.path.dirname(node), "LANG": "C", "LC_ALL": "C", "NO_COLOR": "1"}
    for row in sorted(rows, key=lambda item: str(item.get("relative_path") or "")):
        try:
            rel = _safe_relative(str(row.get("relative_path") or ""))
        except ValueError:
            return {"adapter": "javascript_syntax", "status": "failed", "passed": False, "reason_code": "javascript_path_rejected", "file_count": len(rows), "command_count": len(results)}
        path = root / rel
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_JS_FILE_BYTES:
            results.append({"path_digest": hashlib.sha256(rel.encode()).hexdigest(), "exit_class": "file_rejected", "passed": False})
            continue
        try:
            completed = subprocess.run(
                [node, "--check", str(path)],
                cwd=str(root),
                env=minimal_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=COMMAND_TIMEOUT_SECONDS,
                check=False,
            )
            results.append({
                "path_digest": hashlib.sha256(rel.encode()).hexdigest(),
                "exit_class": "zero" if completed.returncode == 0 else "nonzero",
                "passed": completed.returncode == 0,
                "output_digest": _diagnostic_digest(completed.stdout.decode(errors="replace"), completed.stderr.decode(errors="replace")),
            })
        except subprocess.TimeoutExpired as error:
            results.append({"path_digest": hashlib.sha256(rel.encode()).hexdigest(), "exit_class": "timeout", "passed": False, "output_digest": _diagnostic_digest(str(error))})
        except OSError as error:
            results.append({"path_digest": hashlib.sha256(rel.encode()).hexdigest(), "exit_class": "spawn_failed", "passed": False, "output_digest": _diagnostic_digest(type(error).__name__)})
    passed = all(row["passed"] for row in results)
    return {"adapter": "javascript_syntax", "status": "passed" if passed else "failed", "passed": passed, "file_count": len(rows), "command_count": len(results), "results": results}



def _node_cli_smoke_adapter(root: Path, workspace: Mapping[str, Any], *, node_executable: str | None = None) -> dict[str, Any]:
    names = {str(row.get("relative_path") or "") for row in workspace.get("files") or []}
    if "cli.js" not in names:
        return {"adapter": "node_cli_smoke", "status": "not_applicable", "passed": True, "command_count": 0}
    node = node_executable or shutil.which("node")
    if not node:
        return {"adapter": "node_cli_smoke", "status": "unsupported", "passed": False, "reason_code": "node_unavailable", "command_count": 0}
    path = root / "cli.js"
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_JS_FILE_BYTES:
        return {"adapter": "node_cli_smoke", "status": "failed", "passed": False, "reason_code": "cli_entrypoint_rejected", "command_count": 0}
    minimal_env = {"PATH": os.path.dirname(node), "LANG": "C", "LC_ALL": "C", "NO_COLOR": "1", "HOME": str(root)}
    try:
        completed = subprocess.run(
            [node, str(path), "--help"], cwd=str(root), env=minimal_env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=COMMAND_TIMEOUT_SECONDS, check=False,
        )
        passed = completed.returncode == 0
        return {
            "adapter": "node_cli_smoke", "status": "passed" if passed else "failed", "passed": passed,
            "command_count": 1, "exit_class": "zero" if passed else "nonzero",
            "output_digest": _diagnostic_digest(completed.stdout.decode(errors="replace"), completed.stderr.decode(errors="replace")),
        }
    except subprocess.TimeoutExpired as error:
        return {"adapter": "node_cli_smoke", "status": "failed", "passed": False, "command_count": 1, "exit_class": "timeout", "output_digest": _diagnostic_digest(str(error))}
    except OSError as error:
        return {"adapter": "node_cli_smoke", "status": "failed", "passed": False, "command_count": 1, "exit_class": "spawn_failed", "output_digest": _diagnostic_digest(type(error).__name__)}


def _python_syntax_adapter(root: Path, workspace: Mapping[str, Any], *, python_executable: str | None = None) -> dict[str, Any]:
    rows=[row for row in workspace.get("files") or [] if Path(str(row.get("relative_path") or "")).suffix.lower()==".py"]
    if not rows:return {"adapter":"python_syntax","status":"not_applicable","passed":True,"file_count":0,"command_count":0}
    if len(rows)>24 or sum(int(row.get("size_bytes") or 0) for row in rows)>2*1024*1024:return {"adapter":"python_syntax","status":"failed","passed":False,"reason_code":"python_budget_exceeded","file_count":len(rows),"command_count":0}
    python=python_executable or shutil.which("python3") or shutil.which("python")
    if not python:return {"adapter":"python_syntax","status":"unsupported","passed":False,"reason_code":"python_unavailable","file_count":len(rows),"command_count":0}
    env={"PATH":os.path.dirname(python),"LANG":"C","LC_ALL":"C","NO_COLOR":"1","PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1"};results=[]
    for row in sorted(rows,key=lambda x:str(x.get("relative_path") or "")):
        try:rel=_safe_relative(str(row.get("relative_path") or ""))
        except ValueError:return {"adapter":"python_syntax","status":"failed","passed":False,"reason_code":"python_path_rejected","file_count":len(rows),"command_count":len(results)}
        path=root/rel
        if not path.is_file() or path.is_symlink() or path.stat().st_size>MAX_JS_FILE_BYTES:results.append({"path_digest":hashlib.sha256(rel.encode()).hexdigest(),"exit_class":"file_rejected","passed":False});continue
        try:
            c=subprocess.run([python,"-c","import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read(),filename=sys.argv[1])",str(path)],cwd=str(root),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=COMMAND_TIMEOUT_SECONDS,check=False)
            results.append({"path_digest":hashlib.sha256(rel.encode()).hexdigest(),"exit_class":"zero" if c.returncode==0 else "nonzero","passed":c.returncode==0,"output_digest":_diagnostic_digest(c.stdout.decode(errors="replace"),c.stderr.decode(errors="replace"))})
        except subprocess.TimeoutExpired as e:results.append({"path_digest":hashlib.sha256(rel.encode()).hexdigest(),"exit_class":"timeout","passed":False,"output_digest":_diagnostic_digest(str(e))})
        except OSError as e:results.append({"path_digest":hashlib.sha256(rel.encode()).hexdigest(),"exit_class":"spawn_failed","passed":False,"output_digest":_diagnostic_digest(type(e).__name__)})
    passed=all(x["passed"] for x in results);return {"adapter":"python_syntax","status":"passed" if passed else "failed","passed":passed,"file_count":len(rows),"command_count":len(results),"results":results}

def _python_cli_smoke_adapter(root: Path, workspace: Mapping[str, Any], *, python_executable: str | None = None) -> dict[str, Any]:
    names={str(row.get("relative_path") or "") for row in workspace.get("files") or []}
    if "main.py" not in names:return {"adapter":"python_cli_smoke","status":"not_applicable","passed":True,"command_count":0}
    python=python_executable or shutil.which("python3") or shutil.which("python")
    if not python:return {"adapter":"python_cli_smoke","status":"unsupported","passed":False,"reason_code":"python_unavailable","command_count":0}
    path=root/"main.py"
    if not path.is_file() or path.is_symlink() or path.stat().st_size>MAX_JS_FILE_BYTES:return {"adapter":"python_cli_smoke","status":"failed","passed":False,"reason_code":"python_entrypoint_rejected","command_count":0}
    env={"PATH":os.path.dirname(python),"LANG":"C","LC_ALL":"C","NO_COLOR":"1","HOME":str(root),"PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1"}
    code="import runpy,sys; root,entry=sys.argv[1],sys.argv[2]; sys.path.insert(0,root); sys.argv=[entry,'--help']; runpy.run_path(entry,run_name='__main__')"
    try:
        c=subprocess.run([python,"-I","-c",code,str(root),str(path)],cwd=str(root),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=COMMAND_TIMEOUT_SECONDS,check=False);passed=c.returncode==0
        return {"adapter":"python_cli_smoke","status":"passed" if passed else "failed","passed":passed,"command_count":1,"exit_class":"zero" if passed else "nonzero","output_digest":_diagnostic_digest(c.stdout.decode(errors="replace"),c.stderr.decode(errors="replace"))}
    except subprocess.TimeoutExpired as e:return {"adapter":"python_cli_smoke","status":"failed","passed":False,"command_count":1,"exit_class":"timeout","output_digest":_diagnostic_digest(str(e))}
    except OSError as e:return {"adapter":"python_cli_smoke","status":"failed","passed":False,"command_count":1,"exit_class":"spawn_failed","output_digest":_diagnostic_digest(type(e).__name__)}

def validate_or_resume_workspace(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_workspace_digest: str,
    expected_preview_digest: str = "",
    runtime_root=None,
    node_executable: str | None = None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        workspace, preview, root = _load_bound_records(proposal_id, expected_revision, runtime_root)
        if not workspace or root is None:
            return {"ok": False, "status": "workspace_missing"}
        if workspace.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if workspace.get("workspace_digest") != expected_workspace_digest:
            return {"ok": False, "status": "stale_workspace_revision"}
        if not _verify_record(workspace, root):
            return {"ok": False, "status": "workspace_record_invalid"}
        if expected_preview_digest:
            if not preview or preview.get("preview_digest") != expected_preview_digest:
                return {"ok": False, "status": "stale_or_missing_preview"}
            if preview.get("workspace_digest") != expected_workspace_digest:
                return {"ok": False, "status": "preview_workspace_binding_rejected"}
        record_path = _validation_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(record_path)
        if existing:
            bindings_ok = existing.get("workspace_digest") == expected_workspace_digest and existing.get("preview_digest", "") == expected_preview_digest
            return ({**existing, "operation_status": "resumed"} if bindings_ok and _record_valid(existing) else {"ok": False, "status": "validation_record_invalid"})
        browser = _browser_adapter(root, workspace, preview)
        javascript = _javascript_adapter(root, workspace, node_executable=node_executable)
        cli_smoke = _node_cli_smoke_adapter(root, workspace, node_executable=node_executable)
        python_syntax = _python_syntax_adapter(root, workspace, python_executable=python_executable)
        python_smoke = _python_cli_smoke_adapter(root, workspace, python_executable=python_executable)
        passed = bool(browser.get("passed") and javascript.get("passed") and cli_smoke.get("passed") and python_syntax.get("passed") and python_smoke.get("passed"))
        adapters = [browser, javascript]
        if cli_smoke.get("status") != "not_applicable": adapters.append(cli_smoke)
        if python_syntax.get("status") != "not_applicable": adapters.append(python_syntax)
        if python_smoke.get("status") != "not_applicable": adapters.append(python_smoke)
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "workspace_validation_passed" if passed else "workspace_validation_failed",
            "passed": passed,
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "planning_digest": workspace.get("planning_digest"),
            "generation_digest": workspace.get("generation_digest"),
            "workspace_digest": expected_workspace_digest,
            "preview_digest": expected_preview_digest,
            "approval_receipt_digest": workspace.get("approval_receipt_digest"),
            "adapters": adapters,
            "adapter_count": len(adapters),
            "command_count": int(javascript.get("command_count") or 0) + int(cli_smoke.get("command_count") or 0) + int(python_syntax.get("command_count") or 0) + int(python_smoke.get("command_count") or 0),
            "selected_project_modified": False,
            "source_modified": False,
            "provider_contacted": False,
            "command_executed": (int(javascript.get("command_count") or 0) + int(cli_smoke.get("command_count") or 0) + int(python_syntax.get("command_count") or 0) + int(python_smoke.get("command_count") or 0)) > 0,
            "tests_executed": True,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
        }
        record["validation_digest"] = _digest(record)
        _atomic_json(record_path, record)
        return {**record, "operation_status": "created"}


def public_validation(record: Mapping[str, Any]) -> dict[str, Any]:
    adapters = []
    for adapter in record.get("adapters") or []:
        adapters.append({
            key: value
            for key, value in adapter.items()
            if key not in {"results"}
        })
        if adapter.get("results") is not None:
            adapters[-1]["result_count"] = len(adapter.get("results") or [])
            adapters[-1]["passed_result_count"] = sum(1 for row in adapter.get("results") or [] if row.get("passed"))
    return {
        "ok": bool(record.get("ok")),
        "status": record.get("status", ""),
        "passed": bool(record.get("passed")),
        "proposal_id": record.get("proposal_id", ""),
        "proposal_revision": record.get("proposal_revision", 0),
        "workspace_digest": record.get("workspace_digest", ""),
        "preview_digest": record.get("preview_digest", ""),
        "validation_digest": record.get("validation_digest", ""),
        "adapter_count": record.get("adapter_count", 0),
        "command_count": record.get("command_count", 0),
        "adapters": adapters,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "provider_contacted": False,
        "command_executed": bool(record.get("command_executed")),
        "tests_executed": True,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
