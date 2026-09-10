from __future__ import annotations

"""Legacy supervised-development transaction fixture from the v1200 alpha gate.

This module validates proposal/approval/workspace/receipt mechanics with a
deterministic static-calculator fixture.  It is intentionally *not* evidence of
general code generation.  Current generation evidence belongs to the isolated
coding execution path, which can use grounded project context and a configured
provider while preserving operator approval and workspace isolation.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from paths import DATA_DIR

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1200.0"
SUPPORTED_KIND = "static_calculator_web_app"
EVIDENCE_ROLE = "legacy_transaction_fixture_not_generation_evidence"
GENERAL_GENERATION_PATH = "isolated_coding_execution"
PLANNED_FILES = ("index.html", "styles.css", "calculator.js", "calculator.test.cjs")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (slug[:48] or "calculator-app").strip("-")


def _runtime_root(runtime_root: str | Path | None = None) -> Path:
    return Path(runtime_root).expanduser().resolve() if runtime_root else Path(DATA_DIR).resolve()


def _store_root(runtime_root: str | Path | None = None) -> Path:
    return _runtime_root(runtime_root) / "developer_alpha"


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        json.dump(dict(value), handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _proposal_path(proposal_id: str, runtime_root: str | Path | None = None) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(proposal_id or ""))[:80]
    if not safe_id or safe_id != proposal_id:
        raise ValueError("Invalid developer proposal id.")
    return _store_root(runtime_root) / "proposals" / f"{safe_id}.json"


def _receipt_path(proposal_id: str, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "receipts" / f"{proposal_id}.json"


def _proposal_payload(request: str, workspace_name: str = "") -> dict[str, Any]:
    clean = " ".join(str(request or "").split())[:4000]
    lowered = clean.casefold()
    supported = bool(
        "calculator" in lowered
        and any(token in lowered for token in ("web page", "webpage", "website", "web app", "html"))
        and any(token in lowered for token in ("make", "build", "create", "develop", "implement", "code"))
    )
    request_digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()
    proposal_id = f"dev_{request_digest[:20]}"
    slug = _safe_slug(workspace_name or "calculator-app")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "request": clean,
        "request_digest": request_digest,
        "created_at": _now(),
        "status": "ready_for_operator_review" if supported else "unsupported_alpha_request",
        "supported_kind": SUPPORTED_KIND if supported else "",
        "workspace_name": slug,
        "risk_level": "medium" if supported else "unknown",
        "approval_required": True,
        "approval_granted": False,
        "planned_files": list(PLANNED_FILES) if supported else [],
        "stages": [
            "inspect", "specify", "plan", "operator_review", "implement_in_sandbox",
            "test", "diagnose_or_repair", "present_result", "bounded_learning",
        ] if supported else [],
        "limitations": [] if supported else [
            "The v1200 executable alpha currently supports a static calculator web app; other requests remain proposal-only."
        ],
        "source_write_allowed": False,
        "workspace_write_allowed_after_approval": supported,
        "provider_contacted": False,
        "model_contacted": False,
        "authority_granted": False,
        "evidence_role": EVIDENCE_ROLE,
        "general_generation_path": GENERAL_GENERATION_PATH,
        "general_code_generation_claimed": False,
    }
    payload["proposal_digest"] = _digest(payload)
    return payload


def create_development_proposal(
    request: str,
    *,
    workspace_name: str = "",
    runtime_root: str | Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    proposal = _proposal_payload(request, workspace_name)
    if persist:
        path = _proposal_path(proposal["proposal_id"], runtime_root)
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("request_digest") == proposal["request_digest"]:
                return existing
            raise ValueError("A conflicting proposal already occupies this id.")
        _atomic_json(path, proposal)
    return proposal


def load_development_proposal(proposal_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    path = _proposal_path(proposal_id, runtime_root)
    if not path.exists():
        return {"ok": False, "status": "not_found", "proposal_id": proposal_id}
    proposal = json.loads(path.read_text(encoding="utf-8"))
    supplied = str(proposal.pop("proposal_digest", ""))
    expected = _digest(proposal)
    proposal["proposal_digest"] = supplied
    if supplied != expected:
        return {"ok": False, "status": "tampered", "proposal_id": proposal_id}
    return proposal


def _calculator_files() -> dict[str, str]:
    return {
        "index.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Eidolon Calculator</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="calculator" aria-label="Calculator">
    <header><p>Built by Eidolon</p><h1>Calculator</h1></header>
    <output id="display" aria-live="polite">0</output>
    <div class="keys" aria-label="Calculator keypad">
      <button data-action="clear">AC</button><button data-action="sign">+/-</button><button data-action="percent">%</button><button class="operator" data-value="/">/</button>
      <button data-value="7">7</button><button data-value="8">8</button><button data-value="9">9</button><button class="operator" data-value="*">x</button>
      <button data-value="4">4</button><button data-value="5">5</button><button data-value="6">6</button><button class="operator" data-value="-">-</button>
      <button data-value="1">1</button><button data-value="2">2</button><button data-value="3">3</button><button class="operator" data-value="+">+</button>
      <button class="zero" data-value="0">0</button><button data-value=".">.</button><button class="equals" data-action="equals">=</button>
    </div>
  </main>
  <script defer src="calculator.js"></script>
</body>
</html>
""",
        "styles.css": """* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #eef1f5; color: #17191d; font-family: Inter, system-ui, sans-serif; }
.calculator { width: min(92vw, 360px); padding: 20px; background: #17191d; color: white; border: 1px solid #30343b; border-radius: 8px; box-shadow: 0 18px 48px rgba(0,0,0,.22); }
header p { margin: 0; color: #8fd5a6; font-size: 12px; text-transform: uppercase; }
h1 { margin: 4px 0 18px; font-size: 22px; }
#display { display: block; min-height: 72px; padding: 12px; overflow: hidden; text-align: right; font-size: 42px; background: #0c0e11; border-radius: 6px; }
.keys { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 12px; }
button { min-height: 58px; border: 0; border-radius: 6px; background: #30343b; color: white; font-size: 20px; cursor: pointer; }
button:hover, button:focus-visible { outline: 2px solid #8fd5a6; background: #3b4048; }
.operator { background: #226c43; } .equals { background: #b33a32; } .zero { grid-column: span 2; }
@media (max-height: 600px) { .calculator { padding: 12px; } button { min-height: 44px; } #display { min-height: 54px; font-size: 32px; } }
""",
        "calculator.js": """function calculate(left, operator, right) {
  const a = Number(left); const b = Number(right);
  if (!Number.isFinite(a) || !Number.isFinite(b)) throw new Error('Invalid number');
  if (operator === '+') return a + b;
  if (operator === '-') return a - b;
  if (operator === '*') return a * b;
  if (operator === '/') { if (b === 0) throw new Error('Cannot divide by zero'); return a / b; }
  throw new Error('Unknown operator');
}

if (typeof module !== 'undefined' && module.exports) module.exports = { calculate };

if (typeof document !== 'undefined') {
 const display = document.querySelector('#display');
 let current = '0'; let left = null; let operator = null; let replace = false;
 function render(value = current) { display.textContent = String(value).slice(0, 14); }
 function input(value) {
  if ('+-*/'.includes(value)) { left = Number(current); operator = value; replace = true; return; }
  if (replace) { current = '0'; replace = false; }
  if (value === '.' && current.includes('.')) return;
  current = current === '0' && value !== '.' ? value : current + value; render();
 }
 function equals() {
  if (left === null || !operator) return;
  try { current = String(calculate(left, operator, current)); } catch (error) { current = error.message; }
  left = null; operator = null; replace = true; render();
 }
 document.querySelector('.keys').addEventListener('click', (event) => {
  const button = event.target.closest('button'); if (!button) return;
  if (button.dataset.value) input(button.dataset.value);
  else if (button.dataset.action === 'equals') equals();
  else if (button.dataset.action === 'clear') { current = '0'; left = null; operator = null; render(); }
  else if (button.dataset.action === 'sign') { current = String(Number(current) * -1); render(); }
  else if (button.dataset.action === 'percent') { current = String(Number(current) / 100); render(); }
 });
 window.addEventListener('keydown', (event) => {
  if (/^[0-9.]$/.test(event.key) || '+-*/'.includes(event.key)) input(event.key);
  else if (event.key === 'Enter' || event.key === '=') { event.preventDefault(); equals(); }
  else if (event.key === 'Escape') { current = '0'; left = null; operator = null; render(); }
 });
 window.__eidolonCalculatorReady = true;
}
""",
        "calculator.test.cjs": """const assert = require('node:assert/strict');
const { calculate } = require('./calculator.js');
assert.equal(calculate(2, '+', 3), 5);
assert.equal(calculate(9, '-', 4), 5);
assert.equal(calculate(7, '*', 6), 42);
assert.equal(calculate(8, '/', 2), 4);
assert.throws(() => calculate(1, '/', 0), /divide by zero/);
console.log(JSON.stringify({ok:true, arithmetic_cases:5}));
""",
    }


