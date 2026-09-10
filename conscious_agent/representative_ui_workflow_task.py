from __future__ import annotations

"""v1396 representative responsive, accessible multi-state UI workflow task."""

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1396.8"
TASK_ID = re.compile(r"^gamma_[a-f0-9]{12,64}$")
DENIED = {
    "selected_project_mutation_authorized": False,
    "eidolon_source_mutation_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "independent_authority_granted": False,
}
REQUIRED_WINDOWS_CHECKS = (
    "desktop_layout",
    "narrow_layout",
    "keyboard_forward",
    "keyboard_backward",
    "focus_visible",
    "error_announcement",
    "completion_announcement",
    "no_horizontal_overflow",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _artifact_files() -> dict[str, str]:
    html = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Daily Check-in</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <a class="skip-link" href="#workflow">Skip to check-in</a>
  <main id="workflow" class="workflow" tabindex="-1" aria-labelledby="workflow-title">
    <header>
      <p class="eyebrow">Private local workflow</p>
      <h1 id="workflow-title">Daily Check-in</h1>
      <p id="progress-text">Step 1 of 3</p>
      <progress id="progress" max="3" value="1">1 of 3</progress>
    </header>
    <div id="status" class="status" role="status" aria-live="polite"></div>
    <form id="check-in" novalidate>
      <section class="step" data-step="profile" aria-labelledby="profile-title">
        <h2 id="profile-title">About you</h2>
        <label for="display-name">Display name</label>
        <input id="display-name" name="displayName" autocomplete="name" required maxlength="80">
        <p id="display-name-error" class="error" role="alert" hidden>Please enter a display name.</p>
      </section>
      <section class="step" data-step="preferences" aria-labelledby="preferences-title" hidden>
        <h2 id="preferences-title">Preferences</h2>
        <label for="cadence">Check-in cadence</label>
        <select id="cadence" name="cadence">
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="manual">Only when I ask</option>
        </select>
        <label class="choice"><input id="reminders" name="reminders" type="checkbox"> Show local reminders</label>
      </section>
      <section class="step" data-step="review" aria-labelledby="review-title" hidden>
        <h2 id="review-title">Review</h2>
        <dl>
          <div><dt>Name</dt><dd id="review-name"></dd></div>
          <div><dt>Cadence</dt><dd id="review-cadence"></dd></div>
          <div><dt>Reminders</dt><dd id="review-reminders"></dd></div>
        </dl>
      </section>
      <section class="step completion" data-step="complete" aria-labelledby="complete-title" hidden>
        <h2 id="complete-title" tabindex="-1">Check-in saved</h2>
        <p>Your choices stayed in this page and were not sent anywhere.</p>
      </section>
      <div class="actions">
        <button id="back" type="button" hidden>Back</button>
        <button id="next" type="submit">Continue</button>
        <button id="restart" type="button" hidden>Start over</button>
      </div>
    </form>
  </main>
  <script src="app.js"></script>
</body>
</html>
'''
    css = '''
*{box-sizing:border-box}
:root{color-scheme:light dark;font-family:system-ui,sans-serif;line-height:1.5}
body{min-height:100vh;margin:0;display:grid;place-items:center;padding:1rem;background:#101114;color:#f7f7f7}
.skip-link{position:fixed;left:1rem;top:-5rem;padding:.75rem 1rem;background:#fff;color:#111;z-index:10}
.skip-link:focus{top:1rem}
.workflow{width:min(100%,38rem);padding:clamp(1rem,4vw,2rem);border:1px solid #626773;background:#191b20;border-radius:.5rem}
.eyebrow{margin:0;color:#aeb8cf;font-size:.8rem;text-transform:uppercase}
h1{margin:.25rem 0}progress{width:100%;height:1rem}.status{min-height:1.5rem;color:#b9d7bd}
.step{display:grid;gap:.75rem;padding:1rem 0}.step[hidden]{display:none}
label{font-weight:700}input,select,button{min-height:44px;font:inherit;border:1px solid #9299a8;border-radius:.35rem;padding:.65rem .75rem}
input,select{width:100%;background:#101114;color:#fff}.choice{display:flex;gap:.75rem;align-items:center}.choice input{width:1.25rem;min-height:1.25rem}
.error{margin:0;color:#ffb4ab}dl{display:grid;gap:.75rem}dl div{display:grid;grid-template-columns:minmax(7rem,1fr) 2fr;gap:1rem;border-bottom:1px solid #454a55;padding-bottom:.5rem}dd{margin:0;overflow-wrap:anywhere}
.actions{display:flex;flex-wrap:wrap;gap:.75rem;justify-content:flex-end}.actions button{min-width:8rem;background:#2b303a;color:#fff}.actions button[type=submit]{background:#d6e2ff;color:#101114}
:focus-visible{outline:3px solid #ffcc66;outline-offset:3px}
@media(max-width:420px){body{display:block;padding:.5rem}.workflow{min-height:calc(100dvh - 1rem);padding:1rem}.actions{display:grid;grid-template-columns:1fr}.actions button{width:100%}dl div{grid-template-columns:1fr;gap:.15rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
'''
    javascript = '''(function(root,factory){const api=factory();if(typeof module!=="undefined"&&module.exports)module.exports=api;if(root)root.DailyCheckIn=api;})(typeof globalThis!=="undefined"?globalThis:this,function(){
const STATES=["profile","preferences","review","complete"];
function initialState(){return{step:"profile",displayName:"",cadence:"daily",reminders:false}}
function update(state,patch){return Object.assign({},state,patch||{})}
function validate(state){return state.step!=="profile"||String(state.displayName||"").trim().length>0}
function next(state){if(!validate(state))return state;const i=STATES.indexOf(state.step);return update(state,{step:STATES[Math.min(i+1,STATES.length-1)]})}
function back(state){const i=STATES.indexOf(state.step);return update(state,{step:STATES[Math.max(i-1,0)]})}
function view(state){return{index:STATES.indexOf(state.step),complete:state.step==="complete",valid:validate(state)}}
if(typeof document!=="undefined"){
 const form=document.querySelector("#check-in"),status=document.querySelector("#status"),backButton=document.querySelector("#back"),nextButton=document.querySelector("#next"),restartButton=document.querySelector("#restart"),progress=document.querySelector("#progress"),progressText=document.querySelector("#progress-text"),nameInput=document.querySelector("#display-name"),cadence=document.querySelector("#cadence"),reminders=document.querySelector("#reminders"),nameError=document.querySelector("#display-name-error");let state=initialState();
 function capture(){state=update(state,{displayName:nameInput.value,cadence:cadence.value,reminders:reminders.checked})}
 function render(message){const details=view(state),progressValue=Math.min(details.index+1,3),progressLabel=details.complete?"Complete":"Step "+String(details.index+1)+" of 3";document.querySelectorAll(".step").forEach(node=>{node.hidden=node.dataset.step!==state.step});backButton.hidden=details.index===0||details.complete;nextButton.hidden=details.complete;restartButton.hidden=!details.complete;progress.value=progressValue;progress.textContent=progressLabel;progress.setAttribute("aria-valuetext",progressLabel);progressText.textContent=progressLabel;nextButton.textContent=state.step==="review"?"Save check-in":"Continue";document.querySelector("#review-name").textContent=state.displayName;document.querySelector("#review-cadence").textContent=state.cadence;document.querySelector("#review-reminders").textContent=state.reminders?"On":"Off";status.textContent=message||"";if(details.complete)document.querySelector("#complete-title").focus();else document.querySelector('[data-step="'+state.step+'"] input,[data-step="'+state.step+'"] select')?.focus()}
 form.addEventListener("submit",event=>{event.preventDefault();capture();if(!validate(state)){nameError.hidden=false;nameInput.setAttribute("aria-invalid","true");nameInput.setAttribute("aria-describedby","display-name-error");status.textContent="Please correct the highlighted field.";nameInput.focus();return}nameError.hidden=true;nameInput.removeAttribute("aria-invalid");nameInput.removeAttribute("aria-describedby");state=next(state);render(state.step==="complete"?"Check-in saved locally.":"")});
 backButton.addEventListener("click",()=>{capture();state=back(state);render()});restartButton.addEventListener("click",()=>{state=initialState();nameInput.value="";cadence.value="daily";reminders.checked=false;render("Check-in reset.")});render();
}
return{STATES,initialState,update,validate,next,back,view};});
'''
    tests = '''const assert=require("assert");const ui=require("./app.js");let s=ui.initialState();assert.strictEqual(s.step,"profile");assert.strictEqual(ui.validate(s),false);assert.strictEqual(ui.next(s).step,"profile");s=ui.update(s,{displayName:"Marcus"});s=ui.next(s);assert.strictEqual(s.step,"preferences");s=ui.update(s,{cadence:"weekly",reminders:true});s=ui.next(s);assert.strictEqual(s.step,"review");assert.strictEqual(ui.back(s).step,"preferences");s=ui.next(s);assert.strictEqual(s.step,"complete");assert.strictEqual(ui.view(s).complete,true);console.log("daily check-in workflow tests passed");
'''
    readme = """# Daily Check-in Workflow

Open `index.html` locally. Complete the three keyboard-accessible steps and review the result. No information leaves the page.

Run `node test.js` for deterministic state-machine verification. Manually check 1280x800 and 390x844 viewports on Windows before checkpoint acceptance.
"""
    return {
        "index.html": html,
        "styles.css": css.lstrip(),
        "app.js": javascript,
        "test.js": tests,
        "README.md": readme,
    }


def run_ui_workflow_task(
    *,
    request: str,
    runtime_root: str | Path,
    task_id: str,
    node_executable: str = "node",
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    text = " ".join(str(request or "").split())
    root = Path(runtime_root).expanduser().resolve()
    active = Path(__file__).resolve().parents[1]
    if (
        not TASK_ID.fullmatch(str(task_id or ""))
        or len(text) > 4000
        or not re.search(r"\b(?:workflow|wizard|check[- ]?in)\b", text, re.I)
        or not re.search(r"\b(?:responsive|accessible|accessibility)\b", text, re.I)
    ):
        return {"ok": False, "status": "ui_workflow_request_unsupported", "action_executed": False, **DENIED}
    try:
        root.relative_to(active)
        return {"ok": False, "status": "ui_workflow_runtime_must_be_external", "action_executed": False, **DENIED}
    except ValueError:
        pass
    work = root / "gamma_tasks" / task_id
    if work.exists():
        return {"ok": False, "status": "ui_workflow_task_already_exists", "action_executed": False, **DENIED}
    work.mkdir(parents=True)
    artifacts = _artifact_files()
    for relative, content in artifacts.items():
        (work / relative).write_text(content, encoding="utf-8")
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [node_executable, "test.js"],
            cwd=work,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return {
            "ok": False,
            "status": "ui_workflow_test_execution_failed",
            "reason_digest": _digest(type(exc).__name__),
            "action_executed": True,
            **DENIED,
        }
    structural = {
        "document_language": '<html lang="en">' in artifacts["index.html"],
        "viewport_declared": 'name="viewport"' in artifacts["index.html"],
        "semantic_main": "<main " in artifacts["index.html"],
        "controls_labeled": '<label for="display-name">' in artifacts["index.html"] and '<label for="cadence">' in artifacts["index.html"],
        "live_status": 'role="status" aria-live="polite"' in artifacts["index.html"],
        "progress_announced": 'progress.setAttribute("aria-valuetext",progressLabel)' in artifacts["app.js"],
        "alert_errors": 'role="alert"' in artifacts["index.html"],
        "focus_visible": ":focus-visible" in artifacts["styles.css"],
        "reduced_motion": "prefers-reduced-motion:reduce" in artifacts["styles.css"],
        "responsive_breakpoint": "@media(max-width:420px)" in artifacts["styles.css"],
        "touch_targets": "min-height:44px" in artifacts["styles.css"],
        "multi_state": all(f'data-step="{state}"' in artifacts["index.html"] for state in ("profile", "preferences", "review", "complete")),
    }
    files = [
        {"path": path, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(), "bytes": len(content.encode("utf-8"))}
        for path, content in sorted(artifacts.items())
    ]
    passed = completed.returncode == 0 and all(structural.values())
    core = {
        "contract_version": CONTRACT_VERSION,
        "task_id": task_id,
        "request_digest": _digest(text),
        "workspace_path": str(work),
        "workspace_digest": _digest(str(work)),
        "runnable_entrypoint": "index.html",
        "file_count": len(files),
        "files": files,
        "node_test_exit_code": completed.returncode,
        "node_test_output_digest": hashlib.sha256((completed.stdout or b"") + (completed.stderr or b"")).hexdigest(),
        "test_duration_ms": int((time.monotonic() - started) * 1000),
        "structural_checks": structural,
        "workflow_states": ["profile", "preferences", "review", "complete"],
        "manual_windows_validation_required": True,
        "manual_windows_validation_complete": False,
        "content_free_evidence": True,
        "runnable_result_ready": passed,
        "action_executed": True,
        **DENIED,
    }
    core["task_digest"] = _digest({key: value for key, value in core.items() if key != "workspace_path"})
    return {
        "ok": passed,
        "status": "ui_workflow_ready_for_windows_validation" if passed else "ui_workflow_validation_failed",
        "ui_workflow_task": core,
        "action_executed": True,
        **DENIED,
    }


def record_windows_ui_validation(
    workflow_task: Mapping[str, Any],
    *,
    platform: str,
    checks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    task = dict(workflow_task or {})
    task_digest = str(task.get("task_digest") or "")
    if not re.fullmatch(r"[a-f0-9]{64}", task_digest) or str(platform).strip().lower() != "windows":
        return {"ok": False, "status": "windows_ui_validation_context_invalid", "action_executed": False, **DENIED}
    normalized: dict[str, bool] = {}
    for row in checks:
        name = str(row.get("name") or "")
        if name in REQUIRED_WINDOWS_CHECKS and name not in normalized:
            normalized[name] = row.get("passed") is True
    missing = [name for name in REQUIRED_WINDOWS_CHECKS if name not in normalized]
    failed = [name for name in REQUIRED_WINDOWS_CHECKS if normalized.get(name) is False]
    passed = not missing and not failed
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "task_digest": task_digest,
        "platform": "windows",
        "viewport_count": 2,
        "viewports": ["1280x800", "390x844"],
        "checks": [{"name": name, "passed": normalized.get(name, False)} for name in REQUIRED_WINDOWS_CHECKS],
        "missing_checks": missing,
        "failed_checks": failed,
        "manual_validation_performed": True,
        "manual_windows_validation_complete": passed,
        "content_free_evidence": True,
        "action_executed": False,
        **DENIED,
    }
    receipt["validation_digest"] = _digest(receipt)
    return {
        "ok": passed,
        "status": "windows_ui_validation_passed" if passed else "windows_ui_validation_blocked",
        "windows_ui_validation": receipt,
        "action_executed": False,
        **DENIED,
    }


def process_ui_workflow_task_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {
        "show ui workflow task",
        "inspect ui workflow task",
        "show gamma ui workflow",
    }:
        return {"active": False}
    record = dict((project_state or {}).get("ui_workflow_task") or {})
    return {
        "active": True,
        "ok": bool(record),
        "status": "ui_workflow_task_found" if record else "ui_workflow_task_missing",
        "ui_workflow_task": record,
        "action_executed": False,
        **DENIED,
    }


__all__ = [
    "CONTRACT_VERSION",
    "DENIED",
    "REQUIRED_WINDOWS_CHECKS",
    "run_ui_workflow_task",
    "record_windows_ui_validation",
    "process_ui_workflow_task_control",
]
