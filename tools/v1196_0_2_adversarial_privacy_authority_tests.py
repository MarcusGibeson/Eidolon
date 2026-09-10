from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1196-2-data-"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conscious_agent.adversarial_privacy_authority import ATTACK_CLASSES, AUTHORITY_DOMAINS, build_evidence, validate_adversarial_privacy_authority_evidence
from conscious_agent.adversarial_privacy_authority_checkpoint import build_adversarial_privacy_authority_checkpoint

def d(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
checks=[]
def req(v): checks.append(bool(v)); assert v
report=build_adversarial_privacy_authority_checkpoint(source_root=ROOT)
req(report["ok"]); req(report["contract_version"]=="v1196.2"); req(report["passed"]==report["total"]); req(report["summary"]["attack_class_count"]==14); req(report["summary"]["authority_domain_count"]==16)
req(report["summary"]["authority_state"]=="separate_not_granted"); req(report["summary"]["execution_invoked"] is False); req(report["summary"]["runtime_mutated"] is False)
prior=None
for i, attack in enumerate(ATTACK_CLASSES,1):
    row=build_evidence(attack_class=attack,target_domain=AUTHORITY_DOMAINS[(i-1)%len(AUTHORITY_DOMAINS)],sequence=i,snapshot_digest=d("s"),context_digest=d("c"),artifact_digest=d(f"a{i}"),receipt_digest=d(f"r{i}"),prior_receipt_digest=prior)
    out=validate_adversarial_privacy_authority_evidence(row,expected_snapshot_digest=d("s"),expected_context_digest=d("c"),expected_prior_receipt_digest=prior)
    req(out["ok"]); req(not out["errors"]); req(out["summary"]["content_free"]); req(out["summary"]["attack_blocked"]); req(not out["summary"]["authority_granted"])
    prior=row["receipt_digest"]
base=build_evidence(attack_class=ATTACK_CLASSES[0],target_domain=AUTHORITY_DOMAINS[0],sequence=1,snapshot_digest=d("s"),context_digest=d("c"),artifact_digest=d("a"),receipt_digest=d("r"))
from conscious_agent.adversarial_privacy_authority import _digest
cases=[("stale_snapshot",{"snapshot_digest":d("x")}), ("stale_context",{"context_digest":d("x")}), ("private",{"secret":"x"}), ("authority",{"authority_granted":True}), ("approval",{"approval_created":True}), ("execution",{"execution_invoked":True}), ("cancel",{"cancellation_executed":True}), ("runtime",{"runtime_mutated":True}), ("provider",{"provider_contacted":True}), ("model",{"model_contacted":True}), ("thread",{"thread_started":True}), ("process",{"process_started":True}), ("install",{"installation_performed":True}), ("promote",{"promotion_performed":True}), ("certify",{"certification_performed":True}), ("publish",{"publication_performed":True}), ("release",{"release_performed":True}), ("automatic",{"automatic_continuation":True}), ("class",{"attack_class":"bad"}), ("domain",{"target_domain":"root"}), ("sequence",{"sequence":0}), ("lineage",{"prior_receipt_digest":d("unexpected")})]
for name, changes in cases:
    row=dict(base); row.update(changes); row["evidence_digest"]=_digest({k:v for k,v in row.items() if k!="evidence_digest"})
    out=validate_adversarial_privacy_authority_evidence(row,expected_snapshot_digest=d("s"),expected_context_digest=d("c"))
    req(not out["ok"]); req(bool(out["errors"])); req(out["summary"]["error_count"]>=1)
# API and registry source wiring
api=(ROOT/"conscious_agent/api_server.py").read_text(encoding="utf-8")
req("adversarial-privacy-authority-checkpoint" in api)
release=(ROOT/"tools/release_verify.py").read_text(encoding="utf-8")
req(release.count("v1196.2-adversarial-privacy-authority") == 1); req(release.count("v1196_0_2_adversarial_privacy_authority_tests.py") == 1)
for path in [ROOT/"README.md",ROOT/"README_NEXT_STEPS.md",ROOT/"archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",ROOT/"README_RELEASE_HISTORY.md",ROOT/"conscious_agent/release_metadata.py"]: req("v1196.2" in path.read_text(encoding="utf-8"))
print(f"v1196.0-v1196.2 adversarial privacy authority: {sum(checks)}/{len(checks)} PASS")
