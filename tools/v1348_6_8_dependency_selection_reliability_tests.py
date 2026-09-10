from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from dependency_selection import *
from v1348_dependency_selection_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 cases=[(candidate(license='unknown'),'license_unacceptable_or_unknown'),(candidate(security_status='vulnerable'),'security_state_not_clear'),(candidate(evidence_age_days=999),'evidence_stale'),(candidate(platforms=('posix',)),'target_platform_unverified'),(candidate(offline_ready=False),'offline_suitability_unverified'),(candidate(footprint_kb=999999),'footprint_budget_exceeded'),(candidate(capability_score=.2),'capability_fit_insufficient'),(candidate(provenance_verified=False),'provenance_unverified')]
 for c,reason in cases:
  e=evaluate_dependency_candidates([c]);req(e['selection_status']=='no_viable_candidate' and e['rejected_reason_counts'].get(reason)==1)
 req(not DEPENDENCY_DENIED_AUTHORITY['network_authorized'] and not DEPENDENCY_DENIED_AUTHORITY['lockfile_mutation_authorized'])
 print({'ok':True,'suite':'v1348.6-8-dependency-selection-reliability','passed':p,'total':9})
if __name__=='__main__':main()
