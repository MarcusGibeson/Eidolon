from __future__ import annotations

"""v1260.6-v1260.8 read-only reliability and Desktop handoff evidence."""

import hashlib, json
from pathlib import Path
from typing import Any
from coding_alpha_checkpoint_foundations import DENIED_AUTHORITY, build_coding_alpha_contract

SCHEMA_VERSION="1"
CONTRACT_VERSION="v1260.8"
REQUIRED_SURFACES=(
 "conscious_agent/isolated_coding_execution.py","conscious_agent/controlled_application_rollback.py",
 "conscious_agent/persistent_development_sessions.py","conscious_agent/diagnostic_repair_reasoning.py",
 "conscious_agent/complete_application_construction.py","conscious_agent/conversational_command_integration.py",
 "conscious_agent/ordinary_chat_development_campaign.py","conscious_agent/coding_alpha_checkpoint_foundations.py",
 "conscious_agent/coding_alpha_campaign.py",
)

def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()

def inspect_coding_alpha_health(*,source_root:str|Path|None=None)->dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    hashes={rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in REQUIRED_SURFACES if (root/rel).is_file()}
    checks={
      "all_required_surfaces_present":len(hashes)==len(REQUIRED_SURFACES),
      "canonical_stage_count_complete":build_coding_alpha_contract()["stage_count"]==13,
      "distinct_application_and_rollback_authority":build_coding_alpha_contract()["application_and_rollback_require_distinct_exact_authorizations"],
      "generic_authorization_denied":build_coding_alpha_contract()["generic_authorization_must_never_be_consumed"],
      "restart_provider_replay_forbidden":build_coding_alpha_contract()["provider_replay_on_resume_forbidden"],
    }
    row={"ok":all(checks.values()),"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"coding_alpha_health_ready","checks":checks,
         "required_source_count":len(REQUIRED_SURFACES),"present_source_count":len(hashes),"source_sha256":hashes,"read_only":True,"content_free":True,
         "native_windows_validation":"desktop_review_required",**DENIED_AUTHORITY}
    row["health_digest"]=_digest(row); return row

def build_coding_alpha_operator_handoff(*,source_root:str|Path|None=None)->dict[str,Any]:
    health=inspect_coding_alpha_health(source_root=source_root)
    row={"ok":health["ok"],"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"coding_alpha_operator_handoff_ready" if health["ok"] else "coding_alpha_operator_handoff_blocked",
         "health_digest":health.get("health_digest", ""),"operator_review_required":True,
         "desktop_focus":["ordinary calculator request through exact proposal approval","intentional failed quality attempt and evidence-ranked repair","restart with no duplicate provider call","stale/conflicting selected-project edit before apply","exact controlled application and post-apply verification","exact rollback and byte-for-byte pre-apply restoration","concurrent duplicate controls across Windows processes","NTFS junction/reparse/casefold/long-path boundaries"],
         "native_windows_multi_process_validation":"desktop_review_required","content_free":True,**DENIED_AUTHORITY}
    row["handoff_digest"]=_digest(row); return row

__all__=["CONTRACT_VERSION","inspect_coding_alpha_health","build_coding_alpha_operator_handoff"]
