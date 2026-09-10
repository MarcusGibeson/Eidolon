from __future__ import annotations
import hashlib,os,sys,tempfile
from pathlib import Path
os.environ.setdefault("PYTHONDONTWRITEBYTECODE","1");os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1196-5-data-"))
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.adversarial_replay_recovery_review import *
from conscious_agent.adversarial_replay_recovery_review_checkpoint import build_adversarial_replay_recovery_review_checkpoint
def h(v):return hashlib.sha256(v.encode()).hexdigest()
checks=[]
def req(v):checks.append(bool(v));assert v
r=build_adversarial_replay_recovery_review_checkpoint(source_root=ROOT);req(r["ok"]);req(r["passed"]==r["total"]);req(r["summary"]["event_class_count"]==5);req(r["summary"]["decision_count"]==3)
prior=None
for i,event in enumerate(EVENT_CLASSES,1):
 q=build_review_request(review_id=f"r{i}",event_class=event,action=ACTIONS[(i-1)%4],sequence=i,snapshot_digest=h("s"),context_digest=h("c"),evidence_digest=h("e"),prior_review_digest=prior)
 for name,status in (("approve","review_presented"),("reject","review_rejected"),("defer","review_deferred")):
  d=build_review_decision(request_digest=q["request_digest"],decision=name,operator_review_digest=h(name),reason_code=name)
  out=review_adversarial_event(request=q,decision=d,expected_snapshot_digest=h("s"),expected_context_digest=h("c"),expected_evidence_digest=h("e"),expected_prior_review_digest=prior)
  req(out["ok"]);req(out["status"]==status);req(out["exact_lineage_verified"]);req(out["original_evidence_preserved"]);req(not out["execution_invoked"]);req(not out["authority_granted"])
 prior=out["review_receipt_digest"]
api=(ROOT/"conscious_agent/api_server.py").read_text(encoding="utf-8");req("adversarial-replay-recovery-review-checkpoint" in api)
release=(ROOT/"tools/release_verify.py").read_text(encoding="utf-8");req(release.count("v1196.5-adversarial-replay-recovery-review")==1);req(release.count("v1196_3_5_adversarial_replay_recovery_review_tests.py")==1)
for p in [ROOT/"README.md",ROOT/"README_NEXT_STEPS.md",ROOT/"archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",ROOT/"README_RELEASE_HISTORY.md",ROOT/"conscious_agent/release_metadata.py"]:req("v1196.5" in p.read_text(encoding="utf-8"))
print(f"v1196.3-v1196.5 adversarial replay recovery review: {sum(checks)}/{len(checks)} PASS")
