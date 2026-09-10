from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path.insert(0,str(ROOT/'conscious_agent'))
from comprehensive_verification_checkpoint import comprehensive_verification_checkpoint
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
r=comprehensive_verification_checkpoint(ROOT);req(r['ok'],'checkpoint');req(r['contract_version']=='v1295.9','version');req(all(r['checks'].values()),'checks');req(r['checks']['focused_and_affected_regression_evidence_unified'],'tests');req(r['checks']['fresh_extraction_and_source_only_package_parity_unified'],'package');req(r['checks']['privacy_metadata_registry_and_clean_environment_unified'],'canonical');req(r['checks']['native_windows_is_required_explicit_evidence_domain'] and r['checks']['native_pending_never_counts_as_pass'],'native_truth');req(r['checks']['failed_blocked_unavailable_pending_distinguished'],'states');req(r['checks']['verification_not_certification_release_or_authority'],'boundary');req(r['checks']['native_windows_execution_validation_outstanding_in_this_environment'],'native_pending');req(r['next']=='v1296 Canary Self-Updates' and r['v1296_started'] and r['checks']['v1296_transition_coherent'],'next_transition');req(r['read_only'] and not r['certification_authorized'] and not r['release_authorized'],'readonly')
print(json.dumps({'ok':True,'suite':'v1295.9-comprehensive-verification-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
