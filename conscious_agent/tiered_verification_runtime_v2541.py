from __future__ import annotations

"""v2541-v2543 tiered fast verification runtime.

Provides a cheap-to-expensive verification ladder above retained verification
systems. Tiers 0-2 are bounded and hermetic; Tier 3 delegates to the existing
release/segmented verifiers. No tier grants release or mutation authority.
"""

import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from hermetic_verification_runtime import build_hermetic_environment, run_bounded_command

CONTRACT_VERSION = "v2541.0"
MAX_CHANGED_PATHS = 64
MAX_TIER1_TESTS = 6
MAX_TIER2_TESTS = 8
TIER2_DEFAULT_TESTS = (
    "tools/v2540_9_cognitive_observability_dashboard_beta_completion_tests.py",
    "tools/v2504_9_unified_cognitive_runtime_alpha_checkpoint_tests.py",
    "tools/v2512_9_capability_activity_voice_campaign_checkpoint_tests.py",
    "tools/v2520_9_general_capability_lifecycle_alpha_checkpoint_tests.py",
    "tools/v1082_4_browser_navigation_hardening_tests.py",
)
AUTHORITY = {
    "source_mutation_authorized": False,
    "project_mutation_authorized": False,
    "provider_contact_authorized": False,
    "network_authorized": False,
    "release_authorized": False,
    "certification_authorized": False,
    "independent_authority_granted": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _safe_paths(source_root: Path, changed_paths: Iterable[str]) -> list[str]:
    rows=[]
    for raw in changed_paths:
        token=str(raw or "").replace("\\","/").strip()
        p=PurePosixPath(token)
        if not token or p.is_absolute() or ".." in p.parts:
            raise ValueError("unsafe_changed_path")
        resolved=(source_root / p).resolve()
        try: resolved.relative_to(source_root)
        except ValueError as exc: raise ValueError("changed_path_outside_source") from exc
        if token not in rows: rows.append(token)
        if len(rows)>MAX_CHANGED_PATHS: raise ValueError("changed_path_limit_exceeded")
    if not rows: raise ValueError("changed_paths_required")
    return rows


def _focused_test_candidates(source_root: Path, changed: Sequence[str]) -> list[str]:
    tools = source_root / "tools"
    if not tools.is_dir():
        return []

    generic_stems = {"dashboard", "api_server", "main", "memory", "settings", "release_metadata"}
    unique_stems = {
        Path(p).stem
        for p in changed
        if Path(p).suffix == ".py" and Path(p).stem not in generic_stems
    }
    concept_tokens: set[str] = set()
    import re
    for stem in unique_stems:
        for token in re.split(r"[_\W]+", stem.lower()):
            if len(token) >= 5 and not re.fullmatch(r"v\d+", token):
                concept_tokens.add(token)

    exact_paths = {p for p in changed if Path(p).stem not in generic_stems}
    generic_filenames = {Path(p).name for p in changed if Path(p).stem in generic_stems}
    try:
        from release_authority import WORKING_SOURCE_VERSION
        current_whole = int(str(WORKING_SOURCE_VERSION).split(".", 1)[0])
    except Exception:
        current_whole = 0

    scored: list[tuple[int, int, str]] = []
    for path in tools.glob("*_tests.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lower_name = path.name.lower()
        primary = 0
        # Exact references to unique changed implementation files are strongest evidence.
        primary += 30 * sum(1 for rel in exact_paths if rel and rel in text)
        primary += 14 * sum(1 for stem in unique_stems if stem and stem in text)
        # Concept-bearing test names are strong direct-coverage evidence, particularly for
        # newly introduced modules whose tests import by symbol rather than literal path.
        name_hits = sum(1 for token in concept_tokens if token in lower_name)
        primary += 12 * name_hits
        if primary <= 0:
            # Generic files such as dashboard.py are intentionally insufficient by themselves
            # to drag historical suites into Tier 1. Tier 2 covers broad integration.
            continue

        score = primary
        m = re.match(r"v(\d+)", path.name)
        version = int(m.group(1)) if m else 0
        if current_whole and version >= max(0, current_whole - 20):
            score += 18
        # Generic filename references are only a weak tie-breaker after direct evidence exists.
        score += min(2, sum(1 for name in generic_filenames if name and name in text))
        size_penalty = min(10, max(0, path.stat().st_size // 20000))
        score -= size_penalty
        scored.append((-score, path.stat().st_size, path.name))

    scored.sort()
    return [f"tools/{name}" for _, _, name in scored[:MAX_TIER1_TESTS]]

def build_tiered_verification_plan(source_root: str | Path, changed_paths: Sequence[str]) -> dict[str, Any]:
    root=Path(source_root).resolve(); changed=_safe_paths(root,changed_paths)
    tier0=[p for p in changed if p.endswith(".py")]
    tier1=_focused_test_candidates(root,changed)
    tier2=[p for p in TIER2_DEFAULT_TESTS if (root/p).is_file()][:MAX_TIER2_TESTS]
    plan={
        "ok":True,
        "contract_version":CONTRACT_VERSION,
        "changed_paths":changed,
        "tiers":{
            "0":{"name":"edit","syntax_paths":tier0,"target_seconds":5,"executes_external_process":False},
            "1":{"name":"affected-system","tests":tier1,"target_seconds":30,"max_tests":MAX_TIER1_TESTS},
            "2":{"name":"integration","tests":tier2,"target_seconds":120,"max_tests":MAX_TIER2_TESTS},
            "3":{"name":"release-certification","delegates":["python tools/release_verify.py --profile full","python tools/segmented_release_verify.py"],"bounded_by_existing_verifiers":True},
        },
        "tier1_test_count":len(tier1),
        "tier2_test_count":len(tier2),
        "runs_commands":False,
        **AUTHORITY,
    }
    plan["plan_digest"]=_digest(plan)
    return plan


def run_tier0(source_root: str | Path, changed_paths: Sequence[str]) -> dict[str, Any]:
    root=Path(source_root).resolve(); plan=build_tiered_verification_plan(root,changed_paths); rows=[]
    for rel in plan["tiers"]["0"]["syntax_paths"]:
        path=root/rel
        if not path.is_file(): rows.append({"path":rel,"ok":False,"status":"missing"}); continue
        try: ast.parse(path.read_text(encoding="utf-8"),filename=rel); ok=True; status="parsed"
        except (OSError,SyntaxError,UnicodeError) as exc: ok=False; status=type(exc).__name__
        rows.append({"path":rel,"ok":ok,"status":status})
    result={"ok":all(r["ok"] for r in rows),"contract_version":CONTRACT_VERSION,"tier":0,"status":"tier0_passed" if all(r["ok"] for r in rows) else "tier0_failed","checks":rows,"check_count":len(rows),"external_process_spawned":False,**AUTHORITY}
    result["receipt_digest"]=_digest(result); return result


def _run_tests(source_root: Path, tests: Sequence[str], *, tier: int, timeout_each: float) -> dict[str, Any]:
    outcomes=[]
    with tempfile.TemporaryDirectory(prefix=f"eidolon-tier{tier}-") as td:
        runtime=Path(td)
        env=build_hermetic_environment(runtime_root=runtime,source_root=source_root)
        env["PYTHONPATH"]=os.pathsep.join([str(source_root),str(source_root/"conscious_agent"),str(source_root/"tools")])
        for rel in tests:
            path=source_root/rel
            if not path.is_file():
                outcomes.append({"test":rel,"status":"missing","ok":False}); continue
            receipt=run_bounded_command([sys.executable,rel],cwd=source_root,env=env,timeout_seconds=timeout_each).as_dict()
            outcomes.append({"test":rel,"status":receipt["status"],"ok":receipt["ok"],"elapsed_seconds":receipt["elapsed_seconds"],"stdout_sha256":receipt["stdout_sha256"],"stderr_sha256":receipt["stderr_sha256"],"returncode":receipt["returncode"],"timed_out":receipt["timed_out"]})
    result={"ok":all(r["ok"] for r in outcomes),"contract_version":CONTRACT_VERSION,"tier":tier,"status":f"tier{tier}_passed" if all(r["ok"] for r in outcomes) else f"tier{tier}_failed","tests":outcomes,"test_count":len(outcomes),"content_free_receipts":True,**AUTHORITY}
    result["receipt_digest"]=_digest(result); return result


def run_tier1(source_root: str | Path, changed_paths: Sequence[str], *, timeout_each: float=20.0) -> dict[str, Any]:
    root=Path(source_root).resolve(); plan=build_tiered_verification_plan(root,changed_paths)
    return _run_tests(root,plan["tiers"]["1"]["tests"],tier=1,timeout_each=min(30.0,max(1.0,float(timeout_each))))


def run_tier2(source_root: str | Path, changed_paths: Sequence[str], *, timeout_each: float=30.0) -> dict[str, Any]:
    root=Path(source_root).resolve(); plan=build_tiered_verification_plan(root,changed_paths)
    return _run_tests(root,plan["tiers"]["2"]["tests"],tier=2,timeout_each=min(60.0,max(1.0,float(timeout_each))))


def run_tiered_verification(
    source_root: str | Path,
    changed_paths: Sequence[str],
    *,
    through_tier: int = 1,
    timeout_each_tier1: float = 20.0,
    timeout_each_tier2: float = 30.0,
) -> dict[str, Any]:
    if through_tier not in {0, 1, 2}:
        raise ValueError("through_tier_must_be_0_1_or_2")
    root = Path(source_root).resolve()
    plan = build_tiered_verification_plan(root, changed_paths)
    receipts: list[dict[str, Any]] = []

    tier0 = run_tier0(root, changed_paths)
    receipts.append(tier0)
    if not tier0["ok"] or through_tier == 0:
        status = "passed" if tier0["ok"] else "failed"
        result = {
            "ok": bool(tier0["ok"]),
            "contract_version": CONTRACT_VERSION,
            "through_tier": 0,
            "status": f"tiered_verification_{status}",
            "plan_digest": plan["plan_digest"],
            "receipts": receipts,
            "stopped_after_tier": 0,
            **AUTHORITY,
        }
        result["receipt_digest"] = _digest(result)
        return result

    tier1 = run_tier1(root, changed_paths, timeout_each=timeout_each_tier1)
    receipts.append(tier1)
    if not tier1["ok"] or through_tier == 1:
        status = "passed" if tier1["ok"] else "failed"
        result = {
            "ok": bool(tier1["ok"]),
            "contract_version": CONTRACT_VERSION,
            "through_tier": 1,
            "status": f"tiered_verification_{status}",
            "plan_digest": plan["plan_digest"],
            "receipts": receipts,
            "stopped_after_tier": 1,
            **AUTHORITY,
        }
        result["receipt_digest"] = _digest(result)
        return result

    tier2 = run_tier2(root, changed_paths, timeout_each=timeout_each_tier2)
    receipts.append(tier2)
    result = {
        "ok": bool(tier2["ok"]),
        "contract_version": CONTRACT_VERSION,
        "through_tier": 2,
        "status": "tiered_verification_passed" if tier2["ok"] else "tiered_verification_failed",
        "plan_digest": plan["plan_digest"],
        "receipts": receipts,
        "stopped_after_tier": 2,
        **AUTHORITY,
    }
    result["receipt_digest"] = _digest(result)
    return result


__all__=["CONTRACT_VERSION","build_tiered_verification_plan","run_tier0","run_tier1","run_tier2","run_tiered_verification"]
