from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1500-4-"))
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conversation_surface_contracts import RelationshipMemoryCurationError
from conscious_agent.dashboard_chat_console import (
    _render_entity_association_curation_panel,
    _render_relationship_memory_curation_panel,
)
from conscious_agent.entity_association_curation import (
    ALLOWED_PREDICATES,
    correct_entity_association,
    delete_entity_association,
    entity_association_curation_summary,
    inspect_entity_association,
    list_entity_association_records,
    update_entity_association,
)
from conscious_agent.relationship_memory_curation import (
    create_relationship_memory,
    relationship_memory_deletion_integrity_summary,
)


passed = failed = 0


def check(name: str, condition: bool, details: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, details)


created = create_relationship_memory(
    "personal_fact",
    "Entity association: Project Atlas | uses_provider | Ollama.",
    source="operator_explicit_conversation_memory_request",
)
create_relationship_memory(
    "personal_fact", "The user likes tea.",
    source="operator_relationship_curation_dashboard",
)
check("association fixture created", created.get("created") is True, created)

records = list_entity_association_records()
check("only structured association records are listed", len(records) == 1, records)
record = records[0]
check(
    "private operator record exposes structured fields",
    record["subject"] == "Project Atlas" and record["predicate"] == "uses_provider"
    and record["object"] == "Ollama" and record["private_operator_view"] is True,
    record,
)
check("association identity is revision bound", record["association_id"].startswith("association:") and len(record["record_revision_digest"]) == 64)
inspected = inspect_entity_association(record["association_id"])
check("exact association can be inspected", inspected["record_key"] == record["record_key"])

summary = entity_association_curation_summary()
serialized_summary = json.dumps(summary, sort_keys=True)
check(
    "public summary is content-free and authority-inert",
    summary["record_count"] == 1 and summary["contains_association_content"] is False
    and summary["provider_contacted"] is False and summary["authority_granted"] is False
    and all(token not in serialized_summary for token in ("Project Atlas", "Ollama")),
    summary,
)

try:
    inspect_entity_association("association:stale")
    stale_missing_rejected = False
except RelationshipMemoryCurationError:
    stale_missing_rejected = True
check("unknown revision fails closed", stale_missing_rejected)

corrected = correct_entity_association(
    record["association_id"], subject="Project Atlas", predicate="uses_provider", obj="llama.cpp",
)
new_record = corrected.get("association") or {}
check("structured correction changes only selected association", corrected.get("changed") is True and new_record.get("object") == "llama.cpp", corrected)
check("correction produces a new revision identity", new_record.get("association_id") != record["association_id"])
try:
    inspect_entity_association(record["association_id"])
    stale_after_correction = False
except RelationshipMemoryCurationError:
    stale_after_correction = True
check("pre-correction revision becomes stale", stale_after_correction)

for bad_subject, bad_predicate, bad_object in (
    ("Project Atlas", "executes", "cmd.exe"),
    ("Project|Atlas", "uses_provider", "Ollama"),
    ("Project Atlas", "uses_provider", "Project Atlas"),
):
    try:
        correct_entity_association(
            new_record["association_id"], subject=bad_subject,
            predicate=bad_predicate, obj=bad_object,
        )
        rejected = False
    except RelationshipMemoryCurationError:
        rejected = True
    check(f"invalid structured correction rejected: {bad_predicate}", rejected)

retracted = update_entity_association(new_record["association_id"], "retract")
retracted_record = retracted.get("association") or {}
check("retraction is explicit and reversible", retracted_record.get("state") == "retracted", retracted)
check("retracted association excluded from active list", list_entity_association_records(include_retracted=False) == [])
try:
    correct_entity_association(
        retracted_record["association_id"], subject="Project Atlas",
        predicate="uses_provider", obj="Ollama",
    )
    correction_while_retracted_rejected = False
except RelationshipMemoryCurationError:
    correction_while_retracted_rejected = True
check("retracted association cannot be corrected", correction_while_retracted_rejected)

restored = update_entity_association(retracted_record["association_id"], "restore")
restored_record = restored.get("association") or {}
check("restore returns association to active use", restored_record.get("state") == "active", restored)
try:
    delete_entity_association(restored_record["association_id"], "DELETE")
    active_delete_rejected = False
except RelationshipMemoryCurationError:
    active_delete_rejected = True
check("active association cannot be permanently deleted", active_delete_rejected)

retracted_again = update_entity_association(restored_record["association_id"], "retract")["association"]
try:
    delete_entity_association(retracted_again["association_id"], "delete")
    confirmation_rejected = False
except RelationshipMemoryCurationError:
    confirmation_rejected = True
check("permanent deletion requires exact DELETE", confirmation_rejected)
deleted = delete_entity_association(retracted_again["association_id"], "DELETE")
check("retracted association content is permanently removed", deleted.get("content_removed") is True and deleted.get("tombstone_retained") is True, deleted)
check("deleted association no longer appears in private list", list_entity_association_records() == [])
tombstones = relationship_memory_deletion_integrity_summary()
check("content-free deletion tombstone remains", tombstones["tombstone_count"] == 1 and tombstones["incomplete_cleanup"] == 0, tombstones)

create_relationship_memory(
    "personal_fact",
    "Entity association: main.py | belongs_to_project | Project Eidolon.",
    source="operator_explicit_conversation_memory_request",
)
html = _render_entity_association_curation_panel()
check("dedicated dashboard panel renders structured association", "Manage entity associations" in html and "main.py" in html and "Project Eidolon" in html)
check("dashboard exposes exact correction and retraction controls", "dashboard_entity_association_correct" in html and "dashboard_entity_association_update" in html)
generic_html = _render_relationship_memory_curation_panel()
check("association is not duplicated in generic continuity list", "Entity association:" not in generic_html)

dashboard_source = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
for action in (
    "dashboard_entity_association_update",
    "dashboard_entity_association_correct",
    "dashboard_entity_association_delete",
):
    check(f"dashboard action registered once: {action}", dashboard_source.count(f'action == "{action}"') == 1)
verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check("v1500.4 suite registered exactly once", verifier.count("v1500_4_entity_association_curation_tests.py") == 1)
check("predicate allowlist remains bounded", len(ALLOWED_PREDICATES) == 6)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.4-entity-association-curation",
    "provider_contacted": False,
    "source_mutated": False,
    "authority_granted": False,
    "content_free_public_summary": True,
})
if failed:
    raise SystemExit(1)
