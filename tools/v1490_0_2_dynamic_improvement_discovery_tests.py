from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import ast


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v1490-discovery-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME / "runtime")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AGENT))

from conscious_agent.dynamic_improvement_discovery import (
    DISCOVERY_SCHEMA_VERSION,
    MAX_ESTIMATED_DEPENDENCIES,
    build_dynamic_improvement_discovery,
    build_python_ast_inventory,
    clear_dynamic_discovery_caches,
    public_dynamic_discovery_projection,
    verify_inventory_source_unchanged,
)
from conscious_agent.v1489_product_capability_integration import integrate_v1489_product_capabilities


passed = 0
failed = 0


def check(name: str, condition: bool, detail: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
        return
    failed += 1
    print("FAIL", name, detail)
    raise AssertionError(detail or name)


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def fixture(name: str, module_text: str, test_text: str = "") -> Path:
    root = RUNTIME / name
    agent = root / "conscious_agent"
    tools = root / "tools"
    agent.mkdir(parents=True)
    tools.mkdir(parents=True)
    (agent / "sample.py").write_text(module_text, encoding="utf-8")
    if test_text:
        tree = ast.parse(module_text)
        names = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        import_line = f"from conscious_agent.sample import {', '.join(names)}\n" if names else ""
        (tools / "sample_discovery_tests.py").write_text(import_line + test_text, encoding="utf-8")
    return root


def by_source(result: dict, module: str) -> list[dict]:
    return [row for row in result.get("candidates", []) if row.get("source_module") == module]


try:
    # v1490.0: real source inventory and the current post-extraction self-maintenance surface.
    current_before = snapshot(ROOT / "conscious_agent")
    clear_dynamic_discovery_caches()
    current_started = time.perf_counter()
    current = build_dynamic_improvement_discovery(ROOT)
    current_cold_elapsed_ms = (time.perf_counter() - current_started) * 1000.0
    current_warm_started = time.perf_counter()
    current_warm = build_dynamic_improvement_discovery(ROOT)
    current_warm_elapsed_ms = (time.perf_counter() - current_warm_started) * 1000.0
    current_after = snapshot(ROOT / "conscious_agent")
    check("schema identifies v1490.2 discovery foundation", current["schema_version"] == DISCOVERY_SCHEMA_VERSION, current)
    check("real source inventory is broad", current["module_count"] > 1000 and current["symbol_count"] > 10000, {"modules": current["module_count"], "symbols": current["symbol_count"]})
    focus = current["focus_module_summary"]
    check("current self-maintenance review surface is inventoried", focus["module"] == "conscious_agent/self_maintenance.py" and focus["line_count"] > 40000 and focus["top_level_symbol_count"] > 2000, focus)
    check("installed retained wrappers are recognized", focus["retained_extraction_wrapper_count"] >= 10, focus)
    wrapper_names = {
        "_approval_record_files", "_safe_approval_record_from_path", "_approval_record_id",
        "_approval_record_summary", "_read_approval_record_summaries", "_revocation_record_files",
        "_read_revocation_payload", "_revocation_record_id", "_revocation_validator_rows", "_read_revocation_summaries",
    }
    rediscovered = {name for row in current.get("focus_candidates", []) for name in row.get("source_symbols", [])} & wrapper_names
    check("installed extraction wrappers are not rediscovered", not rediscovered, rediscovered)
    check("current self-maintenance does not invent testability from unrelated same-name references", not current.get("focus_candidates") and any("insufficient_existing_test_reference" in row.get("rejection_codes", []) for row in current.get("focus_rejections", [])), {"candidates": current.get("focus_candidates"), "rejections": current.get("focus_rejections")})
    check("discovery is provider-free and read-only", current["provider_contacted"] is False and current["source_modified"] is False and current["runtime_modified"] is False and current["source_unchanged"] is True, current)
    check("discovery does not rank or select", current["ranking_performed"] is False and current["selection_made"] is False and current["workspace_prepared"] is False and current["approval_requested"] is False, current)
    check("real source remains byte-identical", current_before == current_after)

    check("real-source cold discovery records content-free timing", current["cache_hit"] is False and current_cold_elapsed_ms >= 0.0, {"cold_ms": round(current_cold_elapsed_ms, 3)})
    check("real-source warm discovery uses unchanged-tree cache", current_warm["cache_hit"] is True and current_warm_elapsed_ms < current_cold_elapsed_ms, {"cold_ms": round(current_cold_elapsed_ms, 3), "warm_ms": round(current_warm_elapsed_ms, 3)})
    print("REAL_PERF", json.dumps({"cold_elapsed_ms": round(current_cold_elapsed_ms, 3), "warm_elapsed_ms": round(current_warm_elapsed_ms, 3), "content_free": True}, sort_keys=True))

    # Inventory evidence: module size/lines/symbol spans/adjacency/test references/wrapper status.
    inv_root = fixture(
        "inventory-evidence",
        "from helper import one as one_implementation\n\n"
        "def alpha_cache_entry():\n    return 1\n\n"
        "def beta_cache_entry():\n    return 2\n\n"
        "def retained_cache_entry():\n    return one_implementation()\n",
        "def test_refs():\n    alpha_cache_entry(); beta_cache_entry(); retained_cache_entry()\n",
    )
    inventory = build_python_ast_inventory(inv_root)
    module = inventory["modules"][0]
    symbols = {row["name"]: row for row in module["symbols"]}
    check("inventory records module size line and symbol counts", module["module_size_bytes"] > 0 and module["line_count"] >= 8 and module["top_level_symbol_count"] == 3, module)
    check("inventory records symbol spans and adjacency", symbols["beta_cache_entry"]["end_line"] >= symbols["beta_cache_entry"]["line"] and symbols["beta_cache_entry"]["adjacent_gap_from_previous"] is not None, symbols["beta_cache_entry"])
    check("inventory records test references", symbols["alpha_cache_entry"]["test_reference_count"] >= 1 and symbols["alpha_cache_entry"]["test_reference_file_count"] == 1, symbols["alpha_cache_entry"])
    check("inventory labels retained forwarding wrappers", symbols["retained_cache_entry"]["retained_extraction_wrapper"] is True, symbols["retained_cache_entry"])

    # Windows/LF/CRLF source immutability must use raw bytes consistently.
    newline_root = RUNTIME / "newline-immutability"
    newline_agent = newline_root / "conscious_agent"
    newline_agent.mkdir(parents=True)
    (newline_agent / "lf.py").write_bytes(b"def lf_entry():\n    return 1\n")
    (newline_agent / "crlf.py").write_bytes(b"def crlf_entry():\r\n    return 2\r\n")
    newline_inventory = build_python_ast_inventory(newline_root)
    check("LF source verifies unchanged with raw-byte digest", verify_inventory_source_unchanged(newline_root, newline_inventory) is True)
    check("CRLF source verifies unchanged with raw-byte digest", verify_inventory_source_unchanged(newline_root, newline_inventory) is True)
    (newline_agent / "lf.py").write_bytes(b"def lf_entry():\n    return 9\n")
    check("genuine byte mutation fails source immutability", verify_inventory_source_unchanged(newline_root, newline_inventory) is False)
    (newline_agent / "lf.py").write_bytes(b"def lf_entry():\n    return 1\n")
    check("mixed LF CRLF tree returns unchanged after exact restoration", verify_inventory_source_unchanged(newline_root, newline_inventory) is True)

    # Module-aware test evidence must not transfer across same-named symbols.
    module_ref_root = RUNTIME / "module-aware-tests"
    module_ref_agent = module_ref_root / "conscious_agent"
    module_ref_tools = module_ref_root / "tools"
    module_ref_agent.mkdir(parents=True)
    module_ref_tools.mkdir(parents=True)
    same_body = "def load_cache_entry():\n    return 1\n\ndef save_cache_entry():\n    return 2\n"
    (module_ref_agent / "tested.py").write_text(same_body, encoding="utf-8")
    (module_ref_agent / "untested.py").write_text(same_body, encoding="utf-8")
    (module_ref_tools / "module_reference_tests.py").write_text(
        "from conscious_agent import tested as subject\n"
        "def test_subject():\n    subject.load_cache_entry(); subject.save_cache_entry()\n",
        encoding="utf-8",
    )
    module_ref_inventory = build_python_ast_inventory(module_ref_root)
    module_rows = {row["module"]: row for row in module_ref_inventory["modules"]}
    tested_symbols = {row["name"]: row for row in module_rows["conscious_agent/tested.py"]["symbols"]}
    untested_symbols = {row["name"]: row for row in module_rows["conscious_agent/untested.py"]["symbols"]}
    check("qualified import grants attributable test evidence", tested_symbols["load_cache_entry"]["test_reference_file_count"] == 1, tested_symbols)
    check("same-named symbol in unrelated module gets no test evidence", untested_symbols["load_cache_entry"]["test_reference_file_count"] == 0, untested_symbols)

    ambiguous_ref_root = RUNTIME / "ambiguous-tests"
    ambiguous_agent = ambiguous_ref_root / "conscious_agent"
    ambiguous_tools = ambiguous_ref_root / "tools"
    ambiguous_agent.mkdir(parents=True)
    ambiguous_tools.mkdir(parents=True)
    (ambiguous_agent / "first.py").write_text(same_body, encoding="utf-8")
    (ambiguous_agent / "second.py").write_text(same_body, encoding="utf-8")
    (ambiguous_tools / "ambiguous_tests.py").write_text(
        "def test_bare_name_only():\n    load_cache_entry(); save_cache_entry()\n",
        encoding="utf-8",
    )
    ambiguous_inventory = build_python_ast_inventory(ambiguous_ref_root)
    check("ambiguous bare names are not confirmed test coverage", all(symbol["test_reference_file_count"] == 0 for row in ambiguous_inventory["modules"] for symbol in row["symbols"]), ambiguous_inventory)

    # Compound protected-authority names and called dependencies must survive tokenization.
    authority_root = fixture(
        "compound-authority",
        "def source_apply_cache():\n    return 1\n\n"
        "def live_apply_cache():\n    return 2\n\n"
        "def release_apply_cache():\n    return 3\n\n"
        "def model_install_cache():\n    return 4\n\n"
        "def approval_execute_cache():\n    return 5\n\n"
        "def provider_switch_cache():\n    return 6\n\n"
        "def rollback_apply_cache():\n    return 7\n\n"
        "def harmless_source_cache():\n    return 8\n\n"
        "def harmless_apply_cache():\n    return 9\n\n"
        "def provider_switch():\n    return 10\n\n"
        "def calls_switch_cache():\n    return provider_switch()\n",
        "def test_refs():\n    source_apply_cache(); live_apply_cache(); release_apply_cache(); model_install_cache(); approval_execute_cache(); provider_switch_cache(); rollback_apply_cache(); harmless_source_cache(); harmless_apply_cache(); provider_switch(); calls_switch_cache()\n",
    )
    authority_inventory = build_python_ast_inventory(authority_root)
    authority_symbols = {row["name"]: row for row in authority_inventory["modules"][0]["symbols"]}
    check("source_apply remains protected after tokenization", authority_symbols["source_apply_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("live_apply remains protected after tokenization", authority_symbols["live_apply_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("release_apply remains protected after tokenization", authority_symbols["release_apply_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("model_install remains protected after tokenization", authority_symbols["model_install_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("approval_execute remains protected after tokenization", authority_symbols["approval_execute_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("provider_switch remains protected after tokenization", authority_symbols["provider_switch_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("rollback_apply remains protected after tokenization", authority_symbols["rollback_apply_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("called protected dependency makes caller protected", authority_symbols["calls_switch_cache"]["protected_authority_boundary"] is True, authority_symbols)
    check("source alone does not create protected false positive", authority_symbols["harmless_source_cache"]["protected_authority_boundary"] is False, authority_symbols)
    check("apply alone does not create protected false positive", authority_symbols["harmless_apply_cache"]["protected_authority_boundary"] is False, authority_symbols)

    authority_discovery = build_dynamic_improvement_discovery(authority_root)
    protected_rows = [row for row in authority_discovery.get("rejected_candidates", []) if any("_apply_" in name or "_install_" in name or "_execute_" in name or "_switch_" in name for name in row.get("source_symbols", []))]
    check("protected authority families never become eligible candidates", protected_rows and all("protected_authority_boundary" in row.get("rejection_codes", []) for row in protected_rows), protected_rows)

    # Two equally plausible adjacent families must both survive without ranking/selection.
    equal_root = fixture(
        "equal-families",
        "PRIVATE_SENTINEL = 'never expose this source text'\n\n"
        "def load_cache_entry():\n    return 1\n\n"
        "def save_cache_entry():\n    return 2\n\n"
        "def scan_queue_item():\n    return 3\n\n"
        "def render_queue_item():\n    return 4\n",
        "def test_all():\n    load_cache_entry(); save_cache_entry(); scan_queue_item(); render_queue_item()\n",
    )
    equal_before = snapshot(equal_root)
    equal = build_dynamic_improvement_discovery(equal_root)
    equal_after = snapshot(equal_root)
    eq = by_source(equal, "conscious_agent/sample.py")
    check("two equally plausible families are both described", len(eq) == 2, eq)
    check("equally plausible families are not ranked or selected", all(row["ranking_score"] is None and row["selected"] is False for row in eq) and equal["selection_made"] is False, eq)
    check("candidate evidence contains exact source symbols and stable destination", all(row["source_symbols"] and str(row["proposed_destination_module"]).endswith(".py") for row in eq), eq)
    check("candidate evidence records dependency/test/reversibility metadata", all(isinstance(row["estimated_dependency_count"], int) and row["existing_test_reference_file_count"] >= 1 and row["reversibility_classification"] == "bounded_new_module_retained_wrapper_candidate" for row in eq), eq)
    public = public_dynamic_discovery_projection(equal)
    public_text = json.dumps(public, sort_keys=True)
    check("public evidence excludes source text sentinel", "PRIVATE_SENTINEL" not in public_text and "never expose this source text" not in public_text, public_text)
    check("fixture source is unchanged by discovery", equal_before == equal_after and equal["source_unchanged"] is True)
    private_dir = equal_root / "data"
    private_dir.mkdir()
    (private_dir / "private_runtime.py").write_text("PRIVATE_RUNTIME_SENTINEL = 1\ndef private_runtime_candidate():\n    return 1\n", encoding="utf-8")
    private_probe = build_dynamic_improvement_discovery(equal_root)
    private_public = json.dumps(public_dynamic_discovery_projection(private_probe), sort_keys=True)
    check("private runtime source is not inventoried", "data/private_runtime.py" not in private_public and "PRIVATE_RUNTIME_SENTINEL" not in private_public, private_public)

    exclusion_root = fixture(
        "excluded-symbols",
        "def _build_cache_dependencies():\n    return {}\n\n"
        "def generated_cache_wrapper():\n    return _build_cache_stage()\n\n"
        "def retained_cache_wrapper():\n    return retained_implementation()\n",
        "def test_refs():\n    _build_cache_dependencies(); generated_cache_wrapper(); retained_cache_wrapper()\n",
    )
    exclusions = build_dynamic_improvement_discovery(exclusion_root)["symbol_exclusion_counts"]
    check("dependency factories are excluded from candidate discovery", exclusions["dependency_factory"] >= 1, exclusions)
    check("generated wrappers are excluded from candidate discovery", exclusions["generated_wrapper"] >= 1, exclusions)
    check("retained wrappers are excluded from candidate discovery", exclusions["retained_extraction_wrapper"] >= 1, exclusions)

    # Excessive closure must be explicit rather than becoming a candidate.
    deps = "+".join(f"dep{i}" for i in range(MAX_ESTIMATED_DEPENDENCIES + 8))
    excessive_root = fixture(
        "excessive-deps",
        f"def compute_cache_entry():\n    return {deps}\n\ndef store_cache_entry():\n    return {deps}\n",
        "def test_refs():\n    compute_cache_entry(); store_cache_entry()\n",
    )
    excessive = build_dynamic_improvement_discovery(excessive_root)
    rejection_codes = {code for row in excessive["rejected_candidates"] for code in row["rejection_codes"]}
    check("excessive dependency closure is rejected explicitly", "excessive_dependency_closure" in rejection_codes, excessive["rejected_candidates"])

    # Protected authority boundary.
    protected_root = fixture(
        "protected-boundary",
        "def approval_cache_read():\n    return 1\n\ndef approval_cache_write():\n    return 2\n",
        "def test_refs():\n    approval_cache_read(); approval_cache_write()\n",
    )
    protected = build_dynamic_improvement_discovery(protected_root)
    protected_codes = {code for row in protected["rejected_candidates"] for code in row["rejection_codes"]}
    check("protected authority family is rejected", "protected_authority_boundary" in protected_codes, protected["rejected_candidates"])

    # Existing destination module.
    destination_root = fixture(
        "existing-destination",
        "def load_cache_entry():\n    return 1\n\ndef save_cache_entry():\n    return 2\n",
        "def test_refs():\n    load_cache_entry(); save_cache_entry()\n",
    )
    (destination_root / "conscious_agent" / "sample_cache_entry.py").write_text("VALUE = 1\n", encoding="utf-8")
    destination = build_dynamic_improvement_discovery(destination_root)
    destination_codes = {code for row in destination["rejected_candidates"] for code in row["rejection_codes"]}
    check("existing destination module is rejected", "destination_module_already_exists" in destination_codes, destination["rejected_candidates"])

    # Duplicate operator-installed proposal lineage.
    lineage_root = fixture(
        "installed-lineage",
        "def load_cache_entry():\n    return 1\n\ndef save_cache_entry():\n    return 2\n",
        "def test_refs():\n    load_cache_entry(); save_cache_entry()\n",
    )
    lineage = build_dynamic_improvement_discovery(
        lineage_root,
        completed_lineages=[{"destination_module": "conscious_agent/sample_cache_entry.py", "operator_installed": True}],
    )
    lineage_codes = {code for row in lineage["rejected_candidates"] for code in row["rejection_codes"]}
    check("operator-installed proposal destination is not rediscovered", "completed_proposal_lineage" in lineage_codes, lineage["rejected_candidates"])

    # Explicit honest stop for weak/unverified source.
    stop_root = fixture("honest-stop", "def alpha():\n    return 1\n\ndef beta():\n    return 2\n")
    stop = build_dynamic_improvement_discovery(stop_root)
    check("no qualifying candidate produces explicit honest stop", stop["state"] == "no_qualifying_candidate" and stop["eligible_candidate_count"] == 0, stop)

    # Restart/replay determinism.
    replay_root = fixture(
        "restart-replay",
        "def load_cache_entry():\n    return 1\n\ndef save_cache_entry():\n    return 2\n",
        "def test_refs():\n    load_cache_entry(); save_cache_entry()\n",
    )
    first = build_dynamic_improvement_discovery(replay_root)
    second = build_dynamic_improvement_discovery(replay_root)
    check("restart replay keeps inventory digest stable", first["inventory_digest"] == second["inventory_digest"], (first["inventory_digest"], second["inventory_digest"]))
    check("restart replay keeps discovery digest stable", first["discovery_digest"] == second["discovery_digest"], (first["discovery_digest"], second["discovery_digest"]))
    check("restart replay keeps candidate ids and evidence digests stable", [(r["candidate_id"], r["evidence_digest"]) for r in first["candidates"]] == [(r["candidate_id"], r["evidence_digest"]) for r in second["candidates"]], (first["candidates"], second["candidates"]))

    # Performance/index invalidation: cold/warm timings are content-free and all tree changes invalidate.
    perf_root = fixture(
        "performance-cache",
        "def load_cache_entry():\n    return 1\n\ndef save_cache_entry():\n    return 2\n",
        "def test_refs():\n    load_cache_entry(); save_cache_entry()\n",
    )
    clear_dynamic_discovery_caches()
    cold_started = time.perf_counter()
    cold = build_dynamic_improvement_discovery(perf_root)
    cold_elapsed_ms = (time.perf_counter() - cold_started) * 1000.0
    warm_started = time.perf_counter()
    warm = build_dynamic_improvement_discovery(perf_root)
    warm_elapsed_ms = (time.perf_counter() - warm_started) * 1000.0
    check("cold discovery records content-free elapsed timing", cold["cache_hit"] is False and cold["discovery_elapsed_ms"] >= 0.0, cold)
    check("warm discovery uses deterministic read-only cache", warm["cache_hit"] is True and warm_elapsed_ms <= cold_elapsed_ms, {"cold_ms": round(cold_elapsed_ms, 3), "warm_ms": round(warm_elapsed_ms, 3)})
    original_digest = warm["inventory_digest"]
    sample_path = perf_root / "conscious_agent" / "sample.py"

    # Desktop Codex regression: same-length byte replacement plus restored mtime must
    # never reuse stale discovery or module-analysis evidence.
    original_bytes = sample_path.read_bytes()
    original_stat = sample_path.stat()
    stealth_bytes = original_bytes.replace(b"return 1", b"return 9", 1)
    check("stealth mutation fixture preserves byte length", len(stealth_bytes) == len(original_bytes) and stealth_bytes != original_bytes, {"length": len(original_bytes)})
    sample_path.write_bytes(stealth_bytes)
    os.utime(sample_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    stealth = build_dynamic_improvement_discovery(perf_root)
    check("same-length source replacement with restored mtime invalidates cache", stealth["cache_hit"] is False and stealth["inventory_digest"] != original_digest, stealth)
    check("recomputed stealth inventory describes current bytes", stealth["source_unchanged"] is True, stealth)
    sample_path.write_bytes(original_bytes)
    os.utime(sample_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    restored = build_dynamic_improvement_discovery(perf_root)
    check("restored original bytes are revalidated rather than trusting metadata", restored["cache_hit"] is False and restored["inventory_digest"] == original_digest and restored["source_unchanged"] is True, restored)
    sample_path.write_text("def load_cache_entry():\n    return 3\n\ndef save_cache_entry():\n    return 2\n", encoding="utf-8")
    changed = build_dynamic_improvement_discovery(perf_root)
    check("cache invalidates on changed source file", changed["cache_hit"] is False and changed["inventory_digest"] != original_digest, changed)
    added_path = perf_root / "conscious_agent" / "added.py"
    added_path.write_text("def added_entry():\n    return 1\n", encoding="utf-8")
    added = build_dynamic_improvement_discovery(perf_root)
    check("cache invalidates on added source file", added["cache_hit"] is False and added["module_count"] == changed["module_count"] + 1, added)
    added_path.unlink()
    deleted = build_dynamic_improvement_discovery(perf_root)
    check("cache invalidates on deleted source file", deleted["cache_hit"] is False and deleted["module_count"] == changed["module_count"], deleted)
    test_path = perf_root / "tools" / "sample_discovery_tests.py"
    original_test = test_path.read_text(encoding="utf-8")
    test_stat = test_path.stat()
    test_bytes = test_path.read_bytes()
    if b"load_cache_entry" in test_bytes:
        stealth_test_bytes = test_bytes.replace(b"load_cache_entry", b"save_cache_entry", 1)
        if len(stealth_test_bytes) == len(test_bytes):
            test_path.write_bytes(stealth_test_bytes)
            os.utime(test_path, ns=(test_stat.st_atime_ns, test_stat.st_mtime_ns))
            stealth_test = build_dynamic_improvement_discovery(perf_root)
            check("same-length test replacement with restored mtime invalidates cache", stealth_test["cache_hit"] is False, stealth_test)
            test_path.write_bytes(test_bytes)
            os.utime(test_path, ns=(test_stat.st_atime_ns, test_stat.st_mtime_ns))
            build_dynamic_improvement_discovery(perf_root)
    original_test = test_path.read_text(encoding="utf-8")
    test_path.write_text(original_test + "\n# changed test index\n", encoding="utf-8")
    changed_test = build_dynamic_improvement_discovery(perf_root)
    check("cache invalidates on changed test file", changed_test["cache_hit"] is False, changed_test)
    added_test = perf_root / "tools" / "additional_tests.py"
    added_test.write_text("from conscious_agent.sample import load_cache_entry\ndef test_added():\n    load_cache_entry()\n", encoding="utf-8")
    added_test_result = build_dynamic_improvement_discovery(perf_root)
    check("cache invalidates on added test file", added_test_result["cache_hit"] is False, added_test_result)
    added_test.unlink()
    deleted_test_result = build_dynamic_improvement_discovery(perf_root)
    check("cache invalidates on deleted test file", deleted_test_result["cache_hit"] is False, deleted_test_result)
    print("PERF", json.dumps({"cold_elapsed_ms": round(cold_elapsed_ms, 3), "warm_elapsed_ms": round(warm_elapsed_ms, 3), "content_free": True}, sort_keys=True))

    # Production adapter must expose discovery without proposal/workspace/authority side effects.
    production = integrate_v1489_product_capabilities(
        "Inspect your own project and propose one improvement.", {}, source_root=equal_root
    )
    projection = production["v1490_dynamic_improvement_discovery"]
    supervised = production["v1489_supervised_self_development"]
    check("production self-inspection routes to dynamic discovery", production["event"] == "dynamic_improvement_discovery_candidates_available" and projection["eligible_candidate_count"] == 2, production)
    check("production discovery is provider free", production["provider_contacted"] is False and projection["provider_contacted"] is False, production)
    check("production discovery creates no proposal workspace or approval", supervised["proposal_created"] is False and supervised["workspace_prepared"] is False and projection["approval_requested"] is False, production)
    check("production discovery grants no source install promotion authority", production["source_modified"] is False and production["authority_granted"] is False and supervised["installation_authorized"] is False and supervised["promotion_authorized"] is False, production)

    # Suite registration exactly once.
    release_verify_text = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    suite_path = "tools/v1490_0_2_dynamic_improvement_discovery_tests.py"
    check("v1490 discovery suite registered exactly once", release_verify_text.count(suite_path) == 1, release_verify_text.count(suite_path))

    print(json.dumps({
        "ok": True,
        "suite": "v1490.0-v1490.2-dynamic-improvement-discovery-foundations",
        "passed": passed,
        "failed": failed,
        "content_free": True,
    }, sort_keys=True))
finally:
    shutil.rmtree(RUNTIME, ignore_errors=True)
