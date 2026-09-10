from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT/'conscious_agent', ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from v1271_fixture import prepared_long_chain
from restart_crash_recovery_foundations import prepare_restart_crash_recovery


def prepared_recovery_chain(base: Path, **kwargs):
    chain=prepared_long_chain(base, **kwargs)
    recovery=prepare_restart_crash_recovery(chain['session']['session_id'], runtime_root=chain['runtime'], now=kwargs.get('now'))
    return {**chain, 'recovery': recovery}