def _validate_workspace(workspace: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for name in PLANNED_FILES:
        path = workspace / name
        checks.append({"name": f"file:{name}", "ok": path.is_file() and path.stat().st_size > 0})
    html = (workspace / "index.html").read_text(encoding="utf-8")
    checks.extend((
        {"name": "html:calculator-label", "ok": 'aria-label="Calculator"' in html},
        {"name": "html:responsive-viewport", "ok": 'name="viewport"' in html},
        {"name": "html:browser-script-linked", "ok": '<script defer src="calculator.js"></script>' in html},
    ))
    node = shutil.which("node")
    node_result: dict[str, Any] = {"available": bool(node), "ok": False, "returncode": None}
    if node:
        completed = subprocess.run(
            [node, "calculator.test.cjs"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=15,
        )
        node_result.update({"ok": completed.returncode == 0, "returncode": completed.returncode})
        checks.append({"name": "javascript:arithmetic", "ok": completed.returncode == 0})
    else:
        checks.append({"name": "javascript:arithmetic", "ok": False, "status": "node_unavailable"})
    return {
        "ok": all(row["ok"] for row in checks),
        "checks": checks,
        "passed": sum(bool(row["ok"]) for row in checks),
        "total": len(checks),
        "node": node_result,
    }


def execute_development_proposal(
    proposal_id: str,
    *,
    operator_approved: bool,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    proposal = load_development_proposal(proposal_id, runtime_root=runtime_root)
    if proposal.get("status") in {"not_found", "tampered"}:
        return {"ok": False, "status": proposal["status"], "proposal_id": proposal_id}
    if proposal.get("status") != "ready_for_operator_review":
        return {"ok": False, "status": "blocked", "reason": "unsupported_or_ineligible_proposal", "proposal_id": proposal_id}
    if not operator_approved:
        return {"ok": False, "status": "awaiting_approval", "proposal_id": proposal_id, "source_modified": False}

    root = _store_root(runtime_root).resolve()
    source = _source_root().resolve()
    workspace = (root / "workspaces" / str(proposal["workspace_name"])).resolve()
    if not _is_within(workspace, root) or _is_within(workspace, source) or _is_within(source, workspace):
        return {"ok": False, "status": "blocked", "reason": "workspace_isolation_failed", "proposal_id": proposal_id}

    receipt_path = _receipt_path(proposal_id, runtime_root)
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("proposal_digest") == proposal.get("proposal_digest"):
            existing["idempotent_replay"] = True
            return existing
        return {"ok": False, "status": "blocked", "reason": "receipt_conflict", "proposal_id": proposal_id}

    workspace.mkdir(parents=True, exist_ok=True)
    generated = _calculator_files()
    for relative, content in generated.items():
        destination = (workspace / relative).resolve()
        if not _is_within(destination, workspace):
            return {"ok": False, "status": "blocked", "reason": "generated_path_escaped_workspace", "proposal_id": proposal_id}
        destination.write_text(content, encoding="utf-8", newline="\n")

    validation = _validate_workspace(workspace)
    manifest = {
        relative: hashlib.sha256((workspace / relative).read_bytes()).hexdigest()
        for relative in sorted(generated)
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "ok": bool(validation["ok"]),
        "status": "completed" if validation["ok"] else "failed_validation",
        "proposal_id": proposal_id,
        "proposal_digest": proposal["proposal_digest"],
        "completed_at": _now(),
        "workspace": str(workspace),
        "workspace_manifest": manifest,
        "workspace_manifest_digest": _digest(manifest),
        "validation": validation,
        "stages_completed": [
            "inspect", "specify", "plan", "operator_review", "implement_in_sandbox", "test",
            "diagnose_or_repair", "present_result", "bounded_learning",
        ] if validation["ok"] else ["inspect", "specify", "plan", "operator_review", "implement_in_sandbox", "test"],
        "repair_needed": not validation["ok"],
        "learning_recorded": bool(validation["ok"]),
        "source_modified": False,
        "runtime_workspace_modified": True,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_consumed_once": True,
        "automatic_continuation": False,
        "release_authorized": False,
        "authority_granted": False,
        "evidence_role": EVIDENCE_ROLE,
        "general_generation_path": GENERAL_GENERATION_PATH,
        "general_code_generation_claimed": False,
        "idempotent_replay": False,
    }
    result["receipt_digest"] = _digest(result)
    _atomic_json(receipt_path, result)
    return result


def developer_alpha_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    root = _store_root(runtime_root)
    proposals = sorted((root / "proposals").glob("*.json")) if (root / "proposals").exists() else []
    receipts = sorted((root / "receipts").glob("*.json")) if (root / "receipts").exists() else []
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "proposal_count": len(proposals),
        "completed_count": len(receipts),
        "supported_kind": SUPPORTED_KIND,
        "operator_approval_required": True,
        "source_write_allowed": False,
        "authority_granted": False,
        "evidence_role": EVIDENCE_ROLE,
        "general_generation_path": GENERAL_GENERATION_PATH,
        "general_code_generation_claimed": False,
    }


def public_development_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "schema_version", "contract_version", "proposal_id", "request_digest", "status", "supported_kind",
        "workspace_name", "risk_level", "approval_required", "planned_files", "stages", "limitations",
        "source_write_allowed", "workspace_write_allowed_after_approval", "provider_contacted", "model_contacted",
        "authority_granted", "proposal_digest", "evidence_role", "general_generation_path",
        "general_code_generation_claimed",
    )
    return {key: proposal.get(key) for key in allowed}
