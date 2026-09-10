from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
def candidate(*,existing=False,license='MIT',security_status='clear',evidence_age_days=5,maintenance_age_days=20,footprint_kb=2000,platforms=('windows','posix'),offline_ready=True,capability_score=.9,provenance_verified=True,evidence_digest='e'*64):
 return dict(existing=existing,license=license,security_status=security_status,evidence_age_days=evidence_age_days,maintenance_age_days=maintenance_age_days,footprint_kb=footprint_kb,platforms=list(platforms),offline_ready=offline_ready,capability_score=capability_score,provenance_verified=provenance_verified,evidence_digest=evidence_digest,version='1.0')
