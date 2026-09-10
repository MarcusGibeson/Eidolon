from __future__ import annotations
import hashlib, os, sys, tempfile
from pathlib import Path
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1196-8-data-"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conscious_agent.adversarial_reliability_integration import *
from conscious_agent.adversarial_reliability_integration_checkpoint import build_adversarial_reliability_integration_checkpoint

def h(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()
checks=[]
def req(value): checks.append(bool(value)); assert value
result=build_adversarial_reliability_integration_checkpoint(source_root=ROOT)
req(result["ok"]); req(result["passed"]==result["total"]); req(result["summary"]["event_class_count"]==8); req(result["summary"]["surface_count"]==12)
prior=None
for index,event_class in enumerate(EVENT_CLASSES,1):
    event=build_reliability_event(event_id=f"e{index}",event_class=event_class,surface=SURFACES[(index-1)%len(SURFACES)],sequence=index,snapshot_digest=h("s"),context_digest=h("c"),evidence_digest=h("e"),authority_digest=h("a"),prior_event_digest=prior,foreground_latency_ms=10,latency_budget_ms=250)
    out=inspect_reliability_event(event=event,expected_snapshot_digest=h("s"),expected_context_digest=h("c"),expected_evidence_digest=h("e"),expected_authority_digest=h("a"),expected_prior_event_digest=prior)
    req(out["ok"]); req(out["status"]=="reliability_verified"); req(out["exact_lineage_verified"]); req(out["original_evidence_preserved"]); req(out["foreground_available"])
    for field in ("automatic_recovery_executed","automatic_retry_executed","cancellation_executed","execution_invoked","runtime_mutated","provider_contacted","authority_granted","global_profile_pass_claimed"): req(out[field] is False)
    prior=out["reliability_receipt_digest"]
api=(ROOT/"conscious_agent/api_server.py").read_text(encoding="utf-8"); req("adversarial-reliability-integration-checkpoint" in api)
dashboard=(ROOT/"conscious_agent/dashboard_first_use.py").read_text(encoding="utf-8"); req("adversarial-reliability-integration" in dashboard)
release=(ROOT/"tools/release_verify.py").read_text(encoding="utf-8"); req(release.count("v1196.8-adversarial-reliability-integration")==1); req(release.count("v1196_6_8_adversarial_reliability_integration_tests.py")==1)
for path in [ROOT/"README.md",ROOT/"README_NEXT_STEPS.md",ROOT/"archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",ROOT/"README_RELEASE_HISTORY.md",ROOT/"conscious_agent/release_metadata.py"]: req("v1196.8" in path.read_text(encoding="utf-8"))
print(f"v1196.6-v1196.8 adversarial reliability integration: {sum(checks)}/{len(checks)} PASS")
