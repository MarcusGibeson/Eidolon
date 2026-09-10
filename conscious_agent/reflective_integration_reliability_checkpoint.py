from __future__ import annotations
"""Strictly read-only v1125.8 Reflection Integration and Reliability checkpoint."""
import hashlib, os
from pathlib import Path
from reflective_outcome_lineage import build_reflective_outcome_lineage_inspection
from reflective_reliability_review import build_reflective_reliability_review_inspection
from reflective_communication_recommendation_governance import build_reflective_communication_recommendation_inspection
CONTRACT_VERSION="v1125.8"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(path):
 p=Path(path)
 if not p.exists():return "missing"
 h=hashlib.sha256()
 for f in sorted(x for x in p.rglob("*") if x.is_file()):h.update(str(f.relative_to(p)).encode());h.update(f.read_bytes())
 return h.hexdigest()
def build_reflective_integration_reliability_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb=_sig(runtime);sb=_sig(source);lineage=build_reflective_outcome_lineage_inspection(runtime);reliability=build_reflective_reliability_review_inspection(runtime);recommendations=build_reflective_communication_recommendation_inspection(runtime)
 checks=[lineage.get("ok"),reliability.get("ok"),recommendations.get("ok"),not lineage.get("conclusions_exposed"),not lineage.get("hidden_reasoning_exposed"),not reliability.get("hidden_reasoning_exposed"),not recommendations.get("message_sent"),not recommendations.get("notification_created"),not lineage.get("belief_updated"),not lineage.get("goal_updated"),not lineage.get("self_model_updated"),not lineage.get("initiative_created"),not lineage.get("external_action_executed"),lineage.get("contract_version")=="v1125.6",reliability.get("contract_version")=="v1125.7",recommendations.get("contract_version")=="v1125.4",rb==_sig(runtime),sb==_sig(source)]
 rows=[{"check":f"check_{i+1}","passed":bool(v)} for i,v in enumerate(checks)];passed=sum(bool(x) for x in checks)
 return {"ok":passed==18,"contract_version":CONTRACT_VERSION,"status":"ready_for_desktop_verification" if passed==18 else "degraded","headline":f"v1125.8 Reflection Integration and Reliability: {passed}/18 checks passed","checks":rows,"passed":passed,"total":18,"summary":{"outcome_count":lineage.get("outcome_count",0),"review_count":len(reliability.get("reviews",[])),"recommendation_count":recommendations.get("recommendation_count",0)},"lineage":lineage,"reliability":reliability,"recommendations":recommendations,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"message_sent":False,"notification_created":False,"initiative_created":False,"external_action_executed":False,"runtime_mutated":rb!=_sig(runtime),"source_modified":sb!=_sig(source),"desktop_verification_pending":True}
