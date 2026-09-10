from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from conscious_agent.architecture_checkpoint_dispatch import (
    build_checkpoint_dispatch_consolidation,
    dispatch_registered_checkpoint,
)
from conscious_agent.checkpoint_registry import (
    checkpoint_descriptors,
    inspect_checkpoint_registry,
    resolve_checkpoint_builder,
)

with tempfile.TemporaryDirectory() as temporary:
    runtime = Path(temporary) / "runtime"
    runtime.mkdir()
    registry = inspect_checkpoint_registry(source_root=ROOT)
    descriptors = checkpoint_descriptors(source_root=ROOT)
    one = dispatch_registered_checkpoint(
        "conversation-cognition-unification",
        source_root=ROOT,
        runtime_root=runtime,
    )
    consolidation = build_checkpoint_dispatch_consolidation(
        source_root=ROOT,
        runtime_root=runtime,
        invoke_checkpoint_ids=("understandable-cognitive-controls",),
    )
    architecture_compatibility = [
        dispatch_registered_checkpoint(checkpoint_id, source_root=ROOT, runtime_root=runtime)
        for checkpoint_id in (
            "architecture-consolidation-intake-checkpoint",
            "architecture-consolidation-execution-checkpoint",
            "architecture-consolidation-reliability-checkpoint",
            "architecture-consolidation-governance-checkpoint",
        )
    ]

    first_use_without_input = dispatch_registered_checkpoint(
        "first-use-checkpoint",
        source_root=ROOT,
        runtime_root=runtime,
    )
    bootstrap = {
        "chat_interactive": True,
        "administrative_services_loaded": False,
        "runtime_guidance": {"runtime_external": True},
        "recovery": {},
        "provider": {"status": "unknown"},
        "progress": {"phases": [
            {"name": "conversation_restoration", "status": "ready"},
            {"name": "conversation_ownership_restoration", "status": "ready"},
        ]},
        "accepted_turn_replayed": False,
        "provider_contacted": False,
        "runtime_mutation_performed": False,
    }
    first_use = dispatch_registered_checkpoint(
        "first-use-checkpoint",
        source_root=ROOT,
        runtime_root=runtime,
        checkpoint_inputs={"bootstrap": bootstrap},
    )
    previous_runtime = os.environ.pop("EIDOLON_DATA_DIR", None)
    try:
        isolated = dispatch_registered_checkpoint(
            "conversation-cognition-unification",
            source_root=ROOT,
            runtime_root=None,
        )
    finally:
        if previous_runtime is not None:
            os.environ["EIDOLON_DATA_DIR"] = previous_runtime

checks = [
    registry["contract_version"] == "v1150.2",
    registry["checkpoint_count"] >= 150,
    registry["checkpoint_count"] == len(descriptors),
    not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"],
    registry["all_compatibility_targets_available"],
    registry["required_input_names"] == ["bootstrap"],
    registry["all_required_inputs_dispatch_supported"],
    callable(resolve_checkpoint_builder("conversation-cognition-unification", source_root=ROOT)),
    one["checkpoint_summary"]["invocation_supported"],
    one["read_only"] and not one["source_modified"] and not one["runtime_mutated"],
    not one["raw_checkpoint_included"] and not one["provider_contacted"],
    first_use_without_input["checkpoint_summary"]["invocation_supported"],
    not first_use_without_input["checkpoint_summary"]["invocation_completed"],
    first_use_without_input["checkpoint_summary"]["status"] == "checkpoint_inputs_required",
    first_use["checkpoint_summary"]["invocation_completed"] and first_use["checkpoint_summary"]["ok"],
    first_use["read_only"] and not first_use["runtime_mutated"] and not first_use["source_modified"],
    isolated["checkpoint_summary"]["runtime_isolated"] and isolated["read_only"],
    consolidation["descriptor_count"] == registry["checkpoint_count"],
    consolidation["requested_dispatch_count"] == 1,
    consolidation["all_requested_checkpoints_invocation_supported"],
    consolidation["all_requested_checkpoints_completed"],
    all(row["checkpoint_summary"]["invocation_completed"] for row in architecture_compatibility),
    all(row["checkpoint_summary"]["error_type"] == "" for row in architecture_compatibility),
    all(row["read_only"] and not row["source_modified"] and not row["runtime_mutated"] for row in architecture_compatibility),
    consolidation["historical_aliases_preserved"] and consolidation["content_free"],
]
assert all(checks), {"registry": registry, "one": one, "consolidation": consolidation}
print(json.dumps({"suite": "v1150.2", "passed": len(checks), "total": len(checks), "registered": registry["checkpoint_count"]}))
