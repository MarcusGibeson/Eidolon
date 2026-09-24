from __future__ import annotations

"""Offline identities, request construction, and freeze checks for G-ROUTE1."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from g_route1_contract import DATA, MODEL_TIERS, ROOT, canonical_digest, digest_file, load_corpus
from g_route1_freeze import FREEZE_PATH, verify_manifest as verify_fixture_freeze


CONTRACT_VERSION = "g-route1.execution-contract.v1"
MODEL_BINDINGS_PATH = DATA / "model_bindings.json"
THRESHOLDS_PATH = DATA / "thresholds.json"
SCHEDULE_PATH = DATA / "schedule.json"
EXECUTION_FREEZE_PATH = DATA / "EXECUTION_FREEZE_CANDIDATE.json"
EXPECTED_CALLS = 216
EXPECTED_REPEATS = 3
TIER_ORDER = ("small", "mid", "large")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def json_digest(value: Any) -> str:
    return canonical_digest(canonical_json(value))


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_model_bindings(path: str | Path = MODEL_BINDINGS_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    if payload.get("schema_version") != "g-route1.model-bindings.v1":
        raise ValueError("model_binding_schema_mismatch")
    rows = list(payload.get("bindings") or [])
    if [row.get("tier") for row in rows] != list(TIER_ORDER):
        raise ValueError("model_tier_binding_mismatch")
    if len({row.get("model") for row in rows}) != 3:
        raise ValueError("model_binding_identity_mismatch")
    for row in rows:
        for key in ("manifest_digest", "model_blob_sha256"):
            if len(str(row.get(key) or "")) != 64:
                raise ValueError(f"model_binding_digest_missing:{row.get('tier')}:{key}")
    config = payload.get("generation_configuration") or {}
    if config.get("retry_limit") != 0 or config.get("fresh_session_per_call") is not True:
        raise ValueError("model_generation_policy_mismatch")
    if config.get("silent_fallback") is not False or config.get("output_repair_calls") != 0:
        raise ValueError("model_fallback_or_repair_enabled")
    return payload


def load_thresholds(path: str | Path = THRESHOLDS_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    if payload.get("schema_version") != "g-route1.qualification-thresholds.v1":
        raise ValueError("threshold_schema_mismatch")
    if payload.get("vacuous_pass_allowed") is not False:
        raise ValueError("vacuous_pass_enabled")
    if payload.get("expected_observations_per_cell") != EXPECTED_REPEATS:
        raise ValueError("threshold_denominator_mismatch")
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
    validator_contract: str
    scoring_lineage: str


def build_schedule() -> list[ScheduledCall]:
    corpus = load_corpus()
    bindings = {row["tier"]: row for row in load_model_bindings()["bindings"]}
    config_digest = json_digest(load_model_bindings()["generation_configuration"])
    profiles = load_json(DATA / "prompt_profiles.json")["profiles"]
    calls: list[ScheduledCall] = []
    groups: list[tuple[int, dict[str, Any], int]] = []
    for fixture_index, fixture in enumerate(corpus["fixtures"]):
        for repeat in range(1, EXPECTED_REPEATS + 1):
            groups.append((fixture_index, fixture, repeat))
    groups.sort(key=lambda row: canonical_digest(f"G-ROUTE1|{row[1]['fixture_id']}|{row[2]}"))
    for fixture_index, fixture, repeat in groups:
        rotation = (fixture_index + repeat - 1) % len(TIER_ORDER)
        tiers = TIER_ORDER[rotation:] + TIER_ORDER[:rotation]
        seed = 41000 + fixture_index * EXPECTED_REPEATS + repeat
        for tier in tiers:
            binding = bindings[tier]
            profile = fixture["validator_profile"]
            calls.append(ScheduledCall(
                position=len(calls) + 1,
                call_id=f"GROUTE1-{fixture['fixture_id']}-R{repeat}-{tier}",
                fixture_id=fixture["fixture_id"], task_class=fixture["task_class"],
                risk_class=fixture["consequence_risk"], model_tier=tier,
                model=binding["model"], model_manifest_digest=binding["manifest_digest"],
                model_config_digest=config_digest, repeat=repeat, seed=seed,
                prompt_profile=profile,
                prompt_template_digest=json_digest({
                    "system": profiles[profile], "prompt": fixture["prompt"], "input": fixture["input"],
                }),
                validator_contract="g-route1.validators.v1",
                scoring_lineage="G-ROUTE1-GOLD-R1:g-route1.scorer.v1",
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
    corpus = load_corpus()
    expected = {
        (fixture["fixture_id"], tier, repeat)
        for fixture in corpus["fixtures"] for tier in TIER_ORDER
        for repeat in range(1, EXPECTED_REPEATS + 1)
    }
    actual = {(row.get("fixture_id"), row.get("model_tier"), row.get("repeat")) for row in rows}
    if actual != expected:
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
        "schema_version": "g-route1.schedule.v1", "schedule_id": "G-ROUTE1-SCHEDULE-R1",
        "algorithm": "sha256_fixture_repeat_groups_with_rotating_tier_order",
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
    target.write_text(rendered, encoding="utf-8", newline="\n")
    return payload


def render_prompt(fixture: Mapping[str, Any]) -> dict[str, str]:
    profiles = load_json(DATA / "prompt_profiles.json")["profiles"]
    profile = str(fixture["validator_profile"])
    system = str(profiles[profile])
    user = str(fixture["prompt"]) + "\n\nINPUT:\n" + json.dumps(
        fixture["input"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return {"system": system, "prompt": user}


def request_body(fixture: Mapping[str, Any], call: Mapping[str, Any]) -> dict[str, Any]:
    binding = load_model_bindings()
    prompt = render_prompt(fixture)
    options = dict(binding["generation_configuration"]["options"])
    options["seed"] = int(call["seed"])
    return {
        "model": call["model"], "system": prompt["system"], "prompt": prompt["prompt"],
        "stream": False, "think": False, "options": options,
    }


def verify_fixture_freeze_current() -> None:
    manifest = load_json(FREEZE_PATH)
    result = verify_fixture_freeze(manifest)
    if not result["valid"]:
        raise ValueError("fixture_freeze_drift:" + ",".join(result["reasons"]))


__all__ = [
    "CONTRACT_VERSION", "EXPECTED_CALLS", "EXPECTED_REPEATS", "TIER_ORDER",
    "MODEL_BINDINGS_PATH", "THRESHOLDS_PATH", "SCHEDULE_PATH", "EXECUTION_FREEZE_PATH",
    "ScheduledCall", "canonical_json", "json_digest", "load_json", "load_model_bindings",
    "load_thresholds", "build_schedule", "validate_schedule", "schedule_payload",
    "write_schedule", "render_prompt", "request_body", "verify_fixture_freeze_current",
]
