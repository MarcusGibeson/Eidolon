from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from v1272_fixture import prepared_recovery_chain
from ownership_concurrency_foundations import prepare_ownership_concurrency

def prepared_ownership_chain(base: Path, **kwargs):
    chain=prepared_recovery_chain(base, **kwargs)
    ownership=prepare_ownership_concurrency(chain['recovery']['recovery_id'],runtime_root=chain['runtime'],now=kwargs.get('now'))
    return {**chain,'ownership':ownership}
