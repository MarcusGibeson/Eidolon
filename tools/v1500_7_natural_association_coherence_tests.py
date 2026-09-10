from __future__ import annotations

"""Focused v1500.7 natural association and coherence regression checks."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)

from active_conversation_facts import resolve_active_conversation_facts
from conversation_entity_associations import (
    build_conversation_association_graph,
    conversation_association_prompt_block,
    resolve_conversation_association_query,
)
from entity_association_graph import EntityAssociationGraph
from family_relationship_graph import (
    build_family_graph,
    edges_from_durable_memories,
    family_entity_association_graph,
    family_prompt_block,
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


family_history = [
    {
        "user_message": (
            "Please remember that Bobbie is my biological mother, Reuben Gibeson is my biological father, "
            "Bobbie is Reuben Gibeson's ex-wife, Danielle is my stepmother, and Danielle is married to Reuben Gibeson."
        )
    },
    {"user_message": "My fiancee's name is Melissa."},
    {"user_message": "My stepdaughter's name is Jordyn. Jordyn is Melissa's biological daughter."},
]

mom = resolve_active_conversation_facts("Who is my mom to Melissa?", family_history)
check("natural role alias resolves before relationship reasoning", mom.response.startswith("Bobbie is Melissa's future mother-in-law"), mom.response)
check("role alias query remains provider-free deterministic grounding", mom.state == "derived_user_attributable_relationship", mom.state)

dad = resolve_active_conversation_facts("How is my dad related to Danielle?", family_history)
check("natural related-to wording resolves spouse inverse", dad.response.startswith("Reuben Gibeson is Danielle's spouse"), dad.response)

directional = resolve_active_conversation_facts("Who is Jordyn to my dad?", family_history)
check("directional kinship answer keeps requested subject first", directional.response.startswith("Jordyn is Reuben Gibeson's step-granddaughter"), directional.response)

query_edges = build_family_graph(family_history, current_message="Who is my mom to Melissa?")
check("relationship questions never become family evidence", all(edge.subject.casefold() != "who" for edge in query_edges), query_edges)

relevant = resolve_active_conversation_facts("I had dinner with Melissa.", family_history)
check("mentioned person receives connected attributable context", "Melissa is fiancee" in relevant.prompt_block, relevant.prompt_block)
check("relevant context includes one-hop family association", "Jordyn is biological daughter of Melissa" in relevant.prompt_block, relevant.prompt_block)

unrelated = resolve_active_conversation_facts("Tell me a joke about traffic.", family_history)
check("unrelated casual turn omits personal association payload", "FAMILY RELATIONSHIPS" not in unrelated.prompt_block and "ACTIVE CONVERSATION FACTS" not in unrelated.prompt_block, unrelated.prompt_block)


def curated(content: str, key: str) -> dict[str, object]:
    return {
        "record_key": key,
        "type": "relationship",
        "content": content,
        "state": "active",
        "provenance": {
            "available": True,
            "operator_explicit": True,
            "source": "operator_explicit_conversation_memory_request",
        },
    }


durable = (
    curated("Family relationship: Alice | biological_mother | the user.", "old"),
    curated("Family relationship: Bobbie | biological_mother | the user.", "new"),
)
durable_edges = build_family_graph((), durable)
check("newer durable single-value role supersedes older role", any(edge.subject == "Bobbie" and edge.relation == "biological_mother" for edge in durable_edges), durable_edges)
check("superseded durable parent is absent from active projection", not any(edge.subject == "Alice" and edge.relation == "biological_mother" for edge in durable_edges), durable_edges)

private_graph = family_entity_association_graph(edges_from_durable_memories(durable))
check("family graph keeps one active biological mother", len(private_graph.active_edges(predicate="biological_mother")) == 1, private_graph.export_private())

unknown = resolve_active_conversation_facts("Who is Alice to Melissa?", family_history)
check("unsupported natural relation remains explicitly uncertain", "don't have enough attributable family information" in unknown.response, unknown.response)

association_history = [
    {"user_message": "Eidolon uses Ollama."},
    {"user_message": "What does Eidolon use?"},
]
followup = resolve_conversation_association_query("What does it use?", association_history)
check("singular association follow-up resolves latest attributable subject", followup.response == "You told me Eidolon uses Ollama.", followup)
check("follow-up exposes explicit resolved state", followup.state == "resolved_user_attributable_followup", followup)

ambiguous = resolve_conversation_association_query(
    "What does it use?",
    [{"user_message": "Eidolon uses Ollama and Project Neptune uses llama.cpp."}],
)
check("ambiguous association pronoun fails closed", ambiguous.state == "association_reference_uncertain", ambiguous)

assistant_only = resolve_conversation_association_query(
    "What does it use?",
    [{"user_message": "Sounds good.", "assistant_response": "Eidolon uses Ollama."}],
)
check("assistant-authored association cannot resolve pronoun", assistant_only.state == "association_reference_uncertain", assistant_only)

association_graph = build_conversation_association_graph([
    {"user_message": "Project Atlas uses Ollama."},
    {"user_message": "Project Neptune uses llama.cpp."},
])
atlas_prompt = conversation_association_prompt_block(association_graph, "I was looking at Project Atlas today.")
check("general association prompt selects mentioned entity", "Project Atlas uses provider Ollama" in atlas_prompt, atlas_prompt)
check("general association prompt omits unrelated entity", "Project Neptune" not in atlas_prompt, atlas_prompt)
check("general association prompt is absent for unrelated chat", not conversation_association_prompt_block(association_graph, "How was your morning?"))

family_block = family_prompt_block(build_family_graph(family_history), "Melissa had a long day.")
check("family prompt selects named person's neighborhood", "Melissa is fiancee" in family_block and "Bobbie is biological mother" not in family_block, family_block)

graph = EntityAssociationGraph()
graph.add_entity("the user", entity_kind="operator")
graph.add_entity("Alice", entity_kind="person")
graph.add_entity("Bobbie", entity_kind="person")
graph.add_association("Alice", "biological_mother", "the user", source_offset=1, replace_object_predicate=True)
graph.add_association("Bobbie", "biological_mother", "the user", source_offset=2, explicit_correction=True, replace_object_predicate=True)
check("object-predicate correction activates replacement entity", graph.direct("Bobbie", "the user", predicate="biological_mother") is not None)
check("object-predicate correction deactivates conflicting entity", graph.direct("Alice", "the user", predicate="biological_mother") is None)
check("superseded correction history remains inspectable", graph.public_summary()["superseded_edge_count"] == 1, graph.public_summary())

summary = graph.public_summary()
serialized = json.dumps(summary, sort_keys=True)
check("public graph evidence remains content-free", all(value not in serialized for value in ("Alice", "Bobbie", "Melissa", "Jordyn")), summary)
check("association reasoning grants no authority or provider contact", summary["authority_granted"] is False and summary["provider_contacted"] is False, summary)

verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check("v1500.7 suite registered exactly once", verifier.count("v1500_7_natural_association_coherence_tests.py") == 1)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.7-natural-association-coherence",
    "provider_contacted": False,
    "source_mutated": False,
    "authority_granted": False,
    "content_free_public_evidence": True,
})
if failed:
    raise SystemExit(1)
