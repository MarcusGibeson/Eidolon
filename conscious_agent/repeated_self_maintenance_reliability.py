from __future__ import annotations
"""v1298.6-v1298.8 repeated-cycle stale/duplicate/contradiction hardening."""
from pathlib import Path
from typing import Any,Mapping
from repeated_self_maintenance_foundations import DENIED_AUTHORITY,valid_digest
CONTRACT_VERSION='v1298.8'
def audit_maintenance_state(state:Mapping[str,Any])->dict[str,Any]:
 s=dict(state);findings=[];cycles=list(s.get('cycles') or []);seen=list(s.get('seen_work_item_digests') or [])
 if len(seen)!=len(set(seen)):findings.append('duplicate_work_item')
 if len(cycles)>int(s.get('max_cycles') or 0):findings.append('cycle_budget_exceeded')
 if int(s.get('open_proposal_count') or 0)>int(s.get('max_open_proposals') or 0):findings.append('proposal_growth_unbounded')
 prior=str(s.get('initial_source_digest') or '')
 for idx,c in enumerate(cycles,1):
  if int(c.get('cycle_index') or 0)!=idx:findings.append('cycle_order_contradiction')
  if c.get('source_digest_at_start')!=prior:findings.append('cycle_source_lineage_broken')
  if not valid_digest(c.get('final_source_digest')):findings.append('cycle_final_source_missing')
  prior=str(c.get('final_source_digest') or '')
 if cycles and s.get('current_source_digest')!=prior:findings.append('current_source_contradiction')
 for k in DENIED_AUTHORITY:
  if s.get(k) is not False:findings.append(f'authority_expansion:{k}')
 return {'ok':not findings,'status':'repeated_maintenance_reliability_ready' if not findings else 'repeated_maintenance_reliability_blocked','findings':findings,'read_only':True,'content_free':True,**DENIED_AUTHORITY}
def inspect_repeated_maintenance_surface_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();required=['conscious_agent/repeated_self_maintenance_foundations.py','conscious_agent/repeated_self_maintenance.py','conscious_agent/repeated_self_maintenance_reliability.py','conscious_agent/independent_improvement_proposals.py','conscious_agent/value_risk_deliberation.py','conscious_agent/bounded_development_campaigns.py','conscious_agent/competing_candidate_evaluation.py','conscious_agent/comprehensive_verification.py'];checks={x:(root/x).is_file() for x in required};return {'ok':all(checks.values()),'status':'repeated_self_maintenance_surface_ready' if all(checks.values()) else 'repeated_self_maintenance_surface_blocked','checks':checks,'native_windows_validation':'desktop_review_required','read_only':True,'content_free':True,**DENIED_AUTHORITY}
