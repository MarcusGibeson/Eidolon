from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1500-5-")
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent.conversation_entity_associations import conversation_association_mutation_request
from conscious_agent.entity_association_curation import (
    apply_conversational_entity_association_mutation,
    inspect_entity_association,
    list_entity_association_records,
    update_entity_association,
)
from conscious_agent.relationship_memory_curation import create_relationship_memory
from conversation_surface_contracts import RelationshipMemoryCurationError
from conscious_agent.conversation_runtime import run_conversation_turn


passed = failed = 0


def check(name: str, condition: bool, details: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, details)


create_relationship_memory(
    "personal_fact",
    "Entity association: Project Neptune | uses_provider | Ollama.",
    source="operator_explicit_conversation_memory_request",
)
original = list_entity_association_records()[0]

correction_request = conversation_association_mutation_request(
    "Actually Project Neptune uses llama.cpp, not Ollama."
)
check(
    "explicit correction request is structured",
    correction_request.recognized and correction_request.action == "correct"
    and correction_request.subject == "Project Neptune"
    and correction_request.predicate == "uses_provider"
    and correction_request.object == "llama.cpp",
    correction_request,
)
corrected = apply_conversational_entity_association_mutation(
    "Actually Project Neptune uses llama.cpp, not Ollama."
)
check("conversational correction mutates one active record", corrected["mutated"] and corrected["status"] == "corrected", corrected)
check("correction acknowledgement names actual stored result", "Project Neptune uses llama.cpp" in corrected["response"], corrected)
current = list_entity_association_records()[0]
check("durable object is corrected", current["object"] == "llama.cpp" and current["state"] == "active", current)
try:
    inspect_entity_association(original["association_id"])
    stale_rejected = False
except RelationshipMemoryCurationError:
    stale_rejected = True
check("pre-correction revision is stale", stale_rejected)

same = apply_conversational_entity_association_mutation(
    "Actually Project Neptune uses llama.cpp, not Ollama."
)
check("idempotent correction does not rewrite durable state", not same["mutated"] and same["status"] == "already_current", same)

forget_request = conversation_association_mutation_request("Forget what Project Neptune uses.")
check(
    "natural forget request resolves exact predicate",
    forget_request.recognized and forget_request.action == "retract"
    and forget_request.subject == "Project Neptune" and forget_request.predicate == "uses_provider",
    forget_request,
)
forgotten = apply_conversational_entity_association_mutation("Forget what Project Neptune uses.")
check("conversational forget is reversible retraction", forgotten["mutated"] and forgotten["status"] == "retracted", forgotten)
retracted = list_entity_association_records()[0]
check("retracted record remains inspectable", retracted["state"] == "retracted", retracted)
check("retraction response points to inspector recovery", "restore or permanently delete" in forgotten["response"].lower(), forgotten)

repeat_forget = apply_conversational_entity_association_mutation("Forget what Project Neptune uses.")
check("repeat forget fails truthfully without mutation", not repeat_forget["mutated"] and repeat_forget["status"] == "not_found", repeat_forget)
restored = update_entity_association(retracted["association_id"], "restore")["association"]
check("inspector can restore conversational retraction", restored["state"] == "active", restored)

runtime_result = run_conversation_turn(
    "Actually Project Neptune uses LocalAI, not llama.cpp.", use_ai=False,
)
runtime_record = list_entity_association_records()[0]
check(
    "provider-free runtime returns actual correction result",
    runtime_result.success and runtime_result.provider_request_count == 0
    and runtime_result.completion_state == "grounded_immediate_context"
    and "Project Neptune uses LocalAI" in runtime_result.response,
    runtime_result.response,
)
check("provider-free runtime commits durable correction", runtime_record["object"] == "LocalAI", runtime_record)

unknown = apply_conversational_entity_association_mutation("Forget what Project Unknown uses.")
check("unknown association is not claimed as changed", unknown["handled"] and not unknown["mutated"] and unknown["status"] == "not_found", unknown)
ambiguous = apply_conversational_entity_association_mutation("Forget associations.")
check("ambiguous forget fails closed", ambiguous["handled"] and not ambiguous["mutated"] and ambiguous["status"] == "ambiguous", ambiguous)
delete_request = conversation_association_mutation_request("Delete Project Neptune permanently.")
check("permanent delete language is not silently executed", not delete_request.recognized, delete_request)

file_request = conversation_association_mutation_request("Forget which project main.py belongs to.")
check("file-project forget request is structured", file_request.predicate == "belongs_to_project" and file_request.subject == "main.py", file_request)
preference_request = conversation_association_mutation_request("Forget what I prefer.")
check("provider-preference forget request is structured", preference_request.subject == "the user" and preference_request.predicate == "prefers_provider", preference_request)

dashboard_source = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
console_source = (ROOT / "conscious_agent" / "dashboard_chat_console.py").read_text(encoding="utf-8")
runtime_source = (ROOT / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
check("action redirect preserves query", 'target += "?" + referer_parts.query' in dashboard_source)
check("association actions return to exact panel", 'target += "#chat-entity-association-curation"' in dashboard_source)
check("association drawer state is persisted", console_source.count("'chat-entity-association-curation'") >= 2)
check("association form exposes immediate working feedback", "Updating the selected stored association" in console_source)
check("hash target opens collapsed ancestors", "if (ancestor.tagName === 'DETAILS') ancestor.open = true" in console_source)
check("both runtimes route actual mutation response", runtime_source.count('mutation_result.get("response")') == 2)
check("mutation executes once per user-memory store", runtime_source.count("apply_conversational_entity_association_mutation(message)") == 1)

summary = {
    "handled": corrected["handled"],
    "mutated": corrected["mutated"],
    "status": corrected["status"],
    "provider_contacted": corrected["provider_contacted"],
    "authority_granted": corrected["authority_granted"],
    "content_free_receipt": corrected["content_free_receipt"],
}
serialized = json.dumps(summary, sort_keys=True)
check(
    "public mutation receipt is content-free and authority-inert",
    summary["provider_contacted"] is False and summary["authority_granted"] is False
    and all(value not in serialized for value in ("Project Neptune", "Ollama", "llama.cpp")),
    summary,
)
verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check("v1500.5 suite registered exactly once", verifier.count("v1500_5_conversational_association_governance_tests.py") == 1)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.5-conversational-association-governance",
    "provider_contacted": False,
    "permanent_delete_executed": False,
    "authority_granted": False,
})
if failed:
    raise SystemExit(1)
