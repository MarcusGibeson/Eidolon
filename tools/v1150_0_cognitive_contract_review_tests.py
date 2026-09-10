from __future__ import annotations

import json
from pathlib import Path

from conscious_agent.cognitive_contract_review import build_cognitive_contract_review

ROOT = Path(__file__).resolve().parents[1]
report = build_cognitive_contract_review(ROOT)
findings = {row["finding_id"]: row for row in report["findings"]}
resolved = {row["finding_id"]: row for row in report.get("resolved_findings", [])}
checks = [
    report["contract_version"] == "v1150.0",
    report["content_free"] and not report["provider_contacted"] and not report["runtime_data_read"],
    report["checkpoint_builder_count"] >= 150,
    report["cognitive_capability_count"] >= 100,
    "v1145-contracts-not-in-ordinary-turn-path" in findings or "v1145-contracts-not-in-ordinary-turn-path" in resolved,
    "post-reply-reflection-split-from-authoritative-runtime" in findings or "post-reply-reflection-split-from-authoritative-runtime" in resolved,
    report["integration_state_counts"]["checkpoint_only"] > 0,
    len(report["structural_digest"]) == 64,
]
assert all(checks), report
print(json.dumps({"suite": "v1150.0", "passed": len(checks), "total": len(checks), "findings": report["finding_count"]}))
