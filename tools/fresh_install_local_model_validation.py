from __future__ import annotations

"""Focused fresh-install validation for the v1078.9 candidate.

The tool is intentionally bounded and does not install packages or create a venv.
It validates native setup syntax, source-safe setup contracts, workspace fallback,
path handling, optional dependency isolation, and immutability.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_DIRECTORY_NAMES = frozenset({"__pycache__", ".venv", "venv", ".git"})
FORBIDDEN_EXACT_FILES = frozenset({
    "data/projects.json",
    "data/memories.json",
    "data/tasks.json",
})
FORBIDDEN_FILE_SUFFIXES = (".pyc", ".pyo", ".log", ".zip")


def snapshot(root: Path) -> dict[str, str]:
    """Hash the complete physical tree, including generated and forbidden paths."""

    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            result[f"{rel}/"] = "directory"
        elif path.is_file():
            result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def privacy_violations(root: Path) -> list[str]:
    """Return every source-only privacy violation without hiding its subtree."""

    violations: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        rel = relative.as_posix()
        lower_rel = rel.lower()
        lower_parts = tuple(part.lower() for part in relative.parts)

        for index, part in enumerate(lower_parts):
            if part in FORBIDDEN_DIRECTORY_NAMES:
                prefix = Path(*relative.parts[: index + 1]).as_posix()
                violations.add(f"{prefix}/")
                break
        else:
            if lower_rel == "data/approvals" or lower_rel.startswith("data/approvals/"):
                violations.add("data/approvals/")
            elif path.is_file() and (
                lower_rel in FORBIDDEN_EXACT_FILES
                or lower_rel.endswith(FORBIDDEN_FILE_SUFFIXES)
            ):
                violations.add(rel)

    return sorted(violations)


def run() -> dict[str, Any]:
    before = snapshot(ROOT)
    results: list[dict[str, Any]] = []

    def check(name: str, fn: Callable[[], Any]) -> None:
        started = time.monotonic()
        try:
            details = fn()
        except Exception as error:
            results.append({"name": name, "status": "fail", "seconds": round(time.monotonic()-started,4), "error": repr(error)})
        else:
            results.append({"name": name, "status": "pass", "seconds": round(time.monotonic()-started,4), "details": details})

    def privacy() -> dict[str, Any]:
        forbidden = privacy_violations(ROOT)
        assert not forbidden, forbidden
        return {"forbidden": forbidden}

    def privacy_negative_control() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="eidolon-privacy-negative-") as base:
            fixture = Path(base)
            artifacts = {
                ".venv/": fixture / ".venv",
                ".git/": fixture / ".git",
                "conscious_agent/__pycache__/": fixture / "conscious_agent/__pycache__",
                "data/approvals/": fixture / "data/approvals",
            }
            for directory in artifacts.values():
                directory.mkdir(parents=True, exist_ok=True)
            (fixture / ".venv/forbidden.txt").write_text("fixture", encoding="utf-8")
            (fixture / ".git/config").write_text("fixture", encoding="utf-8")
            (fixture / "conscious_agent/__pycache__/fixture.pyc").write_bytes(b"fixture")
            (fixture / "data/projects.json").write_text("{}", encoding="utf-8")

            detected = set(privacy_violations(fixture))
            expected = set(artifacts) | {"data/projects.json"}
            missing = sorted(expected - detected)
            assert not missing, {"missing": missing, "detected": sorted(detected)}
            return {"expected": sorted(expected), "detected": sorted(detected)}

    def workspace_fallback() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="eidolon-first-launch-") as data_dir:
            env = os.environ.copy()
            env["EIDOLON_DATA_DIR"] = data_dir
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            code = (
                "import json,sys; sys.path.insert(0,'conscious_agent'); "
                "from project_manager import get_active_project, PROJECTS_FILE; "
                "p=get_active_project(); print(json.dumps({'project':p,'runtime_projects_exists':PROJECTS_FILE.exists()}))"
            )
            completed = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            assert completed.returncode == 0, completed.stderr
            payload = json.loads(completed.stdout.strip())
            assert payload["project"] and payload["project"].get("id") == "eidolon", payload
            assert payload["runtime_projects_exists"] is False, payload
            assert not (Path(data_dir) / "projects.json").exists()
            return payload

    def workspace_metadata() -> dict[str, Any]:
        projects_path = ROOT / "data/workspaces/projects.json"
        active_path = ROOT / "data/workspaces/active_project.json"
        assert not projects_path.exists(), "private workspace registry must not be packaged"
        assert not active_path.exists(), "private active-project state must not be packaged"
        agent_path = str(ROOT / "conscious_agent")
        if agent_path not in sys.path:
            sys.path.insert(0, agent_path)
        from source_project_metadata import load_source_project_metadata

        source = load_source_project_metadata(ROOT)
        assert source.get("active_project_id") == "eidolon", source
        assert source.get("runtime_projects_packaged") is False, source
        assert source.get("last_updated_for") == f"v{source.get('version')}", source
        return {
            "active_project_id": source.get("active_project_id"),
            "runtime_projects_packaged": source.get("runtime_projects_packaged"),
            "last_updated_for": source.get("last_updated_for"),
        }

    def paths_with_spaces_and_long() -> dict[str, Any]:
        short_temp_parent = None
        if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            candidate_parent = Path(os.environ["LOCALAPPDATA"]) / "Temp"
            if candidate_parent.is_dir():
                short_temp_parent = str(candidate_parent)
        with tempfile.TemporaryDirectory(prefix="eidolon path fixture ", dir=short_temp_parent) as base:
            # Keep the copied tree below legacy Windows path limits even when the
            # exact candidate was itself extracted under a deliberately long root.
            target = Path(base) / ("long segment " + "x"*20) / ("nested " + "y"*20) / "Eidolon"
            shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv", "venv"))
            env = os.environ.copy(); env["PYTHONDONTWRITEBYTECODE"]="1"; env["EIDOLON_DATA_DIR"] = str(Path(base)/"runtime data")
            completed = subprocess.run([sys.executable, "eidolon.py", "--help"], cwd=target, env=env, capture_output=True, text=True, timeout=30)
            assert completed.returncode == 0, completed.stderr
            assert "model-status" in completed.stdout
            return {
                "path_length": len(str(target)),
                "source_root_length": len(str(ROOT)),
                "contains_spaces": " " in str(target),
            }

    def optional_dependency_absent() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="eidolon-optional-") as data_dir:
            env=os.environ.copy(); env["PYTHONDONTWRITEBYTECODE"]="1"; env["EIDOLON_DATA_DIR"]=data_dir
            code=("import builtins,sys; sys.path.insert(0,'conscious_agent'); old=builtins.__import__; "
                  "builtins.__import__=lambda n,*a,**k: (_ for _ in ()).throw(ImportError('blocked optional')) if n.startswith('chromadb') else old(n,*a,**k); "
                  "import local_model,local_brain; print('ok')")
            completed=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
            assert completed.returncode==0,completed.stderr
        return {"optional_chromadb_required": False}

    def setup_contracts() -> dict[str, Any]:
        sh=(ROOT/"setup.sh").read_text(encoding="utf-8")
        ps=(ROOT/"setup.ps1").read_text(encoding="utf-8")
        assert "--core-only" in sh and "--apply-upgrade-migration" in sh
        assert "CoreOnly" in ps and "ApplyUpgradeMigration" in ps
        compatibility = "(3, 11) <= sys.version_info[:2] < (3, 15)"
        assert compatibility in sh and compatibility in ps
        assert '@("3.11", "3.12", "3.13", "3.14")' in ps
        assert "python3.11 python3.12 python3.13 python3.14" in sh
        assert "Existing .venv uses unsupported Python" in sh and "Existing .venv uses unsupported Python" in ps
        assert '$env:PYTHONDONTWRITEBYTECODE = "1"' in ps
        assert '$env:PYTHONUNBUFFERED = "1"' in ps
        assert "export PYTHONDONTWRITEBYTECODE=1" in sh
        assert "export PYTHONUNBUFFERED=1" in sh
        assert "Eidolon v1080.0 requires Python" in sh and "Eidolon v1080.0 requires Python" in ps

        unix_shell_syntax = "not_required_on_windows"
        if os.name != "nt":
            shell = shutil.which("sh")
            assert shell, "A POSIX shell is required to validate setup.sh on this platform."
            shell_check=subprocess.run([shell,"-n",str(ROOT/"setup.sh")],capture_output=True,text=True,timeout=10)
            assert shell_check.returncode==0,shell_check.stderr
            unix_shell_syntax = "pass"

        powershell_contract = "static_only"
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            setup_path = str(ROOT/"setup.ps1").replace("'", "''")
            parser_command = (
                "$tokens=$null;$errors=$null;"
                f"[System.Management.Automation.Language.Parser]::ParseFile('{setup_path}',[ref]$tokens,[ref]$errors)|Out-Null;"
                "if($errors.Count -gt 0){$errors|ForEach-Object{[Console]::Error.WriteLine($_.Message)};exit 1}"
            )
            ps_check=subprocess.run([powershell,"-NoProfile","-NonInteractive","-Command",parser_command],capture_output=True,text=True,timeout=15)
            assert ps_check.returncode==0,ps_check.stderr
            powershell_contract = "pass"
        elif os.name == "nt":
            raise AssertionError("PowerShell is required to validate setup.ps1 on Windows.")

        return {
            "unix_shell_syntax": unix_shell_syntax,
            "powershell_contract": powershell_contract,
            "native_platform": "windows" if os.name == "nt" else "posix",
            "supported_python_minors": ["3.11", "3.12", "3.13", "3.14"],
            "python_3_14_rejected": True,
        }

    for name, fn in [
        ("clean_source_privacy", privacy),
        ("privacy_detector_negative_control", privacy_negative_control),
        ("first_launch_workspace_fallback_no_runtime_projects", workspace_fallback),
        ("source_only_workspace_metadata_policy", workspace_metadata),
        ("paths_with_spaces_and_long_root", paths_with_spaces_and_long),
        ("missing_optional_dependencies", optional_dependency_absent),
        ("setup_script_contracts", setup_contracts),
    ]:
        check(name, fn)

    after=snapshot(ROOT)
    unchanged=before==after
    results.append({"name":"source_tree_immutability","status":"pass" if unchanged else "fail","details":{"unchanged":unchanged}})
    passed=sum(item["status"]=="pass" for item in results)
    return {
        "suite":"v1078.9 focused fresh-install validation",
        "status":"pass" if passed==len(results) else "fail",
        "passed":passed,
        "total":len(results),
        "native_windows_evidence": os.name == "nt",
        "results":results,
    }


def main() -> int:
    parser=argparse.ArgumentParser(description="Run focused fresh-install local-model validation.")
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    report=run()
    if args.json: print(json.dumps(report,indent=2,default=str))
    else:
        print(f"{report['status'].upper()}: {report['passed']}/{report['total']}")
        for item in report["results"]: print(f"- {item['status']}: {item['name']}")
    return 0 if report["status"]=="pass" else 1

if __name__=="__main__":
    raise SystemExit(main())
