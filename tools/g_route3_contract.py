from __future__ import annotations

"""Identities, loaders, schedules and bindings for G-ROUTE3.

Two corpora are kept apart by construction. Model-facing fixtures and evaluator-only
gold are separate files, gold is loaded only by the scorers and only for the corpus
being scored, and nothing in the collection or routing path can load gold at all.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from g_route1_contract import ROOT, canonical_digest

CONTRACT_VERSION = "g-route3.execution-contract.v1"
DATA = ROOT / "experiments" / "G-ROUTE3-candidate"
PROMPT_PROFILES_PATH = ROOT / "experiments" / "G-ROUTE1-candidate" / "prompt_profiles.json"
MODEL_BINDINGS_PATH = DATA / "model_bindings.json"
THRESHOLDS_PATH = DATA / "thresholds.json"
EXECUTION_FREEZE_PATH = DATA / "EXECUTION_FREEZE_CANDIDATE.json"
QUALIFICATION_TABLE_PATH = DATA / "QUALIFICATION_TABLE.json"

CORPORA = ("A", "B")
TASK_CLASSES = ("ordinary_conversation", "structured_extraction", "grounded_research_synthesis",
                "hierarchical_semantic_synthesis", "coding_generation_repair", "reflective_planning")
RISK_CLASSES = ("R1", "R2", "R3", "R4")
TIER_ORDER = ("small", "mid", "large")
FIXTURES_PER_CELL = 2
EXPECTED_FIXTURES = 48
REPEATS = {"A": 2, "B": 1}
SEED_BASE = {"A": 43000, "B": 44000}
SCHEDULE_SALT = {"A": "G-ROUTE3-A", "B": "G-ROUTE3-B"}
EXPECTED_CALLS = {corpus: EXPECTED_FIXTURES * len(TIER_ORDER) * REPEATS[corpus] for corpus in CORPORA}


def corpus_path(corpus: str) -> Path:
    return DATA / f"corpus_{_corpus(corpus).lower()}.json"


def gold_path(corpus: str) -> Path:
    return DATA / f"gold_{_corpus(corpus).lower()}.json"


def schedule_path(corpus: str) -> Path:
    return DATA / f"schedule_{_corpus(corpus).lower()}.json"


def _corpus(corpus: str) -> str:
    if corpus not in CORPORA:
        raise ValueError(f"unknown_corpus:{corpus}")
    return corpus


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def json_digest(value: Any) -> str:
    return canonical_digest(canonical_json(value))


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_corpus(corpus: str) -> dict[str, Any]:
    payload = dict(load_json(corpus_path(corpus)))
    fixtures = list(payload.get("fixtures") or [])
    if payload.get("schema_version") != "g-route3.fixture-corpus.v1":
        raise ValueError("corpus_schema_mismatch")
    if payload.get("corpus_id") != f"G-ROUTE3-CORPUS-{corpus}":
        raise ValueError("corpus_identity_mismatch")
    if payload.get("model_input_contains_gold") is not False:
        raise ValueError("corpus_gold_exposure")
    if len(fixtures) != EXPECTED_FIXTURES:
        raise ValueError("corpus_fixture_count_mismatch")
    ids = [str(row.get("fixture_id") or "") for row in fixtures]
    if len(set(ids)) != EXPECTED_FIXTURES or any(not item.startswith(corpus + "-") for item in ids):
        raise ValueError("corpus_namespace_violation")
    required = {"fixture_id", "task_class", "consequence_risk", "title", "validator_profile", "prompt", "input"}
    cells: dict[tuple[str, str], int] = {}
    for row in fixtures:
        if set(row) != required:
            raise ValueError(f"corpus_fixture_schema_mismatch:{row.get('fixture_id')}")
        if row["task_class"] not in TASK_CLASSES or row["consequence_risk"] not in RISK_CLASSES:
            raise ValueError(f"corpus_class_mismatch:{row['fixture_id']}")
        key = (row["task_class"], row["consequence_risk"])
        cells[key] = cells.get(key, 0) + 1
    if len(cells) != 24 or set(cells.values()) != {FIXTURES_PER_CELL}:
        raise ValueError("corpus_cell_balance_mismatch")
    return payload


def load_gold(corpus: str) -> dict[str, Any]:
    """Evaluator-only. Never call from collection or routing code."""
    payload = dict(load_json(gold_path(corpus)))
    if payload.get("schema_version") != "g-route3.gold.v1" or payload.get("gold_id") != f"G-ROUTE3-GOLD-{corpus}":
        raise ValueError("gold_identity_mismatch")
    if payload.get("model_input") is not False:
        raise ValueError("gold_marked_as_model_input")
    items = list(payload.get("items") or [])
    if len(items) != EXPECTED_FIXTURES or any(not str(row.get("fixture_id")).startswith(corpus + "-") for row in items):
        raise ValueError("gold_namespace_violation")
    return payload


def runtime_fixtures(corpus: str) -> dict[str, dict[str, Any]]:
    """Model-facing fixtures only. This is all the collection and routing path may see."""
    return {row["fixture_id"]: row for row in load_corpus(corpus)["fixtures"]}


def indexed_fixture_gold(corpus: str) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    """Evaluator-only pairing of fixtures with gold for one corpus."""
    fixtures = runtime_fixtures(corpus)
    gold = {row["fixture_id"]: row for row in load_gold(corpus)["items"]}
    if set(fixtures) != set(gold):
        raise ValueError("corpus_gold_identity_mismatch")
    return {key: (fixtures[key], gold[key]) for key in fixtures}


def load_model_bindings(path: str | Path = MODEL_BINDINGS_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    if payload.get("schema_version") != "g-route3.model-bindings.v1":
        raise ValueError("model_binding_schema_mismatch")
    if [row.get("tier") for row in payload.get("bindings") or []] != list(TIER_ORDER):
        raise ValueError("model_tier_binding_mismatch")
    config = payload.get("generation_configuration") or {}
    if config.get("retry_limit") != 0 or config.get("fresh_session_per_call") is not True:
        raise ValueError("model_generation_policy_mismatch")
    if config.get("silent_fallback") is not False or config.get("output_repair_calls") != 0:
        raise ValueError("model_fallback_or_repair_enabled")
    return payload


def load_thresholds(path: str | Path = THRESHOLDS_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    if payload.get("schema_version") != "g-route3.thresholds.v1":
        raise ValueError("threshold_schema_mismatch")
    if payload.get("thresholds_frozen_before_provider_contact") is not True:
        raise ValueError("thresholds_not_frozen_before_contact")
    qualification = payload.get("qualification") or {}
    if qualification.get("vacuous_pass_allowed") is not False or qualification.get("missing_data_may_qualify") is not False:
        raise ValueError("vacuous_or_missing_data_qualification_enabled")
    if qualification.get("observations_required") != FIXTURES_PER_CELL * REPEATS["A"]:
        raise ValueError("qualification_denominator_mismatch")
    return payload


@dataclass(frozen=True)
class ScheduledCall:
    corpus: str
    position: int
    call_id: str
    fixture_id: str
    task_class: str
    risk_class: str
    model_tier: str
    model: str
    model_manifest_digest: str
    model_config_digest: str
    repeat: int
    seed: int
    prompt_profile: str
    prompt_template_digest: str
    normalization_contract: str
    validator_contract: str


def build_schedule(corpus: str) -> list[ScheduledCall]:
    fixtures = load_corpus(corpus)["fixtures"]
    bindings_doc = load_model_bindings()
    bindings = {row["tier"]: row for row in bindings_doc["bindings"]}
    config_digest = json_digest(bindings_doc["generation_configuration"])
    profiles = load_json(PROMPT_PROFILES_PATH)["profiles"]
    groups = [(index, fixture, repeat) for index, fixture in enumerate(fixtures)
              for repeat in range(1, REPEATS[corpus] + 1)]
    groups.sort(key=lambda row: canonical_digest(f"{SCHEDULE_SALT[corpus]}|{row[1]['fixture_id']}|{row[2]}"))
    calls: list[ScheduledCall] = []
    for group_index, (fixture_index, fixture, repeat) in enumerate(groups):
        rotation = group_index % len(TIER_ORDER)
        for tier in TIER_ORDER[rotation:] + TIER_ORDER[:rotation]:
            binding = bindings[tier]
            profile = fixture["validator_profile"]
            calls.append(ScheduledCall(
                corpus=corpus, position=len(calls) + 1,
                call_id=f"GROUTE3-{fixture['fixture_id']}-R{repeat}-{tier}",
                fixture_id=fixture["fixture_id"], task_class=fixture["task_class"],
                risk_class=fixture["consequence_risk"], model_tier=tier, model=binding["model"],
                model_manifest_digest=binding["manifest_digest"], model_config_digest=config_digest,
                repeat=repeat, seed=SEED_BASE[corpus] + fixture_index * 10 + repeat,
                prompt_profile=profile,
                prompt_template_digest=json_digest({"system": profiles[profile], "prompt": fixture["prompt"],
                                                    "input": fixture["input"]}),
                normalization_contract="g-route2.transport-normalization.v1",
                validator_contract="g-route1.validators.v1",
            ))
    validate_schedule(corpus, [asdict(row) for row in calls])
    return calls


def validate_schedule(corpus: str, rows: list[Mapping[str, Any]]) -> None:
    if len(rows) != EXPECTED_CALLS[corpus]:
        raise ValueError("schedule_call_count_mismatch")
    if len({row["call_id"] for row in rows}) != len(rows):
        raise ValueError("schedule_duplicate_call_id")
    if [row["position"] for row in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("schedule_position_mismatch")
    if any(row["corpus"] != corpus or not str(row["fixture_id"]).startswith(corpus + "-") for row in rows):
        raise ValueError("schedule_corpus_mixing")
    fixtures = [row["fixture_id"] for row in load_corpus(corpus)["fixtures"]]
    expected = {(fid, tier, repeat) for fid in fixtures for tier in TIER_ORDER
                for repeat in range(1, REPEATS[corpus] + 1)}
    if {(row["fixture_id"], row["model_tier"], row["repeat"]) for row in rows} != expected:
        raise ValueError("schedule_coverage_mismatch")
    leaders: dict[str, int] = {tier: 0 for tier in TIER_ORDER}
    for index in range(0, len(rows), len(TIER_ORDER)):
        leaders[rows[index]["model_tier"]] += 1
    if max(leaders.values()) - min(leaders.values()) > 1:
        raise ValueError("schedule_leading_tier_imbalance")


def schedule_payload(corpus: str) -> dict[str, Any]:
    rows = [asdict(row) for row in build_schedule(corpus)]
    return {"schema_version": "g-route3.schedule.v1", "schedule_id": f"G-ROUTE3-SCHEDULE-{corpus}",
            "corpus": corpus, "seed_base": SEED_BASE[corpus], "repeats": REPEATS[corpus],
            "planned_calls": EXPECTED_CALLS[corpus], "fresh_session_per_call": True,
            "transport_retry_limit": 0, "output_repair_calls": 0, "calls": rows,
            "schedule_content_sha256": json_digest(rows), "provider_generation_calls": 0,
            "belief_effects": "none"}


def write_schedule(corpus: str) -> dict[str, Any]:
    payload = schedule_payload(corpus)
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    target = schedule_path(corpus)
    if target.exists() and target.read_text(encoding="utf-8") != rendered:
        raise FileExistsError("conflicting_schedule_exists")
    target.write_text(rendered, encoding="utf-8", newline="\n")
    return payload


def verify_checked_schedule(corpus: str) -> list[dict[str, Any]]:
    checked = load_json(schedule_path(corpus))
    rows = list(checked.get("calls") or [])
    validate_schedule(corpus, rows)
    if rows != [asdict(row) for row in build_schedule(corpus)] or checked.get("schedule_content_sha256") != json_digest(rows):
        raise ValueError("checked_schedule_drift")
    return rows


def render_prompt(fixture: Mapping[str, Any]) -> dict[str, str]:
    profiles = load_json(PROMPT_PROFILES_PATH)["profiles"]
    user = str(fixture["prompt"]) + "\n\nINPUT:\n" + json.dumps(
        fixture["input"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"system": str(profiles[str(fixture["validator_profile"])]), "prompt": user}


def request_body(fixture: Mapping[str, Any], call: Mapping[str, Any]) -> dict[str, Any]:
    prompt = render_prompt(fixture)
    options = dict(load_model_bindings()["generation_configuration"]["options"])
    options["seed"] = int(call["seed"])
    return {"model": call["model"], "system": prompt["system"], "prompt": prompt["prompt"],
            "stream": False, "think": False, "options": options}


__all__ = [name for name in dir() if not name.startswith("_") and name not in {"annotations", "asdict", "dataclass",
                                                                               "json", "Path", "Any", "Mapping"}]
