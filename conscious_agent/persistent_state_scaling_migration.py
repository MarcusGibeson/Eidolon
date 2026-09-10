from __future__ import annotations
import shutil
from pathlib import Path
from typing import Any
try:
    from persistent_state_index import INDEX_FILENAME, rebuild_action_index, rebuild_memory_index, rebuild_session_index, validate_persistent_index_consistency, persistent_state_index_status
except ImportError:
    from persistent_state_index import INDEX_FILENAME,rebuild_action_index,rebuild_memory_index,rebuild_session_index,validate_persistent_index_consistency,persistent_state_index_status
CONTRACT_VERSION="v1252.8"
def rebuild_persistent_indexes(data_root:str|Path)->dict[str,Any]:
    root=Path(data_root); sessions=rebuild_session_index(root/'conversation_sessions'); memories=rebuild_memory_index(root/'memories.json'); actions=rebuild_action_index(root/'chat_actions'); consistency=validate_persistent_index_consistency(root)
    return {"ok":consistency['ok'],"contract_version":CONTRACT_VERSION,"sessions":sessions,"memories":memories,"actions":actions,"consistency":consistency,"canonical_data_mutated":False,"authority_granted":False}
def recover_corrupt_persistent_index(data_root:str|Path)->dict[str,Any]:
    root=Path(data_root); index=root/INDEX_FILENAME; quarantined=""
    if index.exists():
        quarantined=str(index.with_name(index.name+'.corrupt'))
        Path(quarantined).unlink(missing_ok=True); index.replace(quarantined)
        for suffix in ('-wal','-shm'):
            (root/(INDEX_FILENAME+suffix)).unlink(missing_ok=True)
    report=rebuild_persistent_indexes(root); report.update({"quarantined_index":quarantined,"recovered":report['ok']}); return report
