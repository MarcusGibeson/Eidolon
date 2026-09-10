from __future__ import annotations
"""v1383 isolated self-change candidate workspaces with sealed input lineage.

The active Eidolon source is never a mutation target.  A candidate workspace is
materialized beneath an explicitly external runtime root as two trees:
``input`` is a sealed source snapshot and ``work`` is the only writable
candidate tree.  Integrity is checked from content-free manifests before later
stages may trust the workspace.
"""
import hashlib, json, os, re, shutil
from pathlib import Path
from typing import Any, Mapping

CONTRACT_VERSION = "v1383.8"
DIGEST = re.compile(r"^[a-f0-9]{64}$")
CANDIDATE = re.compile(r"^selfc_[a-f0-9]{12,64}$")
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "data", "runtime", "logs", "backups"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
MAX_FILES = 20000
MAX_BYTES = 128 * 1024 * 1024
DENIED = {
    "installation_authorized": False, "promotion_authorized": False,
    "release_authorized": False, "source_mutation_authorized": False,
    "independent_authority_granted": False,
}

def _d(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()

def _under(child: Path, parent: Path) -> bool:
    try: child.relative_to(parent); return True
    except ValueError: return False

def _eligible(root: Path):
    count = 0; total = 0
    for p in sorted(root.rglob("*"), key=lambda x: x.as_posix().lower()):
        if not p.is_file() or p.is_symlink(): continue
        rel = p.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts) or p.suffix.lower() in EXCLUDED_SUFFIXES: continue
        count += 1; total += p.stat().st_size
        if count > MAX_FILES or total > MAX_BYTES: raise ValueError("source snapshot exceeds bounded isolation budget")
        yield p, rel

def _manifest(root: Path) -> dict[str, Any]:
    files=[]; total=0
    for p, rel in _eligible(root):
        b=p.read_bytes();total+=len(b)
        files.append({"path": rel.as_posix(), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})
    core={"file_count":len(files),"total_bytes":total,"files":files}
    return {**core,"manifest_digest":_d(core)}

def _copy_source(source: Path, dest: Path) -> dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=False)
    for p, rel in _eligible(source):
        target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    return _manifest(dest)

