from __future__ import annotations
"""v1297.6-v1297.8 recovery replay/conflict/authority hardening."""
from pathlib import Path
from typing import Any,Mapping
from automated_recovery_foundations import DENIED_AUTHORITY
CONTRACT_VERSION='v1297.8'
def audit_recovery_result(result:Mapping[str,Any])->dict[str,Any]:
 r=dict(result);findings=[]
 if r.get('candidate_reapplied') is not False:findings.append('candidate_reapply_claimed')
 if r.get('arbitrary_content_written') is not False:findings.append('arbitrary_write_claimed')
 if r.get('new_update_authorization_consumed') is not False:findings.append('new_update_authorization_consumed')
 if r.get('operator_initiated_rollback_authorized') is not False:findings.append('general_rollback_conflation')
 for k in DENIED_AUTHORITY:
  if r.get(k) is not False:findings.append(f'authority_expansion:{k}')
 return {"ok":not findings,"status":"automated_recovery_reliability_ready" if not findings else "automated_recovery_reliability_blocked","findings":findings,"read_only":True,"content_free":True,**DENIED_AUTHORITY}
def inspect_automated_recovery_surface_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();required=['conscious_agent/automated_recovery_foundations.py','conscious_agent/automated_recovery.py','conscious_agent/automated_recovery_reliability.py','conscious_agent/governed_self_update.py','conscious_agent/canary_self_updates.py'];checks={x:(root/x).is_file() for x in required};return {"ok":all(checks.values()),"status":"automated_recovery_surface_ready" if all(checks.values()) else "automated_recovery_surface_blocked","checks":checks,"native_windows_validation":"desktop_review_required","read_only":True,"content_free":True,**DENIED_AUTHORITY}
