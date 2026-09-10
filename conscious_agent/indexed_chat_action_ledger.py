from __future__ import annotations
from pathlib import Path
from typing import Any,Sequence
try:
    from persistent_state_index import list_indexed_action_ids, lookup_indexed_action_ids, rebuild_action_index
except ImportError:
    from persistent_state_index import list_indexed_action_ids,lookup_indexed_action_ids,rebuild_action_index
CONTRACT_VERSION="v1252.6"
def action_ledger_index_report(action_dir:str|Path,*,status:str="",include_closed:bool=True)->dict[str,Any]:
    ids=list_indexed_action_ids(action_dir,status=status,include_closed=include_closed); return {"ok":True,"contract_version":CONTRACT_VERSION,"action_ids":ids,"count":len(ids),"full_receipt_parse":False,"authority_granted":False}
def action_ledger_lookup(action_dir:str|Path,*,action_ids:Sequence[str]=(),deduplication_keys:Sequence[str]=())->list[str]: return lookup_indexed_action_ids(action_dir,action_ids=action_ids,deduplication_keys=deduplication_keys)
