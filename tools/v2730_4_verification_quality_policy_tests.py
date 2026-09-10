from __future__ import annotations
import json
from conscious_agent.verification_quality_policy import EvidenceClass, claim_is_sufficient

checks = {
    "source_presence_cannot_certify_behavior": not claim_is_sufficient("memory works", [EvidenceClass.SOURCE_PRESENCE], behavior_claimed=True),
    "docs_marker_cannot_certify_behavior": not claim_is_sufficient("feature works", [EvidenceClass.STRUCTURAL], behavior_claimed=True),
    "synthetic_consistency_cannot_certify_behavior": not claim_is_sufficient("planner correct", [EvidenceClass.SYNTHETIC_CONSISTENCY], behavior_claimed=True),
    "behavioral_test_can_certify_behavior": claim_is_sufficient("fact extraction", [EvidenceClass.BEHAVIORAL], behavior_claimed=True),
    "integration_can_certify_behavior": claim_is_sufficient("chat turn", [EvidenceClass.INTEGRATION], behavior_claimed=True),
    "security_requires_adversarial": not claim_is_sufficient("same-origin", [EvidenceClass.BEHAVIORAL], security_claimed=True),
    "adversarial_can_support_security": claim_is_sufficient("same-origin", [EvidenceClass.ADVERSARIAL], security_claimed=True),
    "structural_is_valid_when_no_behavior_claimed": claim_is_sufficient("docs present", [EvidenceClass.STRUCTURAL]),
}
assert all(checks.values()), checks
print(json.dumps({"ok": True, "passed": len(checks), "total": len(checks), "checks": checks}, sort_keys=True))
