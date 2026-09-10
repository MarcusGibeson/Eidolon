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

from conscious_agent.privacy_security_threat_model import (
    THREAT_CATEGORIES,
    build_privacy_security_threat_model,
)

report = build_privacy_security_threat_model()
checks = [
    report["contract_version"] == "v1148.0",
    report["model_id"] == "privacy-security-threat-model:v1148.0",
    report["threat_count"] == report["category_count"] == 6,
    tuple(report["categories"]) == THREAT_CATEGORIES,
    not report["duplicate_threat_ids"] and not report["missing_categories"],
    all(row["severity"] in range(1, 6) for row in report["threats"]),
    all(row["required_controls"] for row in report["threats"]),
    all(row["expected_outcome"] in {"deny", "quarantine", "review", "constrain", "stop"} for row in report["threats"]),
    all(row["operator_review_required"] and row["lifecycle_state"] == "defined" for row in report["threats"]),
    all(not row["raw_fixture_allowed"] and not row["provider_contact_allowed"] and not row["execution_allowed"] for row in report["threats"]),
    report["content_free"] and report["read_only"] and not any(report["authority_boundary"].values()),
    len(report["structural_digest"]) == 64 and all(len(row["structural_digest"]) == 64 for row in report["threats"]),
]
assert all(checks), [index + 1 for index, value in enumerate(checks) if not value]
print(json.dumps({"suite": "v1148.0", "passed": len(checks), "total": len(checks)}))
