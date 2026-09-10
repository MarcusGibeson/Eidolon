from __future__ import annotations
from pathlib import Path
from typing import Any
try:
    from persistent_state_index import select_cross_session_ids
except ImportError:
    from persistent_state_index import select_cross_session_ids
CONTRACT_VERSION="v1252.1"; MAX_CROSS_SESSION_TRANSCRIPTS=6; MAX_INDEX_CANDIDATES=48
def bounded_cross_session_retrieval(session_dir: str|Path,user_message:str,*,exclude_session_id:str="",project_id:str|None=None,limit:int=MAX_CROSS_SESSION_TRANSCRIPTS)->dict[str,Any]:
    bounded=max(0,min(MAX_CROSS_SESSION_TRANSCRIPTS,int(limit)))
    ids=select_cross_session_ids(session_dir,user_message,exclude_session_id=exclude_session_id,project_id=project_id,limit=bounded,candidate_limit=MAX_INDEX_CANDIDATES)
    return {"ok":True,"contract_version":CONTRACT_VERSION,"session_ids":ids,"selected_count":len(ids),"max_transcripts":MAX_CROSS_SESSION_TRANSCRIPTS,"candidate_limit":MAX_INDEX_CANDIDATES,"full_catalog_transcript_scan":False,"authority_granted":False}
