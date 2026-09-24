from __future__ import annotations

"""Identities, bindings and the frozen schedule for the prospective G-ROUTE2 experiment.

G-ROUTE2 reuses the G-ROUTE1 fixture corpus and evaluator-only gold byte-for-byte
and binds their digests, so the transport contrast is a within-corpus contrast and
not a corpus change. G-ROUTE1 itself is read-only here and is never modified.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from g_route1_contract import (DATA as G_ROUTE1_DATA, MODEL_TIERS, RISK_CLASSES, ROOT,
                               TASK_CLASSES, canonical_digest, digest_file, load_corpus, load_gold)

CONTRACT_VERSION = "g-route2.execution-contract.v1"
DATA = ROOT / "experiments" / "G-ROUTE2-candidate"
CORPUS_PATH = G_ROUTE1_DATA / "corpus.json"
GOLD_PATH = G_ROUTE1_DATA / "gold.json"
PROMPT_PROFILES_PATH = G_ROUTE1_DATA / "prompt_profiles.json"
MODEL_BINDINGS_PATH = DATA / "model_bindings.json"
THRESHOLDS_PATH = DATA / "thresholds.json"
SCHEDULE_PATH = DATA / "schedule.json"
EXECUTION_FREEZE_PATH = DATA / "EXECUTION_FREEZE_CANDIDATE.json"

EXPECTED_CALLS = 216
EXPECTED_FIXTURES = 24
EXPECTED_REPEATS = 3
TIER_ORDER = ("small", "mid", "large")
SEED_BASE = 42000
SCHEDULE_SALT = "G-ROUTE2"

# The inherited scientific content, bound by digest so reuse is provable.
INHERITED = {
    "corpus_id": "G-ROUTE1-FIXTURES-R1",
    "gold_id": "G-ROUTE1-GOLD-R1",
    "corpus_sha256": "57f74610f6836eeb1586c5c7bed59de0c324055d3d119f059ec667c30a00ee79",
    "gold_sha256": "176ea8d6c75ea35fe21b9583944e9876196b93c62df298600babdc2b4e57e72d",
    "prompt_profiles_sha256": "f54e85795a3bf972b8593a28644f9229aea21f61327e324db4af518bc9c368b8",
    "validators_sha256": "64ae53f4510828e1ec8275dc1ef1e6d6fd6bc5fa9b2600116ec9afd32643850d",
    "operational_validator_sha256": "07cbc8c60c1255bdae222c394a7046adad3ed56131d3d30c9071f4832291b0b4",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def json_digest(value: Any) -> str:
    return canonical_digest(canonical_json(value))


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_inherited_scientific_content() -> None:
    """Fail closed if the reused corpus, gold, prompts or validators have drifted."""
    actual = {
        "corpus_sha256": digest_file(CORPUS_PATH),
        "gold_sha256": digest_file(GOLD_PATH),
        "prompt_profiles_sha256": digest_file(PROMPT_PROFILES_PATH),
        "validators_sha256": digest_file(ROOT / "tools" / "g_route1_validators.py"),
        "operational_validator_sha256": digest_file(ROOT / "tools" / "g_route1_operational.py"),
    }
    drift = sorted(key for key, value in actual.items() if INHERITED[key] != value)
    if drift:
        raise ValueError("inherited_scientific_content_drift:" + ",".join(drift))
    corpus, gold = load_corpus(CORPUS_PATH), load_gold(GOLD_PATH)
    if corpus["corpus_id"] != INHERITED["corpus_id"] or gold["gold_id"] != INHERITED["gold_id"]:
        raise ValueError("inherited_identity_mismatch")
    if gold.get("model_input") is not False or corpus.get("model_input_contains_gold") is not False:
        raise ValueError("gold_exposure")


def load_model_bindings(path: str | Path = MODEL_BINDINGS_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    if payload.get("schema_version") != "g-route2.model-bindings.v1":
        raise ValueError("model_binding_schema_mismatch")
    rows = list(payload.get("bindings") or [])
    if [row.get("tier") for row in rows] != list(TIER_ORDER):
        raise ValueError("model_tier_binding_mismatch")
    config = payload.get("generation_configuration") or {}
    if config.get("retry_limit") != 0 or config.get("fresh_session_per_call") is not True:
        raise ValueError("model_generation_policy_mismatch")
    if config.get("silent_fallback") is not False or config.get("output_repair_calls") != 0:
        raise ValueError("model_fallback_or_repair_enabled")
    return payload


def load_thresholds(path: str | Path = THRESHOLDS_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    if payload.get("schema_version") != "g-route2.qualification-thresholds.v1":
        raise ValueError("threshold_schema_mismatch")
    if payload.get("vacuous_pass_allowed") is not False:
        raise ValueError("vacuous_pass_enabled")
    if payload.get("expected_observations_per_cell") != EXPECTED_REPEATS:
        raise ValueError("threshold_denominator_mismatch")
    if payload.get("structural_validity_alone_can_qualify") is not False:
        raise ValueError("structural_only_qualification_enabled")
    if payload.get("thresholds_frozen_before_provider_contact") is not True:
        raise ValueError("thresholds_not_frozen_before_contact")
    return payload


@dataclass(frozen=True)
class ScheduledCall:
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
    routing_policy_contract: str
    validator_contract: str
    scoring_lineage: str


def build_schedule() -> list[ScheduledCall]:
    verify_inherited_scientific_content()
    corpus = load_corpus(CORPUS_PATH)
    bindings_doc = load_model_bindings()
    bindings = {row["tier"]: row for row in bindings_doc["bindings"]}
    config_digest = json_digest(bindings_doc["generation_configuration"])
    profiles = load_json(PROMPT_PROFILES_PATH)["profiles"]
    groups: list[tuple[int, dict[str, Any], int]] = []
    for fixture_index, fixture in enumerate(corpus["fixtures"]):
        for repeat in range(1, EXPECTED_REPEATS + 1):
            groups.append((fixture_index, fixture, repeat))
    groups.sort(key=lambda row: canonical_digest(f"{SCHEDULE_SALT}|{row[1]['fixture_id']}|{row[2]}"))
    calls: list[ScheduledCall] = []
    for fixture_index, fixture, repeat in groups:
        rotation = (fixture_index + repeat - 1) % len(TIER_ORDER)
        tiers = TIER_ORDER[rotation:] + TIER_ORDER[:rotation]
        seed = SEED_BASE + fixture_index * EXPECTED_REPEATS + repeat
        for tier in tiers:
            binding = bindings[tier]
            profile = fixture["validator_profile"]
            calls.append(ScheduledCall(
                position=len(calls) + 1,
                call_id=f"GROUTE2-{fixture['fixture_id']}-R{repeat}-{tier}",
                fixture_id=fixture["fixture_id"], task_class=fixture["task_class"],
                risk_class=fixture["consequence_risk"], model_tier=tier,
                model=binding["model"], model_manifest_digest=binding["manifest_digest"],
                model_config_digest=config_digest, repeat=repeat, seed=seed,
                prompt_profile=profile,
                prompt_template_digest=json_digest({
                    "system": profiles[profile], "prompt": fixture["prompt"], "input": fixture["input"],
                }),
                normalization_contract="g-route2.transport-normalization.v1",
                routing_policy_contract="g-route2.routing-policy.v1",
                validator_contract="g-route1.validators.v1",
                scoring_lineage="G-ROUTE1-GOLD-R1:g-route2.scorer.v1",
            ))
    validate_schedule([asdict(row) for row in calls])
    return calls


def validate_schedule(rows: list[Mapping[str, Any]]) -> None:
    if len(rows) != EXPECTED_CALLS:
        raise ValueError("schedule_call_count_mismatch")
    ids = [str(row.get("call_id") or "") for row in rows]
    if len(set(ids)) != EXPECTED_CALLS:
        raise ValueError("schedule_duplicate_call_id")
    if [row.get("position") for row in rows] != list(range(1, EXPECTED_CALLS + 1)):
        raise ValueError("schedule_position_mismatch")
    if any(str(row.get("call_id") or "").startswith("GROUTE1-") for row in rows):
        raise ValueError("schedule_namespace_collision_with_g_route1")
    corpus = load_corpus(CORPUS_PATH)
    expected = {
        (fixture["fixture_id"], tier, repeat)
        for fixture in corpus["fixtures"] for tier in TIER_ORDER
        for repeat in range(1, EXPECTED_REPEATS + 1)
    }
    if {(row.get("fixture_id"), row.get("model_tier"), row.get("repeat")) for row in rows} != expected:
        raise ValueError("schedule_cell_coverage_mismatch")
    for fixture in corpus["fixtures"]:
        subset = [row for row in rows if row.get("fixture_id") == fixture["fixture_id"]]
        first_counts = {tier: 0 for tier in TIER_ORDER}
        for repeat in range(1, EXPECTED_REPEATS + 1):
            ordered = sorted((row for row in subset if row.get("repeat") == repeat), key=lambda row: row["position"])
            first_counts[ordered[0]["model_tier"]] += 1
        if set(first_counts.values()) != {1}:
            raise ValueError(f"schedule_fixture_order_imbalance:{fixture['fixture_id']}")


def schedule_payload() -> dict[str, Any]:
    rows = [asdict(row) for row in build_schedule()]
    return {
        "schema_version": "g-route2.schedule.v1", "schedule_id": "G-ROUTE2-SCHEDULE-R1",
        "algorithm": "sha256_fixture_repeat_groups_with_rotating_tier_order",
        "seed_base": SEED_BASE, "schedule_salt": SCHEDULE_SALT,
        "independent_of_g_route1_seeds": True,
        "planned_calls": EXPECTED_CALLS, "fresh_session_per_call": True,
        "transport_retry_limit": 0, "output_repair_calls": 0,
        "calls": rows, "schedule_content_sha256": json_digest(rows),
        "provider_generation_calls": 0, "belief_effects": "none",
    }


def write_schedule(path: str | Path = SCHEDULE_PATH) -> dict[str, Any]:
    payload = schedule_payload()
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    target = Path(path)
    if target.exists() and target.read_text(encoding="utf-8") != rendered:
        raise FileExistsError("conflicting_schedule_exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8", newline="\n")
    return payload


def render_prompt(fixture: Mapping[str, Any]) -> dict[str, str]:
    profiles = load_json(PROMPT_PROFILES_PATH)["profiles"]
    profile = str(fixture["validator_profile"])
    user = str(fixture["prompt"]) + "\n\nINPUT:\n" + json.dumps(
        fixture["input"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"system": str(profiles[profile]), "prompt": user}


def request_body(fixture: Mapping[str, Any], call: Mapping[str, Any]) -> dict[str, Any]:
    binding = load_model_bindings()
    prompt = render_prompt(fixture)
    options = dict(binding["generation_configuration"]["options"])
    options["seed"] = int(call["seed"])
    return {"model": call["model"], "system": prompt["system"], "prompt": prompt["prompt"],
            "stream": False, "think": False, "options": options}


__all__ = [
    "CONTRACT_VERSION", "DATA", "CORPUS_PATH", "GOLD_PATH", "PROMPT_PROFILES_PATH",
    "MODEL_BINDINGS_PATH", "THRESHOLDS_PATH", "SCHEDULE_PATH", "EXECUTION_FREEZE_PATH",
    "EXPECTED_CALLS", "EXPECTED_FIXTURES", "EXPECTED_REPEATS", "TIER_ORDER", "INHERITED",
    "MODEL_TIERS", "RISK_CLASSES", "TASK_CLASSES", "canonical_json", "json_digest", "load_json",
    "verify_inherited_scientific_content", "load_model_bindings", "load_thresholds",
    "ScheduledCall", "build_schedule", "validate_schedule", "schedule_payload", "write_schedule",
    "render_prompt", "request_body",
]
