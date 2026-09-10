import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp())

from conscious_agent.privacy_security_test_catalog import build_privacy_security_test_catalog
from conscious_agent.privacy_security_threat_model import build_privacy_security_threat_model

model = build_privacy_security_threat_model()
report = build_privacy_security_test_catalog(threat_model=model)
checks = [
    report["contract_version"] == "v1148.1",
    report["catalog_id"] == "privacy-security-test-catalog:v1148.1",
    report["threat_model_valid"] and report["threat_model_digest"] == model["structural_digest"],
    report["scenario_count"] == 12 and not report["duplicate_scenario_ids"],
    not report["rejected_blueprints"],
    {row["category"] for row in report["scenarios"]} == set(model["categories"]),
    all(row["threat_digest"] for row in report["scenarios"]),
    all(row["fixture_reference"].startswith("structural-fixture:") and not row["fixture_content_included"] for row in report["scenarios"]),
    all(row["expected_outcome"] in {"deny", "quarantine", "review", "constrain", "stop"} for row in report["scenarios"]),
    all(1 <= row["max_steps"] <= 5 and row["max_attempts"] == 1 and row["max_runtime_ms"] == 250 for row in report["scenarios"]),
    all(row["provider_budget_tokens"] == 0 and not row["execution_eligible"] for row in report["scenarios"]),
    all(row["operator_review_required"] and row["lifecycle_state"] == "defined" for row in report["scenarios"]),
    report["content_free"] and report["read_only"] and not any(report["authority_boundary"].values()),
]
invalid = dict(model)
invalid["structural_digest"] = ""
closed = build_privacy_security_test_catalog(threat_model=invalid)
checks.append(not closed["threat_model_valid"] and closed["scenario_count"] == 0)
assert all(checks), [index + 1 for index, value in enumerate(checks) if not value]
print(json.dumps({"suite": "v1148.1", "passed": len(checks), "total": len(checks)}))
