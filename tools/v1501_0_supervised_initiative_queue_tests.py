from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from supervised_initiative_queue import (
    build_supervised_initiative_shortlist,
    control_supervised_initiative,
    inspect_supervised_initiative_queue,
    process_supervised_initiative_control,
    queue_supervised_initiative,
)
from v1489_product_capability_integration import integrate_v1489_product_capabilities
from supervised_self_development_contract import create_isolated_workspace, source_manifest
from symbol_level_refactoring import build_symbol_extraction_changes


CHECKS: list[str] = []


def require(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if "__pycache__" in relative or relative.endswith((".pyc", ".pyo")) or relative.startswith("data/"):
            continue
        rows.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def evidence() -> tuple[dict, dict]:
    rows = []
    ordered = []
    specifications = (
        ("a", "conscious_agent/alpha.py", "conscious_agent/alpha_helpers.py", 8, 1, .98, .93),
        ("b", "conscious_agent/bravo.py", "conscious_agent/bravo_helpers.py", 7, 2, .94, .89),
        ("c", "conscious_agent/charlie.py", "conscious_agent/charlie_helpers.py", 5, 4, .90, .85),
        ("d", "conscious_agent/delta.py", "conscious_agent/delta_helpers.py", 3, 9, .82, .76),
    )
    for suffix, source, destination, tests, dependencies, confidence, quality in specifications:
        candidate_id = f"discovery-{suffix * 20}"
        row = {
            "candidate_id": candidate_id,
            "evidence_digest": hashlib.sha256(candidate_id.encode()).hexdigest(),
            "eligibility_digest": hashlib.sha256((candidate_id + "eligible").encode()).hexdigest(),
            "source_module": source,
            "proposed_destination_module": destination,
            "source_symbols": [f"_{suffix}_load", f"_{suffix}_validate", f"_{suffix}_write"],
            "test_reference_file_count": tests,
            "estimated_dependency_count": dependencies,
            "confidence": confidence,
        }
        rows.append(row)
        ordered.append({"candidate_id": candidate_id, "quality_score": quality})
    return {"eligible_candidates": rows}, {"ordered_comparison": ordered, "comparison_digest": "c" * 64}


before = source_signature()
hardening, comparison = evidence()
shortlist = build_supervised_initiative_shortlist(hardening, comparison)
require(shortlist["ok"], "shortlist_ready")
require(shortlist["shortlist_count"] == 3, "shortlist_has_exactly_three")
require(len({row["source_module"] for row in shortlist["shortlist"]}) == 3, "shortlist_is_source_diverse")
require(shortlist["selected_candidate_id"] == "discovery-aaaaaaaaaaaaaaaaaaaa", "highest_value_candidate_selected")
require(shortlist == build_supervised_initiative_shortlist(hardening, comparison), "shortlist_is_deterministic")
for denied in ("proposal_created", "workspace_prepared", "provider_contacted", "source_modified", "authority_granted"):
    require(shortlist[denied] is False, f"shortlist_denies_{denied}")

with tempfile.TemporaryDirectory(prefix="eid-v1501-workspace-") as directory:
    fixture = Path(directory) / "source"
    fixture.mkdir()
    (fixture / "agent.py").write_text("VALUE = 1\n", encoding="utf-8")
    backup = fixture / "install_backups" / "old-copy"
    backup.mkdir(parents=True)
    (backup / "private-old-source.py").write_text("OLD = True\n", encoding="utf-8")
    workspace = Path(directory) / "workspace"
    created = create_isolated_workspace(fixture, workspace, authorized=True)
    require(created["created"], "source_only_workspace_created")
    require(not (workspace / "install_backups").exists(), "source_only_workspace_excludes_install_backups")
    require(source_manifest(fixture) == source_manifest(workspace), "workspace_manifest_matches_source_only_baseline")

alternative_source = (ROOT / "conscious_agent" / "alternative_planning.py").read_text(encoding="utf-8")
alternative_extraction = build_symbol_extraction_changes(
    alternative_source,
    source_path="conscious_agent/alternative_planning.py",
    destination_path="conscious_agent/alternative_planning_alternative.py",
    symbols=["generate_alternative_plan", "generate_priority_and_alternative_plan", "inspect_alternative_planning"],
)
compile(alternative_extraction["source_content"], "alternative_planning.py", "exec")
compile(alternative_extraction["destination_content"], "alternative_planning_alternative.py", "exec")
require(alternative_extraction["symbol_count"] == 3, "ordinary_import_block_supports_selected_candidate")
require("from alternative_planning_alternative import (" in alternative_extraction["source_content"], "generated_import_uses_destination_module")

with tempfile.TemporaryDirectory(prefix="eid-v1501-queue-") as directory:
    runtime = Path(directory) / "runtime"
    queued = queue_supervised_initiative(shortlist, discovery_digest="d" * 64, comparison_digest="c" * 64, runtime_root=runtime)
    require(queued["status"] == "supervised_initiative_queued", "initiative_queued")
    require(queued["runtime_mutated"] is True, "initial_queue_reports_runtime_mutation")
    initiative = queued["initiative"]
    require(initiative["lifecycle_state"] == "queued", "initiative_starts_queued")
    require(not initiative["proposal_created"], "queue_creates_no_proposal")
    require(not initiative["workspace_prepared"], "queue_prepares_no_workspace")
    require(not initiative["provider_contacted"], "queue_contacts_no_provider")
    require(not initiative["source_modified"], "queue_modifies_no_source")
    require(not initiative["authority_granted"], "queue_grants_no_authority")

    duplicate = queue_supervised_initiative(shortlist, discovery_digest="d" * 64, comparison_digest="c" * 64, runtime_root=runtime)
    require(duplicate["status"] == "supervised_initiative_reused", "duplicate_queue_is_idempotent")
    require(duplicate["initiative"]["initiative_id"] == initiative["initiative_id"], "duplicate_reuses_identity")
    require(inspect_supervised_initiative_queue(runtime)["active_count"] == 1, "restart_view_has_one_active_item")

    shown = process_supervised_initiative_control("Show supervised initiative queue.", runtime_root=runtime)
    require(shown["active"] and initiative["initiative_id"] in shown["conversation_response"], "chat_can_inspect_queue")
    stale = control_supervised_initiative("defer", initiative["initiative_id"], "0" * 16, runtime_root=runtime)
    require(stale["status"] == "initiative_digest_mismatch", "stale_digest_is_rejected")
    require(inspect_supervised_initiative_queue(runtime)["active_count"] == 1, "stale_control_changes_nothing")
    deferred = control_supervised_initiative("defer", initiative["initiative_id"], initiative["initiative_digest"][:16], runtime_root=runtime)
    require(deferred["status"] == "initiative_deferred", "initiative_can_be_deferred")
    require(inspect_supervised_initiative_queue(runtime)["active_count"] == 0, "deferred_item_is_not_active")

with tempfile.TemporaryDirectory(prefix="eid-v1501-advance-") as directory:
    runtime = Path(directory) / "runtime"
    queued = queue_supervised_initiative(shortlist, discovery_digest="d" * 64, comparison_digest="c" * 64, runtime_root=runtime)
    initiative = queued["initiative"]
    advanced = control_supervised_initiative("advance", initiative["initiative_id"], initiative["initiative_digest"][:16], runtime_root=runtime)
    require(advanced["status"] == "initiative_ready_for_proposal_review", "initiative_advances_to_review_only")
    require("Create dynamic self-development proposal" in advanced["conversation_response"], "advance_returns_exact_next_command")
    require(not advanced["initiative"]["proposal_created"], "advance_does_not_create_proposal")
    require(not (runtime / "development_campaigns" / "proposals").exists(), "advance_creates_no_proposal_directory")

with tempfile.TemporaryDirectory(prefix="eid-v1501-integration-") as directory:
    runtime = Path(directory) / "runtime"
    public_discovery = {
        "module_count": 4,
        "eligible_candidate_count": 4,
        "rejected_candidate_count": 2,
        "focus_candidates": [],
        "focus_module_summary": {},
    }
    discovery = {
        **public_discovery,
        "focus_rejections": [],
        "discovery_digest": "d" * 64,
    }
    previous = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        with (
            patch("v1489_product_capability_integration._installed_proposal_history", return_value=[]),
            patch("v1489_product_capability_integration.build_dynamic_improvement_discovery", return_value=discovery),
            patch("v1489_product_capability_integration.public_dynamic_discovery_projection", return_value=public_discovery),
            patch("v1489_product_capability_integration.harden_dynamic_discovery", return_value={**hardening, "eligible_count": 4}),
            patch("v1489_product_capability_integration.compare_dynamic_candidates", return_value={**comparison, "candidate_count": 4}),
        ):
            request = (
                "Inspect your current project and identify the three most valuable distinct improvements you could work on next. "
                "Compare them using concrete source evidence, select one, and place it into your supervised initiative queue. "
                "Do not modify source or begin implementation."
            )
            result = integrate_v1489_product_capabilities(request, {}, source_root=ROOT)
            require(result["event"] == "supervised_initiative_queued", "operator_trial_routes_to_queue")
            require(result["runtime_mutated"] is True, "integration_reports_queue_mutation")
            require(result["v1501_supervised_initiative_shortlist"]["shortlist_count"] == 3, "integration_compares_three")
            require("It is queued as devinit_" in result["conversation_response"], "integration_explains_queue_identity")
            require(result["source_modified"] is False, "integration_preserves_source_authority")

            ordinary = integrate_v1489_product_capabilities("Inspect your project and propose the next distinct improvement to your source.", {}, source_root=ROOT)
            require(ordinary["event"] == "dynamic_improvement_discovery_candidates_available", "legacy_inspection_remains_review_only")
            require(not ordinary["v1501_supervised_initiative_queue"], "legacy_inspection_does_not_queue")
    finally:
        if previous is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = previous

require(source_signature() == before, "suite_preserves_source")
print(json.dumps({
    "ok": True,
    "suite": "v1501.0-supervised-initiative-queue",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
}, indent=2, sort_keys=True))
