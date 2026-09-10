from __future__ import annotations
from pathlib import Path
from typing import Any
try:
    from persistent_state_index import load_indexed_memories, memory_exists, search_indexed_memories
except ImportError:
    from persistent_state_index import load_indexed_memories,memory_exists,search_indexed_memories
CONTRACT_VERSION="v1252.4"
def indexed_memory_window(memory_file:str|Path,*,limit:int=80)->dict[str,Any]:
    rows=load_indexed_memories(memory_file,limit=max(1,int(limit))); return {"ok":True,"contract_version":CONTRACT_VERSION,"memories":rows,"count":len(rows),"full_legacy_json_parse":False,"authority_granted":False}
def indexed_memory_operation_exists(memory_file:str|Path,operation_id:str,memory_type:str)->bool: return memory_exists(memory_file,operation_id,memory_type)
