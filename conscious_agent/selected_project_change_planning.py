from __future__ import annotations
import hashlib,re
from pathlib import PurePosixPath
from typing import Any,Iterable,Mapping
ALLOWED_SUFFIXES={".html",".htm",".css",".js",".mjs",".cjs",".json",".py",".md",".txt",".toml"}
ALLOWED_NAMES={"package.json","pyproject.toml","requirements.txt","setup.cfg","pytest.ini"}
MAX_DIRECTIVES=32
_DIRECTIVE=re.compile(r"\b(create|modify|delete)\s+(?:`([^`]+)`|\"([^\"]+)\"|'([^']+)'|([^\s,;]+))",re.I)
def safe_relative_path(raw:str)->str:
 value=str(raw or "").strip().replace("\\","/"); path=PurePosixPath(value)
 if not value or value.startswith("/") or ":" in value or path.is_absolute() or any(part in {"",".",".."} for part in path.parts): raise ValueError("unsafe_change_path")
 normalized=path.as_posix(); name=path.name.lower(); suffix=path.suffix.lower()
 if name not in ALLOWED_NAMES and suffix not in ALLOWED_SUFFIXES: raise ValueError("unsupported_change_path")
 return normalized
def parse_change_directives(request:str,existing:Iterable[Mapping[str,Any]])->list[dict[str,Any]]:
 existing_names={str(row.get("relative_path") or "") for row in existing}; existing_folded={n.casefold():n for n in existing_names}; rows=[]; seen=set()
 for m in _DIRECTIVE.finditer(str(request or "")):
  op=m.group(1).lower(); raw=next(g for g in m.groups()[1:] if g is not None); rel=safe_relative_path(raw.rstrip(".")); folded=rel.casefold()
  if folded in seen: raise ValueError("duplicate_change_path")
  seen.add(folded); exists=folded in existing_folded
  if op=="create" and exists: raise ValueError("create_target_exists")
  if op in {"modify","delete"} and not exists: raise ValueError(f"{op}_target_missing")
  canonical=existing_folded.get(folded,rel); rows.append({"relative_path":canonical,"relative_path_digest":hashlib.sha256(canonical.encode()).hexdigest(),"operation":op,"authority":"future_isolated_workspace_only","directive_explicit":True})
  if len(rows)>MAX_DIRECTIVES: raise ValueError("change_directive_count_exceeded")
 return rows
