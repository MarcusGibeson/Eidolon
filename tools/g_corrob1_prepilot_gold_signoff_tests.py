"""Regression guards for the G-CORROB1-R2 R22 repair and renewed signoff."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from g_corrob1_freeze import build_manifest, verify_execution_manifest


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "experiments" / "G-CORROB1-candidate-r2"


def _load(name: str) -> dict:
    return json.loads((CANDIDATE / name).read_text(encoding="utf-8"))


class PrepilotGoldSignoffTests(unittest.TestCase):
    def test_failed_r22_formulation_remains_preserved_as_history(self) -> None:
        failed_report = (CANDIDATE / "PREPILOT_INDEPENDENT_GOLD_SIGNOFF.md").read_text(
            encoding="utf-8"
        )
        repair = (CANDIDATE / "R22_REPAIR_RECORD.md").read_text(encoding="utf-8")
        old = "Mixer M completed its sanitation cycle on 2032-08-02."
        self.assertIn("GOLD SIGNOFF REQUIRES REPAIR", failed_report)
        self.assertIn(old, repair)
        self.assertIn("does not exclude an *earlier* completed cycle", failed_report)

    def test_repaired_r22_is_explicitly_bound_and_evidence_is_unchanged(self) -> None:
        corpus = _load("corpus.json")
        gold = _load("gold_candidate.json")
        item = next(value for value in corpus["items"] if value["item_id"] == "R22")
        judgment = next(value for value in gold["items"] if value["item_id"] == "R22")

        self.assertEqual(
            item["proposition"],
            "Mixer M completed sanitation cycle S-44 on 2032-08-02.",
        )
        self.assertEqual(
            item["evidence"],
            "Mixer M's final controller record for 2032-08-02 marks sanitation "
            "cycle S-44 aborted before completion and records no later sanitation cycle.",
        )
        self.assertEqual(judgment["gold_relation"], "contradicts")
        self.assertEqual(judgment["gold_scope"], "match")
        self.assertEqual(judgment["gold_temporal"], "compatible")
        self.assertFalse(judgment["use_permitted"])
        self.assertEqual(judgment["expected_disposition"], "abstain")

    def test_renewed_signoff_is_complete_and_clean(self) -> None:
        report = (CANDIDATE / "PREPILOT_RENEWED_GOLD_SIGNOFF.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("GOLD SIGNOFF CLEAN", report)
        self.assertIn("28/28 crisp primary items", report)
        self.assertIn("4/4 diagnostics", report)
        self.assertIn("Only R22 changed, and only its proposition changed", report)

    def test_unbound_r22_cannot_be_reintroduced(self) -> None:
        corpus = _load("corpus.json")
        item = next(value for value in corpus["items"] if value["item_id"] == "R22")
        self.assertNotEqual(
            item["proposition"],
            "Mixer M completed its sanitation cycle on 2032-08-02.",
        )
        self.assertIn("S-44", item["proposition"])

    def test_execution_freeze_requires_completed_gold_signoff(self) -> None:
        manifest = build_manifest()
        manifest.update(
            status="execution_frozen",
            execution_frozen=True,
            independent_gold_signoff_complete=False,
            model_content_digest="a" * 64,
        )
        result = verify_execution_manifest(manifest)
        self.assertFalse(result["valid"])
        self.assertIn("independent_gold_signoff_incomplete", result["reasons"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
