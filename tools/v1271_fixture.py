from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1270_fixture import prepared_chain,initial_provider,repair_provider
from long_running_work_sessions_foundations import prepare_long_running_work_session

def prepared_long_chain(base: Path, **kwargs):
    chain=prepared_chain(base);session=prepare_long_running_work_session(chain['campaign']['campaign_id'],runtime_root=chain['runtime'],**kwargs);return {**chain,'session':session}