def create_self_change_workspace(*, source_root: str|Path, runtime_root: str|Path, candidate_id: str,
                                 self_model_digest: str, backlog_candidate_digest: str) -> dict[str, Any]:
    source=Path(source_root).expanduser().resolve(); runtime=Path(runtime_root).expanduser().resolve()
    if not source.is_dir() or not CANDIDATE.fullmatch(str(candidate_id or "")) or not DIGEST.fullmatch(str(self_model_digest or "")) or not DIGEST.fullmatch(str(backlog_candidate_digest or "")):
        return {"ok":False,"status":"self_change_isolation_request_invalid","action_executed":False,**DENIED}
    # An isolation root inside active source would make the source mutate merely by creating it.
    if _under(runtime, source):
        return {"ok":False,"status":"self_change_runtime_must_be_external","action_executed":False,**DENIED}
    root=runtime/"self_change_candidates"/candidate_id
    if root.exists(): return {"ok":False,"status":"self_change_candidate_already_exists","action_executed":False,**DENIED}
    input_root=root/"input";work_root=root/"work"
    try:
        source_manifest=_manifest(source)
        input_manifest=_copy_source(source,input_root)
        if input_manifest["manifest_digest"] != source_manifest["manifest_digest"]: raise ValueError("snapshot mismatch")
        work_manifest=_copy_source(input_root,work_root)
        if work_manifest["manifest_digest"] != input_manifest["manifest_digest"]: raise ValueError("work copy mismatch")
        # Best-effort filesystem read-only seal; manifest verification is the actual cross-platform authority check.
        for p,_ in _eligible(input_root):
            try: p.chmod(p.stat().st_mode & ~0o222)
            except OSError: pass
        lineage={"contract_version":CONTRACT_VERSION,"candidate_id":candidate_id,"self_model_digest":self_model_digest,
                 "backlog_candidate_digest":backlog_candidate_digest,"source_manifest_digest":source_manifest["manifest_digest"],
                 "sealed_input_manifest_digest":input_manifest["manifest_digest"],"initial_work_manifest_digest":work_manifest["manifest_digest"],
                 "input_is_mutation_target":False,"work_is_only_candidate_mutation_target":True,"active_source_is_mutation_target":False,
                 "installation_authorized":False,"release_authorized":False}
        lineage["lineage_digest"]=_d(lineage)
        private={"candidate_root":str(root),"input_root":str(input_root),"work_root":str(work_root),"lineage":lineage}
        (root/"lineage.private.json").write_text(json.dumps(private,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        public={**lineage,"candidate_root_digest":_d(str(root)),"input_root_digest":_d(str(input_root)),"work_root_digest":_d(str(work_root)),
                "source_file_count":source_manifest["file_count"],"source_total_bytes":source_manifest["total_bytes"],"content_free":True,
                "isolated":True,"action_executed":True,**DENIED}
        return {"ok":True,"status":"self_change_workspace_isolated","self_change_workspace":public,"private_workspace":private,
                "action_executed":True,**DENIED}
    except Exception as exc:
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file():
                    try:p.chmod(0o600)
                    except OSError:pass
            shutil.rmtree(root,ignore_errors=True)
        return {"ok":False,"status":"self_change_isolation_failed","reason":str(exc)[:160],"action_executed":False,**DENIED}

def verify_self_change_isolation(*, private_workspace: Mapping[str,Any], expected_lineage_digest: str) -> dict[str, Any]:
    pw=dict(private_workspace or {}); lineage=dict(pw.get("lineage") or {}); supplied=str(lineage.pop("lineage_digest", ""))
    if supplied != expected_lineage_digest or supplied != _d(lineage):
        return {"ok":False,"status":"self_change_lineage_stale_or_tampered","action_executed":False,**DENIED}
    try:
        input_root=Path(str(pw["input_root"])).resolve();work_root=Path(str(pw["work_root"])).resolve();candidate_root=Path(str(pw["candidate_root"])).resolve()
        if not (_under(input_root,candidate_root) and _under(work_root,candidate_root) and input_root!=work_root): raise ValueError("workspace topology changed")
        inp=_manifest(input_root);work=_manifest(work_root)
    except Exception as exc:
        return {"ok":False,"status":"self_change_isolation_unreadable","reason":str(exc)[:160],"action_executed":False,**DENIED}
    input_ok=inp["manifest_digest"]==lineage.get("sealed_input_manifest_digest")
    out={"contract_version":CONTRACT_VERSION,"candidate_id":lineage.get("candidate_id"),"lineage_digest":supplied,
         "sealed_input_intact":input_ok,"work_manifest_digest":work["manifest_digest"],"work_changed":work["manifest_digest"]!=lineage.get("initial_work_manifest_digest"),
         "active_source_is_mutation_target":False,"content_free":True,"action_executed":False,**DENIED}
    out["verification_digest"]=_d(out)
    return {"ok":input_ok,"status":"self_change_isolation_verified" if input_ok else "self_change_sealed_input_changed","verification":out,"action_executed":False,**DENIED}

def public_self_change_workspace(result: Mapping[str,Any]) -> dict[str,Any]:
    return dict(result.get("self_change_workspace") or {})

def process_self_change_isolation_control(text: str, *, project_state=None, **_):
    if str(text or "").strip().lower() not in {"show self change isolation","inspect self change isolation","show self change workspace"}: return {"active":False}
    rec=dict((project_state or {}).get("self_change_workspace") or {})
    return {"active":True,"ok":bool(rec),"status":"self_change_workspace_found" if rec else "self_change_workspace_missing","self_change_workspace":rec,"action_executed":False,**DENIED}
