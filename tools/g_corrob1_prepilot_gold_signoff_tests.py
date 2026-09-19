"""Regression guards for the blocked G-CORROB1-R2 pre-pilot gold signoff.

These tests preserve the discovered R22 defect and stop boundary. They do not
change corpus semantics, gold, policy, scoring, or execution authority.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "experiments" / "G-CORROB1-candidate-r2"


def _load(name: str) -> dict:
    return json.loads((CANDIDATE / name).read_text(encoding="utf-8"))


class PrepilotGoldSignoffTests(unittest.TestCase):
    def test_r22_binding_gap_remains_explicit_until_semantic_revision(self) -> None:
        corpus = _load("corpus.json")
        gold = _load("gold_candidate.json")
        item = next(value for value in corpus["items"] if value["item_id"] == "R22")
        judgment = next(value for value in gold["items"] if value["item_id"] == "R22")

        proposition = item["proposition"].lower()
        evidence = item["evidence"].lower()
        self.assertNotIn("s-44", proposition)
        self.assertIn("no later sanitation cycle", evidence)
        self.assertNotIn("no earlier sanitation cycle", evidence)
        self.assertNotIn("only sanitation cycle", evidence)
        self.assertEqual(judgment["gold_relation"], "contradicts")

    def test_independent_signoff_records_requires_repair(self) -> None:
        report = (CANDIDATE / "PREPILOT_INDEPENDENT_GOLD_SIGNOFF.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("GOLD SIGNOFF REQUIRES REPAIR", report)
        self.assertIn("`R22` fails the crisp-primary requirement", report)
        self.assertIn("Provider/configuration preflight", report)
        self.assertIn("were not started", report)

    def test_candidate_remains_non_executable(self) -> None:
        manifest = _load("IMPLEMENTATION_FREEZE_CANDIDATE.json")
        self.assertFalse(manifest["execution_frozen"])
        self.assertFalse(manifest["execution_authorized"])
        self.assertNotIn("provider_contacted", manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
