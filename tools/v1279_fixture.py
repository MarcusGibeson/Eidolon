from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1277_fixture import prepared_observability_chain
from operator_experience import build_operator_experience_snapshot

def prepared_operator_experience_chain(base:Path,**kwargs):
    c=prepared_observability_chain(base,**kwargs)
    c['snapshot']=build_operator_experience_snapshot(c['observability']['observability_id'],runtime_root=c['runtime'])
    return c
