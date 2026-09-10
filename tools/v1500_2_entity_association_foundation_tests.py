from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent.entity_association_graph import EntityAssociationGraph, MAX_PATH_DEPTH
from conscious_agent.family_relationship_graph import (
    FamilyEdge,
    family_entity_association_graph,
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


before = set(Path(tempfile.gettempdir()).glob("eidolon-v1500-2-*"))
graph = EntityAssociationGraph()
project = graph.add_entity(
    "Project Atlas", entity_kind="project", aliases=("Atlas",),
    provenance_class="operator_explicit", evidence_ref="fixture-project",
)
same_project = graph.add_entity("Atlas", entity_kind="project")
check("alias resolves to one canonical entity", project.entity_id == same_project.entity_id)
resolution = graph.resolve("atlas")
check("alias resolution is explicit and unambiguous", resolution.status == "matched" and resolution.resolved_from_alias)

graph.add_entity("app.js", entity_kind="file", provenance_class="source_observed")
graph.add_entity("Ollama", entity_kind="provider", aliases=("local provider",))
belongs = graph.add_association(
    "app.js", "belongs_to", "Project Atlas",
    provenance_class="operator_explicit", evidence_ref="fixture-belongs", source_offset=1,
)
uses = graph.add_association(
    "Project Atlas", "uses_provider", "Ollama",
    provenance_class="operator_explicit", evidence_ref="fixture-provider", source_offset=2,
)
check("typed direct association resolves", graph.direct("app.js", "Atlas", predicate="belongs_to") == belongs)
check("edge retains provenance digest without raw evidence", bool(uses.evidence_digest) and "fixture-provider" not in uses.evidence_digest)

paths = graph.paths("app.js", "local provider", max_depth=3)
check(
    "bounded path traverses file project and provider",
    len(paths) == 1 and paths[0].predicates == ("belongs_to", "uses_provider") and paths[0].depth == 2,
    [path.predicates for path in paths],
)
check("path depth is capped by contract", MAX_PATH_DEPTH == 3 and not graph.paths("app.js", "Ollama", max_depth=1))

graph.add_entity("llama.cpp", entity_kind="provider", aliases=("native server",))
corrected = graph.add_association(
    "Project Atlas", "uses_provider", "llama.cpp",
    provenance_class="operator_correction", evidence_ref="fixture-correction",
    source_offset=3, explicit_correction=True, replace_subject_predicate=True,
)
check("explicit correction becomes active", graph.direct("Atlas", "native server", predicate="uses_provider") == corrected)
check("superseded provider edge is inactive", graph.direct("Atlas", "Ollama", predicate="uses_provider") is None)
private = graph.export_private()
check(
    "superseded history remains inspectable",
    len(private["edges"]) == 3 and sum(not row["active"] for row in private["edges"]) == 1
    and corrected.supersedes_edge_id == uses.edge_id,
)

graph.add_entity("Second Atlas", aliases=("Atlas",), entity_kind="project")
ambiguous = graph.resolve("Atlas")
check("colliding alias fails closed as ambiguous", ambiguous.status == "ambiguous" and not ambiguous.entity_id)

summary = graph.public_summary()
serialized_summary = json.dumps(summary, sort_keys=True)
check(
    "public summary is content-free and authority-inert",
    summary["contains_entity_labels"] is False
    and summary["contains_evidence_text"] is False
    and summary["provider_contacted"] is False
    and summary["runtime_persisted"] is False
    and summary["authority_granted"] is False
    and all(token not in serialized_summary for token in ("Project Atlas", "app.js", "Ollama", "llama.cpp")),
    summary,
)
check(
    "summary counts correction and supersession",
    summary["explicit_correction_count"] == 1 and summary["superseded_edge_count"] == 1,
    summary,
)

family = family_entity_association_graph((
    FamilyEdge("Reuben Gibeson", "father", "the user", 1),
    FamilyEdge("Reuben", "biological_father", "the user", 2, True),
    FamilyEdge("Danielle", "spouse", "Reuben", 1),
))
family_edges = family.active_edges()
check(
    "family bridge shares canonical alias and correction semantics",
    len(family_edges) == 2
    and family.direct("Reuben", "the user", predicate="biological_father") is not None
    and family.direct("Danielle", "Reuben Gibeson", predicate="spouse") is not None,
    family.export_private(),
)

try:
    graph.add_association("A", "not valid!", "B")
    invalid_rejected = False
except ValueError:
    invalid_rejected = True
check("invalid predicate is rejected", invalid_rejected)

after = set(Path(tempfile.gettempdir()).glob("eidolon-v1500-2-*"))
check("graph construction writes no runtime files", before == after)

verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check(
    "v1500.2 suite is registered exactly once",
    verifier.count("v1500_2_entity_association_foundation_tests.py") == 1,
)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.2-entity-association-foundation",
    "provider_contacted": False,
    "runtime_persisted": False,
    "authority_granted": False,
    "content_free": True,
})
if failed:
    raise SystemExit(1)
