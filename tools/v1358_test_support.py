from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
SOURCE='a'*64;E='b'*64
def req(v,m):
 if not v:raise AssertionError(m)
def clean(root:Path):
 root.mkdir();(root/'app.py').write_text('from pathlib import Path\ndef add(a,b): return a+b\n');(root/'config.json').write_text('{"mode":"local"}')
def deps(ok=True):return [{'dependency_id':'stdlib','evidence_digest':E,'known_vulnerability_count':0 if ok else 1,'provenance_verified':True,'lockfile_pinned':True}]
