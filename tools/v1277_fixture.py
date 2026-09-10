from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1274_fixture import prepared_environment_chain
from development_observability_foundations import prepare_development_observability
def prepared_observability_chain(base:Path,**kwargs):
    c=prepared_environment_chain(base,**kwargs);o=prepare_development_observability(c['session']['session_id'],runtime_root=c['runtime'],now=kwargs.get('now'));return {**c,'observability':o}
