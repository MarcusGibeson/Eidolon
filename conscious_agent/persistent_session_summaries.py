from __future__ import annotations
from pathlib import Path
from typing import Any
try:
    from persistent_state_index import session_summary
except ImportError:
    from persistent_state_index import session_summary
CONTRACT_VERSION="v1252.2"
def persistent_session_summary(session_dir:str|Path,session_id:str)->dict[str,Any]:
    row=session_summary(session_dir,session_id)
    return {"ok":row is not None,"contract_version":CONTRACT_VERSION,"session":row,"incremental_from_session_writes":True,"provider_invoked":False,"authority_granted":False}
