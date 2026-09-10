from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ.setdefault("EIDOLON_DATA_DIR", str(Path(tempfile.gettempdir()) / "eidolon-v1500-3-tests"))
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent.active_conversation_facts import resolve_active_conversation_facts
from conscious_agent.conversation_entity_associations import (
    associations_from_durable_memories,
    associations_from_text,
    build_conversation_association_graph,
    conversation_association_memory_acknowledgement,
    conversation_association_prompt_block,
    conversation_association_statement_acknowledgement,
    durable_conversation_association_records,
    resolve_conversation_association_query,
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


uses = associations_from_text("Project Atlas uses Ollama.", offset=1)
check("project provider statement extracted", len(uses) == 1 and uses[0].predicate == "uses_provider")
belongs = associations_from_text("app.js belongs to Project Atlas.", offset=2)
check("file project statement extracted", len(belongs) == 1 and belongs[0].predicate == "belongs_to_project")
contains = associations_from_text("Project Atlas contains app.js.", offset=3)
check("project content statement extracted", len(contains) == 1 and contains[0].predicate == "contains")
owns = associations_from_text("I own Project Atlas.", offset=4)
check("operator ownership statement extracted", len(owns) == 1 and owns[0].object == "the user")
preferred = associations_from_text("My preferred provider is Ollama.", offset=5)
check("provider preference statement extracted", len(preferred) == 1 and preferred[0].predicate == "prefers_provider")
comparison = associations_from_text("I prefer Ollama over llama.cpp.", offset=6)
check("comparative preference statement extracted", len(comparison) == 1 and comparison[0].object == "llama.cpp")
correction = associations_from_text("Actually Project Atlas uses llama.cpp, not Ollama.", offset=7)
check("explicit correction is marked", len(correction) == 1 and correction[0].explicit_correction)
check("action language is not association evidence", not associations_from_text("Install Ollama for Project Atlas.", offset=8))
check("secret language is not association evidence", not associations_from_text("Remember that Project Atlas uses API key abc.", offset=9))

history = [
    {"user_message": "Project Atlas uses Ollama.", "assistant_response": "Project Atlas uses FakeProvider."},
    {"user_message": "app.js belongs to Project Atlas."},
    {"user_message": "I own Project Atlas."},
    {"user_message": "My preferred provider is Ollama."},
]
graph = build_conversation_association_graph(history)
check("project alias resolves", graph.resolve("Atlas").entity_id == graph.resolve("Project Atlas").entity_id)
check("assistant text is not evidence", graph.resolve("FakeProvider").status == "not_found")
check("direct provider edge exists", graph.direct("Atlas", "Ollama", predicate="uses_provider") is not None)
check("bounded path connects file to provider", bool(graph.paths("app.js", "Ollama", max_depth=2)))

corrected_graph = build_conversation_association_graph(history + [{"user_message": "Actually Project Atlas uses llama.cpp, not Ollama."}])
check("new provider correction is active", corrected_graph.direct("Atlas", "llama.cpp", predicate="uses_provider") is not None)
check("old provider edge is superseded", corrected_graph.direct("Atlas", "Ollama", predicate="uses_provider") is None)
check("superseded edge remains in private history", corrected_graph.public_summary()["superseded_edge_count"] == 1)

queries = {
    "What does Project Atlas use?": "Project Atlas uses Ollama",
    "Which project does app.js belong to?": "app.js belongs to Project Atlas",
    "Who owns Project Atlas?": "you own Project Atlas",
    "What do I prefer?": "preferred provider is Ollama",
}
for query, expected in queries.items():
    answer = resolve_conversation_association_query(query, history)
    check(f"grounded query: {query}", expected in answer.response and answer.evidence_count >= 1, answer)

unknown = resolve_conversation_association_query("What does Project Nova use?", history)
check("unsupported query fails with uncertainty", unknown.state == "association_uncertain" and "don't have enough" in unknown.response)

durable_row = {
    "type": "personal_fact",
    "content": "Entity association: Project Atlas | uses_provider | Ollama.",
    "source": "operator_explicit_conversation_memory_request",
    "curation_state": "active",
    "use_in_conversation": True,
    "curation_provenance": {"operator_explicit": True},
}
durable = associations_from_durable_memories([durable_row])
check("explicit durable association is accepted", len(durable) == 1 and durable[0].subject == "Project Atlas")
inactive = dict(durable_row, curation_state="retracted")
check("retracted durable association is rejected", not associations_from_durable_memories([inactive]))
assistant_memory = dict(durable_row, source="conversation_eidolon")
check("assistant-authored durable association is rejected", not associations_from_durable_memories([assistant_memory]))

ack = conversation_association_memory_acknowledgement("Remember that Project Atlas uses Ollama.")
check("explicit memory acknowledgement is grounded", ack == "I'll remember that Project Atlas uses provider Ollama.", ack)
records = durable_conversation_association_records("Remember that Project Atlas uses Ollama.")
check("durable record has structured bounded format", records == ["Entity association: Project Atlas | uses_provider | Ollama."])
prompt = conversation_association_prompt_block(graph)
check("prompt carries attributable associations", "Project Atlas uses provider Ollama" in prompt and "FakeProvider" not in prompt)

integrated = resolve_active_conversation_facts("What does Project Atlas use?", history)
check("active conversation returns deterministic association", integrated.response == "You told me Project Atlas uses Ollama.")
check("active conversation classifies association", integrated.state == "direct_user_attributable_association")
check("active conversation prompt includes association block", "USER-ATTRIBUTABLE ENTITY ASSOCIATIONS" in integrated.prompt_block)
remember_integrated = resolve_active_conversation_facts("Remember that Project Atlas uses Ollama.", [])
check("active conversation acknowledges association memory", remember_integrated.fact_kind == "explicit_entity_association_memory_acknowledgement")
check("association memory request is exposed content-free", remember_integrated.durable_memory_requested)
standalone = conversation_association_statement_acknowledgement("main.py belongs to Project Eidolon.")
check("standalone file association has deterministic acknowledgement", standalone == "Got it: main.py belongs to Project Eidolon.", standalone)
standalone_integrated = resolve_active_conversation_facts("main.py belongs to Project Eidolon.", [])
check("standalone acknowledgement bypasses malformed provider paraphrase", standalone_integrated.response == standalone)
mixed = conversation_association_statement_acknowledgement("Project Eidolon uses Ollama, and I'm excited about that.")
check("mixed conversational statement remains on ordinary conversation path", mixed == "")

summary = graph.public_summary()
serialized = json.dumps(summary, sort_keys=True)
check(
    "public receipt remains content-free and authority-inert",
    summary["provider_contacted"] is False and summary["runtime_persisted"] is False
    and summary["authority_granted"] is False
    and all(value not in serialized for value in ("Project Atlas", "app.js", "Ollama")),
    summary,
)
verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check("v1500.3 suite registered exactly once", verifier.count("v1500_3_conversation_entity_association_tests.py") == 1)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.3-conversation-entity-associations",
    "provider_contacted": False,
    "runtime_persisted": False,
    "authority_granted": False,
    "content_free": True,
})
if failed:
    raise SystemExit(1)
