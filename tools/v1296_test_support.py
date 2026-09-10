from __future__ import annotations
"""Disposable process fixture support for v1296 tests only."""
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path

def d(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()

def run_fixture(role: str, *, regression: bool = False) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"eidolon-v1296-{role}-") as td:
        root = Path(td); script = root / "health.py"
        script.write_text("import json,sys\nrole=sys.argv[1]\nreg=sys.argv[2]=='1'\nprint(json.dumps({'role':role,'startup':True,'conversation':not reg,'quality':0.75 if reg else 0.98,'latency':30 if role=='baseline' else (85 if reg else 32)}))\n", encoding="utf-8")
        cp = subprocess.run([sys.executable, str(script), role, "1" if regression else "0"], cwd=root, text=True, capture_output=True, timeout=5, check=False)
        data = json.loads(cp.stdout)
        return {"returncode": cp.returncode, "workspace_digest": d(str(root)), "evidence_digest": d(data), **data}
