from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for path in (str(ROOT), str(AGENT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from active_conversation_facts import _facts_from_text
from developer_alpha_runtime import EVIDENCE_ROLE, GENERAL_GENERATION_PATH
from release_authority import WORKING_SOURCE_VERSION, PREVIOUS_WORKING_SOURCE_VERSION
from verification_quality_policy import EvidenceClass, claim_is_sufficient
from checkpoint_registry import checkpoint_registry_manifest

checks: dict[str, bool] = {}
def ck(name: str, value: bool) -> None:
    checks[name] = bool(value)
    if not value:
        raise AssertionError(name)

ck("version", WORKING_SOURCE_VERSION in {"2730.9", "2730.9.1", "2730.9.2", "2730.9.3"} and PREVIOUS_WORKING_SOURCE_VERSION in {"2729.9.2", "2730.9", "2730.9.1", "2730.9.2"})
ck("question_not_fact", _facts_from_text("What is my fiancee called?", offset=0) == [])
partner = {f.key: f.value for f in _facts_from_text("My fiancee is named Sarah.", offset=0)}
ck("natural_partner_assertion", partner.get("user.partner.name") == "Sarah")
ck("structural_evidence_not_behavior_proof", not claim_is_sufficient("x", [EvidenceClass.SOURCE_PRESENCE], behavior_claimed=True))
ck("calculator_truth_labeled", EVIDENCE_ROLE == "legacy_transaction_fixture_not_generation_evidence" and GENERAL_GENERATION_PATH == "isolated_coding_execution")
text = (AGENT / "dashboard.py").read_text(encoding="utf-8")
ck("wildcard_cors_removed", 'Access-Control-Allow-Origin", "*"' not in text)
ck("origin_guard_present", "_reject_cross_origin_mutation" in text)
ck("no_v2730_self_maintenance_copy_family", "_build_v2730" not in (AGENT / "self_maintenance.py").read_text(encoding="utf-8"))
ck("product_definition_present", (ROOT / "docs" / "PRODUCT_DEFINITION.md").is_file())
ck("verification_policy_present", (ROOT / "docs" / "VERIFICATION_POLICY.md").is_file())

# Prove the exact direct-suite execution shape that previously failed no longer
# requires PYTHONPATH. Use a clean environment and the historical checkpoint test.
env = dict(os.environ); env.pop("PYTHONPATH", None); env["PYTHONDONTWRITEBYTECODE"] = "1"
proc = subprocess.run(
    [sys.executable, "tools/v2729_9_2_release_parity_campaign_binding_hardening_checkpoint_tests.py"],
    cwd=ROOT, env=env, capture_output=True, text=True, timeout=90,
)
ck("direct_tool_execution_without_pythonpath", proc.returncode == 0)

registry = checkpoint_registry_manifest(source_root=ROOT)
ck("checkpoint_registry_unique", registry.get("ok") is True and not registry.get("errors"))

print(json.dumps({"ok": True, "passed": len(checks), "total": len(checks), "checks": checks}, sort_keys=True))
