from __future__ import annotations
from pathlib import Path
from typing import Any
try:
    from persistent_state_index import list_indexed_sessions, persistent_state_index_status, rebuild_session_index
except ImportError:
    from persistent_state_index import list_indexed_sessions, persistent_state_index_status, rebuild_session_index
CONTRACT_VERSION="v1252.0"
def session_metadata_index_report(session_dir: str|Path, *, rebuild: bool=False) -> dict[str,Any]:
    directory=Path(session_dir)
    rebuild_report=rebuild_session_index(directory) if rebuild else None
    rows=list_indexed_sessions(directory,include_archived=True)
    return {"ok":True,"contract_version":CONTRACT_VERSION,"session_count":len(rows),"sessions":rows,"rebuild":rebuild_report,"transcripts_loaded_for_listing":False,"canonical_transcripts_preserved":True,"authority_granted":False}
