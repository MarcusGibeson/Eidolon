from __future__ import annotations
"""v1300.6-v1300.8 reliability audit for the supervised beta evidence."""
from typing import Any,Mapping
from supervised_self_development_beta_foundations import BETA_STAGES,DENIED_AUTHORITY,digest,valid_digest
CONTRACT_VERSION='v1300.8'
def audit_supervised_self_development_beta(result:Mapping[str,Any])->dict[str,Any]:
 row=dict(result);findings=[]
 if list(row.get('stage_sequence') or [])!=list(BETA_STAGES):findings.append('incomplete_or_reordered_beta')
 if row.get('active_installed_eidolon_modified') is not False:findings.append('active_installation_modified')
 if row.get('exact_authorization_was_fixture_bound') is not True:findings.append('fixture_authorization_boundary_lost')
 if row.get('generic_authorization_phrase_is_sufficient') is not False:findings.append('generic_authorization_expansion')
 if row.get('rollback_remains_separately_governed_for_successful_operator_rollback') is not True:findings.append('rollback_boundary_lost')
 if row.get('native_windows_certified') is not False or str(row.get('native_windows_status') or '') not in {'pending','unavailable'}:findings.append('native_windows_false_pass')
 if any(bool(row.get(k)) for k in DENIED_AUTHORITY):findings.append('authority_expansion')
 if not valid_digest(row.get('beta_digest')):findings.append('beta_digest_missing')
 elif row.get('beta_digest')!=digest({k:v for k,v in row.items() if k!='beta_digest'}):findings.append('beta_digest_mismatch')
 if row.get('integrity_violations'):findings.append('underlying_integrity_violation')
 ok=bool(row.get('ok')) and not findings
 return {'contract_version':CONTRACT_VERSION,'ok':ok,'status':'supervised_self_development_beta_reliable' if ok else 'supervised_self_development_beta_reliability_blocked','findings':findings,'native_windows_beta_validation_pending':True,'roadmap_complete_through_v1300':ok,'content_free':True,'read_only':True,**DENIED_AUTHORITY}
