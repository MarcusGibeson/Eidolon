from __future__ import annotations

"""Restricted disposable execution for the four frozen G-ROUTE1 coding fixtures."""

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from g_route1_contract import canonical_digest
from g_route1_validators import CODING_EVIDENCE_CONTRACT, coding_candidate_source


CONTRACT_VERSION = CODING_EVIDENCE_CONTRACT
ALLOWED_CALL_NAMES = frozenset({"bool", "PurePosixPath"})
ALLOWED_CALL_ATTRIBUTES = frozenset({"strip", "lower", "split", "join", "replace", "startswith"})
ALLOWED_READ_ATTRIBUTES = ALLOWED_CALL_ATTRIBUTES | {"parts"}
DENIED_NODES = (
    ast.AsyncFunctionDef, ast.Await, ast.ClassDef, ast.Delete, ast.Global,
    ast.Lambda, ast.Nonlocal, ast.Raise, ast.Try, ast.With, ast.Yield,
)


def _parse_output(raw_output: Any) -> dict[str, Any]:
    if isinstance(raw_output, Mapping):
        return dict(raw_output)
    value = json.loads(str(raw_output))
    if not isinstance(value, dict):
        raise ValueError("coding_output_not_object")
    return value


def validate_candidate_ast(source: str) -> ast.Module:
    tree = ast.parse(source, filename="app.py")
    for node in ast.walk(tree):
        if isinstance(node, DENIED_NODES):
            raise ValueError(f"coding_ast_node_denied:{type(node).__name__}")
        if isinstance(node, ast.Import):
            raise ValueError("coding_import_denied")
        if isinstance(node, ast.ImportFrom):
            if node.module != "pathlib" or {alias.name for alias in node.names} != {"PurePosixPath"}:
                raise ValueError("coding_import_denied")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in ALLOWED_CALL_NAMES:
                raise ValueError(f"coding_call_denied:{node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr not in ALLOWED_CALL_ATTRIBUTES:
                raise ValueError(f"coding_call_denied:{node.func.attr}")
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                raise ValueError("coding_dynamic_call_denied")
        if isinstance(node, ast.Attribute) and node.attr not in ALLOWED_READ_ATTRIBUTES:
            raise ValueError(f"coding_attribute_denied:{node.attr}")
    return tree


def run_isolated_fixture(fixture: Mapping[str, Any], raw_output: Any) -> dict[str, Any]:
    """Validate, compile, and run the supplied focused test in a disposable directory.

    Candidate syntax is constrained before subprocess execution. The subprocess has
    no inherited Python path, uses isolated interpreter mode, and receives only the
    frozen candidate and focused test. This is not a general-purpose code sandbox.
    """
    output = _parse_output(raw_output)
    fixture_input = fixture["input"]
    if set(output) != {"path", "old", "new"}:
        raise ValueError("coding_output_schema_mismatch")
    if output["path"] != fixture_input["allowed_path"]:
        raise ValueError("coding_path_not_allowed")
    candidate = coding_candidate_source(fixture_input, output)
    validate_candidate_ast(candidate)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    with tempfile.TemporaryDirectory(prefix="g_route1_coding_") as td:
        root = Path(td)
        (root / "app.py").write_text(candidate, encoding="utf-8", newline="\n")
        (root / "test_app.py").write_text(
            str(fixture_input["focused_test"]), encoding="utf-8", newline="\n"
        )
        compiled = subprocess.run(
            [sys.executable, "-I", "-m", "py_compile", "app.py"], cwd=root,
            env=environment, capture_output=True, text=True, timeout=10, check=False,
        )
        test_script = (
            "import sys; sys.path.insert(0, '.'); import test_app; "
            "tests=[getattr(test_app,n) for n in dir(test_app) "
            "if n.startswith('test_') and callable(getattr(test_app,n))]; "
            "assert tests; [test() for test in tests]"
        )
        tested = subprocess.run(
            [sys.executable, "-I", "-c", test_script], cwd=root,
            env=environment, capture_output=True, text=True, timeout=20, check=False,
        )
    return {
        "producer_contract": CONTRACT_VERSION,
        "fixture_id": fixture["fixture_id"],
        "candidate_sha256": canonical_digest(candidate),
        "focused_test_sha256": canonical_digest(fixture_input["focused_test"]),
        "isolated": True,
        "compile_pass": compiled.returncode == 0,
        "tests_pass": tested.returncode == 0,
        "test_exit_code": tested.returncode,
        "test_count": str(fixture_input["focused_test"]).count("def test_"),
    }


__all__ = ["CONTRACT_VERSION", "run_isolated_fixture", "validate_candidate_ast"]
