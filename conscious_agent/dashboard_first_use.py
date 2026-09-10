from __future__ import annotations

"""Lightweight first-use dashboard shell.

The shell is intentionally self-contained. Administrative navigation remains
available through /overview and is not imported merely to render this page.
"""

from html import escape
from typing import Any

from release_metadata import RUNTIME_VERSION


def render_first_use_shell() -> str:
    version = escape(str(RUNTIME_VERSION), quote=True)
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Eidolon v{version}</title>
<style>
:root {{ color-scheme:dark; --bg:#08090b; --panel:#111318; --line:#2c3038; --text:#eee; --muted:#9ca3af; --accent:#ff5148; --good:#73d49b; --warn:#f1c36a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; background:radial-gradient(circle at top,#171014 0,#08090b 38%); color:var(--text); font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; }}
header {{ display:flex; align-items:center; justify-content:space-between; gap:16px; padding:14px 20px; border-bottom:1px solid var(--line); background:rgba(8,9,11,.94); position:sticky; top:0; z-index:4; }}
.brand {{ display:flex; align-items:baseline; gap:10px; }}
.brand b {{ letter-spacing:.16em; color:var(--accent); }}
.brand small,.muted {{ color:var(--muted); }}
nav {{ display:flex; gap:8px; flex-wrap:wrap; }}
a,button {{ color:var(--text); }}
a {{ text-decoration:none; }}
nav a,button {{ border:1px solid var(--line); background:#171a20; border-radius:9px; padding:8px 11px; cursor:pointer; }}
nav a:hover,button:hover {{ border-color:#555b67; }}
main {{ width:min(1100px,calc(100% - 24px)); margin:18px auto; display:grid; grid-template-columns:minmax(0,1fr) 280px; gap:14px; }}
.panel {{ background:rgba(17,19,24,.96); border:1px solid var(--line); border-radius:14px; overflow:hidden; box-shadow:0 20px 55px rgba(0,0,0,.24); position:relative; }}
.panel-head {{ display:flex; justify-content:space-between; gap:12px; align-items:center; padding:12px 14px; border-bottom:1px solid var(--line); }}
.panel-head h1 {{ font-size:16px; margin:0; }}
.conversation-head {{ display:flex; align-items:center; gap:10px; min-width:0; flex:1; }}
.conversation-head select {{ min-width:180px; max-width:360px; border:1px solid var(--line); background:#0c0e12; color:var(--text); border-radius:8px; padding:6px 8px; font:inherit; }}
.badge {{ display:inline-flex; align-items:center; gap:6px; border:1px solid var(--line); border-radius:999px; padding:4px 8px; color:var(--muted); font-size:12px; }}
.badge[data-state='ready'] {{ color:var(--good); border-color:rgba(115,212,155,.35); }}
.badge[data-state='degraded'],.badge[data-state='unavailable'] {{ color:var(--warn); border-color:rgba(241,195,106,.35); }}
#conversation-log {{ min-height:48vh; max-height:58vh; overflow-y:auto; overflow-x:hidden; padding:18px; scroll-behavior:smooth; }}
.jump-latest {{ position:absolute; right:18px; bottom:126px; z-index:3; box-shadow:0 8px 22px rgba(0,0,0,.35); }}
.jump-latest span {{ color:var(--warn); font-variant-numeric:tabular-nums; }}
.empty {{ color:var(--muted); display:grid; place-items:center; min-height:38vh; text-align:center; }}
.message {{ max-width:84%; padding:10px 12px; margin:8px 0; border:1px solid var(--line); border-radius:12px; white-space:pre-wrap; overflow-wrap:anywhere; }}
.message.user {{ margin-left:auto; background:#221719; border-color:#4a292b; }}
.message.eidolon {{ background:#151920; }}
.chat-turn,.chat-bubble {{ min-width:0; max-width:100%; overflow-wrap:anywhere; word-break:break-word; }}
.composer {{ border-top:1px solid var(--line); padding:12px; }}
textarea {{ width:100%; min-height:88px; max-height:35vh; resize:vertical; border:1px solid #3a3f49; border-radius:10px; background:#0c0e12; color:var(--text); padding:12px; font:inherit; }}
textarea:focus {{ outline:2px solid rgba(255,81,72,.28); border-color:var(--accent); }}
.composer-row {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-top:9px; }}
.composer-actions {{ display:flex; align-items:center; gap:8px; }}
button.primary {{ background:#7d211f; border-color:#b83a34; }}
button:disabled {{ opacity:.5; cursor:not-allowed; }}
.status {{ color:var(--muted); min-height:22px; font-size:13px; }}
aside {{ display:grid; gap:12px; align-content:start; }}
.info {{ padding:13px; }}
.info h2 {{ font-size:13px; margin:0 0 8px; color:#d7d9dd; text-transform:uppercase; letter-spacing:.08em; }}
.info p {{ margin:5px 0; overflow-wrap:anywhere; }}
.project-description {{ color:#d7d9dd; }}
.project-meta {{ font-size:12px; color:var(--muted); }}
.progress-list {{ display:grid; gap:7px; margin:0; padding:0; list-style:none; }}
.progress-row {{ display:grid; grid-template-columns:1fr auto; align-items:center; gap:8px; padding:7px 0; border-bottom:1px solid rgba(44,48,56,.65); }}
.progress-row:last-child {{ border-bottom:0; }}
.progress-state {{ font-size:12px; color:var(--muted); }}
.progress-row[data-state='ready'] .progress-state {{ color:var(--good); }}
.progress-row[data-state='degraded'] .progress-state,.progress-row[data-state='pending'] .progress-state {{ color:var(--warn); }}
.retry-small {{ padding:5px 7px; font-size:12px; }}
.recovery {{ border-left:3px solid var(--warn); padding-left:10px; }}
.action-card {{ border:1px solid var(--line); border-radius:10px; padding:10px; margin-top:8px; background:#0c0e12; }}
.action-card h3 {{ font-size:14px; margin:0 0 6px; }}
.action-card p {{ margin:4px 0; }}
.action-card[data-state='blocked'] {{ border-color:rgba(241,195,106,.45); }}
.cognition-controls {{ display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }}
.cognition-controls button,.cognition-controls select {{ min-height:36px; }}
.cognition-controls select {{ border:1px solid var(--line); background:#0c0e12; color:var(--text); border-radius:8px; padding:6px 8px; max-width:100%; }}
.cognition-list {{ margin:8px 0 0; padding-left:18px; color:var(--muted); }}
.cognition-list li {{ margin:5px 0; overflow-wrap:anywhere; }}
.cognition-message {{ border:1px solid var(--line); border-radius:10px; padding:9px; margin-top:8px; background:#0c0e12; overflow-wrap:anywhere; }}
.tool-count {{ font-variant-numeric:tabular-nums; color:var(--good); }}
.hidden {{ display:none!important; }}
@media (max-width:820px) {{ main {{ grid-template-columns:1fr; }} aside {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} #conversation-log {{ min-height:42vh; }} }}
@media (max-width:560px) {{ header {{ align-items:flex-start; flex-direction:column; }} main {{ width:min(100% - 14px,1100px); margin:8px auto; }} aside {{ grid-template-columns:1fr; }} .composer-row,.conversation-head {{ align-items:flex-start; flex-direction:column; }} .conversation-head select {{ width:100%; max-width:none; }} .message {{ max-width:94%; }} .jump-latest {{ bottom:155px; }} }}
</style>
</head>
<body data-first-use-shell='v1101'>
<header>
  <div class='brand'><b>EIDOLON</b><small>v{version} fast first use</small></div>
  <nav><a href='/overview'>Full overview</a><a href='/chat-console?full=1'>Full conversation console</a><a href='/settings'>Settings</a></nav>
</header>
<main>
  <section class='panel' aria-label='Conversation'>
    <div class='panel-head'><div class='conversation-head'><h1 id='session-title'>Restoring conversation…</h1><select id='session-selector' aria-label='Conversation' disabled><option value=''>Restoring conversations…</option></select></div><span class='badge' id='shell-state' data-state='starting'>starting</span></div>
    <div id='conversation-log' aria-live='polite'><div class='empty' id='conversation-empty'>The conversation shell is ready. Private state is restoring in the background.</div></div>
    <button class='jump-latest hidden' id='jump-to-latest' type='button'>Jump to latest <span id='unread-turn-count'></span></button>
    <div class='composer'>
      <textarea id='message' autocomplete='off' enterkeyhint='send' placeholder='Message Eidolon. You can type immediately while local state restores.' aria-label='Message Eidolon'></textarea>
      <div class='composer-row'>
        <div class='status' id='status' role='status' aria-live='polite'>Chat input is interactive. Restoring the selected conversation…</div>
        <div class='composer-actions'><label><input id='use-ai' type='checkbox' checked> local AI</label><button id='action-preview' type='button'>Preview action</button><button id='cancel-active' type='button' class='hidden' disabled>Cancel response</button><button class='primary' id='send' type='button' disabled>Send</button></div>
      </div>
    </div>
  </section>
  <aside>
    <section class='panel info'><h2>Active project</h2><p id='project-name'>Restoring…</p><p class='project-description' id='project-description'>Reading persisted project authority.</p><p class='project-meta' id='project-meta'>Working source and capability truth are still loading.</p></section>
    <section class='panel info'><h2>Runtime home</h2><p><span class='badge' id='runtime-state' data-state='starting'>checking</span></p><p id='runtime-summary' class='project-description'>Checking source and runtime separation.</p><p id='runtime-guidance' class='project-meta'>No data is moved automatically.</p></section>
    <section class='panel info'><h2>Startup progress</h2><ul class='progress-list' id='startup-progress'><li class='progress-row' data-state='ready'><span>Chat input</span><span class='progress-state'>ready</span></li></ul><p class='project-meta' id='restart-state'>Launch continuity has not been compared yet.</p></section>
    <section class='panel info'><h2>First-use checkpoint</h2><p><span class='badge' id='checkpoint-state' data-state='starting'>checking</span></p><p id='checkpoint-summary' class='project-description'>Consolidating startup, continuity, runtime-boundary, and replay-safety truth.</p><p id='checkpoint-next' class='project-meta'>Native Windows evidence remains operator-controlled.</p></section>
    <section class='panel info'><h2>Natural conversation</h2><p><span class='badge' id='conversation-checkpoint-state' data-state='starting'>checking</span></p><p id='conversation-checkpoint-summary' class='project-description'>Checking identity, continuity, correction, response-shape, tuning, and long-session contracts.</p><p id='conversation-checkpoint-next' class='project-meta'>Native quality evidence remains explicit and operator-controlled.</p></section>
    <section class='panel info'><h2>Messaging reliability</h2><p><span class='badge' id='messaging-checkpoint-state' data-state='starting'>checking</span></p><p id='messaging-checkpoint-summary' class='project-description'>Checking timing, keyboard, exactly-once, continuity, cancellation, ownership, and soak contracts.</p><p id='messaging-checkpoint-next' class='project-meta'>Native Windows browser evidence remains explicit and operator-controlled.</p></section>
    <section class='panel info'><h2>Conversational action portal</h2><p><span class='badge' id='action-portal-state' data-state='ready'>preview only</span></p><p id='action-portal-summary' class='project-description'>Classify a turn and inspect a bounded action card before anything runs.</p><p id='action-portal-detail' class='project-meta'><span class='tool-count' id='action-tool-count'>13</span> operator-visible tools. No raw commands, private arguments, automatic approval, or release authority.</p><div id='action-card' class='action-card hidden' data-state='ready' aria-live='polite'></div></section>
    <section class='panel info' id='cognition-panel'><h2>Ongoing cognition</h2><p><span class='badge' id='cognition-state' data-state='starting'>checking</span></p><p id='cognition-summary' class='project-description'>Loading active motivations and bounded-cycle status.</p><p id='cognition-detail' class='project-meta'>Internal state cannot authorize or execute an action.</p><div class='cognition-controls' aria-label='Cognitive cycle controls'><button id='cognition-pause' type='button'>Pause</button><button id='cognition-resume' type='button'>Resume</button><button id='cognition-sleep' type='button'>Sleep</button><button id='cognition-wake' type='button'>Wake</button><select id='cognition-frequency' aria-label='Communication frequency'><option value='minimal'>Minimal initiative</option><option value='low'>Low initiative</option><option value='normal' selected>Normal initiative</option><option value='high'>High initiative</option></select><button id='cognition-quiet' type='button'>Quiet</button></div><ul class='cognition-list' id='cognition-motivations' aria-label='Active motivations'></ul><ul class='cognition-list' id='cognition-reflections' aria-label='Recent reflection conclusions'></ul><div id='cognition-proactive' class='cognition-message hidden' aria-live='polite'></div><button id='cognition-read' class='hidden' type='button'>Mark message read</button></section>
    <section class='panel info' id='internal-life-checkpoint-panel'><h2>Persistent internal-life checkpoint</h2><p><span class='badge' id='internal-life-checkpoint-state' data-state='starting'>checking</span></p><p id='internal-life-checkpoint-summary' class='project-description'>Consolidating persistence, reflection, continuity, belief, privacy, and action-boundary evidence.</p><p id='internal-life-checkpoint-detail' class='project-meta'>This inspection does not claim consciousness, contact a provider, promote, or certify.</p></section>
    <section class='panel info' id='cognitive-development-checkpoint-panel'><h2>Cognitive development checkpoint</h2><p><span class='badge' id='cognitive-development-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-development-checkpoint-summary' class='project-description'>Consolidating bounded inquiry, counterfactual evaluation, resource limits, privacy, and action-boundary evidence.</p><p id='cognitive-development-checkpoint-detail' class='project-meta'>Inquiry and prospective proposals remain browse-free, provider-free, and unauthorized.</p></section>
    <section class='panel info' id='inquiry-continuity-panel'><h2>Inquiry continuity</h2><p><span class='badge' id='inquiry-continuity-state' data-state='starting'>checking</span></p><p id='inquiry-continuity-summary' class='project-description'>Loading attention routing, operator evidence, research proposals, and communication decisions.</p><p id='inquiry-continuity-detail' class='project-meta'>External research and protected actions remain proposal-only and operator-controlled.</p></section>
    <section class='panel info' id='inquiry-cognition-checkpoint-panel'><h2>Inquiry cognition checkpoint</h2><p><span class='badge' id='inquiry-cognition-checkpoint-state' data-state='starting'>checking</span></p><p id='inquiry-cognition-checkpoint-summary' class='project-description'>Consolidating inquiry attention, evidence quality, reflection, communication, resolution, privacy, and authority evidence.</p><p id='inquiry-cognition-checkpoint-detail' class='project-meta'>This read-only checkpoint does not browse, contact a provider, execute actions, certify, or claim consciousness.</p></section>
    <section class='panel info' id='knowledge-confidence-checkpoint-panel'><h2>Knowledge confidence</h2><p><span class='badge' id='knowledge-confidence-checkpoint-state' data-state='starting'>checking</span></p><p id='knowledge-confidence-checkpoint-summary' class='project-description'>Loading residual-question lineage, shared-evidence health, and reconsideration pressure.</p><p id='knowledge-confidence-checkpoint-detail' class='project-meta'>This read-only checkpoint preserves uncertainty and cannot browse, act, promote, certify, or prove consciousness.</p></section>
    <section class='panel info' id='knowledge-reconsideration-panel'><h2>Knowledge reconsideration</h2><p><span class='badge' id='knowledge-reconsideration-state' data-state='starting'>checking</span></p><p id='knowledge-reconsideration-summary' class='project-description'>Loading scheduled reviews, evidence propagation, and communication decisions.</p><p id='knowledge-reconsideration-detail' class='project-meta'>Reconsideration remains bounded, provider-free, and unable to authorize or execute actions.</p></section>
    <section class='panel info' id='knowledge-maintenance-consolidation-panel'><h2>Knowledge maintenance</h2><p><span class='badge' data-state='ready'>bounded</span></p><p class='project-description'>Reconsideration reflections and belief-maintenance outcomes remain concise, accountable, and read-only at consolidation.</p><p class='project-meta'>No provider, browsing, action authority, promotion, certification, or hidden reasoning exposure.</p></section>
    <section class='panel info' id='knowledge-maintenance-checkpoint-panel'><h2>Knowledge maintenance checkpoint</h2><p><span class='badge' id='knowledge-maintenance-checkpoint-state' data-state='starting'>checking</span></p><p id='knowledge-maintenance-checkpoint-summary' class='project-description'>Consolidating reconsideration schedules, evidence propagation, bounded reflection, maintenance outcomes, uncertainty, and communication continuity.</p><p id='knowledge-maintenance-checkpoint-detail' class='project-meta'>This read-only checkpoint does not expose hidden reasoning, contact providers, browse, act, promote, certify, or claim consciousness.</p></section>
    <section class='panel info' id='attention-agenda-checkpoint-panel'><h2>Autonomous attention agenda</h2><p><span class='badge' id='attention-agenda-checkpoint-state' data-state='starting'>checking</span></p><p id='attention-agenda-checkpoint-summary' class='project-description'>Loading durable candidates, bounded arbitration, deliberate no-selection, fairness, and repetition suppression.</p><p id='attention-agenda-checkpoint-detail' class='project-meta'>This read-only view exposes no private subjects, evidence text, provider payloads, hidden reasoning, or action authority.</p></section>
    <section class='panel info' id='attention-intention-checkpoint-panel'><h2>Attention and intention</h2><p><span class='badge' id='attention-intention-checkpoint-state' data-state='starting'>checking</span></p><p id='attention-intention-checkpoint-summary' class='project-description'>Loading one-step reflection intake, deliberate silence, and bounded non-authorizing intentions.</p><p id='attention-intention-checkpoint-detail' class='project-meta'>Attention is not intention; intention is not proposal, authorization, or execution.</p></section>
    <section class='panel info' id='autonomous-attention-intention-checkpoint-panel'><h2>Attention and intention checkpoint</h2><p><span class='badge' id='autonomous-attention-intention-checkpoint-state' data-state='starting'>checking</span></p><p id='autonomous-attention-intention-checkpoint-summary' class='project-description'>Loading the complete durable attention-to-intention lifecycle checkpoint.</p><p id='autonomous-attention-intention-checkpoint-detail' class='project-meta'>Internal attention remains separate from proposal, authorization, and execution.</p></section>
    <section class='panel info' id='persistent-initiative-checkpoint-panel'><h2>Persistent initiative</h2><p><span class='badge' id='persistent-initiative-checkpoint-state' data-state='starting'>checking</span></p><p id='persistent-initiative-checkpoint-summary' class='project-description'>Loading durable initiative candidacy, bounded selection, and deliberate silence.</p><p id='persistent-initiative-checkpoint-detail' class='project-meta'>Selection is not message delivery, proposal, authorization, or execution.</p></section>
    <section class='panel info' id='initiative-lifecycle-checkpoint-panel'><h2>Initiative lifecycle</h2><p><span class='badge' id='initiative-lifecycle-checkpoint-state' data-state='starting'>checking</span></p><p id='initiative-lifecycle-checkpoint-summary' class='project-description'>Loading surfaced initiative and response reconciliation evidence.</p><p id='initiative-lifecycle-checkpoint-detail' class='project-meta'>Read-only accounting; no generation, sending, retry, notification, authorization, or execution.</p></section>
    <section class='panel info' id='long-horizon-objective-checkpoint-panel'><h2>Long-horizon objectives</h2><p><span class='badge' id='long-horizon-objective-checkpoint-state' data-state='starting'>checking</span></p><p id='long-horizon-objective-checkpoint-summary' class='project-description'>Loading durable objectives and bounded review arbitration.</p><p id='long-horizon-objective-checkpoint-detail' class='project-meta'>Read-only structural evidence; objectives cannot authorize or execute actions.</p></section>
    <section class='panel info' id='objective-planning-progress-checkpoint-panel'><h2>Objective planning and progress</h2><p><span class='badge' data-state='starting'>checking</span></p><p class='project-description'>Loading bounded milestones and evidence-based progress accounting.</p><p class='project-meta'>Read-only structural evidence; milestones are not executable tasks and progress is never inferred from discussion volume.</p></section>
    <section class='panel info' id='long-horizon-objective-lifecycle-checkpoint-panel'><h2>Objective lifecycle review</h2><p><span class='badge' data-state='starting'>checking</span></p><p class='project-description'>Loading conflict, completion, abandonment, and retirement evidence.</p><p class='project-meta'>Read-only structural evidence; priority and completion records grant no action authority.</p></section>
    <section class='panel info' id='long-horizon-follow-through-checkpoint-panel'><h2>Long-horizon follow-through checkpoint</h2><p><span class='badge' id='long-horizon-follow-through-checkpoint-state' data-state='starting'>checking</span></p><p id='long-horizon-follow-through-checkpoint-summary' class='project-description'>Consolidating objectives, milestones, progress evidence, conflicts, completion, and abandonment.</p><p id='long-horizon-follow-through-checkpoint-detail' class='project-meta'>Read-only structural evidence; no proposal, authorization, execution, or consciousness claim.</p></section>
    <section class='panel info' id='self-model-continuity-checkpoint-panel'><h2>Persistent self-model</h2><p><span class='badge' id='self-model-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='self-model-continuity-checkpoint-summary' class='project-description'>Loading evidence-backed identity claims and bounded revision outcomes.</p><p id='self-model-continuity-checkpoint-detail' class='project-meta'>Read-only structural evidence; identity claims remain revisable and grant no authority.</p></section>
    <section class='panel info' id='identity-revision-checkpoint-panel'><h2>Identity revision</h2><p><span class='badge' id='identity-revision-checkpoint-state' data-state='starting'>checking</span></p><p id='identity-revision-checkpoint-summary' class='project-description'>Loading contradiction, durable-change, and bounded self-model revision evidence.</p><p id='identity-revision-checkpoint-detail' class='project-meta'>Read-only structural evidence; temporary variation is not permanent identity and revision grants no authority.</p></section>
    <section class='panel info' id='identity-expression-lifecycle-checkpoint-panel'><h2>Identity expression</h2><p><span class='badge' id='identity-expression-lifecycle-checkpoint-state' data-state='starting'>checking</span></p><p id='identity-expression-lifecycle-checkpoint-summary' class='project-description'>Loading bounded reflection influence and communication restraint.</p><p id='identity-expression-lifecycle-checkpoint-detail' class='project-meta'>Read-only structural evidence; identity does not dictate conclusions, send messages, or grant authority.</p></section>
    <section class='panel info' id='curiosity-continuity-checkpoint-panel'><h2>Endogenous curiosity</h2><p><span class='badge' id='curiosity-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='curiosity-continuity-checkpoint-summary' class='project-description'>Loading evidence-backed curiosity candidates and deliberate non-inquiry outcomes.</p><p id='curiosity-continuity-checkpoint-detail' class='project-meta'>Read-only structural evidence; curiosity cannot browse, message, authorize, or execute.</p></section>
    <section class='panel info' id='curiosity-lifecycle-checkpoint-panel'><h2>Curiosity lifecycle</h2><p><span class='badge' id='curiosity-lifecycle-checkpoint-state' data-state='starting'>checking</span></p><p id='curiosity-lifecycle-checkpoint-summary' class='project-description'>Loading inquiry-candidate promotion, reformulation, merge, retirement, and unresolved evidence.</p><p id='curiosity-lifecycle-checkpoint-detail' class='project-meta'>Read-only structural evidence; inquiry candidates cannot browse, ask, message, authorize, or execute.</p></section>
    <section class='panel info' id='behavioral-evidence-checkpoint-panel'><h2>Behavioral evidence checkpoint</h2><p><span class='badge' id='behavioral-evidence-checkpoint-state' data-state='starting'>checking</span></p><p id='behavioral-evidence-checkpoint-summary' class='project-description'>Loading privacy-safe outcomes and bounded attribution.</p><p id='behavioral-evidence-checkpoint-detail' class='project-meta'>Read-only structural evidence; no adaptation, approval, authorization, or execution.</p></section>
    <section class='panel info' id='behavioral-self-evaluation-checkpoint-panel'><h2>Behavioral self-evaluation checkpoint</h2><p><span class='badge' id='behavioral-self-evaluation-checkpoint-state' data-state='starting'>checking</span></p><p id='behavioral-self-evaluation-checkpoint-summary' class='project-description'>Loading evidence-thresholded patterns and bounded self-evaluation.</p><p id='behavioral-self-evaluation-checkpoint-detail' class='project-meta'>Read-only structural inspection; hypotheses cannot adapt behavior or grant authority.</p></section>
    <section class='panel info' id='behavioral-adaptation-checkpoint-panel'><h2>Behavioral adaptation review</h2><p><span class='badge' id='behavioral-adaptation-checkpoint-state' data-state='starting'>checking</span></p><p id='behavioral-adaptation-checkpoint-summary' class='project-description'>Loading proposal and operator-review lifecycle evidence.</p><p id='behavioral-adaptation-checkpoint-detail' class='project-meta'>Read-only inspection; approval never grants authorization or execution.</p></section>
    <section class='panel info' id='active-inquiry-checkpoint-panel'><h2>Active inquiry continuity</h2><p><span class='badge' id='active-inquiry-checkpoint-state' data-state='starting'>checking</span></p><p id='active-inquiry-checkpoint-summary' class='project-description'>Loading bounded active inquiry records and activation restraint.</p><p id='active-inquiry-checkpoint-detail' class='project-meta'>Read-only structural evidence; no browsing, provider contact, prompting, authorization, or execution.</p></section>
    <section class='panel info' id='inquiry-evidence-governance-panel'><h2>Inquiry evidence governance</h2><p><span class='badge' id='inquiry-evidence-governance-state' data-state='starting'>checking</span></p><p id='inquiry-evidence-governance-summary' class='project-description'>Loading bounded evidence-acquisition proposals and operator review state.</p><p id='inquiry-evidence-governance-detail' class='project-meta'>Proposal-only; no browsing, provider contact, prompting, authorization, or execution.</p></section>
    <section class='panel info' id='bounded-inquiry-checkpoint-panel'><h2>Bounded inquiry checkpoint</h2><p><span class='badge' id='bounded-inquiry-checkpoint-state' data-state='starting'>checking</span></p><p id='bounded-inquiry-checkpoint-summary' class='project-description'>Consolidating active inquiry, acquisition governance, evidence assimilation, resolution, and retirement.</p><p id='bounded-inquiry-checkpoint-detail' class='project-meta'>Read-only structural evidence; no autonomous browsing, provider contact, prompting, authorization, execution, or consciousness claim.</p></section>
    <section class='panel info' id='deliberative-decision-review-checkpoint-panel'><h2>Deliberative decision review</h2><p><span class='badge' id='deliberative-decision-review-checkpoint-state' data-state='starting'>checking</span></p><p id='deliberative-decision-review-checkpoint-summary' class='project-description'>Inspecting intention candidacy, commitment outcomes, and bounded reconsideration triggers.</p><p id='deliberative-decision-review-checkpoint-detail' class='project-meta'>Read-only structural evidence; decision, intention, proposal, approval, authorization, and execution remain separate.</p></section>
    <section class='panel info' id='reflective-planning-deliberative-choice-checkpoint-panel'><h2>Reflective planning checkpoint</h2><p><span class='badge' id='reflective-planning-deliberative-choice-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-planning-deliberative-choice-checkpoint-summary' class='project-description'>Consolidating options, comparisons, commitments, intention candidacy, outcome evidence, and reconsideration restraint.</p><p id='reflective-planning-deliberative-choice-checkpoint-detail' class='project-meta'>Read-only structural evidence; deliberation cannot approve, authorize, browse, message, modify, or execute.</p></section>
    <section class='panel info' id='decision-commitment-checkpoint-panel'><h2>Decision commitment checkpoint</h2><p><span class='badge' id='decision-commitment-checkpoint-state' data-state='starting'>checking</span></p><p id='decision-commitment-checkpoint-summary' class='project-description'>Inspecting durable decisions, reconsideration, conflict, replacement, suspension, and retirement.</p><p id='decision-commitment-checkpoint-detail' class='project-meta'>Read-only structural evidence; commitment, intention, proposal, approval, authorization, and execution remain separate.</p></section>
    <section class='panel info' id='cognitive-load-continuity-checkpoint-panel'><h2>Cognitive load continuity checkpoint</h2><p><span class='badge' id='cognitive-load-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-load-continuity-checkpoint-summary' class='project-description'>Inspecting bounded cognitive demands, fairness, and deliberate idle capacity.</p><p id='cognitive-load-continuity-checkpoint-detail' class='project-meta'>Read-only structural evidence; no attention selection, intention, decision, proposal, approval, authorization, or execution.</p></section>
    <section class='panel info' id='cognitive-coordination-review-checkpoint-panel'><h2>Cognitive coordination review</h2><p><span class='badge' id='cognitive-coordination-review-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-coordination-review-checkpoint-summary' class='project-description'>Inspecting completion evidence, interruption outcomes, and scheduling effectiveness.</p><p id='cognitive-coordination-review-checkpoint-detail' class='project-meta'>Read-only structural evidence; review cannot alter scheduling, attention, intentions, authorization, or execution.</p></section>
    <section class='panel info' id='temporal-review-checkpoint-panel'><h2>Temporal review continuity</h2><p><span class='badge' id='temporal-review-checkpoint-state' data-state='starting'>checking</span></p><p id='temporal-review-checkpoint-summary' class='project-description'>Inspecting bounded prospective review sessions and reconciliation.</p><p id='temporal-review-checkpoint-detail' class='project-meta'>Read-only; no reminder, rescheduling, attention, intention, approval, authorization, or execution authority.</p></section>
    <section class='panel info' id='prospective-continuity-review-checkpoint-panel'><h2>Prospective continuity review</h2><p><span class='badge' id='prospective-continuity-review-checkpoint-state' data-state='starting'>checking</span></p><p id='prospective-continuity-review-checkpoint-summary' class='project-description'>Inspecting prospective outcomes and temporal reliability.</p><p id='prospective-continuity-review-checkpoint-detail' class='project-meta'>Read-only; rescheduling proposals require operator review and cannot apply themselves.</p></section>
    <section class='panel info' id='belief-revision-deliberation-checkpoint-panel'><h2>Belief revision deliberation</h2><p><span class='badge' id='belief-revision-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='belief-revision-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded retain, weaken, strengthen, suspend, replace, and unresolved outcomes.</p><p id='belief-revision-deliberation-checkpoint-detail' class='project-meta'>Read-only; deliberation cannot mutate beliefs or grant proposal, approval, authorization, or execution authority.</p></section>
    <section class='panel info' id='epistemic-maintenance-belief-revision-governance-checkpoint-panel'><h2>Epistemic maintenance and belief revision governance</h2><p><span class='badge' id='epistemic-maintenance-belief-revision-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='epistemic-maintenance-belief-revision-governance-checkpoint-summary' class='project-description'>Inspecting evidence-change intake, bounded reconsideration, revision lineage, and epistemic stability.</p><p id='epistemic-maintenance-belief-revision-governance-checkpoint-detail' class='project-meta'>Read-only; no belief mutation, policy application, approval, authorization, or execution authority.</p></section>
    <section class='panel info' id='belief-continuity-review-checkpoint-panel'><h2>Belief continuity review</h2><p><span class='badge' id='belief-continuity-review-checkpoint-state' data-state='starting'>checking</span></p><p id='belief-continuity-review-checkpoint-summary' class='project-description'>Inspecting revision lineage, reversals, recurrence, and epistemic stability.</p><p id='belief-continuity-review-checkpoint-detail' class='project-meta'>Read-only; historical revisions remain visible and policy proposals cannot apply themselves.</p></section>
    <section class='panel info' id='reflective-focus-deliberation-checkpoint-panel'><h2>Reflective focus deliberation</h2><p><span class='badge' id='reflective-focus-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-focus-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded focus sessions, deterministic continuation, deliberate disengagement, and recovery-aware suspension.</p><p class='project-meta'>Read-only; no reflection, intention, initiative, communication, provider contact, browsing, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='real-reflective-cognition-checkpoint-panel'><h2>Real Reflective Cognition</h2><p><span class='badge' id='real-reflective-cognition-checkpoint-state' data-state='starting'>checking</span></p><p id='real-reflective-cognition-checkpoint-summary' class='project-description'>Consolidating structural subject intake, bounded configured-local-model reflection, continuity, deliberate silence, and reliability restraint.</p><p class='project-meta'>Read-only; no reflection is started and no belief, goal, self-model, communication, initiative, approval, authorization, execution, promotion, or certification authority is granted.</p></section>
    <section class='panel info' id='reflection-quality-intake-checkpoint-panel'><h2>Reflection Quality Intake</h2><p><span class='badge' id='reflection-quality-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-quality-intake-checkpoint-summary' class='project-description'>Inspecting structural reflection-quality signals and evaluation candidacy.</p><p class='project-meta'>Read-only; no belief, goal, self-model, provider, communication, approval, authorization, or execution authority is granted.</p></section>
    <section class='panel info' id='reflection-quality-deliberation-checkpoint-panel'><h2>Reflection Quality Deliberation</h2><p><span class='badge' id='reflection-quality-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-quality-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded quality evaluation, contradiction handling, confidence calibration, and provider recovery.</p><p class='project-meta'>Read-only; evaluation outcomes do not revise beliefs, goals, self-model, communication, provider, approval, authorization, or execution state.</p></section>
    <section class='panel info' id='reflection-quality-integration-checkpoint-panel'><h2>Reflection Quality Integration</h2><p><span class='badge' id='reflection-quality-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-quality-integration-checkpoint-summary' class='project-description'>Inspecting quality-outcome lineage, integration reliability, and false-pattern suppression.</p><p class='project-meta'>Read-only; quality reviews do not revise beliefs, goals, self-model, communication, provider, approval, authorization, or execution state.</p></section>
    <section class='panel info' id='continuous-thought-governance-checkpoint-panel'><h2>Continuous Thought Governance</h2><p><span class='badge' id='continuous-thought-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='continuous-thought-governance-checkpoint-summary' class='project-description'>Consolidating durable threads, bounded deliberation, outcome lineage, interruption and resumption reliability, and false-pattern restraint.</p><p class='project-meta'>Strictly read-only; no provider request, reflection, belief revision, communication, initiative, approval, authorization, execution, installation, promotion, or certification authority is granted.</p></section>
    <section class='panel info' id='continuous-thought-integration-checkpoint-panel'><h2>Continuous Thought Integration</h2><p><span class='badge' id='continuous-thought-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='continuous-thought-integration-checkpoint-summary' class='project-description'>Checking thought outcome lineage, interruption and resumption reliability, repeated stalls, fixation, and false-pattern restraint.</p><p class='project-meta'>Read-only; no provider request, reflection, belief revision, communication, initiative, approval, authorization, execution, promotion, or certification authority is granted.</p></section>
    <section class='panel info' id='continuous-thought-deliberation-checkpoint-panel'><h2>Continuous Thought Deliberation</h2><p><span class='badge' id='continuous-thought-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='continuous-thought-deliberation-checkpoint-summary' class='project-description'>Checking bounded thread sessions, pause/resume arbitration, branching, conclusion, unresolved outcomes, and recovery deferral.</p><p class='project-meta'>Read-only; no provider request, internal revision, communication, approval, authorization, execution, promotion, or certification authority is granted.</p></section>
    <section class='panel info' id='reflective-communication-integration-checkpoint-panel'><h2>Reflective communication integration</h2><p><span class='badge' id='reflective-communication-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-communication-integration-checkpoint-summary' class='project-description'>Inspecting content-free communication outcome lineage, delayed follow-up continuity, interruption reliability, pattern review, and false-pattern restraint.</p><p class='project-meta'>Read-only; no provider contact, message text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='reflective-communication-governance-checkpoint-panel'><h2>Real reflective communication governance</h2><p><span class='badge' id='reflective-communication-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-communication-governance-checkpoint-summary' class='project-description'>Consolidating communication eligibility, bounded deliberation, deliberate silence, delayed follow-up continuity, considerate non-interruption, outcome lineage, and reliability restraint.</p><p class='project-meta'>Strictly read-only; no provider contact, message text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='reflective-communication-deliberation-checkpoint-panel'><h2>Reflective communication deliberation</h2><p><span class='badge' id='reflective-communication-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-communication-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded communication deliberation, deliberate silence, timing, curiosity, interruption sensitivity, and recovery-aware deferral.</p><p class='project-meta'>Read-only; no provider contact, message text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='reflective-communication-intake-checkpoint-panel'><h2>Reflective communication intake</h2><p><span class='badge' id='reflective-communication-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-communication-intake-checkpoint-summary' class='project-description'>Inspecting content-free reflection-to-communication eligibility and governed communication candidacy.</p><p class='project-meta'>Read-only; no provider contact, message text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='read-only-perception-intake-checkpoint-panel'><h2>Read-only perception intake</h2><p><span class='badge' id='read-only-perception-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='read-only-perception-intake-checkpoint-summary' class='project-description'>Inspecting content-free project state, system events, completed work, failures, and changed-file signals.</p><p class='project-meta'>Read-only; no raw file content, browsing, provider contact, filesystem mutation, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='revisable-world-model-intake-checkpoint-panel'><h2>Revisable world model intake</h2><p><span class='badge' id='revisable-world-model-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='revisable-world-model-intake-checkpoint-summary' class='project-description'>Inspecting content-free people, projects, events, beliefs, causes, uncertainty, and temporal-context relationships.</p><p class='project-meta'>Read-only; no raw content, evidence text, belief mutation, provider contact, message, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='internally-generated-goal-intake-checkpoint-panel'><h2>Internally generated goal intake</h2><p><span class='badge' id='internally-generated-goal-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='internally-generated-goal-intake-checkpoint-summary' class='project-description'>Inspecting content-free goal-formation lineage, value, cost, uncertainty, time horizon, and dependencies.</p><p class='project-meta'>Read-only; no goal activation, plan, initiative, message, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='prospective-planning-deliberation-checkpoint-panel'><h2>Prospective planning deliberation</h2><p><span class='badge' id='prospective-planning-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='prospective-planning-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded plan comparison, counterfactuals, risk, reversibility, stop conditions, and deliberate no-action.</p><p class='project-meta'>Read-only; no plan activation, initiative, provider contact, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='prospective-planning-integration-checkpoint-panel'><h2>Prospective planning integration</h2><p><span class='badge' id='prospective-planning-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='prospective-planning-integration-checkpoint-summary' class='project-description'>Inspecting planning outcome lineage, continuity, reliability, false-pattern suppression, and visible status.</p><p class='project-meta'>Read-only; no plan activation, initiative, provider contact, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='prospective-planning-governance-checkpoint-panel'><h2>Prospective planning governance</h2><p><span class='badge' id='prospective-planning-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='prospective-planning-governance-checkpoint-summary' class='project-description'>Consolidating prospective-plan intake, bounded comparison, deliberate no-action, outcome lineage, continuity, reliability, and false-pattern restraint.</p><p class='project-meta'>Strictly read-only; no plan activation, initiative, provider contact, file mutation, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='supervised-deficiency-deliberation-checkpoint-panel'><h2>Supervised deficiency deliberation</h2><p><span class='badge' id='supervised-deficiency-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-deficiency-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded deficiency deliberation, evidence sufficiency, impact, feasibility, and deterministic verified-deficiency-versus-deferral outcomes.</p><p class='project-meta'>Read-only; verified outcomes cannot create proposals, patches, sandboxes, approvals, authorizations, execution, promotion, or certification.</p></section>
    <section class='panel info' id='supervised-deficiency-integration-checkpoint-panel'><h2>Supervised deficiency integration</h2><p><span class='badge' id='supervised-deficiency-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-deficiency-integration-checkpoint-summary' class='project-description'>Inspecting outcome lineage, continuity, false-positive and missed-deficiency review, and operator-visible policy boundaries.</p><p class='project-meta'>Read-only; reliability findings cannot create or approve development or policy proposals.</p></section>
    <section class='panel info' id='supervised-deficiency-governance-checkpoint-panel'><h2>Supervised deficiency identification governance</h2><p><span class='badge' id='supervised-deficiency-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-deficiency-governance-checkpoint-summary' class='project-description'>Consolidating structural deficiency intake, bounded deliberation, evidence arbitration, outcome lineage, continuity, and reliability restraint.</p><p class='project-meta'>Strictly read-only; no proposal, specification, test plan, sandbox change, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-deficiency-intake-checkpoint-panel'><h2>Supervised deficiency intake</h2><p><span class='badge' id='supervised-deficiency-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-deficiency-intake-checkpoint-summary' class='project-description'>Inspecting content-free capability, reliability, usability, architecture, test, documentation, and governance deficiency lineage.</p><p class='project-meta'>Read-only; no proposal, patch, sandbox, test execution, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-sandbox-change-integration-checkpoint-panel'><h2>Sandbox-change integration</h2><p><span class='badge' id='supervised-sandbox-change-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-change-integration-checkpoint-summary' class='project-description'>Inspecting sandbox-change outcome lineage, continuity, false positives, missed changes, containment, reversibility, isolation, path, and resource drift.</p><p class='project-meta'>Read-only; no patch text, source mutation, sandbox creation, commands, tests, installation, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-isolated-sandbox-execution-governance-checkpoint-panel'><h2>Supervised isolated sandbox execution governance</h2><p><span class='badge' id='supervised-isolated-sandbox-execution-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-isolated-sandbox-execution-governance-checkpoint-summary' class='project-description'>Consolidating isolated-execution eligibility, candidates, bounded deliberation, deterministic arbitration, continuity, containment, reversibility, isolation, resources, and reliability restraint.</p><p class='project-meta'>Strictly read-only; no raw source, patch text, sandbox creation, file mutation, commands, tests, installation, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='operator-correction-reasoning-integration-checkpoint-panel'><h2>Operator correction reasoning integration</h2><p><span class='badge' id='operator-correction-reasoning-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-correction-reasoning-integration-checkpoint-summary' class='project-description'>Inspecting exact correction guidance selection, deterministic conflict deferral, restart continuity, and stale-worker recovery.</p><p class='project-meta'>Strictly read-only; no operator text, reasoning text, history rewrite, belief, goal, motivation, self-model, execution, approval, authorization, installation, promotion, or certification mutation.</p></section>
    <section class='panel info' id='operator-correction-reliability-visible-behavior-checkpoint-panel'><h2>Operator correction reliability and visible behavior</h2><p><span class='badge' id='operator-correction-reliability-visible-behavior-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-correction-reliability-visible-behavior-checkpoint-summary' class='project-description'>Inspecting missed corrections, over-application, conflict, drift, outcome lineage, and restrained visible evidence while preserving historical truth.</p><p class='project-meta'>Strictly read-only; no operator text, reasoning text, history rewrite, belief, goal, motivation, self-model, execution, approval, authorization, installation, promotion, or certification mutation.</p></section>
    <section class='panel info' id='workload-coordination-intake-checkpoint-panel'><h2>Workload coordination intake</h2><p><span class='badge' id='workload-coordination-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='workload-coordination-intake-checkpoint-summary' class='project-description'>Inspecting bounded CPU, memory, latency, and token eligibility across cognition, conversation, inquiry, and development workloads.</p><p class='project-meta'>Strictly read-only; no workload execution, scheduling, preemption, cancellation, provider contact, source mutation, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='workload-coordination-execution-checkpoint-panel'><h2>Workload coordination execution</h2><p><span class='badge' id='workload-coordination-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='workload-coordination-execution-checkpoint-summary' class='project-description'>Inspecting bounded admission, reservation, preemption requests, cancellation, restart continuity, and budget enforcement.</p><p class='project-meta'>Strictly read-only; coordination records grant no authority to execute the underlying cognition, conversation, inquiry, or development work.</p></section>
    <section class='panel info' id='workload-coordination-reliability-checkpoint-panel'><h2>Workload coordination reliability</h2><p><span class='badge' id='workload-coordination-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='workload-coordination-reliability-checkpoint-summary' class='project-description'>Inspecting fairness, starvation risk, latency pressure, contention, and resource drift across bounded workloads.</p><p class='project-meta'>Strictly read-only; no scheduler mutation or authority to execute underlying work.</p></section>
    <section class='panel info' id='workload-coordination-governance-checkpoint-panel'><h2>Workload coordination governance</h2><p><span class='badge' id='workload-coordination-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='workload-coordination-governance-checkpoint-summary' class='project-description'>Consolidating bounded workload eligibility, arbitration, continuity, budget enforcement, fairness review, and restrained visible evidence.</p><p class='project-meta'>Strictly read-only; no underlying workload execution, scheduler mutation, provider contact, source mutation, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='multi-day-continuity-soak-intake-checkpoint-panel'><h2>Multi-day continuity soak intake</h2><p><span class='badge' id='multi-day-continuity-soak-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='multi-day-continuity-soak-intake-checkpoint-summary' class='project-description'>Inspecting bounded sleep, restart, interruption, provider-outage, stale-work, and recovery soak eligibility and campaign candidates.</p><p class='project-meta'>Strictly read-only; no campaign launch, fault injection, provider contact, process restart, work interruption, source mutation, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='multi-day-continuity-soak-execution-checkpoint-panel'><h2>Multi-day continuity soak execution</h2><p><span class='badge' id='multi-day-continuity-soak-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='multi-day-continuity-soak-execution-checkpoint-summary' class='project-description'>Inspecting operator-confirmed launches, bounded observations, recovery receipts, cancellation, timeout, and stale-worker handling.</p><p class='project-meta'>Strictly read-only inspection; no new soak launch, provider action, restart, interruption, source mutation, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='multi-day-continuity-soak-reliability-checkpoint-panel'><h2>Multi-day continuity soak reliability</h2><p><span class='badge' id='multi-day-continuity-soak-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='multi-day-continuity-soak-reliability-checkpoint-summary' class='project-description'>Inspecting repeated failures, recovery and latency drift, scenario gaps, contamination risk, and operator-visible evidence.</p><p class='project-meta'>Strictly read-only inspection; no provider action, restart, interruption, source mutation, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='multi-day-continuity-soak-governance-checkpoint-panel'><h2>Multi-day continuity soak governance</h2><p><span class='badge' id='multi-day-continuity-soak-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='multi-day-continuity-soak-governance-checkpoint-summary' class='project-description'>Consolidating eligibility, campaigns, bounded execution, recovery receipts, reliability review, contamination checks, and visible evidence.</p><p class='project-meta'>Strictly read-only; no campaign launch, fault injection, provider contact, restart, interruption, recovery action, source mutation, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='conversation-cognition-unification-intake-checkpoint-panel'><h2>Conversation and cognition unification intake</h2><p><span class='badge' id='conversation-cognition-unification-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='conversation-cognition-unification-intake-checkpoint-summary' class='project-description'>Inspecting exact content-free cognition, memory, relationship, mood, goal, concern, session, policy, provider, and budget lineage for future conversational use.</p><p class='project-meta'>Strictly read-only; relevance does not grant disclosure, generation, message, cognition-mutation, approval, authorization, installation, promotion, or certification authority. Silence remains valid.</p></section>
    <section class='panel info' id='conversation-cognition-unification-reliability-checkpoint-panel'><h2>Conversation and cognition reliability</h2><p><span class='badge' id='conversation-cognition-unification-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='conversation-cognition-unification-reliability-checkpoint-summary' class='project-description'>Inspecting cross-cycle grounding, stale context, correction effectiveness, coherence, deliberate silence, and structural visible behavior.</p><p class='project-meta'>Strictly read-only; no private text, provider contact, message delivery, cognition mutation, approval, authorization, installation, promotion, or certification authority.</p></section>
    <section class='panel info' id='understandable-cognitive-controls-intake-checkpoint-panel'><h2>Understandable cognitive controls</h2><p><span class='badge' id='understandable-cognitive-controls-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='understandable-cognitive-controls-intake-checkpoint-summary' class='project-description'>Inspecting safe defaults, exact ownership and scope, preview lineage, privacy, resource restraint, and development-proposal boundaries.</p><p class='project-meta'>Strictly read-only; controls cannot be applied and no cognition, provider, message, proposal, approval, installation, promotion, or certification authority is granted.</p></section>
    <section class='panel info' id='understandable-cognitive-controls-reliability-checkpoint-panel'><h2>Cognitive control reliability</h2><p><span class='badge' id='understandable-cognitive-controls-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='understandable-cognitive-controls-reliability-checkpoint-summary' class='project-description'>Inspecting cross-cycle continuity, drift, conflicts, correction effectiveness, safe-default recovery, and bounded visible behavior.</p><p class='project-meta'>Strictly read-only; reliability evidence cannot execute cognition, contact providers, send messages, create proposals, or grant release authority.</p></section>
    <section class='panel info' id='understandable-cognitive-controls-governance-checkpoint-panel'><h2>Cognitive controls governance</h2><p><span class='badge' id='understandable-cognitive-controls-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='understandable-cognitive-controls-governance-checkpoint-summary' class='project-description'>Consolidating safe defaults, exact preview activation, bounded enforcement, rollback, cross-cycle continuity, drift, correction effectiveness, and reliability restraint.</p><p class='project-meta'>Strictly read-only; no private content, cognition execution, provider contact, messaging, proposal creation, approval, authorization, installation, promotion, or certification authority.</p></section>
    <section class='panel info' id='architecture-consolidation-intake-checkpoint-panel'><h2>Architecture consolidation intake</h2><p><span class='badge' id='architecture-consolidation-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='architecture-consolidation-intake-checkpoint-summary' class='project-description'>Inspecting structural ownership, checkpoint registration, and startup tiers.</p><p class='project-meta'>Strictly read-only; no runtime mutation, provider contact, message sending, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='architecture-consolidation-execution-checkpoint-panel'><h2>Architecture consolidation execution</h2><p><span class='badge' id='architecture-consolidation-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='architecture-consolidation-execution-checkpoint-summary' class='project-description'>Inspecting registry-backed checkpoint dispatch and bounded startup tiers.</p><p class='project-meta'>Strictly read-only checkpoint; no provider contact, deferred service startup, message sending, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='architecture-consolidation-reliability-checkpoint-panel'><h2>Architecture consolidation reliability</h2><p><span class='badge' id='architecture-consolidation-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='architecture-consolidation-reliability-checkpoint-summary' class='project-description'>Inspecting ownership drift, duplicate plumbing, startup continuity, and bounded visible behavior.</p><p class='project-meta'>Strictly read-only checkpoint; no provider contact, deferred service startup, source mutation, message sending, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='architecture-consolidation-governance-checkpoint-panel'><h2>Architecture consolidation governance</h2><p><span class='badge' id='architecture-consolidation-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='architecture-consolidation-governance-checkpoint-summary' class='project-description'>Consolidating ownership, registry dispatch, startup tiers, continuity, drift detection, duplicate-plumbing review, and bounded reliability evidence.</p><p class='project-meta'>Strictly read-only; no provider contact, deferred service startup, source or runtime mutation, message sending, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='privacy-security-hardening-intake-checkpoint-panel'><h2>Privacy and security hardening intake</h2><p><span class='badge' id='privacy-security-hardening-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='privacy-security-hardening-intake-checkpoint-summary' class='project-description'>Inspecting six threat classes and twelve bounded, content-free security-test candidates.</p><p class='project-meta'>Strictly read-only; no attack payloads, provider contact, command execution, cognitive mutation, message sending, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='privacy-security-hardening-execution-checkpoint-panel'><h2>Privacy and security hardening execution</h2><p><span class='badge' id='privacy-security-hardening-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='privacy-security-hardening-execution-checkpoint-summary' class='project-description'>Inspecting bounded structural security-test execution, containment, recovery, and exact finding lineage.</p><p class='project-meta'>Strictly read-only inspection; no attack payloads, provider contact, commands, source mutation, messaging, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='privacy-security-hardening-reliability-checkpoint-panel'><h2>Privacy and security hardening reliability</h2><p><span class='badge' id='privacy-security-hardening-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='privacy-security-hardening-reliability-checkpoint-summary' class='project-description'>Inspecting cross-cycle recurrence, drift, containment, recovery, and bounded security reliability.</p><p class='project-meta'>Strictly read-only inspection; no attack content, provider contact, commands, cognition mutation, messaging, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='privacy-security-hardening-governance-checkpoint-panel'><h2>Privacy and security hardening governance</h2><p><span class='badge' id='privacy-security-hardening-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='privacy-security-hardening-governance-checkpoint-summary' class='project-description'>Consolidating threat coverage, bounded execution, findings, containment, recovery, continuity, drift, recurrence, and reliability evidence.</p><p class='project-meta'>Strictly read-only; no attack content, provider contact, commands, source or cognition mutation, messaging, approval, authorization, installation, promotion, or certification.</p></section>
    <section class='panel info' id='cognitive-alpha-feature-freeze-intake-checkpoint-panel'><h2>Cognitive Alpha feature freeze intake</h2><p><span class='badge' id='cognitive-alpha-feature-freeze-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-alpha-feature-freeze-intake-checkpoint-summary' class='project-description'>Checking frozen feature scope and installation, upgrade, backup, rollback, and packaging readiness intake.</p><p class='project-meta'>Strictly read-only; no install, rollback, provider contact, command execution, mutation, approval, promotion, or certification.</p></section>
    <section class='panel info' id='cognitive-alpha-feature-freeze-execution-checkpoint-panel'><h2>Cognitive Alpha feature freeze execution</h2><p><span class='badge' id='cognitive-alpha-feature-freeze-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-alpha-feature-freeze-execution-checkpoint-summary' class='project-description'>Checking bounded release-readiness execution and recovery continuity.</p><p class='project-meta'>Strictly read-only; no installation, upgrade, backup, rollback, provider contact, command execution, promotion, or certification.</p></section>
    <section class='panel info' id='cognitive-alpha-feature-freeze-reliability-checkpoint-panel'><h2>Cognitive Alpha feature freeze reliability</h2><p><span class='badge' id='cognitive-alpha-feature-freeze-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-alpha-feature-freeze-reliability-checkpoint-summary' class='project-description'>Checking cross-cycle release continuity, recovery reliability, drift, and operator-visible readiness.</p><p class='project-meta'>Strictly read-only; no installation, upgrade, backup, rollback, packaging, provider contact, command execution, promotion, or certification.</p></section>
    <section class='panel info' id='cognitive-alpha-feature-freeze-governance-checkpoint-panel'><h2>Cognitive Alpha feature freeze governance</h2><p><span class='badge' id='cognitive-alpha-feature-freeze-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-alpha-feature-freeze-governance-checkpoint-summary' class='project-description'>Consolidating frozen feature scope, release readiness, recovery continuity, reliability, and v1150 benchmark readiness.</p><p class='project-meta'>Strictly read-only; no installation, upgrade, backup, rollback, packaging, provider contact, command execution, approval, promotion, certification, or benchmark execution.</p></section>
    <section class='panel info' id='reasoning-alpha-checkpoint-panel'><h2>Reasoning Alpha checkpoint</h2><p><span class='badge' id='reasoning-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='reasoning-alpha-checkpoint-summary' class='project-description'>Consolidating cognitive integration, external runtime migration, checkpoint discovery, ordinary-turn cognition, recovery, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only; no provider contact, commands, actions, cognition mutation, approval, authorization, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='reflection-alpha-checkpoint-panel'><h2>Reflection Alpha checkpoint</h2><p><span class='badge' id='reflection-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-alpha-checkpoint-summary' class='project-description'>Consolidating actual-subject reflection, bounded evidence, revision lineage, correction precedence, contradiction restraint, quarantine, prompt safety, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only; no raw reflection text, provider contact, commands, actions, memory mutation, approval, authorization, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='belief-revision-alpha-checkpoint-panel'><h2>Belief Revision Alpha checkpoint</h2><p><span class='badge' id='belief-revision-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='belief-revision-alpha-checkpoint-summary' class='project-description'>Consolidating provisional beliefs, explicit uncertainty, evidence revision, conflict preservation, correction supersession, bounded deliberation, recovery, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only; no belief or evidence text, conflict resolution, provider contact, commands, actions, memory mutation, approval, authorization, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='multi-step-deliberation-alpha-checkpoint-panel'><h2>Multi-Step Deliberation Alpha checkpoint</h2><p><span class='badge' id='multi-step-deliberation-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='multi-step-deliberation-alpha-checkpoint-summary' class='project-description'>Consolidating bounded alternatives, prerequisite-aware reasoning, evidence comparison, cross-turn continuity, goal constraints, recovery, prompt safety, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only; no proposition or goal text, conflict resolution, decision creation, provider contact, commands, actions, memory mutation, approval, authorization, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='decision-boundary-alpha-checkpoint-panel'><h2>Decision-Boundary Alpha checkpoint</h2><p><span class='badge' id='decision-boundary-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='decision-boundary-alpha-checkpoint-summary' class='project-description'>Consolidating explicit no-decision states, evidence and prerequisite gates, candidate recommendations, cost and rollback review, exact-digest previews, recovery, tamper rejection, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only; no candidate text, approval request, approval, decision, intention, execution, provider contact, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='reasoning-alpha-consolidation-checkpoint-panel'><h2>Reasoning Alpha Consolidation checkpoint</h2><p><span class='badge' id='reasoning-alpha-consolidation-checkpoint-state' data-state='starting'>checking</span></p><p id='reasoning-alpha-consolidation-checkpoint-summary' class='project-description'>Consolidating unified reasoning outcomes, bounded prompt projection, cross-turn transitions, recovery, stale and malformed-state handling, integrity checks, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only; no private chain-of-thought, reasoning content, decision, intention, approval, execution, provider contact, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='conversation-intent-selection-checkpoint-panel'><h2>Conversation Intent Selection checkpoint</h2><p><span class='badge' id='conversation-intent-selection-checkpoint-state' data-state='starting'>checking</span></p><p id='conversation-intent-selection-checkpoint-summary' class='project-description'>Consolidating bounded response-intent evidence, deterministic candidate comparison, contextual posture, shared streaming and non-streaming integration, malformed-input recovery, prompt-envelope integrity, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no message or memory text, private chain-of-thought, provider contact, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='contextual-conversation-behavior-checkpoint-panel'><h2>Contextual Conversation Behavior checkpoint</h2><p><span class='badge' id='contextual-conversation-behavior-checkpoint-state' data-state='starting'>checking</span></p><p id='contextual-conversation-behavior-checkpoint-summary' class='project-description'>Consolidating bounded warmth, familiarity, directness, reassurance, continuity, follow-up, stale-context, conflict, adversarial-input, shared-path, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no identity, mood, relationship, conversation, or memory text, private chain-of-thought, provider contact, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='follow-up-silence-checkpoint-panel'><h2>Follow-Up and Intentional Silence checkpoint</h2><p><span class='badge' id='follow-up-silence-checkpoint-state' data-state='starting'>checking</span></p><p id='follow-up-silence-checkpoint-summary' class='project-description'>Consolidating bounded follow-up usefulness, one-question scope, redundancy restraint, literal intentional silence, malformed and adversarial recovery, shared-path integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no user text, generated response, memory text, private chain-of-thought, provider contact, proactive turn, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='cognitive-integration-alpha-checkpoint-panel'><h2>Cognitive Integration Alpha checkpoint</h2><p><span class='badge' id='cognitive-integration-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-integration-alpha-checkpoint-summary' class='project-description'>Consolidating response intent, contextual behavior, follow-up and silence, canonical conversation policy, post-commit continuity, adversarial recovery, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no user or assistant text, memory text, identifiers, private chain-of-thought, provider contact, proactive turn, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='conversation-policy-checkpoint-panel'><h2>Conversation Policy checkpoint</h2><p><span class='badge' id='conversation-policy-checkpoint-state' data-state='starting'>checking</span></p><p id='conversation-policy-checkpoint-summary' class='project-description'>Consolidating bounded discourse relations, natural continuity, repair and clarification sequences, closure restraint, verified silence, stale and adversarial history recovery, shared-path integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no conversation, message, memory, prompt, provider, or private reasoning content, proactive turn, learning mutation, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='natural-conversation-continuity-checkpoint-panel'><h2>Natural Conversation Continuity checkpoint</h2><p><span class='badge' id='natural-conversation-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='natural-conversation-continuity-checkpoint-summary' class='project-description'>Consolidating bounded fresh, adjacent, prior-question, continuation, repair, closure, ambiguity, contradiction, stale-history, evidence-integrity, shared-path, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no user or assistant text, memory, prompt, provider, identifier, or private reasoning content, proactive turn, learning mutation, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='natural-follow-up-checkpoint-panel'><h2>Natural Follow-Up checkpoint</h2><p><span class='badge' id='natural-follow-up-checkpoint-state' data-state='starting'>checking</span></p><p id='natural-follow-up-checkpoint-summary' class='project-description'>Consolidating bounded follow-up relevance, topic continuity, repetition restraint, conservative recovery, diagnostics integrity, shared-path, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no user or assistant text, memory, prompt, provider, identifier, or private reasoning content, proactive turn, learning mutation, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='governed-speech-checkpoint-panel'><h2>Governed Proactive Speech checkpoint</h2><p><span class='badge' id='governed-speech-checkpoint-state' data-state='starting'>checking</span></p><p id='governed-speech-checkpoint-summary' class='project-description'>Consolidating bounded response-turn speech modes, operator suppression, anti-rambling limits, interruption, cooldown, deliberate silence, response-shape audit, diagnostics integrity, shared-path, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no conversation or generated response text, memory, reflection, prompt, provider, identifier, or private reasoning content, autonomous turn, rambling, reflection delivery, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='daily-companion-cognition-checkpoint-panel'><h2>Daily Companion Cognition checkpoint</h2><p><span class='badge' id='daily-companion-cognition-checkpoint-state' data-state='starting'>checking</span></p><p id='daily-companion-cognition-checkpoint-summary' class='project-description'>Consolidating bounded companion postures, cross-policy reconciliation, verified continuity receipts, replay and tamper recovery, deliberate silence, response-shape audit, diagnostics integrity, shared-path, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no conversation or generated response text, memory, reflection, prompt, provider, identifier, or private reasoning content, memory unification, learning mutation, autonomous turn, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='unified-memory-checkpoint-panel'><h2>Unified Memory checkpoint</h2><p><span class='badge' id='unified-memory-checkpoint-state' data-state='starting'>checking</span></p><p id='unified-memory-checkpoint-summary' class='project-description'>Consolidating five-domain memory coordination, provenance preservation, duplicate and contradiction handling, verified continuity receipts, replay and tamper recovery, selection auditing, shared-path integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no memory, conversation, project, prompt, provider, identifier, or private reasoning content, physical store merge, retrieval reweighting, learning mutation, autonomous turn, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='memory-retrieval-relevance-checkpoint-panel'><h2>Retrieval Relevance checkpoint</h2><p><span class='badge' id='memory-retrieval-relevance-checkpoint-state' data-state='starting'>checking</span></p><p id='memory-retrieval-relevance-checkpoint-summary' class='project-description'>Consolidating literal relevance, freshness and archival bounds, stale-conflict suppression, correction preservation, verified retrieval continuity, malformed and oversized recovery, selection auditing, shared-path integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no memory, conversation, prompt, provider, identifier, or private reasoning content, memory mutation, correction learning, autonomous turn, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='immediate-memory-learning-checkpoint-panel'><h2>Immediate Learning checkpoint</h2><p><span class='badge' id='immediate-memory-learning-checkpoint-state' data-state='starting'>checking</span></p><p id='immediate-memory-learning-checkpoint-summary' class='project-description'>Consolidating corrections, retractions, preference changes, temporary and durable scope, commit-boundary handoffs, verified cross-turn receipts, conflict recovery, compliance auditing, shared-path integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no changed value, memory, conversation, prompt, provider, identifier, or private reasoning content, automatic learning, memory mutation, experiential lesson conversion, autonomous turn, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='bounded-experiential-lessons-checkpoint-panel'><h2>Bounded Experiential Lessons checkpoint</h2><p><span class='badge' id='bounded-experiential-lessons-checkpoint-state' data-state='starting'>checking</span></p><p id='bounded-experiential-lessons-checkpoint-summary' class='project-description'>Consolidating bounded lesson candidates, failure and recovery evidence, repeated-success thresholds, review-boundary handoffs, verified cross-turn lesson receipts, conflict recovery, compliance auditing, shared-path integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no lesson, experience, memory, conversation, prompt, provider, identifier, or private reasoning content, model training, self-training, automatic generalization, durable commit, memory mutation, autonomous turn, action, approval, source or runtime mutation, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='memory-experiential-learning-alpha-checkpoint-panel'><h2>Memory and Experiential Learning Alpha checkpoint</h2><p><span class='badge' id='memory-experiential-learning-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='memory-experiential-learning-alpha-checkpoint-summary' class='project-description'>Consolidating unified memory, retrieval relevance, current-turn learning precedence, bounded lessons, verified continuity, compliance auditing, reliability recovery, shared-path integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no memory, correction, preference, lesson, experience, conversation, prompt, provider, identifier, or private reasoning content, automatic mutation, training, goals, plans, tools, actions, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='internally-generated-goal-candidate-checkpoint-panel'><h2>Internally Generated Goal Candidate checkpoint</h2><p><span class='badge' id='internally-generated-goal-candidate-checkpoint-state' data-state='starting'>checking</span></p><p id='internally-generated-goal-candidate-checkpoint-summary' class='project-description'>Consolidating bounded deficiency evidence, review-only goal nomination, verified cross-turn review continuity, operator-review packets, fail-closed reliability, shared ordinary-conversation integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no goal text, conversation, memory, lesson, prompt, provider, identifier, or private reasoning content, goal activation, planning, tools, actions, mutation, training, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='hierarchical-planning-checkpoint-panel'><h2>Hierarchical Planning checkpoint</h2><p><span class='badge' id='hierarchical-planning-checkpoint-state' data-state='starting'>checking</span></p><p id='hierarchical-planning-checkpoint-summary' class='project-description'>Consolidating bounded planning hierarchy, milestones, dependencies, stopping conditions, verified review continuity, operator-review packets, fail-closed reliability, shared ordinary-conversation integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no goal or plan text, prompts, provider payloads, identifiers, private reasoning, plan activation, persistence, scheduling, simulation, tools, actions, mutation, training, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='plan-simulation-checkpoint-panel'><h2>Plan Simulation checkpoint</h2><p><span class='badge' id='plan-simulation-checkpoint-state' data-state='starting'>checking</span></p><p id='plan-simulation-checkpoint-summary' class='project-description'>Consolidating bounded structural alternatives, risk prediction, verified simulation-review continuity, operator-review packets, strict diagnostics, fail-closed reliability, shared ordinary-conversation integration, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no goal, plan, or alternative text, prompts, provider payloads, identifiers, private reasoning, alternative selection, plan activation, persistence, scheduling, follow-through, tools, actions, mutation, training, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='persistent-follow-through-checkpoint-panel'><h2>Persistent Follow-Through checkpoint</h2><p><span class='badge' id='persistent-follow-through-checkpoint-state' data-state='starting'>checking</span></p><p id='persistent-follow-through-checkpoint-summary' class='project-description'>Consolidating bounded milestone, dependency, stopping-condition, interruption, restart, priority-reconciliation, verified continuity, operator-review, strict-diagnostics, fail-closed reliability, shared ordinary-conversation, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no goal, plan, milestone, alternative, prompt, provider, identifier, or private reasoning content, plan activation, persistence, scheduling, tools, actions, mutation, training, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='goal-and-planning-alpha-checkpoint-panel'><h2>Goal and Planning Alpha checkpoint</h2><p><span class='badge' id='goal-and-planning-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='goal-and-planning-alpha-checkpoint-summary' class='project-description'>Consolidating bounded goal nomination, hierarchical planning, simulation risk comparison, persistent follow-through, verified cross-turn alpha review, strict diagnostics, fail-closed reliability, shared ordinary-conversation, and source-only privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; no goal, plan, alternative, milestone, dependency, prompt, provider, identifier, or private reasoning content, activation, persistence, scheduling, tool routing, actions, mutation, training, installation, promotion, certification, or consciousness claim.</p></section>
    <section class='panel info' id='natural-language-action-execution-checkpoint-panel'><h2>Natural-Language Action and Supervised Execution checkpoint</h2><p><span class='badge' id='natural-language-action-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='natural-language-action-execution-checkpoint-summary' class='project-description'>Consolidating bounded intent classification, registered capability grounding, proposal handoff, exact approval admission, replay-safe synthetic terminal results, conversation parity, and privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; ordinary conversation cannot persist proposals, create approval, invoke execution, expose raw arguments or output, mutate source or runtime, manage models, install, promote, or certify.</p></section>
    <section class='panel info' id='clarification-argument-routing-checkpoint-panel'><h2>Clarification and Argument Routing checkpoint</h2><p><span class='badge' id='clarification-argument-routing-checkpoint-state' data-state='starting'>checking</span></p><p id='clarification-argument-routing-checkpoint-summary' class='project-description'>Consolidating bounded capability argument schemas, structured clarification, exact proposal binding, durable content-free continuity, cancellation, expiry, replay resistance, conversation parity, and privacy evidence.</p><p class='project-meta'>Strictly read-only and content-free; the checkpoint persists no request text, answer values, arguments, proposal, approval, execution authority, source mutation, model operation, installation, promotion, or certification.</p></section>
    <section class='panel info' id='natural-language-action-approval-governance-checkpoint-panel'><h2>Natural-Language Action and Approval Governance checkpoint</h2><p><span class='badge' id='natural-language-action-approval-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='natural-language-action-approval-governance-checkpoint-summary' class='project-description'>Consolidating intent, argument clarification, content-free proposal persistence, explicit approval requests, exact operator decisions, authorization, execution admission, replay resistance, conversation separation, and privacy evidence.</p><p class='project-meta'>Strictly read-only; synthetic temporary ledgers only. No real proposal, approval, authorization, executor, tool, provider, source mutation, installation, promotion, or certification operation is performed.</p></section>
    <section class='panel info' id='natural-language-action-authoritative-result-checkpoint-panel'><h2>Natural-Language Action and Authoritative Result checkpoint</h2><p><span class='badge' id='natural-language-action-authoritative-result-checkpoint-state' data-state='starting'>checking</span></p><p id='natural-language-action-authoritative-result-checkpoint-summary' class='project-description'>Consolidating governed action admission, bounded supervised execution results, terminal replay resistance, content-free conversation presentation, stale-attempt recovery, receipt deduplication, ambiguity preservation, and privacy evidence.</p><p class='project-meta'>Strictly read-only; temporary synthetic ledgers and in-memory executors only. No registered tool, provider, production runtime, source mutation, automatic approval, installation, promotion, or certification operation is performed.</p></section>
    <section class='panel info' id='natural-language-action-checkpoint-panel'><h2>Natural-Language Action checkpoint</h2><p><span class='badge' id='natural-language-action-checkpoint-state' data-state='starting'>checking</span></p><p id='natural-language-action-checkpoint-summary' class='project-description'>Consolidating bounded action history, exact status references, governed follow-through, restart-safe continuity, replay and contradiction detection, stale-state review, and long-session reliability.</p><p class='project-meta'>Strictly read-only and content-free; synthetic caller-owned records and temporary continuity state only. No ledger discovery, retry, approval, authorization, execution, provider, source mutation, installation, promotion, or certification operation is performed.</p></section>
    <section class='panel info' id='supervised-project-inspection-planning-checkpoint-panel'><h2>Supervised Project Inspection and Planning checkpoint</h2><p><span class='badge' id='supervised-project-inspection-planning-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-project-inspection-planning-checkpoint-summary' class='project-description'>Consolidating explicit-root source inspection, operator deficiency review, structural specifications, and bounded implementation and test planning.</p><p class='project-meta'>Strictly read-only and content-free; temporary synthetic project fixtures only. No private registry discovery, patching, test execution, shell, tool, provider, model, approval, authorization, source mutation, installation, promotion, or certification operation is performed.</p></section>
    <section class='panel info' id='supervised-implementation-checkpoint-panel'><h2>Supervised Implementation checkpoint</h2><p><span class='badge' id='supervised-implementation-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-implementation-checkpoint-summary' class='project-description'>Consolidating exact implementation preparation, private patch drafting, operator review, and isolated sandbox materialization.</p><p class='project-meta'>Strictly read-only for production source and runtime. Temporary synthetic contracts and isolated sandbox fixtures only; no source application, tests, shell, tool, provider, model, installation, promotion, certification, or release authorization.</p></section>
    <section class='panel info' id='supervised-sandbox-testing-repair-checkpoint-panel'><h2>Supervised Sandbox Testing and Repair checkpoint</h2><p><span class='badge' id='supervised-sandbox-testing-repair-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-testing-repair-checkpoint-summary' class='project-description'>Consolidating exact sandbox-test review and execution, content-free evidence, conservative diagnosis, and operator-reviewed repair and retest planning.</p><p class='project-meta'>Production source remains read-only. Temporary synthetic sandboxes only; no repair execution, retest, source application, provider/model use, promotion, certification, or release authorization.</p></section>
    <section class='panel info' id='supervised-sandbox-repair-draft-checkpoint-panel'><h2>Supervised Sandbox Repair Draft Foundations</h2><p><span class='badge' id='supervised-sandbox-repair-draft-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-repair-draft-checkpoint-summary' class='project-description'>Binding one exact reviewed repair plan and failed-test lineage to one fresh sandbox baseline and bounded private replacement draft.</p><p class='project-meta'>Public diagnostics remain content-free. No sandbox or production write, repair materialization, retest, automatic approval, provider/model contact, promotion, certification, or release authorization.</p></section>
    <section class='panel info' id='supervised-sandbox-repair-materialization-checkpoint-panel'><h2>Operator Repair Review and Sandbox Materialization</h2><p><span class='badge' id='supervised-sandbox-repair-materialization-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-repair-materialization-checkpoint-summary' class='project-description'>Reviewing one exact private repair draft and materializing only an approved replacement inside an isolated sandbox with rollback evidence.</p><p class='project-meta'>Public diagnostics remain content-free. No retest, production-source application, provider/model contact, promotion, certification, or release authorization.</p></section>
    <section class='panel info' id='supervised-sandbox-retesting-checkpoint-panel'><h2>Governed Sandbox Retesting</h2><p><span class='badge' id='supervised-sandbox-retesting-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-retesting-checkpoint-summary' class='project-description'>Binding one exact repaired sandbox target to a separately approved bounded retest and content-free before/after result.</p><p class='project-meta'>Regression detection and rollback availability are reported without production-source application, promotion, certification, or release authority.</p></section>
    <section class='panel info' id='supervised-sandbox-repair-retest-checkpoint-panel'><h2>Supervised Sandbox Repair and Retest</h2><p><span class='badge' id='supervised-sandbox-repair-retest-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-repair-retest-checkpoint-summary' class='project-description'>Consolidating private repair drafting, explicit repair review, isolated sandbox materialization, rollback evidence, separately governed retesting, and bounded repair results.</p><p class='project-meta'>Read-only checkpoint. No production-source application, rollback execution, promotion, installation, certification, or release authority. Next bounded unit: v1184.0-v1184.2.</p></section>
    <section class='panel info' id='supervised-project-development-foundations-panel'><h2>Supervised Project-Development Foundations</h2><p><span class='badge' id='supervised-project-development-foundations-state' data-state='starting'>checking</span></p><p id='supervised-project-development-foundations-summary' class='project-description'>Joining the governed inspection through retest lineage without executing or authorizing any stage.</p><p class='project-meta'>Read-only, content-free lineage checkpoint. Next bounded unit: v1184.3-v1184.5.</p></section>
    <section class='panel info' id='supervised-project-outcome-learning-panel'><h2>Project Results and Accountable Learning</h2><p><span class='badge' id='supervised-project-outcome-learning-state' data-state='starting'>checking</span></p><p id='supervised-project-outcome-learning-summary' class='project-description'>Presenting content-free governed outcomes and bounded lessons without granting authority.</p><p class='project-meta'>Read-only checkpoint. Next bounded unit: v1184.6-v1184.8.</p></section>
    <section class='panel info' id='supervised-project-reliability-recovery-panel'><h2>Project Reliability and Recovery</h2><p><span class='badge' id='supervised-project-reliability-recovery-state' data-state='starting'>checking</span></p><p id='supervised-project-reliability-recovery-summary' class='project-description'>Checking drift, interruption recovery, rollback evidence, and privacy boundaries without execution.</p><p class='project-meta'>Read-only checkpoint. Next bounded unit: v1184.9.</p></section>
    <section class='panel info' id='supervised-project-development-alpha-checkpoint-panel'><h2>Supervised Project Development Alpha</h2><p><span class='badge' id='supervised-project-development-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-project-development-alpha-checkpoint-summary' class='project-description'>Consolidating the complete governed inspection through learning and recovery loop.</p><p class='project-meta'>Read-only, content-free checkpoint. Next bounded unit: v1185.0-v1185.2 Persistent Development Campaign Foundations.</p></section>
    <section class='panel info' id='persistent-supervised-developer-alpha-checkpoint-panel'><h2>Persistent Supervised Developer Alpha</h2><p><span class='badge' id='persistent-supervised-developer-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='persistent-supervised-developer-alpha-checkpoint-summary' class='project-description'>Consolidating governed campaign scope, continuation, work selection, budgets, stale-work reconciliation, and recovery evidence.</p><p class='project-meta'>Strictly read-only and content-free. No campaign execution, durable resume, provider reconnection, source mutation, promotion, certification, or release authority. Next bounded unit: v1186.0-v1186.2 Durable Campaign Storage and Multi-Session Restoration Foundations.</p></section>
    <section class='panel info' id='durable-campaign-continuation-checkpoint-panel'><h2>Durable Campaign Continuation</h2><p><span class='badge' id='durable-campaign-continuation-checkpoint-state' data-state='starting'>checking</span></p><p id='durable-campaign-continuation-checkpoint-summary' class='project-description'>Consolidating durable storage, restoration review, source-drift reconciliation, lease-backed resumed-session materialization, restart reconciliation, and lease release.</p><p class='project-meta'>Strictly read-only over production source and content-free. Temporary external-runtime fixtures only; no campaign work execution, automatic resume, provider/model contact, source mutation, promotion, certification, or release authority. Next bounded unit: v1187.0-v1187.2 Bounded Campaign Work Execution Foundations.</p></section>
    <section class='panel info' id='persistent-campaign-work-execution-checkpoint-panel'><h2>Persistent Campaign Work Execution</h2><p><span class='badge' id='persistent-campaign-work-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='persistent-campaign-work-execution-checkpoint-summary' class='project-description'>Consolidating bounded execution, governed result accounting, terminal ledger and budget evidence, failure handling, follow-up selection, and durable next-generation persistence.</p><p class='project-meta'>Read-only checkpoint over production source. Isolated synthetic fixtures only; no automatic retry, resume, reselection, repair, provider/model contact, source application, promotion, certification, or release authority. Next bounded unit: v1188.0-v1188.2 Complete Campaign Development Loop Foundations.</p></section>
    <section class='panel info' id='adversarial-campaign-hardening-long-session-checkpoint-panel'><h2>Campaign Hardening & Long Sessions</h2><p><span class='badge' data-state='review'>review required</span></p><p class='project-description'>Durable replay defense and bounded long-session evidence.</p><p class='project-meta'>Content-free, operator-reviewed, and authority-free. Next bounded unit: v1189.6-v1189.8.</p></section>
    <section class='panel info' id='persistent-developer-adversarial-reliability-checkpoint-panel'><h2>Persistent Developer Reliability</h2><p><span class='badge' data-state='review'>operator review required</span></p><p class='project-description'>Adversarial stale-state, replay, interruption, privacy, and authority reliability evidence.</p><p class='project-meta'>Content-free and authority-free. Retained v1189.8 layer.</p></section>
    <section class='panel info' id='persistent-supervised-developer-alpha-hardening-checkpoint-panel'><h2>Persistent Supervised Developer Alpha Hardening</h2><p><span class='badge' id='persistent-supervised-developer-alpha-hardening-checkpoint-state' data-state='starting'>checking</span></p><p id='persistent-supervised-developer-alpha-hardening-checkpoint-summary' class='project-description'>Consolidating adversarial campaign hardening, durable replay defense, long-session evidence, stale-state, privacy, authority, and recovery-review boundaries.</p><p class='project-meta'>Strictly read-only and content-free; no retry, resume, recovery, campaign work, policy change, source mutation, provider/model contact, promotion, certification, publication, or release authority. Next bounded unit: v1190.0-v1190.2 Unified Experience Foundations.</p></section>
    <section class='panel info' id='responsive-work-queue-checkpoint-panel'><h2>Responsive Work Queue Foundations</h2><p><span class='badge' id='responsive-work-queue-checkpoint-state' data-state='starting'>checking</span></p><p id='responsive-work-queue-checkpoint-summary' class='project-description'>Validating content-free foreground/background work separation, deterministic queue order, lifecycle truth, and latency evidence.</p><p class='project-meta'>Evidence-only and read-only; no execution, cancellation, thread/process start, provider/model contact, approval consumption, runtime mutation, or authority expansion. Next bounded unit: v1191.3-v1191.5 operator queue review and cancellation.</p></section>
    <section class='panel info' id='responsive-work-queue-review-checkpoint-panel'><h2>Operator Queue Review</h2><p><span class='badge' id='responsive-work-queue-review-checkpoint-state' data-state='starting'>checking</span></p><p id='responsive-work-queue-review-checkpoint-summary' class='project-description'>Validating content-free operator-reviewed queue, pause, cancellation, supersession, completion, and result-presentation evidence.</p><p class='project-meta'>Presentation-only transitions; no execution, no real work cancelled, paused, superseded, or completed, and no approval or authority consumed. Next bounded unit: v1191.6-v1191.8 reliability hardening.</p></section>
    <section class='panel info' id='responsive-work-queue-reliability-checkpoint-panel'><h2>Responsive Work Reliability</h2><p><span class='badge' id='responsive-work-queue-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='responsive-work-queue-reliability-checkpoint-summary' class='project-description'>Validating interruption, restart, stale-work, provider-outage, starvation, fairness, privacy, and foreground latency evidence.</p><p class='project-meta'>Evidence-only; no retry, recovery, execution, cancellation, provider/model contact, or runtime mutation.</p></section>
    <section class='panel info' id='bounded-evidence-compaction-checkpoint-panel'><h2>Bounded Evidence Compaction</h2><p><span class='badge' id='bounded-evidence-compaction-checkpoint-state' data-state='starting'>checking</span></p><p id='bounded-evidence-compaction-checkpoint-summary' class='project-description'>Verifying deterministic, lossless, content-free evidence compaction.</p><p class='project-meta'>Read-only foundations; exact lineage, uncertainty, approval, rollback, privacy, and authority separation remain explicit. Next bounded unit: v1192.3-v1192.5 operator compaction review.</p></section>
    <section class='panel info' id='evidence-compaction-review-checkpoint-panel'><h2>Operator Evidence Compaction Review</h2><p><span class='badge' id='evidence-compaction-review-checkpoint-state' data-state='starting'>checking</span></p><p id='evidence-compaction-review-checkpoint-summary' class='project-description'>Validating approve, reject, and defer review over exact, equivalent compacted evidence.</p><p class='project-meta'>Presentation-only review; original evidence is preserved and no replacement, deletion, execution, approval consumption, or authority occurs. Next bounded unit: v1192.6-v1192.8 reliability hardening.</p></section>
    <section class='panel info' id='evidence-compaction-reliability-checkpoint-panel'><h2>Evidence Compaction Reliability</h2><p><span class='badge' id='evidence-compaction-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='evidence-compaction-reliability-checkpoint-summary' class='project-description'>Validating replay, interruption, restart, stale-compaction, privacy, and tamper hardening.</p><p class='project-meta'>Read-only evidence; no automatic recovery, replacement, deletion, execution, approval consumption, or authority. Next bounded unit: v1192.9 checkpoint.</p></section>
    <section class='panel info' id='evidence-compaction-checkpoint-panel'><h2>Bounded Evidence Compaction Checkpoint</h2><p><span class='badge' id='evidence-compaction-checkpoint-state' data-state='starting'>checking</span></p><p id='evidence-compaction-checkpoint-summary' class='project-description'>Consolidating exact compaction, deterministic expansion, operator review, and reliability evidence.</p><p class='project-meta'>Read-only checkpoint; original evidence remains preserved and no replacement, deletion, recovery execution, provider/model contact, or authority occurs. Next bounded unit: v1193 verifier ownership and historical-debt consolidation.</p></section>
    <section class='panel info' id='verifier-ownership-checkpoint-panel'><h2>Verifier Ownership</h2><p><span class='badge' id='verifier-ownership-checkpoint-state' data-state='starting'>checking</span></p><p id='verifier-ownership-checkpoint-summary' class='project-description'>Assigning verifier ownership and separating current regressions from inherited historical debt.</p><p class='project-meta'>Read-only foundations; no fixture deletion, verifier retirement, execution, or authority. Next bounded unit: v1193.3-v1193.5 profile reconciliation.</p></section>
    <section class='panel info' id='fixture-historical-debt-consolidation-checkpoint-panel'><h2>Fixture Consolidation</h2><p><span class='badge' id='fixture-historical-debt-consolidation-checkpoint-state' data-state='starting'>checking</span></p><p id='fixture-historical-debt-consolidation-checkpoint-summary' class='project-description'>Consolidating fixture overlap and historical debt ownership.</p><p class='project-meta'>Read-only evidence; no fixture deletion, verifier retirement, execution, or authority. Next bounded unit: v1193.9.</p></section>
    <section class='panel info' id='verifier-historical-debt-checkpoint-panel'><h2>Verifier Ownership and Historical Debt Checkpoint</h2><p><span class='badge' id='verifier-historical-debt-checkpoint-state' data-state='starting'>checking</span></p><p id='verifier-historical-debt-checkpoint-summary' class='project-description'>Consolidating verifier ownership, deterministic profiles, fixture overlap, cleanup ownership, and inherited debt truth.</p><p class='project-meta'>Read-only checkpoint; no suite execution, fixture deletion, verifier retirement, history rewrite, runtime mutation, or authority. Next bounded unit: v1194.0-v1194.2 Unified Cognitive and Developer Experience Foundations.</p></section>
    <section class='panel info' id='unified-cognitive-developer-experience-panel'><h2>Unified Cognitive and Developer Experience</h2><p><span class='badge' id='unified-cognitive-developer-experience-state' data-state='starting'>checking</span></p><p id='unified-cognitive-developer-experience-summary' class='project-description'>Unifying cognition, development, responsiveness, compacted evidence, and verifier truth.</p><p class='project-meta'>Read-only foundations; no execution, approval consumption, runtime mutation, provider/model contact, or authority. Next bounded unit: v1194.3-v1194.5.</p></section>
    <section class='panel info' id='unified-cognitive-developer-coordination-panel'><h2>Operator Coordination and Accountable Navigation</h2><p><span class='badge' id='unified-cognitive-developer-coordination-state' data-state='starting'>checking</span></p><p id='unified-cognitive-developer-coordination-summary' class='project-description'>Reviewing content-free coordination and presentation-only navigation.</p><p class='project-meta'>Approve, reject, or defer presentation focus only; no subsystem mutation, execution, approval consumption, automatic continuation, or authority. Next bounded unit: v1194.6-v1194.8.</p></section>
    <section class='panel info' id='unified-cognitive-developer-reliability-panel'><h2>Unified Experience Reliability</h2><p><span class='badge' id='unified-cognitive-developer-reliability-state' data-state='starting'>checking</span></p><p id='unified-cognitive-developer-reliability-summary' class='project-description'>Checking interruption, restart, stale lineage, privacy, latency, and integration boundaries.</p><p class='project-meta'>Evidence-only reliability; no automatic recovery, execution, provider/model contact, mutation, or authority. Next bounded unit: v1194.9.</p></section>
    <section class='panel info' id='unified-cognitive-developer-checkpoint-panel'><h2>Unified Cognitive and Developer Experience Checkpoint</h2><p><span class='badge' id='unified-cognitive-developer-checkpoint-state' data-state='starting'>checking</span></p><p id='unified-cognitive-developer-checkpoint-summary' class='project-description'>Consolidating unified domains, accountable navigation, reliability, evidence preservation, responsiveness, and verifier truth.</p><p class='project-meta'>Read-only checkpoint; no subsystem mutation, execution, approval consumption, automatic recovery, provider/model contact, global pass claim, or authority. Next bounded unit: v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations.</p></section>
    <section class='panel info' id='general-test-adapter-consolidation-checkpoint-panel'><h2>General Test Adapter Consolidation Checkpoint</h2><p><span class='badge' id='general-test-adapter-consolidation-checkpoint-state' data-state='starting'>checking</span></p><p id='general-test-adapter-consolidation-checkpoint-summary' class='project-description'>Consolidating browser, Node/JavaScript, and Python adapter selection, dispatch, evidence, cleanup, privacy, and authority boundaries.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no project tests executed, runtime probes, dependency installation, repair, apply, promotion, release, or authority.</p></section>
    <section class='panel info' id='conversational-build-test-loop-checkpoint-panel'><h2>Conversational Build-and-Test Loop Checkpoint</h2><p><span class='badge' id='conversational-build-test-loop-checkpoint-state' data-state='starting'>checking</span></p><p id='conversational-build-test-loop-checkpoint-summary' class='project-description'>Checking exact conversational authorization, isolated build delegation, unified tests, durable recovery, privacy, and operator authority.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no provider contact, project tests, diagnosis, repair, apply, installation, promotion, release, or authority.</p></section>
    <section class='panel info' id='operator-build-test-results-checkpoint-panel'><h2>Operator Build-and-Test Results and Continuation Checkpoint</h2><p><span class='badge' id='operator-build-test-results-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-build-test-results-checkpoint-summary' class='project-description'>Checking content-free results, exact operator decisions, durable replay, continuation preparation, privacy, and authority boundaries.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no provider contact, project tests, automatic continuation, diagnosis, repair, apply, installation, promotion, release, or authority.</p></section>
    <section class='panel info' id='conversational-build-test-continuation-checkpoint-panel'><h2>Conversational Build-and-Test Continuation Checkpoint</h2><p><span class='badge' id='conversational-build-test-continuation-checkpoint-state' data-state='starting'>checking</span></p><p id='conversational-build-test-continuation-checkpoint-summary' class='project-description'>Checking exact continuation authorization, retained build/test delegation, attempt lineage, durable replay, privacy, and authority boundaries.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no provider contact, project tests, automatic continuation, diagnosis, repair, apply, installation, promotion, release, or authority.</p></section>
    <section class='panel info' id='bounded-automatic-diagnosis-checkpoint-panel'><h2>Bounded Automatic Diagnosis Checkpoint</h2><p><span class='badge' id='bounded-automatic-diagnosis-checkpoint-state' data-state='starting'>checking</span></p><p id='bounded-automatic-diagnosis-checkpoint-summary' class='project-description'>Checking exact failure-evidence binding, conservative diagnosis candidates, ordinary-chat attachment, replay, recovery, privacy, and review gates.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no runtime diagnosis, provider contact, project tests, proven root cause, repair, retest, apply, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='operator-diagnosis-review-checkpoint-panel'><h2>Operator Diagnosis Review and Repair Proposal Checkpoint</h2><p><span class='badge' id='operator-diagnosis-review-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-diagnosis-review-checkpoint-summary' class='project-description'>Checking exact diagnosis review, operator decisions, bounded repair-proposal preparation, replay, privacy, and separate authorization.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no provider contact, patch generation, tests, retests, repair execution, project mutation, apply, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='conversational-supervised-repair-execution-checkpoint-panel'><h2>Conversational Supervised Repair Execution Checkpoint</h2><p><span class='badge' id='conversational-supervised-repair-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='conversational-supervised-repair-execution-checkpoint-summary' class='project-description'>Checking exact repair authorization, one isolated repair attempt, retained build-and-test delegation, replay, recovery, privacy, and operator review.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no runtime repair, provider contact, project tests, retest, project mutation, apply, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='operator-repair-result-review-checkpoint-panel'><h2>Operator Repair Result Review and Apply Proposal Checkpoint</h2><p><span class='badge' id='operator-repair-result-review-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-repair-result-review-checkpoint-summary' class='project-description'>Checking exact repair-result review, passing-only apply eligibility, operator dispositions, apply-proposal preparation, replay, privacy, and separate authorization.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no runtime review, provider contact, tests, candidate read, project mutation, apply, rollback, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='supervised-repaired-candidate-apply-checkpoint-panel'><h2>Conversational Supervised Repaired-Candidate Apply Checkpoint</h2><p><span class='badge' id='supervised-repaired-candidate-apply-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-repaired-candidate-apply-checkpoint-summary' class='project-description'>Checking exact v1216 authorization, transactional repaired-candidate apply, sealed rollback evidence, replay, recovery, privacy, and operator review.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no runtime apply, rollback, provider contact, tests, project mutation, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='operator-repaired-candidate-apply-result-review-checkpoint-panel'><h2>Operator Repaired-Candidate Apply Result Review and Rollback Proposal Checkpoint</h2><p><span class='badge' id='operator-repaired-candidate-apply-result-review-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-repaired-candidate-apply-result-review-checkpoint-summary' class='project-description'>Checking exact apply-result review, rollback eligibility, operator dispositions, rollback-proposal preparation, replay, privacy, and separate authorization.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no runtime review, provider contact, tests, project mutation, apply, rollback, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='supervised-repaired-candidate-rollback-checkpoint-panel'><h2>Conversational Supervised Repaired-Candidate Rollback Checkpoint</h2><p><span class='badge' id='supervised-repaired-candidate-rollback-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-repaired-candidate-rollback-checkpoint-summary' class='project-description'>Checking exact v1218 authorization, one-use transactional rollback, replay, recovery, privacy, and operator review.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no runtime rollback, provider contact, tests, project mutation, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='operator-repaired-candidate-rollback-result-review-checkpoint-panel'><h2>Operator Repaired-Candidate Rollback Result Review Checkpoint</h2><p><span class='badge' id='operator-repaired-candidate-rollback-result-review-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-repaired-candidate-rollback-result-review-checkpoint-summary' class='project-description'>Checking exact terminal rollback-result review, content-free dispositions, replay, tamper resistance, and preserved authority boundaries.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; no retry, provider contact, tests, project mutation, installation, promotion, release, or authority grant.</p></section>
    <section class='panel info' id='unified-supervised-development-transaction-history-checkpoint-panel'><h2>Unified Supervised Development Transaction History Checkpoint</h2><p><span class='badge' id='unified-supervised-development-transaction-history-checkpoint-state' data-state='starting'>checking</span></p><p id='unified-supervised-development-transaction-history-checkpoint-summary' class='project-description'>Checking content-free transaction history, authoritative receipt lineage, bounded pagination, restart continuity, refresh lineage, and tamper resistance.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; history never replaces receipts or grants provider, test, repair, apply, rollback, installation, promotion, or release authority.</p></section>
    <section class='panel info' id='transaction-resumption-abandoned-work-reconciliation-checkpoint-panel'><h2>Transaction Resumption and Abandoned-Work Reconciliation Checkpoint</h2><p><span class='badge' id='transaction-resumption-abandoned-work-reconciliation-checkpoint-state' data-state='starting'>checking</span></p><p id='transaction-resumption-abandoned-work-reconciliation-checkpoint-summary' class='project-description'>Checking safe-resumption classification, abandoned-work reconciliation, fresh-authority requirements, stale-history rejection, and content-free operator review.</p><p class='project-meta'>Strictly read-only synthetic checkpoint; old approvals are never reusable and continuation proposals cannot execute work.</p></section>
    <section class='panel info' id='adversarial-privacy-authority-panel'><h2>Adversarial Privacy and Authority Foundations</h2><p><span class='badge' id='adversarial-privacy-authority-state' data-state='starting'>checking</span></p><p id='adversarial-privacy-authority-summary' class='project-description'>Reviewing content-free privacy attacks, forged authority, replay, stale-state, and lineage tampering.</p><p class='project-meta'>Evidence-only; no private-state fetch, execution, mutation, approval consumption, provider/model contact, release, or authority grant. Next bounded unit: v1196.3-v1196.5.</p></section>
    <section class='panel info' id='adversarial-replay-recovery-review-panel'><h2>Adversarial Replay and Recovery Review</h2><p><span class='badge' id='adversarial-replay-recovery-review-state' data-state='starting'>checking</span></p><p id='adversarial-replay-recovery-review-summary' class='project-description'>Reviewing replay, stale state, interruption, cancellation races, and recovery abuse.</p><p class='project-meta'>Presentation-only review; no recovery, retry, cancellation, execution, mutation, provider contact, or authority. Next bounded unit: v1196.6-v1196.8.</p></section>
    <section class='panel info' id='adversarial-reliability-integration-panel'><h2>Adversarial Reliability and Integration</h2><p><span class='badge' id='adversarial-reliability-integration-state' data-state='starting'>checking</span></p><p id='adversarial-reliability-integration-summary' class='project-description'>Hardening replay, stale authority, interruption, cancellation, recovery, privacy, and cross-surface integration boundaries.</p><p class='project-meta'>Evidence-only; no recovery, retry, cancellation, execution, provider/model contact, mutation, global pass claim, or authority. Next bounded unit: v1196.9 checkpoint.</p></section>
    <section class='panel info' id='adversarial-privacy-authority-replay-recovery-checkpoint-panel'><h2>Adversarial Privacy, Authority, Replay, and Recovery Checkpoint</h2><p><span class='badge' id='adversarial-privacy-authority-replay-recovery-checkpoint-state' data-state='starting'>checking</span></p><p id='adversarial-privacy-authority-replay-recovery-checkpoint-summary' class='project-description'>Consolidating privacy, authority, replay, interruption, cancellation, recovery, and integration evidence.</p><p class='project-meta'>Read-only and content-free; no attacks, recovery, retry, cancellation, execution, provider/model contact, mutation, release, or authority. Global pass not claimed. Next bounded unit: v1197.0-v1197.2.</p></section>
    <section class='panel info' id='runtime-lifecycle-migration-checkpoint-panel'><h2>Runtime Lifecycle Foundations</h2><p><span class='badge' id='runtime-lifecycle-migration-checkpoint-state' data-state='starting'>checking</span></p><p id='runtime-lifecycle-migration-checkpoint-summary' class='project-description'>Validating content-free migration, backup, upgrade, rollback, and fresh-install evidence.</p><p class='project-meta'>Evidence-only; no runtime data is read, copied, migrated, upgraded, restored, or installed. Next bounded unit: v1197.3-v1197.5 operator lifecycle review.</p></section>
    <section class='panel info' id='runtime-lifecycle-application-review-checkpoint-panel'><h2>Operator-Reviewed Runtime Lifecycle Application</h2><p><span class='badge' id='runtime-lifecycle-application-review-checkpoint-state' data-state='starting'>checking</span></p><p id='runtime-lifecycle-application-review-checkpoint-summary' class='project-description'>Reviewing content-free backup, migration, upgrade, rollback, and fresh-install application evidence.</p><p class='project-meta'>Approve, reject, and defer are presentation-only; no runtime data is read or changed and no application authority is granted. Next bounded unit: v1197.6-v1197.8 lifecycle reliability hardening.</p></section>
    <section class='panel info' id='runtime-lifecycle-reliability-adversarial-checkpoint-panel'><h2>Runtime Lifecycle Reliability</h2><p><span class='badge' id='runtime-lifecycle-reliability-adversarial-checkpoint-state' data-state='starting'>checking</span></p><p id='runtime-lifecycle-reliability-adversarial-checkpoint-summary' class='project-description'>Validating content-free lifecycle interruption, integrity, rollback, contamination, drift, and recovery-reentry evidence.</p><p class='project-meta'>Evidence-only; no runtime data is read or changed, no recovery or retry occurs, and no authority is granted. Next bounded unit: v1197.9 runtime lifecycle checkpoint.</p></section>
    <section class='panel info' id='runtime-lifecycle-checkpoint-panel'><h2>Runtime Lifecycle Checkpoint</h2><p><span class='badge' id='runtime-lifecycle-checkpoint-state' data-state='starting'>checking</span></p><p id='runtime-lifecycle-checkpoint-summary' class='project-description'>Consolidating read-only backup, migration, upgrade, rollback, fresh-install, operator-review, and reliability evidence.</p><p class='project-meta'>No runtime data is read or changed; no lifecycle operation, recovery, retry, approval, or authority is applied. Global pass not claimed. Next bounded unit: v1198.0-v1198.2 feature-freeze and architecture-consolidation foundations.</p></section>
    <section class='panel info' id='feature-freeze-architecture-consolidation-panel'><h2>Feature Freeze & Architecture Consolidation</h2><p><span class='badge' id='feature-freeze-architecture-consolidation-state' data-state='starting'>checking</span></p><p id='feature-freeze-architecture-consolidation-summary' class='project-description'>Validating content-free feature-freeze, ownership, duplication, startup-budget, and consolidation-candidate evidence.</p><p class='project-meta'>Read-only foundations; no files are moved, merged, deleted, or rewritten, no startup is executed, and global pass not claimed. Next bounded unit: v1198.3-v1198.5 operator freeze exceptions and consolidation review.</p></section>
    <section class='panel info' id='performance-documentation-verifier-hardening-panel'><h2>Performance, Documentation & Verifier Hardening</h2><p><span class='badge' id='performance-documentation-verifier-hardening-state' data-state='starting'>checking</span></p><p id='performance-documentation-verifier-hardening-summary' class='project-description'>Validating content-free budgets, documentation consistency, verifier registration, freeze compliance, ownership, and historical truth.</p><p class='project-meta'>Read-only; no profiling or verifier execution, source consolidation, release, or authority grant. Next: v1198.9 checkpoint.</p></section>
    <section class='panel info' id='feature-freeze-consolidation-review-panel'><h2>Freeze Exceptions & Consolidation Review</h2><p><span class='badge' id='feature-freeze-consolidation-review-state' data-state='starting'>checking</span></p><p id='feature-freeze-consolidation-review-summary' class='project-description'>Validating content-free operator review for freeze exceptions and consolidation proposals.</p><p class='project-meta'>Presentation-only review; no exceptions are applied, no files are moved or merged, and no authority is granted. Next bounded unit: v1198.6-v1198.8 performance, documentation, and verifier reconciliation hardening.</p></section>
    <section class='panel info' id='feature-freeze-architecture-consolidated-panel'><h2>Feature Freeze & Architecture Consolidation Checkpoint</h2><p><span class='badge' id='feature-freeze-architecture-consolidated-state' data-state='starting'>checking</span></p><p id='feature-freeze-architecture-consolidated-summary' class='project-description'>Consolidating read-only freeze, ownership, review, performance, documentation, and verifier evidence.</p><p class='project-meta'>No files are moved, merged, deleted, or rewritten; no profiling, verifier execution, release, or authority grant occurs. Global pass not claimed. Next bounded unit: v1199.0-v1199.2 final source-only candidate preparation foundations.</p></section>
    <section class='panel info' id='final-source-candidate-checkpoint-panel'><h2>Final Source-Only Candidate Checkpoint</h2><p><span class='badge' id='final-source-candidate-checkpoint-state' data-state='starting'>checking</span></p><p id='final-source-candidate-checkpoint-summary' class='project-description'>Consolidating final manifest, retained verification, unresolved risks, operator review, reliability, and v1200 handoff boundaries.</p><p class='project-meta'>Read-only checkpoint; no candidate or handoff is accepted, no risk is waived, and no installation, promotion, certification, publication, release, or authority grant occurs. Global pass not claimed. Next: separate v1200 Desktop Codex and native-provider decision gate.</p></section>
    <section class='panel info' id='final-candidate-reliability-panel'><h2>Final Candidate Reliability & Handoff Hardening</h2><p><span class='badge' id='final-candidate-reliability-state' data-state='starting'>checking</span></p><p id='final-candidate-reliability-summary' class='project-description'>Validating candidate integrity, retained verification, unresolved risks, handoffs, privacy, authority, and replay resistance.</p><p class='project-meta'>Read-only reliability; no candidate acceptance, risk waiver, release, mutation, global pass claim, or authority grant. Next: v1199.9 final source-only candidate checkpoint.</p></section>
    <section class='panel info' id='final-candidate-review-panel'><h2>Operator Final-Candidate Review</h2><p><span class='badge' id='final-candidate-review-state' data-state='starting'>checking</span></p><p id='final-candidate-review-summary' class='project-description'>Reviewing candidate, verification, risk, Desktop, and native-provider handoffs.</p><p class='project-meta'>Presentation-only review; no acceptance, waiver, promotion, certification, publication, release, installation, or authority grant. Next: v1199.6-v1199.8 final candidate reliability hardening.</p></section>
    <section class='panel info' id='final-source-candidate-preparation-panel'><h2>Final Source-Only Candidate Preparation</h2><p><span class='badge' id='final-source-candidate-preparation-state' data-state='starting'>checking</span></p><p id='final-source-candidate-preparation-summary' class='project-description'>Validating content-free source manifest, retained verification, unresolved risks, and review handoff boundaries.</p><p class='project-meta'>Read-only foundations; no candidate promotion, certification, publication, release, installation, or authority grant. Next: v1199.3-v1199.5 operator final-candidate review.</p></section>
    <section class='panel info' id='long-session-multi-day-soak-checkpoint-panel'><h2>Long-Session and Multi-Day Soak Foundations</h2><p><span class='badge' id='long-session-multi-day-soak-checkpoint-state' data-state='starting'>checking</span></p><p id='long-session-multi-day-soak-checkpoint-summary' class='project-description'>Reviewing bounded synthetic observation intervals across conversation, cognition, action, campaigns, queues, cancellation, interruption, restart, and recovery.</p><p class='project-meta'>Evidence-only foundations with no real waiting, execution, cancellation, recovery, provider/model contact, process/thread start, runtime mutation, global pass claim, or authority. Next bounded unit: v1195.3-v1195.5 Operator-Reviewed Soak Progression.</p></section>
    <section class='panel info' id='operator-reviewed-soak-progression-panel'><h2>Operator-Reviewed Soak Progression</h2><p><span class='badge' id='operator-reviewed-soak-progression-state' data-state='starting'>checking</span></p><p id='operator-reviewed-soak-progression-summary' class='project-description'>Reviewing approve, reject, defer, pause, resume, interruption, restart, and terminal soak dispositions.</p><p class='project-meta'>Presentation-only progression with exact multi-session lineage; no real waiting, continuation, pause, resume, cancellation, recovery, execution, runtime mutation, provider/model contact, global pass claim, or authority. Next bounded unit: v1195.6-v1195.8 Soak Reliability and Adversarial Hardening.</p></section>
    <section class='panel info' id='soak-reliability-adversarial-panel'><h2>Soak Reliability and Adversarial Hardening</h2><p><span class='badge' id='soak-reliability-adversarial-state' data-state='starting'>checking</span></p><p id='soak-reliability-adversarial-summary' class='project-description'>Reviewing restart storms, resource exhaustion, latency degradation, outages, starvation, cancellation races, privacy attacks, and long-duration drift.</p><p class='project-meta'>Evidence-only reliability; no real recovery, retry, cancellation, execution, provider/model contact, runtime mutation, global pass claim, or authority. Next bounded unit: v1195.9 checkpoint.</p></section>
    <section class='panel info' id='long-session-multi-day-soak-consolidated-checkpoint-panel'><h2>Long-Session and Multi-Day Soak Checkpoint</h2><p><span class='badge' id='long-session-multi-day-soak-consolidated-checkpoint-state' data-state='starting'>checking</span></p><p id='long-session-multi-day-soak-consolidated-checkpoint-summary' class='project-description'>Consolidating bounded soak foundations, accountable progression, and adversarial reliability evidence.</p><p class='project-meta'>Read-only checkpoint; no real waiting, continuation, pause, resume, cancellation, recovery, execution, provider/model contact, runtime mutation, global pass claim, or authority. Next bounded unit: v1196.0-v1196.2 Adversarial Privacy and Authority Foundations.</p></section>
    <section class='panel info' id='verifier-profile-reconciliation-checkpoint-panel'><h2>Verifier Profiles</h2><p><span class='badge' id='verifier-profile-reconciliation-checkpoint-state' data-state='starting'>checking</span></p><p id='verifier-profile-reconciliation-checkpoint-summary' class='project-description'>Reconciling deterministic focused, quick, and full profile membership and budgets.</p><p class='project-meta'>Read-only evidence; no suite execution, fixture deletion, verifier retirement, or authority. Next bounded unit: v1193.6-v1193.8.</p></section>
    <section class='panel info' id='responsiveness-background-work-checkpoint-panel'><h2>Responsiveness and Background Work Checkpoint</h2><p><span class='badge' id='responsiveness-background-work-checkpoint-state' data-state='starting'>checking</span></p><p id='responsiveness-background-work-checkpoint-summary' class='project-description'>Consolidating v1191 queue foundations, operator transitions, reliability hardening, ordinary-chat campaign visibility, and Windows compatibility repairs.</p><p class='project-meta'>Read-only checkpoint; software-development chat requests remain proposal-only and no work, approval, cancellation, provider/model operation, or authority is invoked. Next bounded unit: v1192 bounded evidence compaction.</p></section>
    <section class='panel info' id='unified-experience-foundations-checkpoint-panel'><h2>Unified Experience Foundations</h2><p><span class='badge' id='unified-experience-foundations-checkpoint-state' data-state='starting'>checking</span></p><p id='unified-experience-foundations-checkpoint-summary' class='project-description'>Projecting one exact content-free current-state surface across conversation, cognition, reasoning, planning, campaign, approval, action, result, and learning.</p><p class='project-meta'>Strictly read-only and authority-free; no private records, duplicate surfaces, approval creation or consumption, execution, continuation, source/runtime mutation, provider/model contact, promotion, certification, publication, or release authority. Next bounded unit: v1190.3-v1190.5 Operator Navigation and Coordinated Experience Transitions.</p></section>
    <section class='panel info' id='unified-experience-navigation-checkpoint-panel'><h2>Unified Experience Navigation</h2><p><span class='badge' id='unified-experience-navigation-checkpoint-state' data-state='starting'>checking</span></p><p id='unified-experience-navigation-checkpoint-summary' class='project-description'>Validating operator-reviewed, content-free focus transitions across unified experience domains.</p><p class='project-meta'>Read-only presentation coordination only; no subsystem state change, approval consumption, execution, continuation, provider/model contact, or authority expansion. Next bounded unit: v1190.6-v1190.8 Unified Experience Reliability and Privacy Hardening.</p></section>
    <section class='panel info' id='unified-experience-reliability-checkpoint-panel'><h2>Unified Experience Reliability</h2><p><span class='badge' id='unified-experience-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='unified-experience-reliability-checkpoint-summary' class='project-description'>Validating stale-state, privacy, authority, and recovery-presentation boundaries.</p><p class='project-meta'>Read-only reliability review only; no subsystem mutation, recovery execution, continuation, provider/model contact, or authority expansion. Next bounded unit: v1190.9 Unified Experience checkpoint.</p></section>
    <section class='panel info' id='unified-experience-checkpoint-panel'><h2>Unified Experience Checkpoint</h2><p><span class='badge' id='unified-experience-checkpoint-state' data-state='starting'>checking</span></p><p id='unified-experience-checkpoint-summary' class='project-description'>Consolidating unified domain surfaces, accountable navigation, stale-state handling, privacy hardening, and reliability review.</p><p class='project-meta'>Strictly read-only and presentation-only; no live-state fetch, refresh, recovery, subsystem mutation, approval consumption, execution, continuation, provider/model contact, or authority expansion. Next bounded unit: v1191.0-v1191.2 Responsiveness and Background-Work Foundations.</p></section>
    <section class='panel info' id='complete-campaign-development-loop-alpha-checkpoint-panel'><h2>Complete Campaign Development Loop</h2><p><span class='badge' id='complete-campaign-development-loop-alpha-checkpoint-state' data-state='starting'>checking</span></p><p id='complete-campaign-development-loop-alpha-checkpoint-summary' class='project-description'>Consolidating one operator-approved inspect-through-learning campaign loop, reviewed stage outcomes, reliability, recovery, rollback evidence, and bounded historical learning.</p><p class='project-meta'>Strictly read-only and content-free; no development stage, automatic recovery, rollback execution, policy mutation, source change, provider/model contact, promotion, certification, or release authority. Next bounded unit: v1189.0-v1189.2 Persistent Supervised Developer Alpha Hardening Foundations.</p></section>



    <section class='panel info' id='understandable-cognitive-controls-execution-checkpoint-panel'><h2>Cognitive control execution</h2><p><span class='badge' id='understandable-cognitive-controls-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='understandable-cognitive-controls-execution-checkpoint-summary' class='project-description'>Inspecting exact preview activation, explicit confirmation, bounded enforcement, rollback, restart continuity, and structural receipts.</p><p class='project-meta'>Read-only checkpoint; active controls constrain later consumers but cannot themselves start cognition, contact providers, send messages, or create proposals.</p></section>
    <section class='panel info' id='conversation-cognition-unification-governance-checkpoint-panel'><h2>Conversation and cognition governance</h2><p><span class='badge' id='conversation-cognition-unification-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='conversation-cognition-unification-governance-checkpoint-summary' class='project-description'>Consolidating exact context eligibility, deterministic arbitration, bounded local generation, deliberate silence, cross-cycle continuity, correction effectiveness, and reliability restraint.</p><p class='project-meta'>Strictly read-only; no raw private text, provider contact, output commit, message delivery, cognition mutation, approval, authorization, installation, promotion, or certification authority.</p></section>
    <section class='panel info' id='conversation-cognition-unification-execution-checkpoint-panel'><h2>Conversation and cognition execution</h2><p><span class='badge' id='conversation-cognition-unification-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='conversation-cognition-unification-execution-checkpoint-summary' class='project-description'>Inspecting deterministic communication arbitration, deliberate silence, exact provider-context assembly, bounded local generation, cancellation, timeout, workload lineage, and structural receipts.</p><p class='project-meta'>Strictly read-only; no prompt, provider payload, generated response, message delivery, cognition mutation, approval, authorization, installation, promotion, or certification authority is exposed.</p></section>

    <section class='panel info' id='operator-correction-acceptance-learning-governance-checkpoint-panel'><h2>Operator correction and acceptance learning governance</h2><p><span class='badge' id='operator-correction-acceptance-learning-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-correction-acceptance-learning-governance-checkpoint-summary' class='project-description'>Consolidating exact operator decisions, bounded advisory influence, restart continuity, reliability review, and restrained visible evidence while preserving historical truth.</p><p class='project-meta'>Strictly read-only; no operator text, reasoning text, historical rewrite, belief, goal, motivation, self-model, approval, authorization, execution, installation, promotion, or certification mutation.</p></section>
    <section class='panel info' id='operator-correction-acceptance-intake-checkpoint-panel'><h2>Operator correction and acceptance intake</h2><p><span class='badge' id='operator-correction-acceptance-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='operator-correction-acceptance-intake-checkpoint-summary' class='project-description'>Inspecting explicit operator corrections and acceptance decisions, exact target lineage, historical preservation, and bounded future-reasoning guidance.</p><p class='project-meta'>Strictly read-only; no raw operator text, history rewrite, belief, goal, motivation, self-model, approval, authorization, execution, installation, promotion, or certification mutation.</p></section>
    <section class='panel info' id='supervised-sandbox-repair-implementation-governance-checkpoint-panel'><h2>Supervised sandbox repair implementation governance</h2><p><span class='badge' id='supervised-sandbox-repair-implementation-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-repair-implementation-governance-checkpoint-summary' class='project-description'>Consolidating authorized eligibility, immutable work orders, operator-confirmed isolation, bounded execution, rollback, continuity, reliability, and candidate-evidence restraint.</p><p class='project-meta'>Strictly read-only; no patch text, command arguments, logs, source or installation mutation, approval, authorization, installation, promotion, certification, or self-granted authority.</p></section>
    <section class='panel info' id='supervised-repair-implementation-intake-checkpoint-panel'><h2>Supervised repair implementation intake</h2><p><span class='badge' id='supervised-repair-implementation-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-repair-implementation-intake-checkpoint-summary' class='project-description'>Inspecting exact authorized repair eligibility, immutable work-order bounds, and operator-confirmed materialization readiness.</p><p class='project-meta'>Strictly read-only; no patch text, sandbox materialization, file mutation, commands, tests, approval, authorization, installation, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-repair-execution-checkpoint-panel'><h2>Supervised repair execution</h2><p><span class='badge' id='supervised-repair-execution-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-repair-execution-checkpoint-summary' class='project-description'>Inspecting isolated materialization, bounded execution, rollback, and authority separation.</p><p class='project-meta'>Read-only inspection; patch text, command arguments, logs, source mutation, installation, approval, authorization, promotion, and certification remain unavailable.</p></section>
    <section class='panel info' id='supervised-sandbox-change-governance-checkpoint-panel'><h2>Supervised sandbox-change governance</h2><p><span class='badge' id='supervised-sandbox-change-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-change-governance-checkpoint-summary' class='project-description'>Consolidating structural sandbox-change eligibility, candidates, bounded deliberation, deterministic arbitration, path-digest lineage, continuity, containment, reversibility, isolation, resources, and reliability restraint.</p><p class='project-meta'>Strictly read-only; no raw source, patch text, sandbox creation, file mutation, commands, tests, installation, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-test-plan-integration-checkpoint-panel'><h2>Test-plan integration</h2><p><span class='badge' id='supervised-test-plan-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-test-plan-integration-checkpoint-summary' class='project-description'>Inspecting test-plan outcome lineage, continuity, reliability, false positives, missed plans, coverage drift, dependency drift, reproducibility, determinism, and flaky-plan patterns.</p><p class='project-meta'>Read-only; no test-plan text, test code, fixtures, commands, sandbox work, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-test-planning-governance-checkpoint-panel'><h2>Supervised test-planning governance</h2><p><span class='badge' id='supervised-test-planning-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-test-planning-governance-checkpoint-summary' class='project-description'>Consolidating structural test-plan eligibility, candidates, bounded deliberation, deterministic arbitration, outcome lineage, continuity, reliability, coverage, dependencies, reproducibility, determinism, and flaky-plan restraint.</p><p class='project-meta'>Strictly read-only; no test-plan text, test code, fixtures, commands, sandbox changes, test execution, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-specification-integration-checkpoint-panel'><h2>Specification integration</h2><p><span class='badge' id='supervised-specification-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-specification-integration-checkpoint-summary' class='project-description'>Inspecting specification outcome lineage, continuity, reliability, false positives, missed specifications, scope drift, and risk drift.</p><p class='project-meta'>Read-only; no specification text, source access, test plan, sandbox, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-test-plan-intake-checkpoint-panel'><h2>Supervised test-plan intake</h2><p><span class='badge' id='supervised-test-plan-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-test-plan-intake-checkpoint-summary' class='project-description'>Inspecting content-free test-plan eligibility, coverage targets, environments, dependencies, reproducibility, and deterministic-test requirements.</p><p class='project-meta'>Strictly read-only; no test-plan text, test code, fixture, sandbox, test execution, source modification, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-sandbox-change-intake-checkpoint-panel'><h2>Supervised sandbox-change intake</h2><p><span class='badge' id='supervised-sandbox-change-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-change-intake-checkpoint-summary' class='project-description'>Inspecting content-free sandbox-change eligibility, path digests, bounded operations, isolation profiles, reversibility, and containment confidence.</p><p class='project-meta'>Strictly read-only; no raw source, patch text, sandbox creation, file mutation, commands, tests, installation, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-sandbox-change-deliberation-checkpoint-panel'><h2>Supervised sandbox-change deliberation</h2><p><span class='badge' id='supervised-sandbox-change-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-sandbox-change-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded evidence, scope, containment, reversibility, isolation, prerequisites, recovery, resources, and operator review.</p><p class='project-meta'>Strictly read-only; no raw source, patch text, sandbox creation, file mutation, commands, tests, installation, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-specification-governance-checkpoint-panel'><h2>Supervised specification governance</h2><p><span class='badge' id='supervised-specification-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-specification-governance-checkpoint-summary' class='project-description'>Consolidating structural specification eligibility, candidates, bounded deliberation, deterministic arbitration, outcome lineage, continuity, and reliability review.</p><p class='project-meta'>Strictly read-only; no specification text, source access, test plan, sandbox, test execution, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-development-proposal-integration-checkpoint-panel'><h2>Development proposal integration</h2><p><span class='badge' id='supervised-development-proposal-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-development-proposal-integration-checkpoint-summary' class='project-description'>Inspecting proposal outcome lineage, continuity, reliability, false positives, missed proposals, scope drift, and risk drift.</p><p class='project-meta'>Read-only; no proposal text, source access, specification, test plan, sandbox, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-development-proposal-governance-checkpoint-panel'><h2>Supervised development proposal governance</h2><p><span class='badge' id='supervised-development-proposal-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-development-proposal-governance-checkpoint-summary' class='project-description'>Consolidating structural proposal eligibility, candidates, bounded deliberation, deterministic arbitration, outcome lineage, continuity, and reliability review.</p><p class='project-meta'>Strictly read-only; no proposal text, source access, specification, test plan, sandbox, test execution, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='supervised-development-proposal-intake-checkpoint-panel'><h2>Supervised development proposals</h2><p><span class='badge' id='supervised-development-proposal-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='supervised-development-proposal-intake-checkpoint-summary' class='project-description'>Inspecting content-free proposal eligibility and candidate lineage.</p><p class='project-meta'>Read-only; no proposal text, source access, specification, test plan, sandbox, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='prospective-planning-intake-checkpoint-panel'><h2>Prospective planning intake</h2><p><span class='badge' id='prospective-planning-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='prospective-planning-intake-checkpoint-summary' class='project-description'>Inspecting content-free goal lineage, alternatives, counterfactuals, risks, reversibility, timing, and stop conditions.</p><p class='project-meta'>Read-only; no plan activation, initiative, provider contact, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='internally-generated-goal-deliberation-checkpoint-panel'><h2>Internally generated goal deliberation</h2><p><span class='badge' id='internally-generated-goal-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='internally-generated-goal-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded goal comparison, value, feasibility, risk, conflict, and deterministic deferral.</p><p class='project-meta'>Read-only; recommendations cannot activate goals, create plans or initiatives, or confer operational authority.</p></section>
    <section class='panel info' id='revisable-world-model-deliberation-checkpoint-panel'><h2>Revisable world model deliberation</h2><p><span class='badge' id='revisable-world-model-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='revisable-world-model-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded relationship acceptance, contradiction reconciliation, correction handling, uncertainty, and deterministic deferral.</p><p class='project-meta'>Read-only; recommendations cannot mutate beliefs, memories, goals, identity, files, messages, approvals, authorizations, execution, promotion, or certification.</p></section>
    <section class='panel info' id='internally-generated-goal-integration-checkpoint-panel'><h2>Internally generated goal integration</h2><p><span class='badge' id='internally-generated-goal-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='internally-generated-goal-integration-checkpoint-summary' class='project-description'>Inspecting goal outcome lineage, lifecycle continuity, reliability, fixation, abandonment, and false-pattern suppression.</p><p class='project-meta'>Read-only; outcomes cannot activate goals, create plans or initiatives, or confer operational authority.</p></section>
    <section class='panel info' id='internally-generated-goal-governance-checkpoint-panel'><h2>Internally generated goal governance</h2><p><span class='badge' id='internally-generated-goal-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='internally-generated-goal-governance-checkpoint-summary' class='project-description'>Consolidating goal formation, comparison, deliberate no-goal, lifecycle continuity, fixation and abandonment review, and false-pattern restraint.</p><p class='project-meta'>Strictly read-only; no goal activation, planning, initiative, provider contact, message, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='revisable-world-model-integration-checkpoint-panel'><h2>Revisable world model integration</h2><p><span class='badge' id='revisable-world-model-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='revisable-world-model-integration-checkpoint-summary' class='project-description'>Inspecting world-model outcome lineage, continuity, correction stability, reliability, and false-pattern suppression.</p><p class='project-meta'>Read-only; no autonomous revision, raw content, provider contact, file mutation, message, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='revisable-world-model-governance-checkpoint-panel'><h2>Revisable world model governance</h2><p><span class='badge' id='revisable-world-model-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='revisable-world-model-governance-checkpoint-summary' class='project-description'>Consolidating structural relationships, bounded deliberation, deterministic arbitration, outcome lineage, correction continuity, reliability, and false-pattern restraint.</p><p class='project-meta'>Strictly read-only; no world-model revision, belief or memory mutation, raw content, provider contact, file mutation, message, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='read-only-perception-integration-checkpoint-panel'><h2>Read-only perception integration</h2><p><span class='badge' id='read-only-perception-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='read-only-perception-integration-checkpoint-summary' class='project-description'>Inspecting perception outcome lineage, continuity, reliability, missed and excessive perception review, and false-pattern suppression.</p><p class='project-meta'>Read-only; no raw file content, browsing, provider contact, filesystem mutation, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='read-only-perception-deliberation-checkpoint-panel'><h2>Read-only perception deliberation</h2><p><span class='badge' id='read-only-perception-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='read-only-perception-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded perception deliberation, failure and changed-file prioritization, deliberate non-perception, and recovery-aware deferral.</p><p class='project-meta'>Read-only; no raw file content, browsing, provider contact, filesystem mutation, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='genuine-inquiry-intake-checkpoint-panel'><h2>Genuine inquiry intake</h2><p><span class='badge' id='genuine-inquiry-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='genuine-inquiry-intake-checkpoint-summary' class='project-description'>Inspecting content-free inquiry eligibility and governed inquiry candidacy from curiosity, uncertainty, contradiction, unfinished thought, and knowledge gaps.</p><p class='project-meta'>Read-only; no browsing, provider contact, question text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='read-only-perception-governance-checkpoint-panel'><h2>Read-only perception governance</h2><p><span class='badge' id='read-only-perception-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='read-only-perception-governance-checkpoint-summary' class='project-description'>Consolidating structural project and system perception, bounded deliberation, deterministic arbitration, outcome continuity, freshness, reliability, and deliberate non-perception.</p><p class='project-meta'>Read-only; no raw file content, event payload, filesystem mutation, browsing, provider contact, message, notification, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='genuine-inquiry-governance-checkpoint-panel'><h2>Genuine inquiry governance</h2><p><span class='badge' id='genuine-inquiry-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='genuine-inquiry-governance-checkpoint-summary' class='project-description'>Consolidating genuine inquiry eligibility, candidacy, bounded deliberation, deterministic arbitration, outcome lineage, continuity, reliability, and deliberate non-inquiry.</p><p class='project-meta'>Read-only; no browsing, provider contact, question text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='genuine-inquiry-integration-checkpoint-panel'><h2>Genuine inquiry integration</h2><p><span class='badge' id='genuine-inquiry-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='genuine-inquiry-integration-checkpoint-summary' class='project-description'>Inspecting inquiry outcome lineage, continuity, reliability, bounded usefulness, false-pattern suppression, and operator-reviewed policy proposals.</p><p class='project-meta'>Read-only; no browsing, provider contact, question text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='genuine-inquiry-deliberation-checkpoint-panel'><h2>Genuine inquiry deliberation</h2><p><span class='badge' id='genuine-inquiry-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='genuine-inquiry-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded inquiry deliberation, proceed-versus-defer arbitration, contradiction and uncertainty handling, deliberate no-inquiry, and recovery-aware deferral.</p><p class='project-meta'>Read-only; no browsing, provider contact, question text, message, notification, initiative, approval, authorization, execution, promotion, or certification is created.</p></section>
    <section class='panel info' id='reflection-supported-revision-governance-checkpoint-panel'><h2>Reflection-Supported Revision Governance</h2><p><span class='badge' id='reflection-supported-revision-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-supported-revision-governance-checkpoint-summary' class='project-description'>Consolidating accountable revision intake, bounded deliberation, outcome lineage, correction history, integration reliability, and false-pattern restraint.</p><p class='project-meta'>Strictly read-only; no belief, motivation, goal, self-model, provider, communication, initiative, approval, authorization, execution, installation, promotion, or certification state is changed.</p></section>
    <section class='panel info' id='reflection-supported-revision-integration-checkpoint-panel'><h2>Reflection-supported revision integration</h2><p><span class='badge' id='reflection-supported-revision-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-supported-revision-integration-checkpoint-summary' class='project-description'>Inspecting revision outcome lineage, correction history, reliability, and false-pattern restraint.</p><p class='project-meta'>Read-only; no revision is applied and no target, provider, message, approval, authorization, execution, promotion, or certification state is changed.</p></section>
    <section class='panel info' id='reflection-supported-revision-deliberation-checkpoint-panel'><h2>Reflection-supported revision deliberation</h2><p><span class='badge' id='reflection-supported-revision-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-supported-revision-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded target-specific revision deliberation and deliberate non-application.</p><p class='project-meta'>Read-only; outcomes recommend or defer but never apply revisions.</p></section>
    <section class='panel info' id='reflection-supported-revision-intake-checkpoint-panel'><h2>Reflection-supported revision intake</h2><p><span class='badge' id='reflection-supported-revision-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-supported-revision-intake-checkpoint-summary' class='project-description'>Inspecting accountable reflection-supported revision signals and candidates for beliefs, motivations, goals, and self-model records.</p><p class='project-meta'>Read-only; no candidate revises a target, contacts providers, communicates, approves, authorizes, executes, promotes, or certifies.</p></section>
    <section class='panel info' id='continuous-thought-intake-checkpoint-panel'><h2>Continuous Thought Intake</h2><p><span class='badge' id='continuous-thought-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='continuous-thought-intake-checkpoint-summary' class='project-description'>Checking durable thought threads, pause/resume, branch lineage, conclusions, unresolved states, and restart continuity.</p><p class='project-meta'>Read-only; no provider request, belief revision, communication, initiative, approval, authorization, execution, promotion, or certification authority is granted.</p></section>
    <section class='panel info' id='reflection-quality-governance-checkpoint-panel'><h2>Reflection Quality Governance</h2><p><span class='badge' id='reflection-quality-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='reflection-quality-governance-checkpoint-summary' class='project-description'>Consolidating reflection-quality signals, bounded evaluation, outcome lineage, reliability review, and false-pattern restraint.</p><p class='project-meta'>Read-only; no quality record revises beliefs, goals, self-model, communication, provider, approval, authorization, execution, promotion, or certification state.</p></section>
    <section class='panel info' id='reflective-integration-reliability-checkpoint-panel'><h2>Reflection integration and reliability</h2><p><span class='badge' id='reflective-integration-reliability-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-integration-reliability-checkpoint-summary' class='project-description'>Inspecting durable reflection outcomes, unsupported-conclusion restraint, provider reliability, and visible status.</p><p class='project-meta'>Read-only; no belief, goal, self-model, communication, initiative, approval, authorization, execution, promotion, or certification authority.</p></section>
    <section class='panel info' id='selected-attention-reflective-focus-governance-checkpoint-panel'><h2>Selected attention and reflective focus governance</h2><p><span class='badge' id='selected-attention-reflective-focus-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='selected-attention-reflective-focus-governance-checkpoint-summary' class='project-description'>Consolidating eligibility-gated selected attention, bounded focus deliberation, durable continuity, reliability restraint, and downstream-authority separation.</p><p class='project-meta'>Read-only; the checkpoint creates no selected attention, focus state, reflection, intention, initiative, communication, provider contact, browsing, policy application, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='reflective-execution-continuity-checkpoint-panel'><h2>Reflective execution continuity</h2><p><span class='badge' id='reflective-execution-continuity-checkpoint-state' data-state='ready'>read-only</span></p><p id='reflective-execution-continuity-checkpoint-summary' class='project-description'>Inspecting bounded reflective execution, pause/resume continuity, provider recovery, and silence or communication recommendations.</p><p class='project-meta'>Recommendations cannot send messages, create notifications, revise beliefs, or execute actions.</p></section>
    <section class='panel info' id='reflective-session-intake-checkpoint-panel'><h2>Reflective session intake</h2><p><span class='badge' id='reflective-session-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-session-intake-checkpoint-summary' class='project-description'>Inspecting structural reflection subjects and bounded local-model session foundations.</p><p class='project-meta'>Read-only; no reflection is started by this panel and no conclusion can update beliefs, goals, self-model, communication, or external action.</p></section>
    <section class='panel info' id='reflective-focus-continuity-review-checkpoint-panel'><h2>Reflective focus continuity</h2><p><span class='badge' id='reflective-focus-continuity-review-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-focus-continuity-review-checkpoint-summary' class='project-description'>Inspecting focus outcome lineage, interruption and resumption continuity, repeated disengagement, fixation, and reliability evidence.</p><p class='project-meta'>Read-only; no reflection, intention, initiative, communication, provider contact, browsing, policy application, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='selected-attention-focus-intake-checkpoint-panel'><h2>Selected attention and reflective focus intake</h2><p><span class='badge' id='selected-attention-focus-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='selected-attention-focus-intake-checkpoint-summary' class='project-description'>Inspecting content-free selected-attention and bounded reflective-focus lineage.</p><p class='project-meta'>Read-only inspection; selected attention cannot create reflection, intention, initiative, communication, provider contact, browsing, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='reflective-attention-salience-governance-checkpoint-panel'><h2>Reflective attention and salience governance</h2><p><span class='badge' id='reflective-attention-salience-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-attention-salience-governance-checkpoint-summary' class='project-description'>Consolidating structural salience, bounded attention review, durable outcome continuity, reliability restraint, and authority separation.</p><p class='project-meta'>Read-only; no selected attention, reflection, intention, initiative, messaging, notification, provider contact, browsing, schedule mutation, policy application, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='reflective-attention-continuity-review-checkpoint-panel'><h2>Reflective attention continuity review</h2><p><span class='badge' id='reflective-attention-continuity-review-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-attention-continuity-review-checkpoint-summary' class='project-description'>Inspecting durable attention outcomes, interruption and resumption continuity, distraction, fixation, reliability, and false-pattern restraint.</p><p class='project-meta'>Read-only; no attention selection, reflection, intention, initiative, messaging, notification, provider contact, browsing, policy application, approval, authorization, or execution.</p></section>
    <section class='panel info' id='reflective-attention-deliberation-checkpoint-panel'><h2>Reflective attention deliberation</h2><p><span class='badge' id='reflective-attention-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-attention-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded attention-review sessions, deterministic salience comparison, deliberate non-selection, and recovery-aware deferral.</p><p class='project-meta'>Read-only; no attention selection, reflection, intention, initiative, messaging, notification, provider contact, browsing, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='reflective-attention-salience-intake-checkpoint-panel'><h2>Reflective attention and salience intake</h2><p><span class='badge' id='reflective-attention-salience-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-attention-salience-intake-checkpoint-summary' class='project-description'>Inspecting structural salience, durable relevance, novelty restraint, and content-free attention-review candidacy.</p><p class='project-meta'>Read-only; no attention selection, reflection, intention, initiative, messaging, notification, provider contact, browsing, approval, authorization, execution, promotion, or certification.</p></section>
    <section class='panel info' id='motivational-continuity-intake-checkpoint-panel'><h2>Motivational continuity intake</h2><p><span class='badge' id='motivational-continuity-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='motivational-continuity-intake-checkpoint-summary' class='project-description'>Inspecting durable motivational pressure, transient urgency, false-urgency restraint, and content-free review candidacy.</p><p class='project-meta'>Read-only; no attention selection, initiative, messaging, notification, provider contact, browsing, approval, authorization, or execution.</p></section>
    <section class='panel info' id='motivational-drive-deliberation-checkpoint-panel'><h2>Motivational drive deliberation</h2><p><span class='badge' id='motivational-drive-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='motivational-drive-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded drive comparison, transient urgency restraint, deliberate non-selection, and operator-review boundaries.</p><p class='project-meta'>Read-only; no attention selection, initiative, messaging, notification, provider contact, browsing, approval, authorization, or execution.</p></section>
    <section class='panel info' id='motivational-continuity-endogenous-drive-regulation-checkpoint-panel'><h2>Motivational continuity governance</h2><p><span class='badge' id='motivational-continuity-endogenous-drive-regulation-checkpoint-state' data-state='starting'>checking</span></p><p id='motivational-continuity-endogenous-drive-regulation-checkpoint-summary' class='project-description'>Consolidating motivational-pressure intake, bounded drive deliberation, durable outcomes, and continuity review.</p><p class='project-meta'>Read-only; no attention selection, initiative, communication, notification, provider contact, browsing, policy application, approval, authorization, or execution.</p></section>
    <section class='panel info' id='motivational-continuity-review-checkpoint-panel'><h2>Motivational continuity review</h2><p><span class='badge' id='motivational-continuity-review-checkpoint-state' data-state='starting'>checking</span></p><p id='motivational-continuity-review-checkpoint-summary' class='project-description'>Inspecting durable motivational outcomes, continuity, decay, recurrence, reversal, and false-pattern restraint.</p><p class='project-meta'>Read-only; no attention selection, initiative, messaging, notification, provider contact, browsing, policy application, approval, authorization, or execution.</p></section>

    <section class='panel info' id='goal-continuity-review-checkpoint-panel'><h2>Goal continuity review</h2><p><span class='badge' id='goal-continuity-review-checkpoint-state' data-state='starting'>checking</span></p><p id='goal-continuity-review-checkpoint-summary' class='project-description'>Inspecting durable outcome lineage, long-horizon stability, recurrence, reversal, and false-instability restraint.</p><p class='project-meta'>Read-only; no reprioritization, abandonment, dependency mutation, milestone mutation, policy application, approval, authorization, or execution.</p></section>
    <section class='panel info' id='goal-coherence-long-horizon-objective-governance-checkpoint-panel'><h2>Goal coherence governance</h2><p><span class='badge' id='goal-coherence-long-horizon-objective-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='goal-coherence-long-horizon-objective-governance-checkpoint-summary' class='project-description'>Consolidating objective-coherence intake, bounded deliberation, durable outcomes, and long-horizon stability.</p><p class='project-meta'>Read-only; no reprioritization, abandonment, dependency or milestone mutation, policy application, approval, authorization, or execution.</p></section>
    <section class='panel info' id='objective-coherence-deliberation-checkpoint-panel'><h2>Goal coherence deliberation</h2><p><span class='badge' id='objective-coherence-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='objective-coherence-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded retain, reprioritization-candidate, dependency-repair, milestone-revision, abandonment-clarification, unresolved, and deliberate non-repair outcomes.</p><p class='project-meta'>Read-only; no reprioritization, abandonment, dependency mutation, milestone mutation, approval, authorization, or execution.</p></section>
    <section class='panel info' id='objective-coherence-intake-checkpoint-panel'><h2>Goal coherence intake</h2><p><span class='badge' id='objective-coherence-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='objective-coherence-intake-checkpoint-summary' class='project-description'>Inspecting objective dependencies, conflicts, duplication, priority mismatch, milestone feasibility, drift, and abandonment ambiguity.</p><p class='project-meta'>Read-only; no reprioritization, abandonment, milestone mutation, approval, authorization, or execution.</p></section>
    <section class='panel info' id='self-model-integrity-intake-checkpoint-panel'><h2>Self-model integrity intake</h2><p><span class='badge' id='self-model-integrity-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='self-model-integrity-intake-checkpoint-summary' class='project-description'>Inspecting support, contradiction, temporal scope, persistence, and uncertainty across identity and self-model claims.</p><p class='project-meta'>Read-only; no identity revision, self-model revision, trait promotion, approval, authorization, or execution.</p></section>
    <section class='panel info' id='self-model-revision-deliberation-checkpoint-panel'><h2>Self-model revision deliberation</h2><p><span class='badge' id='self-model-revision-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='self-model-revision-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded retain, weaken, suspend, reclassify, replace, unresolved, and deliberate non-revision outcomes.</p><p class='project-meta'>Read-only; deliberation cannot revise identity, revise the self-model, promote traits, approve, authorize, or execute.</p></section>
    <section class='panel info' id='self-model-integrity-identity-claim-governance-checkpoint-panel'><h2>Self-model integrity and identity governance</h2><p><span class='badge' id='self-model-integrity-identity-claim-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='self-model-integrity-identity-claim-governance-checkpoint-summary' class='project-description'>Consolidating integrity intake, bounded revision deliberation, durable identity lineage, and stability review.</p><p class='project-meta'>Read-only; no identity revision, self-model mutation, trait promotion, policy application, approval, authorization, or execution.</p></section>
    <section class='panel info' id='self-model-continuity-review-checkpoint-panel'><h2>Self-model continuity review</h2><p><span class='badge' id='self-model-continuity-review-checkpoint-state' data-state='starting'>checking</span></p><p id='self-model-continuity-review-checkpoint-summary' class='project-description'>Inspecting durable revision lineage, historical supersession, stability, recurrence, and false-instability restraint.</p><p class='project-meta'>Read-only; continuity review cannot revise identity, revise the self-model, promote traits, apply policy, approve, authorize, or execute.</p></section>

    <section class='panel info' id='epistemic-coherence-intake-checkpoint-panel'><h2>Epistemic coherence intake</h2><p><span class='badge' id='epistemic-coherence-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='epistemic-coherence-intake-checkpoint-summary' class='project-description'>Inspecting structural contradictions, duplicates, stale dependencies, and confidence mismatches.</p><p class='project-meta'>Read-only; no evidence, knowledge, belief, or self-model mutation authority.</p></section>
    <section class='panel info' id='epistemic-coherence-deliberation-checkpoint-panel'><h2>Epistemic coherence deliberation</h2><p><span class='badge' id='epistemic-coherence-deliberation-checkpoint-state' data-state='starting'>checking</span></p><p id='epistemic-coherence-deliberation-checkpoint-summary' class='project-description'>Inspecting bounded coherence-response options and deliberate non-repair.</p><p class='project-meta'>Read-only; deliberation cannot repair, merge, mutate, approve, authorize, or execute.</p></section>
    <section class='panel info' id='knowledge-belief-integration-checkpoint-panel'><h2>Knowledge-belief integration</h2><p><span class='badge' id='knowledge-belief-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='knowledge-belief-integration-checkpoint-summary' class='project-description'>Inspecting coherence outcome lineage, repeated inconsistency, and integration stability.</p><p class='project-meta'>Read-only; no repair, merge, policy application, approval, authorization, or execution.</p></section>
    <section class='panel info' id='epistemic-coherence-knowledge-belief-integration-checkpoint-panel'><h2>Epistemic coherence and knowledge-belief integration</h2><p><span class='badge' id='epistemic-coherence-knowledge-belief-integration-checkpoint-state' data-state='starting'>checking</span></p><p id='epistemic-coherence-knowledge-belief-integration-checkpoint-summary' class='project-description'>Consolidating coherence intake, bounded deliberation, outcome lineage, and integration stability.</p><p class='project-meta'>Read-only; no repair, merge, mutation, policy application, approval, authorization, or execution.</p></section>
    <section class='panel info' id='belief-reconsideration-intake-checkpoint-panel'><h2>Belief reconsideration intake</h2><p><span class='badge' id='belief-reconsideration-intake-checkpoint-state' data-state='starting'>checking</span></p><p id='belief-reconsideration-intake-checkpoint-summary' class='project-description'>Inspecting evidence-change signals and bounded belief reconsideration candidates.</p><p id='belief-reconsideration-intake-checkpoint-detail' class='project-meta'>Read-only; no belief revision, attention selection, proposal, approval, authorization, or execution authority.</p></section>
    <section class='panel info' id='reflective-temporal-continuity-prospective-memory-checkpoint-panel'><h2>Reflective temporal continuity</h2><p><span class='badge' id='reflective-temporal-continuity-prospective-memory-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-temporal-continuity-prospective-memory-checkpoint-summary' class='project-description'>Consolidating prospective obligations, review lifecycle, outcomes, and temporal reliability.</p><p id='reflective-temporal-continuity-prospective-memory-checkpoint-detail' class='project-meta'>Read-only; no reminders, autonomous rescheduling, approval, authorization, execution, or consciousness claim.</p></section>
    <section class='panel info' id='prospective-memory-continuity-checkpoint-panel'><h2>Prospective memory continuity</h2><p><span class='badge' id='prospective-memory-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='prospective-memory-continuity-checkpoint-summary' class='project-description'>Inspecting structural future review obligations and temporal eligibility.</p><p id='prospective-memory-continuity-checkpoint-detail' class='project-meta'>Read-only; no reminder, notification, attention, intention, approval, authorization, or execution authority.</p></section>
    <section class='panel info' id='cognitive-homeostasis-sustainable-cognition-checkpoint-panel'><h2>Cognitive homeostasis and sustainable cognition</h2><p><span class='badge' id='cognitive-homeostasis-sustainable-cognition-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-homeostasis-sustainable-cognition-checkpoint-summary' class='project-description'>Consolidating pressure, recovery, sustainable-window, overload-pattern, and drift evidence.</p><p id='cognitive-homeostasis-sustainable-cognition-checkpoint-detail' class='project-meta'>Read-only structural evidence; no schedule mutation, work control, adaptation, authorization, or execution.</p></section>
    <section class='panel info' id='cognitive-sustainability-review-checkpoint-panel'><h2>Cognitive sustainability review</h2><p><span class='badge' id='cognitive-sustainability-review-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-sustainability-review-checkpoint-summary' class='project-description'>Inspecting overload patterns, homeostasis drift, and recovery effectiveness.</p><p id='cognitive-sustainability-review-checkpoint-detail' class='project-meta'>Read-only structural evidence; no schedule mutation, adaptation, authorization, or execution.</p></section>
    <section class='panel info' id='cognitive-recovery-continuity-checkpoint-panel'><h2>Cognitive recovery continuity</h2><p><span class='badge' id='cognitive-recovery-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-recovery-continuity-checkpoint-summary' class='project-description'>Inspecting recovery lifecycle, sustainable workload windows, and content-free outcomes.</p><p id='cognitive-recovery-continuity-checkpoint-detail' class='project-meta'>Read-only structural evidence; no schedule mutation, pause, resume, adaptation, authorization, or execution.</p></section>
    <section class='panel info' id='cognitive-homeostasis-continuity-checkpoint-panel'><h2>Cognitive homeostasis</h2><p><span class='badge' id='cognitive-homeostasis-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-homeostasis-continuity-checkpoint-summary' class='project-description'>Inspecting structural load pressure, fragmentation, recovery margin, and deliberate rest recommendations.</p><p id='cognitive-homeostasis-continuity-checkpoint-detail' class='project-meta'>Read-only structural evidence; no schedule mutation, pause, resume, attention selection, authorization, or execution.</p></section>
    <section class='panel info' id='internal-coordination-cognitive-load-governance-checkpoint-panel'><h2>Internal coordination checkpoint</h2><p><span class='badge' id='internal-coordination-cognitive-load-governance-checkpoint-state' data-state='starting'>checking</span></p><p id='internal-coordination-cognitive-load-governance-checkpoint-summary' class='project-description'>Consolidating cognitive demand, load allocation, scheduling, interruption, outcomes, and effectiveness review.</p><p id='internal-coordination-cognitive-load-governance-checkpoint-detail' class='project-meta'>Read-only structural evidence; coordination cannot select attention, alter scheduling, authorize, or execute.</p></section>
    <section class='panel info' id='cognitive-work-continuity-checkpoint-panel'><h2>Cognitive work continuity checkpoint</h2><p><span class='badge' id='cognitive-work-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='cognitive-work-continuity-checkpoint-summary' class='project-description'>Inspecting bounded scheduling, interruption, resumption, and stale-work retirement.</p><p id='cognitive-work-continuity-checkpoint-detail' class='project-meta'>Read-only structural evidence; no attention selection, intention, proposal, approval, authorization, or execution.</p></section>
    <section class='panel info' id='deliberative-continuity-checkpoint-panel'><h2>Deliberative continuity checkpoint</h2><p><span class='badge' id='deliberative-continuity-checkpoint-state' data-state='starting'>checking</span></p><p id='deliberative-continuity-checkpoint-summary' class='project-description'>Inspecting durable options, bounded comparison, and deliberate no-choice.</p><p id='deliberative-continuity-checkpoint-detail' class='project-meta'>Read-only structural evidence; no decision commitment, intention formation, proposal, approval, authorization, or execution.</p></section>
    <section class='panel info' id='reflective-behavioral-learning-checkpoint-panel'><h2>Reflective behavioral learning</h2><p><span class='badge' id='reflective-behavioral-learning-checkpoint-state' data-state='starting'>checking</span></p><p id='reflective-behavioral-learning-checkpoint-summary' class='project-description'>Consolidating outcomes, attribution, patterns, evaluations, hypotheses, proposals, and review lifecycle.</p><p id='reflective-behavioral-learning-checkpoint-detail' class='project-meta'>Read-only structural evidence; no autonomous adaptation, authorization, execution, or consciousness claim.</p></section>
    <section class='panel info' id='endogenous-curiosity-checkpoint-panel'><h2>Endogenous curiosity checkpoint</h2><p><span class='badge' id='endogenous-curiosity-checkpoint-state' data-state='starting'>checking</span></p><p id='endogenous-curiosity-checkpoint-summary' class='project-description'>Consolidating curiosity candidacy, question quality, inquiry-candidate promotion, and lifecycle evidence.</p><p id='endogenous-curiosity-checkpoint-detail' class='project-meta'>Read-only structural evidence; curiosity cannot browse, prompt, message, authorize, execute, or prove consciousness.</p></section>
    <section class='panel info' id='curiosity-quality-checkpoint-panel'><h2>Curiosity quality</h2><p><span class='badge' id='curiosity-quality-checkpoint-state' data-state='starting'>checking</span></p><p id='curiosity-quality-checkpoint-summary' class='project-description'>Loading bounded question formulation, answerability, relevance, and restraint evidence.</p><p id='curiosity-quality-checkpoint-detail' class='project-meta'>Read-only structural evidence; questions cannot browse, interrogate, authorize, or execute.</p></section>
    <section class='panel info' id='persistent-self-model-checkpoint-panel'><h2>Persistent self-model checkpoint</h2><p><span class='badge' id='persistent-self-model-checkpoint-state' data-state='starting'>checking</span></p><p id='persistent-self-model-checkpoint-summary' class='project-description'>Consolidating identity evidence, revision, reflection influence, and communication restraint.</p><p id='persistent-self-model-checkpoint-detail' class='project-meta'>Read-only structural evidence; identity remains revisable, private, and unable to authorize or execute actions.</p></section>
    <section class='panel info' id='persistent-initiative-consolidation-checkpoint-panel'><h2>Persistent initiative checkpoint</h2><p><span class='badge' id='persistent-initiative-consolidation-checkpoint-state' data-state='starting'>checking</span></p><p id='persistent-initiative-consolidation-checkpoint-summary' class='project-description'>Consolidating initiative candidacy, restraint, explicit surfacing, response outcomes, and retirement.</p><p id='persistent-initiative-consolidation-checkpoint-detail' class='project-meta'>Read-only structural evidence; no generation, sending, notification, retry, authorization, execution, or consciousness claim.</p></section>
    <section class='panel info' id='initiative-communication-checkpoint-panel'><h2>Initiative communication</h2><p><span class='badge' id='initiative-communication-checkpoint-state' data-state='starting'>checking</span></p><p id='initiative-communication-checkpoint-summary' class='project-description'>Loading non-sending proposals, restraint, timing, and deliberate silence.</p><p id='initiative-communication-checkpoint-detail' class='project-meta'>A proposal may surface only through normal local chat and never authorizes delivery or action.</p></section>
    <section class='panel info' id='intention-lifecycle-review-panel'><h2>Intention lifecycle</h2><p><span class='badge' id='intention-lifecycle-review-state' data-state='starting'>checking</span></p><p id='intention-lifecycle-review-summary' class='project-description'>Loading bounded reconsideration, expiry, retirement, and deterministic conflict handling.</p><p id='intention-lifecycle-review-detail' class='project-meta'>Lifecycle changes remain non-authorizing and provider-neutral.</p></section>
    <section class='panel info'><h2>Message delivery</h2><p><span class='badge' id='delivery-state' data-state='starting'>not measured</span></p><p id='delivery-summary' class='project-description'>First-visible-token timing will appear after an explicit send.</p><p id='delivery-detail' class='project-meta'>No message or response content is recorded in timing evidence.</p></section>
    <section class='panel info'><h2>Provider</h2><p><span class='badge' id='provider-state' data-state='starting'>not checked</span></p><p class='muted' id='provider-label'>The shell does not pretend the provider is ready.</p><button id='provider-retry' type='button'>Check provider</button></section>
    <section class='panel info'><h2>Ownership</h2><p id='ownership'>Coordinating this browser tab…</p><button id='take-control' class='hidden' type='button'>Take control</button><p class='project-meta' id='ownership-detail'>Ownership transfers are explicit. Stale tabs never send automatically.</p></section>
    <section class='panel info recovery hidden' id='recovery'><h2>Partial startup</h2><p id='recovery-text'></p><button id='bootstrap-retry' type='button'>Retry failed startup services</button><p class='project-meta' id='retry-budget'></p></section>
  </aside>
</main>
<script>
(() => {{
  'use strict';
  const started = performance.now();
  const log = document.getElementById('conversation-log');
  const empty = document.getElementById('conversation-empty');
  const message = document.getElementById('message');
  const send = document.getElementById('send');
  const cancelActive = document.getElementById('cancel-active');
  const actionPreview = document.getElementById('action-preview');
  const actionPortalState = document.getElementById('action-portal-state');
  const actionPortalSummary = document.getElementById('action-portal-summary');
  const actionPortalDetail = document.getElementById('action-portal-detail');
  const actionToolCount = document.getElementById('action-tool-count');
  const actionCard = document.getElementById('action-card');
  const cognitionState = document.getElementById('cognition-state');
  const cognitionSummary = document.getElementById('cognition-summary');
  const cognitionDetail = document.getElementById('cognition-detail');
  const cognitionMotivations = document.getElementById('cognition-motivations');
  const cognitionReflections = document.getElementById('cognition-reflections');
  const cognitionProactive = document.getElementById('cognition-proactive');
  const cognitionRead = document.getElementById('cognition-read');
  const cognitionFrequency = document.getElementById('cognition-frequency');
  const internalLifeCheckpointState = document.getElementById('internal-life-checkpoint-state');
  const internalLifeCheckpointSummary = document.getElementById('internal-life-checkpoint-summary');
  const internalLifeCheckpointDetail = document.getElementById('internal-life-checkpoint-detail');
  const cognitiveDevelopmentCheckpointState = document.getElementById('cognitive-development-checkpoint-state');
  const inquiryContinuityState = document.getElementById('inquiry-continuity-state');
  const inquiryContinuitySummary = document.getElementById('inquiry-continuity-summary');
  const inquiryContinuityDetail = document.getElementById('inquiry-continuity-detail');
  const inquiryCognitionCheckpointState = document.getElementById('inquiry-cognition-checkpoint-state');
  const knowledgeConfidenceCheckpointState = document.getElementById('knowledge-confidence-checkpoint-state');
  const knowledgeConfidenceCheckpointSummary = document.getElementById('knowledge-confidence-checkpoint-summary');
  const knowledgeConfidenceCheckpointDetail = document.getElementById('knowledge-confidence-checkpoint-detail');
  const knowledgeReconsiderationState = document.getElementById('knowledge-reconsideration-state');
  const knowledgeReconsiderationSummary = document.getElementById('knowledge-reconsideration-summary');
  const knowledgeReconsiderationDetail = document.getElementById('knowledge-reconsideration-detail');
  const knowledgeMaintenanceCheckpointState = document.getElementById('knowledge-maintenance-checkpoint-state');
  const knowledgeMaintenanceCheckpointSummary = document.getElementById('knowledge-maintenance-checkpoint-summary');
  const knowledgeMaintenanceCheckpointDetail = document.getElementById('knowledge-maintenance-checkpoint-detail');
  const attentionAgendaCheckpointState = document.getElementById('attention-agenda-checkpoint-state');
  const attentionAgendaCheckpointSummary = document.getElementById('attention-agenda-checkpoint-summary');
  const attentionAgendaCheckpointDetail = document.getElementById('attention-agenda-checkpoint-detail');
  const attentionIntentionCheckpointState = document.getElementById('attention-intention-checkpoint-state');
  const attentionIntentionCheckpointSummary = document.getElementById('attention-intention-checkpoint-summary');
  const attentionIntentionCheckpointDetail = document.getElementById('attention-intention-checkpoint-detail');
  const autonomousAttentionIntentionCheckpointState = document.getElementById('autonomous-attention-intention-checkpoint-state');
  const autonomousAttentionIntentionCheckpointSummary = document.getElementById('autonomous-attention-intention-checkpoint-summary');
  const autonomousAttentionIntentionCheckpointDetail = document.getElementById('autonomous-attention-intention-checkpoint-detail');
  const persistentInitiativeCheckpointState = document.getElementById('persistent-initiative-checkpoint-state');
  const persistentInitiativeCheckpointSummary = document.getElementById('persistent-initiative-checkpoint-summary');
  const persistentInitiativeCheckpointDetail = document.getElementById('persistent-initiative-checkpoint-detail');
  const initiativeLifecycleCheckpointState = document.getElementById('initiative-lifecycle-checkpoint-state');
  const initiativeLifecycleCheckpointSummary = document.getElementById('initiative-lifecycle-checkpoint-summary');
  const initiativeLifecycleCheckpointDetail = document.getElementById('initiative-lifecycle-checkpoint-detail');
  const longHorizonObjectiveCheckpointState = document.getElementById('long-horizon-objective-checkpoint-state');
  const longHorizonObjectiveCheckpointSummary = document.getElementById('long-horizon-objective-checkpoint-summary');
  const longHorizonObjectiveCheckpointDetail = document.getElementById('long-horizon-objective-checkpoint-detail');
  const longHorizonFollowThroughCheckpointState = document.getElementById('long-horizon-follow-through-checkpoint-state');
  const longHorizonFollowThroughCheckpointSummary = document.getElementById('long-horizon-follow-through-checkpoint-summary');
  const longHorizonFollowThroughCheckpointDetail = document.getElementById('long-horizon-follow-through-checkpoint-detail');
  const selfModelContinuityCheckpointState = document.getElementById('self-model-continuity-checkpoint-state');
  const selfModelContinuityCheckpointSummary = document.getElementById('self-model-continuity-checkpoint-summary');
  const selfModelContinuityCheckpointDetail = document.getElementById('self-model-continuity-checkpoint-detail');
  const identityRevisionCheckpointState = document.getElementById('identity-revision-checkpoint-state');
  const identityRevisionCheckpointSummary = document.getElementById('identity-revision-checkpoint-summary');
  const identityRevisionCheckpointDetail = document.getElementById('identity-revision-checkpoint-detail');
  const identityExpressionLifecycleCheckpointState = document.getElementById('identity-expression-lifecycle-checkpoint-state');
  const identityExpressionLifecycleCheckpointSummary = document.getElementById('identity-expression-lifecycle-checkpoint-summary');
  const identityExpressionLifecycleCheckpointDetail = document.getElementById('identity-expression-lifecycle-checkpoint-detail');
  const curiosityContinuityCheckpointState = document.getElementById('curiosity-continuity-checkpoint-state');
  const curiosityContinuityCheckpointSummary = document.getElementById('curiosity-continuity-checkpoint-summary');
  const curiosityContinuityCheckpointDetail = document.getElementById('curiosity-continuity-checkpoint-detail');
  const curiosityLifecycleCheckpointState = document.getElementById('curiosity-lifecycle-checkpoint-state');
  const curiosityLifecycleCheckpointSummary = document.getElementById('curiosity-lifecycle-checkpoint-summary');
  const curiosityLifecycleCheckpointDetail = document.getElementById('curiosity-lifecycle-checkpoint-detail');
  const behavioralEvidenceCheckpointState = document.getElementById('behavioral-evidence-checkpoint-state');
  const behavioralEvidenceCheckpointSummary = document.getElementById('behavioral-evidence-checkpoint-summary');
  const behavioralEvidenceCheckpointDetail = document.getElementById('behavioral-evidence-checkpoint-detail');
  const endogenousCuriosityCheckpointState = document.getElementById('endogenous-curiosity-checkpoint-state');
  const endogenousCuriosityCheckpointSummary = document.getElementById('endogenous-curiosity-checkpoint-summary');
  const endogenousCuriosityCheckpointDetail = document.getElementById('endogenous-curiosity-checkpoint-detail');
  const curiosityQualityCheckpointState = document.getElementById('curiosity-quality-checkpoint-state');
  const curiosityQualityCheckpointSummary = document.getElementById('curiosity-quality-checkpoint-summary');
  const curiosityQualityCheckpointDetail = document.getElementById('curiosity-quality-checkpoint-detail');
  const persistentSelfModelCheckpointState = document.getElementById('persistent-self-model-checkpoint-state');
  const persistentSelfModelCheckpointSummary = document.getElementById('persistent-self-model-checkpoint-summary');
  const persistentSelfModelCheckpointDetail = document.getElementById('persistent-self-model-checkpoint-detail');
  const persistentInitiativeConsolidationCheckpointState = document.getElementById('persistent-initiative-consolidation-checkpoint-state');
  const persistentInitiativeConsolidationCheckpointSummary = document.getElementById('persistent-initiative-consolidation-checkpoint-summary');
  const persistentInitiativeConsolidationCheckpointDetail = document.getElementById('persistent-initiative-consolidation-checkpoint-detail');
  const initiativeCommunicationCheckpointState = document.getElementById('initiative-communication-checkpoint-state');
  const initiativeCommunicationCheckpointSummary = document.getElementById('initiative-communication-checkpoint-summary');
  const initiativeCommunicationCheckpointDetail = document.getElementById('initiative-communication-checkpoint-detail');
  const intentionLifecycleReviewState = document.getElementById('intention-lifecycle-review-state');
  const intentionLifecycleReviewSummary = document.getElementById('intention-lifecycle-review-summary');
  const intentionLifecycleReviewDetail = document.getElementById('intention-lifecycle-review-detail');
  const inquiryCognitionCheckpointSummary = document.getElementById('inquiry-cognition-checkpoint-summary');
  const inquiryCognitionCheckpointDetail = document.getElementById('inquiry-cognition-checkpoint-detail');
  const cognitiveDevelopmentCheckpointSummary = document.getElementById('cognitive-development-checkpoint-summary');
  const cognitiveDevelopmentCheckpointDetail = document.getElementById('cognitive-development-checkpoint-detail');
  const takeControl = document.getElementById('take-control');
  const ownershipDetail = document.getElementById('ownership-detail');
  const sessionSelector = document.getElementById('session-selector');
  const jumpToLatest = document.getElementById('jump-to-latest');
  const unreadTurnCount = document.getElementById('unread-turn-count');
  const status = document.getElementById('status');
  const sessionTitle = document.getElementById('session-title');
  const shellState = document.getElementById('shell-state');
  const projectName = document.getElementById('project-name');
  const projectDescription = document.getElementById('project-description');
  const projectMeta = document.getElementById('project-meta');
  const runtimeState = document.getElementById('runtime-state');
  const runtimeSummary = document.getElementById('runtime-summary');
  const runtimeGuidance = document.getElementById('runtime-guidance');
  const startupProgress = document.getElementById('startup-progress');
  const restartState = document.getElementById('restart-state');
  const retryBudget = document.getElementById('retry-budget');
  const checkpointState = document.getElementById('checkpoint-state');
  const checkpointSummary = document.getElementById('checkpoint-summary');
  const checkpointNext = document.getElementById('checkpoint-next');
  const conversationCheckpointState = document.getElementById('conversation-checkpoint-state');
  const conversationCheckpointSummary = document.getElementById('conversation-checkpoint-summary');
  const conversationCheckpointNext = document.getElementById('conversation-checkpoint-next');
  const messagingCheckpointState = document.getElementById('messaging-checkpoint-state');
  const messagingCheckpointSummary = document.getElementById('messaging-checkpoint-summary');
  const messagingCheckpointNext = document.getElementById('messaging-checkpoint-next');
  const deliveryState = document.getElementById('delivery-state');
  const deliverySummary = document.getElementById('delivery-summary');
  const deliveryDetail = document.getElementById('delivery-detail');
  const providerState = document.getElementById('provider-state');
  const providerLabel = document.getElementById('provider-label');
  const ownership = document.getElementById('ownership');
  const recovery = document.getElementById('recovery');
  const recoveryText = document.getElementById('recovery-text');
  const useAi = document.getElementById('use-ai');
  let selectedSessionId = '';
  let projectId = '';
  let draftRevision = 0;
  let draftUpdatedAt = '';
  let draftDirty = false;
  let draftTimer = 0;
  let draftSaveInFlight = null;
  let sending = false;
  let loadedConversationId = '';
  let coordination = {{ revision:0, lease_token:'', is_owner:false }};
  let failedRetryServices = [];
  let retryAttempt = 0;
  let retryMaximum = 3;
  let compositionActive = false;
  let keyboardSubmitLatch = false;
  let followLatest = true;
  let unreadTurns = 0;
  let sessionTurnCount = 0;
  let lastSeenTurnCount = 0;
  let presentationUpdatedAt = '';
  let presentationSaveTimer = 0;
  let selectionGeneration = 0;
  let switchingSession = false;
  let providerCheckInFlight = false;
  let providerReturned = false;
  let lastProviderObservedState = 'unknown';
  let lastProviderCheckAt = 0;
  let activeOperationId = '';
  let activeAcceptanceKey = '';
  let actionPreviewInFlight = false;
  let coordinationHeartbeat = 0;
  let cognitionRefreshTimer = 0;
  let activeProactiveMessageId = '';

  const uuid = () => (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : '00000000-0000-4000-8000-' + Math.random().toString(16).slice(2).padEnd(12,'0').slice(0,12);
  const navigationClientId = uuid();
  const tabKey = 'eidolon.first-use.tab.v1';
  let identity;
  try {{ identity = JSON.parse(sessionStorage.getItem(tabKey) || 'null'); }} catch (_error) {{ identity = null; }}
  const hadTabIdentity = !!(identity && identity.tab_id);
  if (!identity || !identity.tab_id) identity = {{ tab_id:uuid(), browser_id:uuid(), instance_nonce:'instance-' + uuid().replaceAll('-','') }};
  sessionStorage.setItem(tabKey, JSON.stringify(identity));
  const navigationEntry = performance.getEntriesByType ? performance.getEntriesByType('navigation')[0] : null;
  const navigationType = navigationEntry && navigationEntry.type ? navigationEntry.type : 'navigate';
  const launchMarkerKey = 'eidolon.first-use.last-ready.v2';
  const launchMode = navigationType === 'reload' ? 'refresh' : (hadTabIdentity ? 'warm' : (localStorage.getItem(launchMarkerKey) ? 'reopen' : 'cold'));
  try {{ lastProviderObservedState=localStorage.getItem('eidolon.first-use.provider-state.v1103') || lastProviderObservedState; }} catch (_error) {{}}

  function setStatus(text, state='ready') {{ status.textContent = text; shellState.textContent = state; shellState.dataset.state = state; }}
  function renderJumpState() {{
    jumpToLatest.classList.toggle('hidden', followLatest);
    unreadTurnCount.textContent = unreadTurns > 0 ? '(' + unreadTurns + ' new)' : '';
  }}
  function visibleTurnAnchor() {{
    const frame = log.getBoundingClientRect();
    const rows = Array.from(log.querySelectorAll('[data-session-turn-id]'));
    const node = rows.find(row => row.getBoundingClientRect().bottom > frame.top + 2) || rows[0] || null;
    if (!node) return {{turn_id:'',offset_px:0}};
    return {{turn_id:String(node.dataset.sessionTurnId || ''),offset_px:Math.round(node.getBoundingClientRect().top-frame.top)}};
  }}
  function captureScrollPresentation() {{
    const distance = Math.max(0, Math.round(log.scrollHeight-log.clientHeight-log.scrollTop));
    const nearLatest = distance <= 96;
    followLatest = nearLatest;
    if (nearLatest) {{ unreadTurns=0; lastSeenTurnCount=sessionTurnCount; }}
    const anchor = nearLatest ? {{turn_id:'',offset_px:0}} : visibleTurnAnchor();
    renderJumpState();
    return {{
      follow_latest:nearLatest,
      scroll_from_bottom_px:nearLatest?0:distance,
      view_anchor_turn_id:anchor.turn_id,
      view_anchor_offset_px:anchor.offset_px,
      last_seen_turn_id:nearLatest ? String((Array.from(log.querySelectorAll('[data-session-turn-id]')).pop() || {{dataset:{{}}}}).dataset.sessionTurnId || '') : '',
      last_seen_turn_count:nearLatest?sessionTurnCount:lastSeenTurnCount,
      composer_intentionally_empty:!message.value
    }};
  }}
  function preserveScrollAnchor(mutator) {{
    const beforeHeight=log.scrollHeight; const beforeTop=log.scrollTop; const wasFollowing=followLatest;
    const result=mutator();
    if (wasFollowing) log.scrollTop=log.scrollHeight;
    else log.scrollTop=Math.max(0,beforeTop+(log.scrollHeight-beforeHeight));
    return result;
  }}
  function restorePresentation(value) {{
    const presentation=value && typeof value==='object' ? value : {{}};
    followLatest=presentation.follow_latest!==false;
    unreadTurns=Math.max(0,Number(presentation.unread_turn_count || 0));
    lastSeenTurnCount=Math.max(0,Number(presentation.last_seen_turn_count || 0));
    presentationUpdatedAt=String(presentation.updated_at || '');
    requestAnimationFrame(() => {{
      if (followLatest) log.scrollTop = log.scrollHeight;
      else {{
        const anchorId=String(presentation.view_anchor_turn_id || '');
        const anchor=anchorId ? log.querySelector("[data-session-turn-id='"+CSS.escape(anchorId)+"']") : null;
        if (anchor) log.scrollTop += Math.round(anchor.getBoundingClientRect().top-log.getBoundingClientRect().top-Number(presentation.view_anchor_offset_px || 0));
        else log.scrollTop=Math.max(0,log.scrollHeight-log.clientHeight-Number(presentation.scroll_from_bottom_px || 0));
      }}
      renderJumpState();
    }});
  }}
  function bubble(role, text) {{
    if (empty) empty.remove();
    const node = document.createElement('div'); node.className = 'message ' + role; node.textContent = text; log.appendChild(node);
    if (followLatest) log.scrollTop = log.scrollHeight;
    else {{ unreadTurns=Math.max(1,unreadTurns); renderJumpState(); }}
    return node;
  }}
  function renderSessionCatalog(catalog) {{
    const rows=Array.isArray(catalog)?catalog.filter(row=>row && row.status!=='archived'):[];
    sessionSelector.replaceChildren();
    if (!rows.length) {{ const option=document.createElement('option'); option.value=''; option.textContent='New conversation'; sessionSelector.appendChild(option); }}
    for (const row of rows) {{
      const option=document.createElement('option'); option.value=String(row.id || ''); option.textContent=String(row.title || 'New conversation')+' · '+String(row.turn_count || 0)+' turns'; sessionSelector.appendChild(option);
    }}
    if (selectedSessionId && !rows.some(row=>String(row.id || '')===selectedSessionId)) {{ const option=document.createElement('option'); option.value=selectedSessionId; option.textContent=sessionTitle.textContent || 'Current conversation'; sessionSelector.appendChild(option); }}
    sessionSelector.value=selectedSessionId; sessionSelector.disabled=!coordination.is_owner || sending || switchingSession || rows.length<2;
  }}
  function mutationFields(key) {{ return {{ tab_id:identity.tab_id, lease_token:coordination.lease_token || '', mutation_key:key, coordination_revision:Number(coordination.revision || 0), project_id:projectId }}; }}
  function applyCoordination(value) {{
    if (!value || typeof value !== 'object') return;
    coordination = Object.assign({{}}, coordination, value);
    const staleIdentity = !!coordination.renew_tab_id || String(coordination.status || '') === 'identity_conflict';
    ownership.textContent = coordination.is_owner ? 'This tab controls conversation changes.' : (staleIdentity ? 'This duplicated tab has a stale identity and cannot mutate conversation state.' : (coordination.owner_present ? 'Another tab controls conversation changes. Typing remains available.' : 'No tab currently owns conversation changes.'));
    ownershipDetail.textContent = staleIdentity ? 'Reload this duplicated tab to obtain a fresh identity. No automatic takeover or send occurred.' : (coordination.is_owner ? 'The lease is renewed while this tab remains active.' : 'Takeover is explicit. A stale or follower tab never sends, cancels, retries, or switches automatically.');
    takeControl.classList.toggle('hidden', coordination.is_owner || staleIdentity);
    takeControl.disabled = coordination.is_owner || staleIdentity || sending;
    send.disabled = !coordination.is_owner || sending;
    sessionSelector.disabled = !coordination.is_owner || sending || switchingSession || sessionSelector.options.length < 2;
  }}

  async function registerTab() {{
    const response = await fetch('/api/dashboard-chat/coordination', {{method:'POST', headers:{{'Content-Type':'application/json'}}, cache:'no-store', body:JSON.stringify({{action:'register', tab_id:identity.tab_id, browser_id:identity.browser_id, instance_nonce:identity.instance_nonce, visible:!document.hidden}})}});
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || 'Tab coordination failed');
    applyCoordination(payload);
  }}

  function renderProgress(progress) {{
    const rows = Array.isArray(progress && progress.phases) ? progress.phases : [];
    startupProgress.replaceChildren();
    for (const row of rows) {{
      const item = document.createElement('li'); item.className='progress-row'; item.dataset.state=String(row.status || 'pending');
      const label = document.createElement('span'); label.textContent=String(row.label || row.name || 'Startup phase'); item.appendChild(label);
      const right = document.createElement('span'); right.className='progress-state'; right.textContent=String(row.status || 'pending');
      if (row.retry_available && row.retry_service) {{
        const button = document.createElement('button'); button.type='button'; button.className='retry-small'; button.textContent='Retry';
        button.addEventListener('click', () => bootstrap([String(row.retry_service)])); right.appendChild(document.createTextNode(' ')); right.appendChild(button);
      }}
      item.appendChild(right); startupProgress.appendChild(item);
    }}
    const retry = progress && progress.retry ? progress.retry : {{}};
    retryAttempt = Number(retry.attempt || retryAttempt || 0); retryMaximum = Number(retry.maximum_attempts || retryMaximum || 3);
    retryBudget.textContent = retryAttempt ? ('Optional retry ' + retryAttempt + ' of ' + retryMaximum + '. No accepted work is replayed.') : ('Up to ' + retryMaximum + ' explicit optional retries are available.');
  }}

  function applyRestartTruth(restart) {{
    const digest = String(restart && restart.continuity_digest || '');
    if (!digest || !projectId) {{ restartState.textContent='Launch continuity could not be compared yet.'; return; }}
    const key = 'eidolon.first-use.continuity.v2.' + projectId;
    const previous = localStorage.getItem(key);
    if (!previous) restartState.textContent = launchMode + ' launch established a continuity baseline.';
    else if (previous === digest) restartState.textContent = launchMode + ' launch restored the same project, conversation, draft, and view state.';
    else restartState.textContent = launchMode + ' launch restored current persisted truth, but continuity changed since the prior browser state.';
    localStorage.setItem(key, digest); localStorage.setItem(launchMarkerKey, new Date().toISOString());
  }}

  async function savePresentation() {{
    if (!selectedSessionId || !coordination.is_owner || switchingSession) return false;
    const view=captureScrollPresentation(); const stamp=new Date().toISOString(); const key='presentation-'+uuid();
    try {{
      const response=await fetch('/api/dashboard-chat/presentation', {{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify(Object.assign({{session_id:selectedSessionId,client_updated_at:stamp}},view,mutationFields(key)))}});
      const payload=await response.json(); if (payload.coordination) applyCoordination(payload.coordination);
      if (!response.ok || !payload.ok) return false;
      presentationUpdatedAt=String(payload.updated_at || stamp); followLatest=payload.follow_latest!==false; unreadTurns=Math.max(0,Number(payload.unread_turn_count || unreadTurns)); lastSeenTurnCount=Math.max(0,Number(payload.last_seen_turn_count || lastSeenTurnCount)); renderJumpState(); return true;
    }} catch (_error) {{ return false; }}
  }}

  function applySessionSnapshot(snapshot, catalog, forceDraft=false) {{
    if (!snapshot || snapshot.ok===false) return false;
    const session=snapshot.session || {{}}; const targetId=String(session.id || '');
    if (!targetId) return false;
    selectedSessionId=targetId; loadedConversationId=targetId; sessionTitle.textContent=String(session.title || 'New conversation'); sessionTurnCount=Math.max(0,Number(session.turn_count || 0));
    const draft=snapshot.draft || {{}}; draftRevision=Math.max(0,Number(draft.revision || 0)); draftUpdatedAt=String(draft.updated_at || '');
    if (forceDraft || !draftDirty) {{ message.value=String(draft.content || ''); draftDirty=false; }}
    if (snapshot.transcript_html) log.innerHTML=String(snapshot.transcript_html);
    renderSessionCatalog(catalog); restorePresentation(snapshot.presentation || {{}});
    const providerCue=snapshot.provider_recovery || {{}}; if (providerCue.state) lastProviderObservedState=String(providerCue.observed_state || providerCue.state || 'unknown');
    sessionSelector.value=selectedSessionId; setStatus('Conversation ready. Switching restored its draft and view without sending anything.', 'ready'); return true;
  }}

  async function switchConversationSession(targetSessionId) {{
    const target=String(targetSessionId || ''); const source=selectedSessionId;
    if (!target || target===source || !source || !coordination.is_owner || sending || switchingSession) {{ sessionSelector.value=source; return false; }}
    switchingSession=true; sessionSelector.disabled=true; clearTimeout(draftTimer); clearTimeout(presentationSaveTimer);
    setStatus('Switching conversations never sends a draft automatically. Saving this draft and view first…','starting');
    if (draftSaveInFlight) await draftSaveInFlight;
    const view=captureScrollPresentation(); const generation=++selectionGeneration; const stamp=new Date().toISOString();
    try {{
      const response=await fetch('/api/dashboard-chat/session-switch', {{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify(Object.assign({{
        source_session_id:source,target_session_id:target,navigation_client_id:navigationClientId,selection_generation:generation,
        source_draft_content:message.value,source_draft_updated_at:stamp,source_draft_base_revision:draftRevision,source_draft_editor_id:identity.tab_id,
        source_follow_latest:view.follow_latest,source_scroll_from_bottom_px:view.scroll_from_bottom_px,source_composer_intentionally_empty:view.composer_intentionally_empty,
        source_presentation_updated_at:stamp,source_view_anchor_turn_id:view.view_anchor_turn_id,source_view_anchor_offset_px:view.view_anchor_offset_px,
        source_last_seen_turn_id:view.last_seen_turn_id,source_last_seen_turn_count:view.last_seen_turn_count
      }},mutationFields('switch-'+uuid())))}});
      const payload=await response.json(); if (payload.coordination) applyCoordination(payload.coordination);
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Conversation switch failed');
      if (generation!==selectionGeneration || payload.stale_selection_ignored) {{ sessionSelector.value=selectedSessionId; setStatus('A newer conversation selection won. The older switch was ignored safely.','degraded'); return false; }}
      return applySessionSnapshot(payload.snapshot || {{}}, payload.catalog || [], true);
    }} catch (error) {{ sessionSelector.value=source; setStatus('The conversation could not be switched safely. The source draft remains in this tab and nothing was sent.','degraded'); return false; }}
    finally {{ switchingSession=false; sessionSelector.disabled=!coordination.is_owner || sending || sessionSelector.options.length<2; }}
  }}

  async function bootstrap(services=[]) {{
    const requested = Array.isArray(services) ? services.filter(Boolean) : [];
    const nextAttempt = requested.length ? retryAttempt + 1 : retryAttempt;
    if (nextAttempt > retryMaximum) {{ setStatus('Optional startup retry limit reached. Conversation remains usable; reopen the dashboard for a fresh attempt.', 'degraded'); return; }}
    recovery.classList.add('hidden');
    try {{
      const query = new URLSearchParams({{tab_id:identity.tab_id, launch:launchMode, attempt:String(nextAttempt)}});
      if (requested.length) query.set('retry', requested.join(','));
      const response = await fetch('/api/first-use/bootstrap?' + query.toString(), {{cache:'no-store'}});
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'First-use restoration failed');
      const session = payload.selected_session || {{}};
      const project = payload.active_project || {{}};
      selectedSessionId = String(session.id || ''); projectId = String(project.id || '');
      sessionTitle.textContent = session.title || 'New conversation';
      sessionTurnCount = Math.max(0,Number(session.turn_count || 0));
      renderSessionCatalog(payload.session_catalog || []);
      projectName.textContent = project.name || 'No active project';
      projectDescription.textContent = project.description || project.summary || 'No project description is available.';
      const source = project.source || {{}}; const versions = project.versions || {{}};
      projectMeta.textContent = 'Working source v' + String(versions.working_source || 'unknown') + ' · ' + (source.development_available ? 'development available' : 'development paused') + ' · ' + String(project.truth_status || 'unknown');
      const runtime = payload.runtime_guidance || {{}};
      runtimeState.textContent = runtime.runtime_external ? 'external' : 'source-local';
      runtimeState.dataset.state = runtime.runtime_external ? 'ready' : 'degraded';
      runtimeSummary.textContent = runtime.headline || 'Runtime placement could not be described.';
      runtimeGuidance.textContent = runtime.summary || 'No data is moved automatically. Use the local runtime-guide command for review.';
      const draft = payload.draft || {{}}; draftRevision = Number(draft.revision || 0); draftUpdatedAt = String(draft.updated_at || '');
      if (!draftDirty && !message.value) message.value = String(draft.content || '');
      const presentation = payload.presentation || {{}};
      followLatest = presentation.follow_latest !== false; unreadTurns=Math.max(0,Number(presentation.unread_turn_count || 0)); lastSeenTurnCount=Math.max(0,Number(presentation.last_seen_turn_count || 0)); presentationUpdatedAt=String(presentation.updated_at || ''); renderJumpState();
      applyCoordination(payload.coordination || {{}});
      const provider = payload.provider || {{}}; lastProviderObservedState=String(provider.status || 'unknown'); providerState.textContent = provider.status || 'unknown'; providerState.dataset.state = provider.recovery_proven ? 'ready' : (provider.status || 'degraded'); providerLabel.textContent = provider.label || 'Provider readiness has not been checked.';
      renderProgress(payload.progress || {{}}); applyRestartTruth(payload.restart || {{}});
      const checkpoint = payload.checkpoint || {{}};
      checkpointState.textContent = String(checkpoint.status || 'unavailable').replaceAll('_',' ');
      checkpointState.dataset.state = checkpoint.status === 'ready' || checkpoint.status === 'ready_for_native_windows_review' ? 'ready' : (checkpoint.status || 'degraded');
      checkpointSummary.textContent = checkpoint.headline || 'First-use coherence could not be summarized.';
      checkpointNext.textContent = Number(checkpoint.current_product_defect_count || 0) + ' current issue(s) · ' + Number(checkpoint.pending_evidence_count || 0) + ' pending evidence item(s) · operator authority preserved.';
      const conversationCheckpoint = payload.natural_conversation_checkpoint || {{}};
      conversationCheckpointState.textContent = String(conversationCheckpoint.status || 'unavailable').replaceAll('_',' ');
      conversationCheckpointState.dataset.state = String(conversationCheckpoint.status || '').startsWith('ready') ? 'ready' : (conversationCheckpoint.status || 'degraded');
      conversationCheckpointSummary.textContent = conversationCheckpoint.headline || 'Natural-conversation coherence could not be summarized.';
      conversationCheckpointNext.textContent = Number(conversationCheckpoint.current_product_defect_count || 0) + ' current issue(s) · ' + Number(conversationCheckpoint.pending_evidence_count || 0) + ' pending evidence item(s) · no automatic tuning.';
      const messagingCheckpoint = payload.messaging_reliability_checkpoint || {{}};
      messagingCheckpointState.textContent = String(messagingCheckpoint.status || 'unavailable').replaceAll('_',' ');
      messagingCheckpointState.dataset.state = String(messagingCheckpoint.status || '').startsWith('ready') ? 'ready' : (messagingCheckpoint.status || 'degraded');
      messagingCheckpointSummary.textContent = messagingCheckpoint.headline || 'Messaging reliability could not be summarized.';
      messagingCheckpointNext.textContent = Number(messagingCheckpoint.current_product_defect_count || 0) + ' current issue(s) · ' + Number(messagingCheckpoint.pending_evidence_count || 0) + ' pending evidence item(s) · no automatic replay, retry, takeover, or certification.';
      failedRetryServices = Array.from(new Set((payload.optional_failures || []).map(row => String(row.service || '')).filter(Boolean)));
      const retryRemaining = Math.max(0, retryMaximum - retryAttempt);
      if (failedRetryServices.length) {{
        recovery.classList.remove('hidden');
        recoveryText.textContent = 'Optional local services failed: ' + failedRetryServices.join(', ') + '. Conversation input remains available and nothing was replayed.';
        document.getElementById('bootstrap-retry').disabled = retryRemaining <= 0;
      }}
      setStatus(selectedSessionId ? 'Conversation restored. Loading recent messages without replaying work…' : 'No conversation exists yet. Type below to start one explicitly.', payload.status || 'ready');
      send.disabled = !coordination.is_owner;
      sessionSelector.disabled = !coordination.is_owner || sending || switchingSession || sessionSelector.options.length < 2;
      if (selectedSessionId && loadedConversationId !== selectedSessionId) {{ loadedConversationId = selectedSessionId; loadConversation(); }}
    }} catch (error) {{
      setStatus('The shell remains usable, but local state could not be restored. No message was sent or replayed.', 'degraded');
      recovery.classList.remove('hidden'); recoveryText.textContent = String(error && error.message || error);
    }}
  }}

  async function loadConversation() {{
    try {{
      const response = await fetch('/api/dashboard-chat/active-session', {{cache:'no-store'}});
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Conversation history unavailable');
      if (!payload.snapshot) {{ renderSessionCatalog(payload.catalog || []); return; }}
      applySessionSnapshot(payload.snapshot, payload.catalog || [], false);
      setStatus('Conversation ready. Startup did not replay an accepted message.', 'ready');
    }} catch (error) {{
      setStatus('Chat input is ready, but recent history is temporarily unavailable. Retry from the full console.', 'degraded');
    }}
  }}

  async function saveDraft() {{
    if (!selectedSessionId || !coordination.is_owner || sending || switchingSession) return false;
    if (draftSaveInFlight) return draftSaveInFlight;
    const key = 'draft-' + uuid(); const sessionAtStart=selectedSessionId; const contentAtStart=message.value; const revisionAtStart=draftRevision;
    const task=(async () => {{
      try {{
        const response = await fetch('/api/dashboard-chat/draft', {{method:'POST', headers:{{'Content-Type':'application/json'}}, cache:'no-store', body:JSON.stringify(Object.assign({{session_id:sessionAtStart, content:contentAtStart, client_updated_at:new Date().toISOString(), base_revision:revisionAtStart, editor_id:identity.tab_id}}, mutationFields(key)))}});
        const payload = await response.json();
        if (payload.coordination) applyCoordination(payload.coordination);
        if (!response.ok || !payload.ok || payload.draft_conflict) {{ setStatus('Draft was not overwritten because another tab changed it. Review in the full console.', 'degraded'); return false; }}
        if (selectedSessionId===sessionAtStart) {{ draftRevision=Number(payload.revision || draftRevision); draftUpdatedAt=String(payload.updated_at || draftUpdatedAt); if (message.value===contentAtStart) draftDirty=false; }}
        setStatus('Draft saved locally.', 'ready'); return true;
      }} catch (_error) {{ setStatus('Draft save is uncertain. The text remains in this tab; nothing was sent.', 'degraded'); return false; }}
    }})();
    draftSaveInFlight=task;
    try {{ return await task; }} finally {{ if (draftSaveInFlight===task) draftSaveInFlight=null; }}
  }}

  function parseFrames(buffer, flush=false) {{
    const normalized = buffer.replaceAll('\\r\\n','\\n'); const parts = normalized.split('\\n\\n');
    const remainder = flush ? '' : parts.pop(); return {{frames:parts, remainder:remainder || ''}};
  }}
  function parseFrame(frame) {{
    let type='message', data=''; for (const line of frame.split('\\n')) {{ if (line.startsWith('event:')) type=line.slice(6).trim(); if (line.startsWith('data:')) data += line.slice(5).trim(); }}
    try {{ return {{type,payload:JSON.parse(data || '{{}}')}}; }} catch (_error) {{ return {{type,payload:{{text:data}}}}; }}
  }}

  async function sendMessage() {{
    const text = message.value.trim();
    if (!text || !coordination.is_owner || sending) return;
    const intentStarted = performance.now();
    sending = true; send.disabled = true; sessionSelector.disabled=true; followLatest=true; unreadTurns=0; renderJumpState(); const acceptanceKey = uuid(); const outgoing = bubble('user', text); const reply = bubble('eidolon','Connecting…');
    sessionStorage.setItem('eidolon.first-use.pending-send.v1103', JSON.stringify({{session_id:selectedSessionId, acceptance_key:acceptanceKey}}));
    deliveryState.textContent='measuring'; deliveryState.dataset.state='starting'; deliverySummary.textContent='Waiting for acceptance and the first visible response token.';
    message.value = ''; setStatus('Submitting once. Network uncertainty will not trigger an automatic resend.', 'starting');
    try {{
      const response = await fetch('/api/dashboard-chat/stream', {{method:'POST', headers:{{'Content-Type':'application/json'}}, cache:'no-store', body:JSON.stringify(Object.assign({{message:text, use_ai:useAi.checked, session_id:selectedSessionId, acceptance_key:acceptanceKey}}, mutationFields(acceptanceKey)))}});
      if (!response.ok || !response.body) throw new Error('The turn could not be confirmed. Nothing will be resent automatically.');
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer=''; let accepted=false; let acceptanceAt=0; let firstVisibleScheduled=false; let serverTiming=null; reply.textContent='';
      while (true) {{
        const chunk = await reader.read(); const parsed = parseFrames(buffer + decoder.decode(chunk.value || new Uint8Array(), {{stream:!chunk.done}}), chunk.done); buffer = parsed.remainder;
        for (const raw of parsed.frames) {{
          const event = parseFrame(raw); const payload = event.payload || {{}};
          if (payload.coordination) applyCoordination(payload.coordination);
          if (event.type === 'accepted') {{ accepted=true; acceptanceAt=performance.now(); activeOperationId=String(payload.operation_id || (payload.operation && payload.operation.operation_id) || ''); activeAcceptanceKey=acceptanceKey; cancelActive.classList.toggle('hidden',!activeOperationId); cancelActive.disabled=!activeOperationId || !coordination.is_owner; selectedSessionId = String(payload.session_id || selectedSessionId); sessionTitle.textContent = selectedSessionId ? 'New conversation' : sessionTitle.textContent; setStatus('Turn accepted once. Streaming response…','ready'); }}
          else if (event.type === 'delta') {{ const visible=String(payload.text || payload.delta || ''); if (payload.timing) serverTiming=payload.timing; reply.textContent += visible; if (followLatest) log.scrollTop=log.scrollHeight; else {{ unreadTurns=Math.max(1,unreadTurns); renderJumpState(); }} if (!firstVisibleScheduled && visible.trim()) {{ firstVisibleScheduled=true; requestAnimationFrame(() => {{ const visibleAt=performance.now(); const intentToVisible=Math.round(visibleAt-intentStarted); const acceptToVisible=acceptanceAt ? Math.round(visibleAt-acceptanceAt) : null; window.__eidolonLastDeliveryTiming={{intent_to_acceptance_ms:acceptanceAt?Math.round(acceptanceAt-intentStarted):null,acceptance_to_first_visible_ms:acceptToVisible,intent_to_first_visible_ms:intentToVisible,server:serverTiming,content_free:true}}; deliveryState.textContent='measured'; deliveryState.dataset.state='ready'; deliverySummary.textContent='First visible response: '+intentToVisible+' ms after Send.'; deliveryDetail.textContent='Acceptance '+(acceptanceAt?Math.round(acceptanceAt-intentStarted)+' ms':'pending')+' · browser render '+(acceptToVisible===null?'pending':acceptToVisible+' ms')+' · content-free evidence.'; }}); }} }}
          else if (event.type === 'provider_request') {{ window.__eidolonProviderRequestCount = Number(payload.request_index || 1); }}
          else if (event.type === 'done') {{ activeOperationId=''; activeAcceptanceKey=''; cancelActive.disabled=true; cancelActive.classList.add('hidden'); sessionStorage.removeItem('eidolon.first-use.pending-send.v1103'); if (payload.text && !reply.textContent) reply.textContent=String(payload.text); setStatus('Response complete.','ready'); }}
          else if (event.type === 'error') {{ cancelActive.disabled=true; reply.textContent += String(payload.message || payload.error || 'The response failed.'); setStatus('The accepted turn failed safely. It was not replayed.','degraded'); }}
        }}
        if (chunk.done) break;
      }}
      if (!accepted) setStatus('Acceptance was not proven. No automatic retry occurred.','degraded'); else sessionStorage.removeItem('eidolon.first-use.pending-send.v1103');
      draftRevision += 1; draftUpdatedAt = new Date().toISOString(); draftDirty = false; sessionTurnCount+=1; if (followLatest) lastSeenTurnCount=sessionTurnCount; savePresentation(); if (accepted) window.setTimeout(loadConversation, 0);
    }} catch (error) {{
      reply.textContent = String(error && error.message || error); message.value = text; draftDirty = true;
      setStatus('Delivery is uncertain. The draft was restored and no automatic resend occurred.','degraded');
    }} finally {{ sending=false; send.disabled = !coordination.is_owner; sessionSelector.disabled=!coordination.is_owner || switchingSession || sessionSelector.options.length<2; }}
  }}

  function renderActionCard(payload) {{
    const card=payload || {{}}; const classification=String(card.classification || 'unknown');
    actionPortalState.textContent=classification.replaceAll('_',' ');
    actionPortalState.dataset.state=classification==='blocked'?'degraded':'ready';
    actionPortalSummary.textContent=String(card.summary || 'No action preview is available.');
    actionPortalDetail.textContent='Risk '+String(card.risk_level || 'unknown')+' · '+String(card.execution_timing || 'review only').replaceAll('_',' ')+' · preview only.';
    actionCard.dataset.state=classification==='blocked'?'blocked':'ready';
    actionCard.classList.remove('hidden');
    const title=document.createElement('h3'); title.textContent=String(card.title || 'Action preview');
    const decision=document.createElement('p'); decision.textContent='Operator decision: '+String(card.operator_decision || 'review');
    const boundary=document.createElement('p'); boundary.className='project-meta'; boundary.textContent=String(card.safety_boundary || 'Nothing runs automatically.');
    actionCard.replaceChildren(title,decision,boundary);
  }}

  async function loadActionCatalog() {{
    try {{
      const response=await fetch('/api/conversation-action/catalog',{{cache:'no-store'}}); const payload=await response.json();
      actionToolCount.textContent=String(payload.tool_count || 0);
      if (!response.ok || payload.catalog_bounded!==true) throw new Error('catalog unavailable');
      actionPortalState.textContent='preview only'; actionPortalState.dataset.state='ready';
    }} catch (_error) {{ actionPortalState.textContent='catalog unavailable'; actionPortalState.dataset.state='degraded'; actionPortalDetail.textContent='The action portal remains non-authorizing. Use the full console for governed actions.'; }}
  }}

  async function previewConversationAction() {{
    if (actionPreviewInFlight) return false;
    const text=message.value.trim();
    if (!text) {{ renderActionCard({{classification:'ambiguous',title:'Nothing to preview',summary:'Write a request first. No tool was selected.',risk_level:'none',execution_timing:'not_applicable',operator_decision:'write_a_request',safety_boundary:'Nothing was saved, sent, or executed.'}}); return false; }}
    actionPreviewInFlight=true; actionPreview.disabled=true; actionPortalState.textContent='classifying'; actionPortalState.dataset.state='starting';
    try {{
      const response=await fetch('/api/conversation-action/proposal',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify({{text}})}}); const payload=await response.json();
      if (!response.ok) throw new Error(payload.error || 'preview unavailable');
      renderActionCard(payload); setStatus('Action preview created. Nothing was saved, executed, or authorized.','ready'); return true;
    }} catch (_error) {{ actionPortalState.textContent='preview unavailable'; actionPortalState.dataset.state='degraded'; actionPortalSummary.textContent='The request was not executed. Use the full console or try again.'; return false; }}
    finally {{ actionPreviewInFlight=false; actionPreview.disabled=false; }}
  }}

  function renderCognitionList(target, rows, emptyText, formatter) {{
    target.replaceChildren();
    if (!rows.length) {{ const item=document.createElement('li'); item.textContent=emptyText; target.appendChild(item); return; }}
    rows.slice(0,4).forEach(row => {{ const item=document.createElement('li'); item.textContent=formatter(row); target.appendChild(item); }});
  }}

  async function claimProactiveMessage(messageRow) {{
    if (!messageRow || messageRow.state!=='queued' || activeProactiveMessageId===messageRow.message_id) return false;
    const deliveryId='dashboard-delivery-'+uuid();
    try {{
      const response=await fetch('/api/cognition/proactive/claim',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify({{event_id:'dashboard-claim-'+deliveryId,message_id:messageRow.message_id,delivery_id:deliveryId,tab_id:identity.tab_id}})}});
      const payload=await response.json(); const data=payload.data || payload; const delivered=data.message || messageRow;
      if (!response.ok || !data.ok || !(data.result && data.result.delivered)) return false;
      activeProactiveMessageId=String(delivered.message_id || ''); cognitionProactive.textContent=String(delivered.body || ''); cognitionProactive.classList.remove('hidden'); cognitionRead.classList.remove('hidden');
      cognitionDetail.textContent=String(delivered.reason || 'A persisted internal state produced a bounded communication proposal.');
      return true;
    }} catch (_error) {{ return false; }}
  }}

  async function loadCognition() {{
    try {{
      const response=await fetch('/api/cognition/inspection',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('inspection unavailable');
      const motivation=data.motivation || {{}}; const cycle=data.cycle || {{}}; const communication=data.communication || {{}}; const continuity=data.continuity || {{}}; const beliefs=data.beliefs || {{}}; const nativeEvaluation=data.native_evaluation || {{}}; const controls=cycle.controls || {{}};
      cognitionState.textContent=String(cycle.status || 'running'); cognitionState.dataset.state=cycle.status==='running'?'ready':'degraded';
      cognitionSummary.textContent=String(motivation.active_motivation_count || 0)+' active motivations · '+String((data.unresolved_concerns || []).length)+' unresolved concerns · '+String(continuity.due_subject_count || 0)+' scheduled revisits · '+String(beliefs.active_conflict_count || 0)+' belief conflicts · '+String(communication.unread_count || 0)+' unread proactive messages.';
      cognitionDetail.textContent='Cycle '+String(cycle.last_cycle && cycle.last_cycle.status || 'never run')+' · continuity '+String(continuity.mode || 'awake')+' · '+String(cycle.last_cycle && cycle.last_cycle.communication_reason || 'Silence remains valid.')+' · native evaluation '+String(nativeEvaluation.last_evaluation && nativeEvaluation.last_evaluation.status || 'not run')+'. Internal state has no action authority.';
      cognitionFrequency.value=String(communication.preferences && communication.preferences.frequency || 'normal');
      renderCognitionList(cognitionMotivations,motivation.active_motivations || [],'No active motivation is currently recorded.',row => String(row.kind || 'state').replaceAll('_',' ')+': '+String(row.summary || '')+' · urgency '+String(row.urgency ?? 0));
      renderCognitionList(cognitionReflections,cycle.recent_reflections || [],'No authored reflection conclusion is recorded yet.',row => 'Reflection: '+String(row.conclusion || '')+' · uncertainty '+String(row.uncertainty ?? 'retained'));
      const messages=(communication.recent_messages || []).filter(row => row.state==='queued');
      if (messages.length) await claimProactiveMessage(messages[messages.length-1]);
      return true;
    }} catch (_error) {{ cognitionState.textContent='unavailable'; cognitionState.dataset.state='degraded'; cognitionSummary.textContent='Cognitive inspection is unavailable. Conversation and action boundaries remain unchanged.'; return false; }}
  }}

  async function loadInternalLifeCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/internal-life-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('checkpoint unavailable');
      const summary=data.summary || {{}}; internalLifeCheckpointState.textContent=String(data.status || 'unknown'); internalLifeCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      internalLifeCheckpointSummary.textContent=String(summary.active_motivation_count || 0)+' motivations · '+String(summary.cycle_count || 0)+' cycles · '+String(summary.continuity_subject_count || 0)+' continuity subjects · '+String(summary.active_belief_count || 0)+' beliefs.';
      internalLifeCheckpointDetail.textContent='Provider '+String(data.provider_classification || 'not run')+' · runtime '+(data.runtime_external?'external':'needs Desktop review')+' · no consciousness claim, action authority, promotion, or certification.'; return true;
    }} catch (_error) {{ internalLifeCheckpointState.textContent='unavailable'; internalLifeCheckpointState.dataset.state='degraded'; internalLifeCheckpointSummary.textContent='Checkpoint evidence is unavailable; existing cognition and action boundaries remain unchanged.'; return false; }}
  }}

  async function loadCognitiveDevelopmentCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/development-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('checkpoint unavailable');
      const summary=data.summary || {{}}; cognitiveDevelopmentCheckpointState.textContent=String(data.status || 'unknown'); cognitiveDevelopmentCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      cognitiveDevelopmentCheckpointSummary.textContent=String(summary.active_inquiry_count || 0)+' active inquiries · '+String(summary.paused_inquiry_count || 0)+' paused · '+String(summary.active_plan_count || 0)+' prospective plans · '+String(summary.proposal_count || 0)+' internal proposals.';
      cognitiveDevelopmentCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · zero provider contact, external browsing, action authority, execution, promotion, or certification.'; return true;
    }} catch (_error) {{ cognitiveDevelopmentCheckpointState.textContent='unavailable'; cognitiveDevelopmentCheckpointState.dataset.state='degraded'; cognitiveDevelopmentCheckpointSummary.textContent='Cognitive development evidence is unavailable; existing cognition and action boundaries remain unchanged.'; return false; }}
  }}


  async function loadInquiryContinuity() {{
    try {{
      const [a,e,c]=await Promise.all([fetch('/api/cognition/inquiry-attention',{{cache:'no-store'}}),fetch('/api/cognition/inquiry-evidence',{{cache:'no-store'}}),fetch('/api/cognition/inquiry-conversation',{{cache:'no-store'}})]);
      const ar=(await a.json()).data||{{}}, er=(await e.json()).data||{{}}, cr=(await c.json()).data||{{}};
      if (!a.ok || !e.ok || !c.ok) throw new Error('inquiry continuity unavailable');
      inquiryContinuityState.textContent='bounded'; inquiryContinuityState.dataset.state='ready';
      inquiryContinuitySummary.textContent=String(ar.activation_count||0)+' attention activations · '+String(er.active_evidence_count||0)+' active evidence items · '+String(er.research_proposal_count||0)+' research proposals · '+String(cr.decision_count||0)+' communication decisions.';
      inquiryContinuityDetail.textContent='No autonomous browsing, provider request, action authorization, execution, model management, promotion, or certification.'; return true;
    }} catch (_error) {{ inquiryContinuityState.textContent='unavailable'; inquiryContinuityState.dataset.state='degraded'; inquiryContinuitySummary.textContent='Inquiry continuity inspection is unavailable; established authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadInquiryCognitionCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/inquiry-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('inquiry checkpoint unavailable');
      const summary=data.summary || {{}}; inquiryCognitionCheckpointState.textContent=String(data.status || 'unknown'); inquiryCognitionCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      inquiryCognitionCheckpointSummary.textContent=String(summary.active_inquiry_count || 0)+' active inquiries · '+String(summary.active_evidence_count || 0)+' active evidence · '+String(summary.reflection_count || 0)+' reflections · '+String(summary.resolution_count || 0)+' resolutions.';
      inquiryCognitionCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · no provider contact, browsing, action authority, execution, promotion, certification, or consciousness claim.'; return true;
    }} catch (_error) {{ inquiryCognitionCheckpointState.textContent='unavailable'; inquiryCognitionCheckpointState.dataset.state='degraded'; inquiryCognitionCheckpointSummary.textContent='Inquiry cognition checkpoint evidence is unavailable; established privacy and authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadKnowledgeConfidenceCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/knowledge-confidence-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('knowledge confidence unavailable');
      const summary=data.summary || {{}}; knowledgeConfidenceCheckpointState.textContent=String(data.status || 'unknown'); knowledgeConfidenceCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      knowledgeConfidenceCheckpointSummary.textContent=String(summary.residual_lineage_link_count||0)+' residual links · '+String(summary.cross_inquiry_evidence_link_count||0)+' shared evidence links · '+String(summary.reconsideration_candidate_count||0)+' belief reviews · '+String(summary.inquiry_review_candidate_count||0)+' inquiry reviews.';
      knowledgeConfidenceCheckpointDetail.textContent='Uncertainty and contradiction remain explicit · no provider contact, browsing, action authority, promotion, certification, or consciousness claim.'; return true;
    }} catch (_error) {{ knowledgeConfidenceCheckpointState.textContent='unavailable'; knowledgeConfidenceCheckpointState.dataset.state='degraded'; knowledgeConfidenceCheckpointSummary.textContent='Knowledge-confidence evidence is unavailable; established privacy and authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadKnowledgeReconsideration() {{
    try {{
      const [scheduleResponse, propagationResponse, conversationResponse]=await Promise.all([
        fetch('/api/cognition/knowledge-reconsideration',{{cache:'no-store'}}),
        fetch('/api/cognition/evidence-change-propagation',{{cache:'no-store'}}),
        fetch('/api/cognition/reconsideration-conversation',{{cache:'no-store'}})
      ]);
      const schedulePayload=await scheduleResponse.json(); const propagationPayload=await propagationResponse.json(); const conversationPayload=await conversationResponse.json();
      const schedule=schedulePayload.data || schedulePayload; const propagation=propagationPayload.data || propagationPayload; const conversation=conversationPayload.data || conversationPayload;
      if (!scheduleResponse.ok || !propagationResponse.ok || !conversationResponse.ok) throw new Error('knowledge reconsideration unavailable');
      knowledgeReconsiderationState.textContent='bounded'; knowledgeReconsiderationState.dataset.state='ready';
      knowledgeReconsiderationSummary.textContent=String(schedule.scheduled_count||0)+' scheduled reviews · '+String(schedule.due_count||0)+' due · '+String(propagation.propagation_count||0)+' evidence propagations · '+String(conversation.decision_count||0)+' communication decisions.';
      knowledgeReconsiderationDetail.textContent='Quiet, cooldown, unread, non-response, provider, browsing, action, promotion, and certification boundaries remain intact.'; return true;
    }} catch (_error) {{ knowledgeReconsiderationState.textContent='unavailable'; knowledgeReconsiderationState.dataset.state='degraded'; knowledgeReconsiderationSummary.textContent='Knowledge reconsideration evidence is unavailable; established authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadKnowledgeMaintenanceCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/knowledge-maintenance-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('knowledge maintenance checkpoint unavailable');
      const summary=data.summary || {{}}; knowledgeMaintenanceCheckpointState.textContent=String(data.status || 'unknown'); knowledgeMaintenanceCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      knowledgeMaintenanceCheckpointSummary.textContent=String(summary.scheduled_reconsideration_count||0)+' scheduled · '+String(summary.evidence_propagation_count||0)+' propagations · '+String(summary.bounded_reflection_count||0)+' reflections · '+String(summary.maintenance_outcome_count||0)+' outcomes · '+String(summary.communication_decision_count||0)+' communication decisions.';
      knowledgeMaintenanceCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · uncertainty remains explicit · no hidden reasoning, provider contact, browsing, action authority, promotion, certification, or consciousness claim.'; return true;
    }} catch (_error) {{ knowledgeMaintenanceCheckpointState.textContent='unavailable'; knowledgeMaintenanceCheckpointState.dataset.state='degraded'; knowledgeMaintenanceCheckpointSummary.textContent='Knowledge-maintenance checkpoint evidence is unavailable; established privacy and authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadAttentionAgendaCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/attention-agenda-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('attention agenda checkpoint unavailable');
      const summary=data.summary || {{}}; attentionAgendaCheckpointState.textContent=String(data.status || 'unknown'); attentionAgendaCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      attentionAgendaCheckpointSummary.textContent=String(summary.active_candidate_count||0)+' active · '+String(summary.eligible_candidate_count||0)+' eligible · '+String(summary.selection_count||0)+' selected · '+String(summary.deliberate_no_selection_count||0)+' deliberate no-selections.';
      attentionAgendaCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · one bounded handoff maximum · no private subject, provider, browsing, file, action, model, approval, promotion, certification, or consciousness claim.'; return true;
    }} catch (_error) {{ attentionAgendaCheckpointState.textContent='unavailable'; attentionAgendaCheckpointState.dataset.state='degraded'; attentionAgendaCheckpointSummary.textContent='Attention-agenda checkpoint evidence is unavailable; established privacy and authority boundaries remain unchanged.'; return false; }}
  }}


  async function loadAttentionIntentionCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/attention-intention-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('attention intention checkpoint unavailable');
      const summary=data.summary || {{}}; attentionIntentionCheckpointState.textContent=String(data.status || 'unknown'); attentionIntentionCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      attentionIntentionCheckpointSummary.textContent=String(summary.reflection_intake_count||0)+' reflections · '+String(summary.deliberate_silence_count||0)+' silences · '+String(summary.active_intention_count||0)+' active intentions.';
      attentionIntentionCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · attention remains separate from proposal, authorization, execution, provider use, browsing, file changes, model management, promotion, certification, and consciousness claims.'; return true;
    }} catch (_error) {{ attentionIntentionCheckpointState.textContent='unavailable'; attentionIntentionCheckpointState.dataset.state='degraded'; attentionIntentionCheckpointSummary.textContent='Attention-to-intention checkpoint evidence is unavailable; established privacy and authority boundaries remain unchanged.'; return false; }}
  }}


  async function loadPersistentInitiativeCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/persistent-initiative-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      persistentInitiativeCheckpointState.textContent=data.ok?'ready':'pending'; persistentInitiativeCheckpointState.dataset.state=data.ok?'ready':'degraded';
      const summary=data.summary || {{}}; persistentInitiativeCheckpointSummary.textContent=String(summary.candidate_count || 0)+' candidates; '+String(summary.selection_count || 0)+' selections; '+String(summary.deliberate_silence_count || 0)+' deliberate silences.';
      persistentInitiativeCheckpointDetail.textContent='Read-only structural evidence. No message was sent and no action authority changed.'; return true;
    }} catch (_error) {{ persistentInitiativeCheckpointState.textContent='unavailable'; persistentInitiativeCheckpointState.dataset.state='degraded'; return false; }}
  }}


  async function loadInitiativeLifecycleCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/initiative-lifecycle-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      initiativeLifecycleCheckpointState.textContent=data.ok?'ready':'pending'; initiativeLifecycleCheckpointState.dataset.state=data.ok?'ready':'degraded';
      const summary=data.summary || {{}}; initiativeLifecycleCheckpointSummary.textContent=String(summary.surface_receipt_count || 0)+' surface receipts; '+String(summary.response_outcome_count || 0)+' response outcomes; '+String(summary.terminal_outcome_count || 0)+' terminal.';
      initiativeLifecycleCheckpointDetail.textContent='Read-only structural evidence. No message was generated, sent, retried, or authorized.'; return true;
    }} catch (_error) {{ initiativeLifecycleCheckpointState.textContent='unavailable'; initiativeLifecycleCheckpointState.dataset.state='degraded'; return false; }}
  }}


  async function loadLongHorizonObjectiveCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/long-horizon-objective-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('objective checkpoint unavailable');
      const summary=data.summary || {{}}; longHorizonObjectiveCheckpointState.textContent=String(data.status || 'unknown'); longHorizonObjectiveCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      longHorizonObjectiveCheckpointSummary.textContent=String(summary.objective_count || 0)+' objectives · '+String(summary.review_selection_count || 0)+' reviews · '+String(summary.deliberate_no_selection_count || 0)+' deliberate no-selections.';
      longHorizonObjectiveCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · objective remains separate from proposal, authorization, and execution.'; return true;
    }} catch (_error) {{ longHorizonObjectiveCheckpointState.textContent='unavailable'; longHorizonObjectiveCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadLongHorizonFollowThroughCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/long-horizon-follow-through-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('long-horizon follow-through checkpoint unavailable');
      const summary=data.summary || {{}}; const continuity=summary.objective_continuity || {{}}; const planning=summary.planning_and_progress || {{}}; const lifecycle=summary.conflict_completion_and_abandonment || {{}};
      longHorizonFollowThroughCheckpointState.textContent=String(data.status || 'unknown'); longHorizonFollowThroughCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      longHorizonFollowThroughCheckpointSummary.textContent=String(continuity.objective_count || 0)+' objectives · '+String(planning.milestone_count || 0)+' milestones · '+String(planning.progress_claim_count || 0)+' progress claims · '+String(lifecycle.lifecycle_review_count || 0)+' lifecycle reviews.';
      longHorizonFollowThroughCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · objective, milestone, progress, proposal, authorization, execution, and verified completion remain separate.'; return true;
    }} catch (_error) {{ longHorizonFollowThroughCheckpointState.textContent='unavailable'; longHorizonFollowThroughCheckpointState.dataset.state='degraded'; longHorizonFollowThroughCheckpointSummary.textContent='The v1109.9 checkpoint is unavailable; established privacy and authority boundaries remain unchanged.'; return false; }}
  }}


  async function loadIdentityExpressionLifecycleCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/identity-expression-lifecycle-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('identity expression checkpoint unavailable');
      const summary=data.summary || {{}}; identityExpressionLifecycleCheckpointState.textContent=String(data.status || 'unknown'); identityExpressionLifecycleCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      identityExpressionLifecycleCheckpointSummary.textContent=String(summary.claim_count || 0)+' claims · '+String(summary.reflection_influence_count || 0)+' reflection lenses · '+String(summary.communication_decision_count || 0)+' communication decisions.';
      identityExpressionLifecycleCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · identity, reflection, message delivery, proposal, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ identityExpressionLifecycleCheckpointState.textContent='unavailable'; identityExpressionLifecycleCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadCuriosityContinuityCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/curiosity-continuity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('curiosity checkpoint unavailable');
      const summary=data.summary || {{}}; curiosityContinuityCheckpointState.textContent=String(data.status || 'unknown'); curiosityContinuityCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      curiosityContinuityCheckpointSummary.textContent=String(summary.candidate_count || 0)+' candidates · '+String(summary.selection_count || 0)+' selected · '+String(summary.no_selection_count || 0)+' deliberate non-inquiry outcomes.';
      curiosityContinuityCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · curiosity, inquiry, intention, proposal, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ curiosityContinuityCheckpointState.textContent='unavailable'; curiosityContinuityCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadCuriosityLifecycleCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/curiosity-lifecycle-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('curiosity lifecycle checkpoint unavailable');
      const summary=data.summary || {{}}; curiosityLifecycleCheckpointState.textContent=String(data.status || 'unknown'); curiosityLifecycleCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      curiosityLifecycleCheckpointSummary.textContent=String(summary.promotion_count || 0)+' inquiry candidates · '+String(summary.lifecycle_decision_count || 0)+' lifecycle decisions.';
      curiosityLifecycleCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · curiosity, inquiry candidates, active inquiry, browsing, prompts, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ curiosityLifecycleCheckpointState.textContent='unavailable'; curiosityLifecycleCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadBehavioralEvidenceCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/behavioral-evidence-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('behavioral evidence checkpoint unavailable');
      const summary=data.summary || {{}}; behavioralEvidenceCheckpointState.textContent=String(data.status || 'unknown'); behavioralEvidenceCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      behavioralEvidenceCheckpointSummary.textContent=String(summary.outcome_count || 0)+' outcomes · '+String(summary.attribution_count || 0)+' attributions · '+String(summary.ambiguous_or_unresolved_count || 0)+' uncertain.';
      behavioralEvidenceCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · outcome, attribution, evaluation, adaptation proposal, approval, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ behavioralEvidenceCheckpointState.textContent='unavailable'; behavioralEvidenceCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadBehavioralSelfEvaluationCheckpoint() {{
    const state=document.getElementById('behavioral-self-evaluation-checkpoint-state');
    const summary=document.getElementById('behavioral-self-evaluation-checkpoint-summary');
    const detail=document.getElementById('behavioral-self-evaluation-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/behavioral-self-evaluation-checkpoint');
      const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('behavioral self-evaluation checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state='ready';
      const x=data.summary||{{}}; summary.textContent=`${{x.supported_pattern_count||0}} supported patterns, ${{x.suppressed_pattern_count||0}} suppressed patterns, ${{x.evaluation_count||0}} evaluations, ${{x.hypothesis_count||0}} hypotheses.`;
      detail.textContent='Evidence thresholds and uncertainty remain visible; no adaptation proposal, approval, authorization, or execution.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadBehavioralAdaptationCheckpoint() {{
    const state=document.getElementById('behavioral-adaptation-checkpoint-state');
    const summary=document.getElementById('behavioral-adaptation-checkpoint-summary');
    const detail=document.getElementById('behavioral-adaptation-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/behavioral-adaptation-checkpoint');
      const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('behavioral adaptation checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state='ready';
      const x=data.summary||{{}}; summary.textContent=`${{x.proposal_count||0}} proposals, ${{x.pending_review_count||0}} pending review, ${{x.lifecycle_decision_count||0}} lifecycle decisions, ${{x.weight_receipt_count||0}} bounded receipts.`;
      detail.textContent='Operator confirmation remains mandatory; no proposal, approval, or receipt authorizes behavioral mutation or execution.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadReflectiveBehavioralLearningCheckpoint() {{
    const state=document.getElementById('reflective-behavioral-learning-checkpoint-state');
    const summary=document.getElementById('reflective-behavioral-learning-checkpoint-summary');
    const detail=document.getElementById('reflective-behavioral-learning-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/reflective-behavioral-learning-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('reflective behavioral learning checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const all=data.summary||{{}}; const ev=all.behavioral_evidence||{{}}; const se=all.behavioral_self_evaluation||{{}}; const ar=all.behavioral_adaptation_review||{{}};
      summary.textContent=`${{ev.outcome_count||0}} outcomes, ${{ev.attribution_count||0}} attributions, ${{se.supported_pattern_count||0}} supported patterns, ${{se.hypothesis_count||0}} hypotheses, ${{ar.proposal_count||0}} proposals.`;
      detail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · evidence, evaluation, proposal, approval, authorization, application, rollback, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadActiveInquiryCheckpoint() {{
    const state=document.getElementById('active-inquiry-checkpoint-state');
    const summary=document.getElementById('active-inquiry-checkpoint-summary');
    const detail=document.getElementById('active-inquiry-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/active-inquiry-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('active inquiry checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.record_count||0}} records, ${{x.active_count||0}} active internally, ${{x.pending_count||0}} pending, ${{x.arbitration_count||0}} arbitration decisions.`;
      detail.textContent='Inquiry records remain structural and non-browsing; research proposal, approval, authorization, provider contact, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadInquiryEvidenceGovernanceCheckpoint() {{
    const state=document.getElementById('inquiry-evidence-governance-state');
    const summary=document.getElementById('inquiry-evidence-governance-summary');
    const detail=document.getElementById('inquiry-evidence-governance-detail');
    try {{
      const response=await fetch('/api/cognition/inquiry-evidence-governance-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('inquiry evidence governance checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.proposal_count||0}} proposals, ${{x.pending_review_count||0}} pending review, ${{x.governance_decision_count||0}} source-governance decisions.`;
      detail.textContent='Evidence acquisition remains proposal-only; operator review grants neither authorization, browsing, provider contact, prompting, nor execution.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadBoundedInquiryCheckpoint() {{
    const state=document.getElementById('bounded-inquiry-checkpoint-state');
    const summary=document.getElementById('bounded-inquiry-checkpoint-summary');
    const detail=document.getElementById('bounded-inquiry-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/bounded-inquiry-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('bounded inquiry checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const all=data.summary||{{}}; const active=all.active_inquiry_continuity||{{}}; const governance=all.inquiry_evidence_governance||{{}}; const resolution=all.inquiry_resolution_continuity||{{}};
      summary.textContent=`${{active.record_count||0}} inquiry records, ${{governance.proposal_count||0}} acquisition proposals, ${{resolution.receipt_count||0}} evidence receipts, ${{resolution.resolution_count||0}} resolution decisions.`;
      detail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · inquiry, proposal, approval, authorization, evidence acquisition, belief revision, messaging, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}




  async function loadDeliberativeDecisionReviewCheckpoint() {{
    const state=document.getElementById('deliberative-decision-review-checkpoint-state');
    const summary=document.getElementById('deliberative-decision-review-checkpoint-summary');
    const detail=document.getElementById('deliberative-decision-review-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/deliberative-decision-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('deliberative decision review unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.commitment_count||0}} commitments, ${{x.candidate_count||0}} intention candidates, ${{x.outcome_count||0}} outcome receipts.`;
      detail.textContent='Candidates and outcome triggers remain non-authorizing; intention, proposal, approval, authorization, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}
  async function loadReflectivePlanningDeliberativeChoiceCheckpoint() {{
    const state=document.getElementById('reflective-planning-deliberative-choice-checkpoint-state');
    const summary=document.getElementById('reflective-planning-deliberative-choice-checkpoint-summary');
    const detail=document.getElementById('reflective-planning-deliberative-choice-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/reflective-planning-deliberative-choice-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('reflective planning checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; const options=x.deliberative_option_continuity||{{}}; const commitments=x.decision_commitment_lifecycle||{{}}; const follow=x.deliberative_decision_follow_through||{{}};
      summary.textContent=`${{options.option_count||0}} options, ${{commitments.commitment_count||0}} commitments, ${{follow.candidate_count||0}} intention candidates.`;
      detail.textContent='Read-only consolidation; option, decision, intention candidate, intention, proposal, approval, authorization, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}
  async function loadDecisionCommitmentCheckpoint() {{
    const state=document.getElementById('decision-commitment-checkpoint-state');
    const summary=document.getElementById('decision-commitment-checkpoint-summary');
    const detail=document.getElementById('decision-commitment-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/decision-commitment-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('decision commitment checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.commitment_count||0}} commitments, ${{x.active_commitment_count||0}} active, ${{x.replaced_commitment_count||0}} replaced.`;
      detail.textContent='Commitments remain non-authorizing; intention, proposal, approval, authorization, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}
  async function loadCognitiveLoadContinuityCheckpoint() {{
    const state=document.getElementById('cognitive-load-continuity-checkpoint-state');
    const summary=document.getElementById('cognitive-load-continuity-checkpoint-summary');
    const detail=document.getElementById('cognitive-load-continuity-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/cognitive-load-continuity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('cognitive load checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.demand_count||0}} demands, ${{x.candidate_count||0}} candidates, ${{x.allocation_count||0}} allocations.`;
      detail.textContent='Demand admission remains non-authorizing; attention, intention, decision, proposal, approval, authorization, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}


  async function loadCognitiveCoordinationReviewCheckpoint() {{
    const state=document.getElementById('cognitive-coordination-review-checkpoint-state');
    const summary=document.getElementById('cognitive-coordination-review-checkpoint-summary');
    const detail=document.getElementById('cognitive-coordination-review-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/cognitive-coordination-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('cognitive coordination review unavailable');
      state.textContent=data.status||'ready'; state.dataset.state='ready'; const x=data.summary||{{}};
      summary.textContent=`${{x.work_item_count||0}} work items, ${{x.outcome_count||0}} outcomes; ${{x.effectiveness_status||'unknown'}}.`;
      detail.textContent='Read-only review; no schedule mutation, attention selection, adaptation, authorization, or execution.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent=String(error); }}
  }}








  async function loadEpistemicMaintenanceBeliefRevisionGovernanceCheckpoint() {{
    const state=document.getElementById('epistemic-maintenance-belief-revision-governance-checkpoint-state');
    const summary=document.getElementById('epistemic-maintenance-belief-revision-governance-checkpoint-summary');
    const detail=document.getElementById('epistemic-maintenance-belief-revision-governance-checkpoint-detail');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/epistemic-maintenance-belief-revision-governance-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('epistemic maintenance checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; const intake=x.belief_reconsideration_intake||{{}}; const deliberation=x.belief_revision_deliberation||{{}}; const continuity=x.belief_continuity_review||{{}};
      summary.textContent=data.headline||'Epistemic maintenance checkpoint available.';
      detail.textContent=`Signals ${{intake.signal_count||0}}; deliberation sessions ${{deliberation.session_count||0}}; revision records ${{continuity.revision_count||0}}. Read-only and authority-inert.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Epistemic maintenance checkpoint unavailable.'; }}
  }}

  async function loadBeliefContinuityReviewCheckpoint() {{
    const state=document.getElementById('belief-continuity-review-checkpoint-state');
    const summary=document.getElementById('belief-continuity-review-checkpoint-summary');
    const detail=document.getElementById('belief-continuity-review-checkpoint-detail');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/belief-continuity-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('belief continuity review unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.revision_count||0}} revision records across ${{x.reviewed_belief_count||0}} reviewed beliefs.`;
      detail.textContent='Read-only continuity review; historical lineage remains visible and policy proposals remain unapplied.';
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Belief continuity review unavailable.'; }}
  }}

  async function loadBeliefRevisionDeliberationCheckpoint() {{
    const state=document.getElementById('belief-revision-deliberation-checkpoint-state');
    const summary=document.getElementById('belief-revision-deliberation-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/belief-revision-deliberation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('belief revision deliberation unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.session_count||0}} deliberation sessions; beliefs remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Belief revision deliberation unavailable.'; }}
  }}



  async function loadEpistemicCoherenceKnowledgeBeliefIntegrationCheckpoint() {{
    const state=document.getElementById('epistemic-coherence-knowledge-belief-integration-checkpoint-state');
    const summary=document.getElementById('epistemic-coherence-knowledge-belief-integration-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/epistemic-coherence-knowledge-belief-integration-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('epistemic coherence and knowledge-belief integration unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      const intake=x.epistemic_coherence_intake||{{}}; const integration=x.knowledge_belief_integration||{{}};
      summary.textContent=`${{intake.signal_count||0}} signals, ${{intake.candidate_count||0}} candidates, and ${{integration.outcome_count||0}} coherence outcomes; records remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Consolidated epistemic coherence checkpoint unavailable.'; }}
  }}

  async function loadKnowledgeBeliefIntegrationCheckpoint() {{
    const state=document.getElementById('knowledge-belief-integration-checkpoint-state');
    const summary=document.getElementById('knowledge-belief-integration-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/knowledge-belief-integration-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('knowledge-belief integration unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.outcome_count||0}} coherence outcomes across ${{x.reviewed_candidate_count||0}} reviewed candidates; records remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Knowledge-belief integration review unavailable.'; }}
  }}

  async function loadEpistemicCoherenceDeliberationCheckpoint() {{
    const state=document.getElementById('epistemic-coherence-deliberation-checkpoint-state');
    const summary=document.getElementById('epistemic-coherence-deliberation-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/epistemic-coherence-deliberation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('epistemic coherence deliberation unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.session_count||0}} coherence deliberation sessions; underlying records remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Epistemic coherence deliberation unavailable.'; }}
  }}


  async function loadSelfModelIntegrityIdentityClaimGovernanceCheckpoint() {{
    const state=document.getElementById('self-model-integrity-identity-claim-governance-checkpoint-state');
    const summary=document.getElementById('self-model-integrity-identity-claim-governance-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/self-model-integrity-identity-claim-governance-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('self-model integrity and identity claim governance unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      const intake=x.self_model_integrity_intake||{{}}; const continuity=x.self_model_continuity_review||{{}};
      summary.textContent=`${{intake.signal_count||0}} integrity signals, ${{intake.candidate_count||0}} review candidates, and ${{continuity.revision_count||0}} identity revision records; claims remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Consolidated self-model integrity checkpoint unavailable.'; }}
  }}

  async function loadSelfModelContinuityReviewCheckpoint() {{
    const state=document.getElementById('self-model-continuity-review-checkpoint-state');
    const summary=document.getElementById('self-model-continuity-review-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/self-model-continuity-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('self-model continuity review unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.revision_count||0}} identity revision records across ${{x.reviewed_claim_count||0}} reviewed claims; history remains preserved.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Self-model continuity review unavailable.'; }}
  }}

  async function loadSelfModelRevisionDeliberationCheckpoint() {{
    const state=document.getElementById('self-model-revision-deliberation-checkpoint-state');
    const summary=document.getElementById('self-model-revision-deliberation-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/self-model-revision-deliberation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('self-model revision deliberation unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.session_count||0}} bounded deliberation sessions; identity and self-model claims remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Self-model revision deliberation unavailable.'; }}
  }}


  async function loadMotivationalContinuityEndogenousDriveRegulationCheckpoint() {{
    const state=document.getElementById('motivational-continuity-endogenous-drive-regulation-checkpoint-state'); const summary=document.getElementById('motivational-continuity-endogenous-drive-regulation-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/motivational-continuity-endogenous-drive-regulation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; const intake=x.motivational_continuity_intake||{{}}; const review=x.motivational_continuity_review||{{}}; summary.textContent=`${{intake.signal_count||0}} signals, ${{intake.candidate_count||0}} candidates, ${{review.outcome_count||0}} durable outcomes; governance remains read-only.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Motivational continuity governance checkpoint unavailable.'; }}
  }}




  async function loadRealReflectiveCognitionCheckpoint() {{
    const state=document.getElementById('real-reflective-cognition-checkpoint-state');
    const summary=document.getElementById('real-reflective-cognition-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/real-reflective-cognition-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if(!response.ok||data.ok===false)throw new Error('unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.subject_count||0}} subjects, ${{x.session_count||0}} model-backed sessions, ${{x.execution_count||0}} execution records, and ${{x.outcome_count||0}} durable outcomes; downstream authority remains blocked.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Real Reflective Cognition checkpoint unavailable.'; }}
  }}

  async function loadReflectiveIntegrationReliabilityCheckpoint() {{
    const state=document.getElementById('reflective-integration-reliability-checkpoint-state');
    const summary=document.getElementById('reflective-integration-reliability-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/reflective-integration-reliability-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if(!response.ok||data.ok===false)throw new Error('unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.outcome_count||0}} durable outcomes, ${{x.review_count||0}} reliability reviews, and ${{x.recommendation_count||0}} communication recommendations; downstream authority remains blocked.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Reflection integration and reliability checkpoint unavailable.'; }}
  }}

  async function loadSelectedAttentionReflectiveFocusGovernanceCheckpoint() {{
    const state=document.getElementById('selected-attention-reflective-focus-governance-checkpoint-state');
    const summary=document.getElementById('selected-attention-reflective-focus-governance-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/selected-attention-reflective-focus-governance-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if(!response.ok||data.ok===false)throw new Error('unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.attention_count||0}} selected-attention records, ${{x.focus_count||0}} focus states, ${{x.session_count||0}} bounded sessions, and ${{x.outcome_count||0}} durable outcomes; downstream authority remains blocked.`;
    }} catch(error) {{
      state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Selected attention and reflective focus governance checkpoint unavailable.';
    }}
  }}


  async function loadReflectiveAttentionSalienceGovernanceCheckpoint() {{
    const focusDelibState=document.getElementById('reflective-focus-deliberation-checkpoint-state'); const focusDelibSummary=document.getElementById('reflective-focus-deliberation-checkpoint-summary'); if(focusDelibState) {{ try {{ const response=await fetch('/api/cognition/reflective-focus-deliberation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); focusDelibState.textContent=data.status||'ready'; focusDelibState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; focusDelibSummary.textContent=`${{x.session_count||0}} bounded focus sessions; downstream authority remains blocked.`; }} catch(error) {{ focusDelibState.textContent='unavailable'; focusDelibState.dataset.state='blocked'; }} }}
    const focusContinuityState=document.getElementById('reflective-focus-continuity-review-checkpoint-state'); const focusContinuitySummary=document.getElementById('reflective-focus-continuity-review-checkpoint-summary'); if(focusContinuityState) {{ try {{ const response=await fetch('/api/cognition/reflective-focus-continuity-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); focusContinuityState.textContent=data.status||'ready'; focusContinuityState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; focusContinuitySummary.textContent=`${{x.outcome_count||0}} focus outcomes; ${{x.reviewed_attention_count||0}} attention lineages reviewed; downstream authority remains blocked.`; }} catch(error) {{ focusContinuityState.textContent='unavailable'; focusContinuityState.dataset.state='blocked'; }} }}
    const selectedAttentionState=document.getElementById('selected-attention-focus-intake-checkpoint-state'); const selectedAttentionSummary=document.getElementById('selected-attention-focus-intake-checkpoint-summary');
    if(selectedAttentionState) {{ try {{ const response=await fetch('/api/cognition/selected-attention-focus-intake-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); selectedAttentionState.textContent=data.status||'ready'; selectedAttentionState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; selectedAttentionSummary.textContent=`${{x.attention_count||0}} selected-attention records and ${{x.focus_count||0}} reflective-focus states; downstream authority remains blocked.`; }} catch(error) {{ selectedAttentionState.textContent='unavailable'; selectedAttentionState.dataset.state='blocked'; selectedAttentionSummary.textContent='Selected attention and reflective focus intake checkpoint unavailable.'; }} }}
    const state=document.getElementById('reflective-attention-salience-governance-checkpoint-state'); const summary=document.getElementById('reflective-attention-salience-governance-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/reflective-attention-salience-governance-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; summary.textContent=`${{x.signal_count||0}} signals, ${{x.candidate_count||0}} candidates, ${{x.session_count||0}} bounded sessions, ${{x.outcome_count||0}} durable outcomes; governance remains authority-inert.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Reflective attention and salience governance checkpoint unavailable.'; }}
  }}


  async function loadReflectiveAttentionContinuityReviewCheckpoint() {{
    const state=document.getElementById('reflective-attention-continuity-review-checkpoint-state'); const summary=document.getElementById('reflective-attention-continuity-review-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/reflective-attention-continuity-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; summary.textContent=`${{x.outcome_count||0}} durable outcomes across ${{x.reviewed_candidate_count||0}} reviewed candidates; continuity remains authority-inert.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Reflective attention continuity review unavailable.'; }}
  }}

  async function loadReflectiveAttentionDeliberationCheckpoint() {{
    const state=document.getElementById('reflective-attention-deliberation-checkpoint-state'); const summary=document.getElementById('reflective-attention-deliberation-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/reflective-attention-deliberation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; summary.textContent=`${{x.session_count||0}} bounded sessions; deterministic comparison remains authority-inert.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Reflective attention deliberation unavailable.'; }}
  }}

  async function loadReflectiveAttentionSalienceIntakeCheckpoint() {{
    const state=document.getElementById('reflective-attention-salience-intake-checkpoint-state'); const summary=document.getElementById('reflective-attention-salience-intake-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/reflective-attention-salience-intake-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; summary.textContent=`${{x.signal_count||0}} salience signals, ${{x.candidate_count||0}} attention-review candidates, ${{x.suppressed_candidate_count||0}} restrained candidates; authority remains unchanged.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Reflective attention and salience intake unavailable.'; }}
  }}

  async function loadMotivationalContinuityIntakeCheckpoint() {{
    const state=document.getElementById('motivational-continuity-intake-checkpoint-state'); const summary=document.getElementById('motivational-continuity-intake-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/motivational-continuity-intake-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; summary.textContent=`${{x.signal_count||0}} pressure signals, ${{x.candidate_count||0}} drive candidates, ${{x.suppressed_candidate_count||0}} false-urgency suppressions; authority remains unchanged.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Motivational continuity intake unavailable.'; }}
  }}

  async function loadGoalContinuityReviewCheckpoint() {{
    const state=document.getElementById('goal-continuity-review-checkpoint-state'); const summary=document.getElementById('goal-continuity-review-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/goal-continuity-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; summary.textContent=`${{x.outcome_count||0}} durable outcomes across ${{x.reviewed_objective_count||0}} reviewed objectives; history remains preserved.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Goal continuity review unavailable.'; }}
  }}

  async function loadGoalCoherenceLongHorizonObjectiveGovernanceCheckpoint() {{
    const state=document.getElementById('goal-coherence-long-horizon-objective-governance-checkpoint-state'); const summary=document.getElementById('goal-coherence-long-horizon-objective-governance-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/goal-coherence-long-horizon-objective-governance-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; const intake=x.objective_coherence_intake||{{}}; const continuity=x.goal_continuity_review||{{}}; summary.textContent=`${{intake.signal_count||0}} signals, ${{intake.candidate_count||0}} candidates, ${{continuity.outcome_count||0}} durable outcomes; governance remains read-only.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Goal coherence governance checkpoint unavailable.'; }}
  }}

  async function loadObjectiveCoherenceDeliberationCheckpoint() {{
    const state=document.getElementById('objective-coherence-deliberation-checkpoint-state'); const summary=document.getElementById('objective-coherence-deliberation-checkpoint-summary'); if(!state)return;
    try {{ const response=await fetch('/api/cognition/objective-coherence-deliberation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload; if(!response.ok||data.ok===false)throw new Error('unavailable'); state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; summary.textContent=`${{x.session_count||0}} bounded deliberation sessions; objectives and milestones remain unchanged.`; }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Goal coherence deliberation unavailable.'; }}
  }}

  async function loadObjectiveCoherenceIntakeCheckpoint() {{
    const state=document.getElementById('objective-coherence-intake-checkpoint-state');
    const summary=document.getElementById('objective-coherence-intake-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/objective-coherence-intake-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('goal coherence intake unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.signal_count||0}} coherence signals and ${{x.candidate_count||0}} review candidates; objectives and milestones remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Goal coherence intake unavailable.'; }}
  }}

  async function loadSelfModelIntegrityIntakeCheckpoint() {{
    const state=document.getElementById('self-model-integrity-intake-checkpoint-state');
    const summary=document.getElementById('self-model-integrity-intake-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/self-model-integrity-intake-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('self-model integrity intake unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.signal_count||0}} integrity signals and ${{x.candidate_count||0}} review candidates; identity and self-model claims remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Self-model integrity intake unavailable.'; }}
  }}

  async function loadEpistemicCoherenceIntakeCheckpoint() {{
    const state=document.getElementById('epistemic-coherence-intake-checkpoint-state');
    const summary=document.getElementById('epistemic-coherence-intake-checkpoint-summary');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/epistemic-coherence-intake-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('epistemic coherence intake unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.signal_count||0}} coherence signals and ${{x.candidate_count||0}} review candidates; records remain unchanged.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Epistemic coherence intake unavailable.'; }}
  }}

  async function loadBeliefReconsiderationIntakeCheckpoint() {{
    const state=document.getElementById('belief-reconsideration-intake-checkpoint-state');
    const summary=document.getElementById('belief-reconsideration-intake-checkpoint-summary');
    const detail=document.getElementById('belief-reconsideration-intake-checkpoint-detail');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/belief-reconsideration-intake-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('belief reconsideration intake unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.signal_count||0}} evidence-change signals and ${{x.candidate_count||0}} reconsideration candidates.`;
      detail.textContent='Read-only intake; evidence change never revises a belief or grants approval, authorization, or execution authority.';
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Belief reconsideration intake unavailable.'; }}
  }}

  async function loadReflectiveTemporalContinuityProspectiveMemoryCheckpoint() {{
    const state=document.getElementById('reflective-temporal-continuity-prospective-memory-checkpoint-state');
    const summary=document.getElementById('reflective-temporal-continuity-prospective-memory-checkpoint-summary');
    const detail=document.getElementById('reflective-temporal-continuity-prospective-memory-checkpoint-detail');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/reflective-temporal-continuity-prospective-memory-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('reflective temporal continuity checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}}; const memory=x.prospective_memory_continuity||{{}}; const review=x.temporal_review_continuity||{{}}; const continuity=x.prospective_continuity_review||{{}};
      summary.textContent=data.headline||'Reflective temporal continuity checkpoint available.';
      detail.textContent=`Obligations ${{memory.obligation_count||0}}; review sessions ${{review.session_count||0}}; outcome evidence ${{continuity.outcome_evidence_count||0}}. Read-only and authority-inert.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Reflective temporal continuity checkpoint unavailable.'; }}
  }}

  async function loadProspectiveContinuityReviewCheckpoint() {{
    const state=document.getElementById('prospective-continuity-review-checkpoint-state');
    const summary=document.getElementById('prospective-continuity-review-checkpoint-summary');
    const detail=document.getElementById('prospective-continuity-review-checkpoint-detail');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/prospective-continuity-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      state.textContent=data.ok?'ready':'blocked'; state.dataset.state=data.ok?'ready':'blocked'; summary.textContent=data.headline||'Prospective continuity review available.'; const x=data.summary||{{}};
      detail.textContent=`Outcomes ${{x.outcome_evidence_count||0}}; reliability reviews ${{x.reliability_review_count||0}}; rescheduling proposals ${{x.rescheduling_proposal_count||0}}. Read-only.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Prospective continuity review unavailable.'; }}
  }}

  async function loadTemporalReviewCheckpoint() {{
    const state=document.getElementById('temporal-review-checkpoint-state');
    const summary=document.getElementById('temporal-review-checkpoint-summary');
    const detail=document.getElementById('temporal-review-checkpoint-detail');
    if(!state)return;
    try {{
      const response=await fetch('/api/cognition/temporal-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      state.textContent=data.ok?'ready':'blocked'; state.dataset.state=data.ok?'ready':'blocked'; summary.textContent=data.headline||'Temporal review checkpoint available.'; const x=data.summary||{{}};
      detail.textContent=`Sessions ${{x.session_count||0}}; reconciliations ${{x.reconciliation_count||0}}; conflicts ${{x.conflict_count||0}}. Read-only.`;
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent='Temporal review checkpoint unavailable.'; }}
  }}

  async function loadProspectiveMemoryContinuityCheckpoint() {{
    const state=document.getElementById('prospective-memory-continuity-checkpoint-state');
    const summary=document.getElementById('prospective-memory-continuity-checkpoint-summary');
    const detail=document.getElementById('prospective-memory-continuity-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/prospective-memory-continuity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('prospective memory checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.obligation_count||0}} obligations, ${{x.eligibility_count||0}} eligibility records, ${{x.missed_window_count||0}} missed windows.`;
      detail.textContent='Read-only temporal continuity; timestamps never create notification, approval, authorization, or execution authority.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadCognitiveHomeostasisSustainableCognitionCheckpoint() {{
    const state=document.getElementById('cognitive-homeostasis-sustainable-cognition-checkpoint-state');
    const summary=document.getElementById('cognitive-homeostasis-sustainable-cognition-checkpoint-summary');
    const detail=document.getElementById('cognitive-homeostasis-sustainable-cognition-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/cognitive-homeostasis-sustainable-cognition-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('cognitive homeostasis and sustainable cognition checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; const home=x.cognitive_homeostasis_continuity||{{}}; const recovery=x.cognitive_recovery_continuity||{{}}; const review=x.cognitive_sustainability_review||{{}};
      summary.textContent=`${{home.signal_count||0}} pressure signals, ${{recovery.recovery_record_count||0}} recovery records, ${{review.pattern_count||0}} overload patterns.`;
      detail.textContent='Read-only consolidation; homeostasis evidence cannot change schedules, pause work, adapt behavior, authorize, or execute.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadCognitiveSustainabilityReviewCheckpoint() {{
    const state=document.getElementById('cognitive-sustainability-review-checkpoint-state');
    const summary=document.getElementById('cognitive-sustainability-review-checkpoint-summary');
    const detail=document.getElementById('cognitive-sustainability-review-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/cognitive-sustainability-review-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('cognitive sustainability review unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded'; const x=data.summary||{{}};
      summary.textContent=`${{x.pattern_count||0}} overload patterns, ${{x.drift_review_count||0}} drift reviews.`;
      detail.textContent='Read-only sustainability review; no schedule mutation, adaptation, authorization, or execution.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadCognitiveRecoveryContinuityCheckpoint() {{
    const state=document.getElementById('cognitive-recovery-continuity-checkpoint-state');
    const summary=document.getElementById('cognitive-recovery-continuity-checkpoint-summary');
    const detail=document.getElementById('cognitive-recovery-continuity-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/cognitive-recovery-continuity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('cognitive recovery checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.recovery_record_count||0}} recovery records, ${{x.window_outcome_count||0}} sustainable-window outcomes.`;
      detail.textContent='Read-only recovery continuity; records cannot mutate schedules, pause work, adapt behavior, authorize, or execute.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadCognitiveHomeostasisContinuityCheckpoint() {{
    const state=document.getElementById('cognitive-homeostasis-continuity-checkpoint-state');
    const summary=document.getElementById('cognitive-homeostasis-continuity-checkpoint-summary');
    const detail=document.getElementById('cognitive-homeostasis-continuity-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/cognitive-homeostasis-continuity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('cognitive homeostasis checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.signal_count||0}} pressure signals, ${{x.review_count||0}} recovery reviews.`;
      detail.textContent='Read-only homeostasis review; recommendations cannot change schedules, pause work, select attention, authorize, or execute.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadInternalCoordinationCognitiveLoadGovernanceCheckpoint() {{
    const state=document.getElementById('internal-coordination-cognitive-load-governance-checkpoint-state');
    const summary=document.getElementById('internal-coordination-cognitive-load-governance-checkpoint-summary');
    const detail=document.getElementById('internal-coordination-cognitive-load-governance-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/internal-coordination-cognitive-load-governance-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('internal coordination checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; const load=x.cognitive_load_continuity||{{}}; const work=x.cognitive_work_continuity||{{}}; const review=x.cognitive_coordination_review||{{}};
      summary.textContent=`${{load.demand_count||0}} demands, ${{work.work_item_count||0}} work items, ${{review.outcome_count||0}} outcomes.`;
      detail.textContent='Read-only consolidation; scheduling review cannot select attention, adapt behavior, authorize, browse, message, modify, or execute.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadCognitiveWorkContinuityCheckpoint() {{
    const state=document.getElementById('cognitive-work-continuity-checkpoint-state');
    const summary=document.getElementById('cognitive-work-continuity-checkpoint-summary');
    const detail=document.getElementById('cognitive-work-continuity-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/cognitive-work-continuity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('cognitive work checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state='ready';
      const counts=(data.summary||{{}}).state_counts||{{}}; summary.textContent=`${{(data.summary||{{}}).work_item_count||0}} work items; scheduled ${{counts.scheduled||0}}, resumable ${{counts.resumable||0}}, retired ${{counts.retired||0}}.`;
      detail.textContent='Read-only structural continuity; no attention selection, intention, proposal, approval, authorization, or execution.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='blocked'; summary.textContent=String(error); }}
  }}

  async function loadDeliberativeContinuityCheckpoint() {{
    const state=document.getElementById('deliberative-continuity-checkpoint-state');
    const summary=document.getElementById('deliberative-continuity-checkpoint-summary');
    const detail=document.getElementById('deliberative-continuity-checkpoint-detail');
    try {{
      const response=await fetch('/api/cognition/deliberative-continuity-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      if (!response.ok || data.ok===false) throw new Error('deliberative continuity checkpoint unavailable');
      state.textContent=data.status||'ready'; state.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      const x=data.summary||{{}}; summary.textContent=`${{x.option_count||0}} options, ${{x.candidate_count||0}} candidates, ${{x.comparison_count||0}} comparisons.`;
      detail.textContent='Options remain structural and non-authorizing; decision, intention, proposal, approval, authorization, and execution remain separate.';
    }} catch (error) {{ state.textContent='unavailable'; state.dataset.state='error'; summary.textContent=String(error); }}
  }}

  async function loadEndogenousCuriosityCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/endogenous-curiosity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('endogenous curiosity checkpoint unavailable');
      const summary=data.summary || {{}}; const continuity=summary.curiosity_continuity || {{}}; const quality=summary.question_quality || {{}}; const lifecycle=summary.inquiry_candidate_lifecycle || {{}};
      endogenousCuriosityCheckpointState.textContent=String(data.status || 'unknown'); endogenousCuriosityCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      endogenousCuriosityCheckpointSummary.textContent=String(continuity.candidate_count || 0)+' candidates · '+String(quality.question_count || 0)+' questions · '+String(lifecycle.promotion_count || 0)+' inquiry candidates · '+String(lifecycle.lifecycle_decision_count || 0)+' lifecycle decisions.';
      endogenousCuriosityCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · curiosity, questions, inquiry candidates, active inquiry, browsing, prompts, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ endogenousCuriosityCheckpointState.textContent='unavailable'; endogenousCuriosityCheckpointState.dataset.state='degraded'; endogenousCuriosityCheckpointSummary.textContent='The v1111.9 checkpoint is unavailable; established curiosity and authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadCuriosityQualityCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/curiosity-quality-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('curiosity quality checkpoint unavailable');
      const summary=data.summary || {{}}; curiosityQualityCheckpointState.textContent=String(data.status || 'unknown'); curiosityQualityCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      curiosityQualityCheckpointSummary.textContent=String(summary.question_count || 0)+' questions · '+String(summary.decision_count || 0)+' quality decisions.';
      curiosityQualityCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · questions, inquiries, prompts, proposals, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ curiosityQualityCheckpointState.textContent='unavailable'; curiosityQualityCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadPersistentSelfModelCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/persistent-self-model-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('persistent self-model checkpoint unavailable');
      const summary=data.summary || {{}}; const continuity=summary.identity_continuity || {{}}; const revision=summary.identity_revision || {{}}; const expression=summary.identity_expression || {{}};
      persistentSelfModelCheckpointState.textContent=String(data.status || 'unknown'); persistentSelfModelCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      persistentSelfModelCheckpointSummary.textContent=String(continuity.claim_count || 0)+' claims · '+String(revision.detection_count || 0)+' change detections · '+String(revision.revision_count || 0)+' revisions · '+String(expression.communication_decision_count || 0)+' expression decisions.';
      persistentSelfModelCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · identity evidence, reflection, communication, proposal, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ persistentSelfModelCheckpointState.textContent='unavailable'; persistentSelfModelCheckpointState.dataset.state='degraded'; persistentSelfModelCheckpointSummary.textContent='The v1110.9 checkpoint is unavailable; established identity and authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadIdentityRevisionCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/identity-revision-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('identity revision checkpoint unavailable');
      const summary=data.summary || {{}}; identityRevisionCheckpointState.textContent=String(data.status || 'unknown'); identityRevisionCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      identityRevisionCheckpointSummary.textContent=String(summary.detection_count || 0)+' detections · '+String(summary.eligible_revision_count || 0)+' revision-eligible · '+String(summary.revision_count || 0)+' revisions.';
      identityRevisionCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · observation, identity, revision, intention, proposal, authorization, and execution remain separate.'; return true;
    }} catch (_error) {{ identityRevisionCheckpointState.textContent='unavailable'; identityRevisionCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadSelfModelContinuityCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/self-model-continuity-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('self-model continuity checkpoint unavailable');
      const summary=data.summary || {{}}; selfModelContinuityCheckpointState.textContent=String(data.status || 'unknown'); selfModelContinuityCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      selfModelContinuityCheckpointSummary.textContent=String(summary.claim_count || 0)+' claims · '+String(summary.active_claim_count || 0)+' active · '+String(summary.arbitration_count || 0)+' evidence reviews.';
      selfModelContinuityCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · identity remains revisable and separate from intention, proposal, authorization, and execution.'; return true;
    }} catch (_error) {{ selfModelContinuityCheckpointState.textContent='unavailable'; selfModelContinuityCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadPersistentInitiativeConsolidationCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/persistent-initiative-consolidation-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('persistent initiative checkpoint unavailable');
      const summary=data.summary || {{}}; const foundation=summary.initiative_foundation || {{}}; const lifecycle=summary.surface_response_lifecycle || {{}}; const diagnostics=summary.background_diagnostics || {{}};
      persistentInitiativeConsolidationCheckpointState.textContent=String(data.status || 'unknown'); persistentInitiativeConsolidationCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      persistentInitiativeConsolidationCheckpointSummary.textContent=String(foundation.candidate_count || 0)+' candidates · '+String(lifecycle.surface_receipt_count || 0)+' surfaces · '+String(lifecycle.response_outcome_count || 0)+' responses · '+String(diagnostics.failure_count || 0)+' background failures recorded.';
      persistentInitiativeConsolidationCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · initiative remains non-sending, retry-free, private, and unable to authorize or execute actions.'; return true;
    }} catch (_error) {{ persistentInitiativeConsolidationCheckpointState.textContent='unavailable'; persistentInitiativeConsolidationCheckpointState.dataset.state='degraded'; persistentInitiativeConsolidationCheckpointSummary.textContent='The v1108.9 checkpoint is unavailable; established initiative and authority boundaries remain unchanged.'; return false; }}
  }}

  async function loadInitiativeCommunicationCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/initiative-communication-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      initiativeCommunicationCheckpointState.textContent=data.ok?'ready':'pending'; initiativeCommunicationCheckpointState.dataset.state=data.ok?'ready':'degraded';
      const summary=data.summary || {{}}; const counts=summary.outcome_counts || {{}}; initiativeCommunicationCheckpointSummary.textContent=String(summary.proposal_count || 0)+' proposals; '+String(counts.eligible_to_surface || 0)+' eligible; '+String(counts.defer || 0)+' deferred; '+String(counts.deliberate_silence || 0)+' silences.';
      initiativeCommunicationCheckpointDetail.textContent='Read-only structural evidence. No message or notification was sent and no action authority changed.'; return true;
    }} catch (_error) {{ initiativeCommunicationCheckpointState.textContent='unavailable'; initiativeCommunicationCheckpointState.dataset.state='degraded'; return false; }}
  }}

  async function loadAutonomousAttentionIntentionCheckpoint() {{
    try {{
      const response=await fetch('/api/cognition/autonomous-attention-intention-checkpoint',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('autonomous attention intention checkpoint unavailable');
      const summary=data.summary || {{}}; const ati=summary.attention_to_intention || {{}}; autonomousAttentionIntentionCheckpointState.textContent=String(data.status || 'unknown'); autonomousAttentionIntentionCheckpointState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      autonomousAttentionIntentionCheckpointSummary.textContent=String((ati.active_intention_count||0))+' active intentions · '+String(data.check_count||0)+' structural checks.';
      autonomousAttentionIntentionCheckpointDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · privacy, provider-neutrality, source/runtime, and non-authorization boundaries remain intact.'; return true;
    }} catch (_error) {{ autonomousAttentionIntentionCheckpointState.textContent='unavailable'; autonomousAttentionIntentionCheckpointState.dataset.state='degraded'; autonomousAttentionIntentionCheckpointSummary.textContent='The v1107.9 checkpoint is unavailable; established safety boundaries remain unchanged.'; return false; }}
  }}

  async function loadIntentionLifecycleReview() {{
    try {{
      const response=await fetch('/api/cognition/intention-lifecycle-review',{{cache:'no-store'}}); const payload=await response.json(); const data=payload.data || payload;
      if (!response.ok || data.ok===false) throw new Error('intention lifecycle review unavailable');
      const summary=data.summary || {{}}; const counts=summary.lifecycle_counts || {{}}; intentionLifecycleReviewState.textContent=String(data.status || 'unknown'); intentionLifecycleReviewState.dataset.state=data.status==='ready_for_desktop_verification'?'ready':'degraded';
      intentionLifecycleReviewSummary.textContent=String(counts.active||0)+' active · '+String(counts.suspended||0)+' suspended · '+String(counts.expired||0)+' expired · '+String(summary.replaced_intention_count||0)+' replaced.';
      intentionLifecycleReviewDetail.textContent='Runtime '+(data.runtime_external?'external':'needs Desktop review')+' · reconsideration, decay, and conflict handling cannot create proposals, authorization, execution, provider use, or release authority.'; return true;
    }} catch (_error) {{ intentionLifecycleReviewState.textContent='unavailable'; intentionLifecycleReviewState.dataset.state='degraded'; intentionLifecycleReviewSummary.textContent='Intention-lifecycle evidence is unavailable; established privacy and authority boundaries remain unchanged.'; return false; }}
  }}

  async function setCognitionControl(action) {{
    const eventId='dashboard-cognition-'+action+'-'+uuid();
    try {{ const response=await fetch('/api/cognition/control',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify({{event_id:eventId,action}})}}); if (!response.ok) throw new Error('control failed'); await loadCognition(); return true; }}
    catch (_error) {{ cognitionDetail.textContent='The control change was not confirmed. Existing persisted state was left intact.'; return false; }}
  }}

  async function setCommunicationPreference(fields) {{
    try {{ const response=await fetch('/api/cognition/communication/preferences',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify(Object.assign({{event_id:'dashboard-communication-'+uuid()}},fields))}}); if (!response.ok) throw new Error('preference failed'); await loadCognition(); return true; }}
    catch (_error) {{ cognitionDetail.textContent='The communication preference change was not confirmed. Continuity was not erased.'; return false; }}
  }}

  async function markProactiveRead() {{
    if (!activeProactiveMessageId) return false;
    try {{ const response=await fetch('/api/cognition/proactive/read',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify({{event_id:'dashboard-read-'+uuid(),message_id:activeProactiveMessageId}})}}); if (!response.ok) throw new Error('read failed'); cognitionProactive.classList.add('hidden'); cognitionRead.classList.add('hidden'); activeProactiveMessageId=''; await loadCognition(); return true; }}
    catch (_error) {{ return false; }}
  }}

  async function checkProvider(trigger='manual_check') {{
    if (providerCheckInFlight) return false;
    providerCheckInFlight=true; lastProviderCheckAt=Date.now(); providerState.textContent='checking'; providerState.dataset.state='starting'; providerLabel.textContent='Running one bounded readiness check. No generation request is sent.';
    const previous=lastProviderObservedState || 'unknown';
    try {{
      const response = await fetch('/api/local-model/readiness', {{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify({{previous_state:previous,recovery_trigger:trigger}})}}); const payload = await response.json(); const data = payload.data || payload; const availability=data.availability || {{}};
      const observed=String(availability.observed_state || availability.state || data.readiness_state || data.availability_state || data.status || 'unknown');
      const ready=!!(availability.generation_available || (data.service_available && data.generation_model_available!==false) || observed==='ready');
      providerReturned=ready && !['ready','recovering','returned'].includes(previous);
      lastProviderObservedState=ready?'ready':observed; try {{ localStorage.setItem('eidolon.first-use.provider-state.v1103',lastProviderObservedState); }} catch (_error) {{}}
      providerState.textContent=providerReturned?'returned':(ready?'ready':observed); providerState.dataset.state=ready?'ready':'unavailable';
      if (providerReturned) providerLabel.textContent='Provider returned. Your draft is intact. No message was replayed or sent automatically. Send explicitly when ready.';
      else if (ready) providerLabel.textContent='Configured generation service is ready. Sending remains explicit.';
      else providerLabel.textContent='Provider is not ready. Conversation history, switching, scrolling, and drafts remain local and usable.';
      return ready;
    }} catch (_error) {{ lastProviderObservedState='unavailable'; providerState.textContent='unavailable'; providerState.dataset.state='unavailable'; providerLabel.textContent='Provider readiness could not be checked. Local conversation state remains usable. No message was replayed or sent automatically.'; return false; }}
    finally {{ providerCheckInFlight=false; }}
  }}

  async function cancelActiveOperation() {{
    if (!activeOperationId || !coordination.is_owner) return false;
    cancelActive.disabled=true; setStatus('Requesting cancellation for this exact response…','starting');
    try {{
      const response=await fetch('/api/dashboard-chat/cancel',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify(Object.assign({{operation_id:activeOperationId}},mutationFields('cancel-'+uuid())))}});
      const payload=await response.json(); if (payload.coordination) applyCoordination(payload.coordination);
      if (!response.ok || payload.ok===false) throw new Error(payload.error || payload.message || 'Cancellation could not be confirmed');
      const reconciliation=payload.operation_reconciliation || {{}};
      setStatus(reconciliation.completion_won_before_cancellation ? 'The reply completed before cancellation won.' : 'Cancellation requested. A late result cannot overwrite terminal truth.','degraded');
      return true;
    }} catch (_error) {{ setStatus('Cancellation is uncertain. No retry or second provider request was started.','degraded'); return false; }}
  }}

  async function takeConversationControl() {{
    if (coordination.is_owner || sending) return false;
    takeControl.disabled=true;
    try {{
      const response=await fetch('/api/dashboard-chat/coordination',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify({{action:'acquire',tab_id:identity.tab_id,browser_id:identity.browser_id,instance_nonce:identity.instance_nonce,lease_token:coordination.lease_token || '',visible:!document.hidden}})}});
      const payload=await response.json(); if (!response.ok) throw new Error(payload.error || 'Ownership recovery failed'); applyCoordination(payload);
      setStatus(payload.is_owner ? 'This tab now controls conversation changes.' : 'Another active tab still owns conversation changes. Nothing was sent.','ready');
      return !!payload.is_owner;
    }} catch (_error) {{ setStatus('Ownership recovery failed safely. This tab remains read-only.','degraded'); return false; }}
    finally {{ takeControl.disabled=coordination.is_owner || sending; }}
  }}

  async function heartbeatOwnership() {{
    if (!coordination.lease_token || !coordination.is_owner) return;
    try {{
      const response=await fetch('/api/dashboard-chat/coordination',{{method:'POST',headers:{{'Content-Type':'application/json'}},cache:'no-store',body:JSON.stringify({{action:'heartbeat',tab_id:identity.tab_id,lease_token:coordination.lease_token,instance_nonce:identity.instance_nonce,visible:!document.hidden}})}});
      if (response.ok) applyCoordination(await response.json());
    }} catch (_error) {{ ownershipDetail.textContent='Ownership heartbeat is uncertain. Mutations remain fenced until reconciliation.'; }}
  }}

  function requestComposerSend(event) {{
    if (keyboardSubmitLatch || sending) {{ if (event) event.preventDefault(); return false; }}
    keyboardSubmitLatch=true; if (event) event.preventDefault();
    Promise.resolve().then(() => {{ keyboardSubmitLatch=false; }});
    sendMessage(); return true;
  }}
  message.addEventListener('compositionstart', () => {{ compositionActive=true; }});
  message.addEventListener('compositionend', () => {{ compositionActive=false; }});
  message.addEventListener('input', () => {{ draftDirty=true; clearTimeout(draftTimer); draftTimer=setTimeout(saveDraft,700); }});
  log.addEventListener('scroll', () => {{ captureScrollPresentation(); clearTimeout(presentationSaveTimer); presentationSaveTimer=setTimeout(savePresentation,300); }}, {{passive:true}});
  message.addEventListener('keydown', event => {{
    if (event.key!=='Enter') return;
    if (event.shiftKey) return;
    if (compositionActive || event.isComposing || event.keyCode===229) return;
    if (event.repeat) {{ event.preventDefault(); return; }}
    requestComposerSend(event);
  }});
  message.addEventListener('beforeinput', event => {{
    if (!['insertLineBreak','insertParagraph'].includes(String(event.inputType || ''))) return;
    if (compositionActive || event.isComposing) return;
    if (event.shiftKey) return;
    requestComposerSend(event);
  }});
  send.addEventListener('click', event => requestComposerSend(event));
  actionPreview.addEventListener('click', previewConversationAction);
  document.getElementById('cognition-pause').addEventListener('click', () => setCognitionControl('pause'));
  document.getElementById('cognition-resume').addEventListener('click', () => setCognitionControl('resume'));
  document.getElementById('cognition-sleep').addEventListener('click', () => setCognitionControl('sleep'));
  document.getElementById('cognition-wake').addEventListener('click', () => setCognitionControl('wake'));
  cognitionFrequency.addEventListener('change', () => setCommunicationPreference({{frequency:cognitionFrequency.value}}));
  document.getElementById('cognition-quiet').addEventListener('click', () => setCommunicationPreference({{quiet_indefinite:true}}));
  cognitionRead.addEventListener('click', markProactiveRead);
  cancelActive.addEventListener('click', cancelActiveOperation);
  takeControl.addEventListener('click', takeConversationControl);
  jumpToLatest.addEventListener('click', () => {{ followLatest=true; unreadTurns=0; lastSeenTurnCount=sessionTurnCount; log.scrollTop=log.scrollHeight; renderJumpState(); savePresentation(); }});
  sessionSelector.addEventListener('change', () => switchConversationSession(sessionSelector.value));
  document.getElementById('provider-retry').addEventListener('click', () => checkProvider('manual_check'));
  document.getElementById('bootstrap-retry').addEventListener('click', () => bootstrap(failedRetryServices));
  document.addEventListener('visibilitychange', () => {{
    if (coordination.lease_token) fetch('/api/dashboard-chat/coordination', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{action:'heartbeat',tab_id:identity.tab_id,lease_token:coordination.lease_token,instance_nonce:identity.instance_nonce,visible:!document.hidden}}),keepalive:true}}).then(r=>r.json()).then(applyCoordination).catch(()=>{{}});
    if (!document.hidden && !providerCheckInFlight && !['ready','recovering','returned'].includes(lastProviderObservedState) && Date.now()-lastProviderCheckAt>15000) checkProvider('visibility_recovery');
  }});
  window.addEventListener('pagehide', () => {{
    if (!selectedSessionId || !coordination.is_owner) return;
    const view=captureScrollPresentation(); const payload=JSON.stringify(Object.assign({{session_id:selectedSessionId,client_updated_at:new Date().toISOString()}},view,mutationFields('presentation-'+uuid())));
    if (navigator.sendBeacon) navigator.sendBeacon('/api/dashboard-chat/presentation',new Blob([payload],{{type:'application/json'}}));
  }});

  coordinationHeartbeat=window.setInterval(heartbeatOwnership,5000);
  registerTab().catch(error => {{ ownership.textContent='Conversation ownership is unavailable: ' + String(error.message || error); }}).finally(bootstrap);
  window.setTimeout(loadActionCatalog, 0);
  window.setTimeout(loadCognition, 0);
  window.setTimeout(loadInternalLifeCheckpoint, 0);
  window.setTimeout(loadCognitiveDevelopmentCheckpoint, 0);
  window.setTimeout(loadInquiryContinuity, 0);
  window.setTimeout(loadInquiryCognitionCheckpoint, 0);
  window.setTimeout(loadKnowledgeConfidenceCheckpoint, 0);
  window.setTimeout(loadKnowledgeReconsideration, 0);
  window.setTimeout(loadKnowledgeMaintenanceCheckpoint, 0);
  window.setTimeout(loadAttentionAgendaCheckpoint, 0);
  window.setTimeout(loadAttentionIntentionCheckpoint, 0);
  window.setTimeout(loadInitiativeLifecycleCheckpoint, 0);
  window.setTimeout(loadPersistentInitiativeConsolidationCheckpoint, 0);
  window.setTimeout(loadLongHorizonObjectiveCheckpoint, 0);
  window.setTimeout(loadLongHorizonFollowThroughCheckpoint, 0);
  window.setTimeout(loadSelfModelContinuityCheckpoint, 0);
  window.setTimeout(loadIdentityRevisionCheckpoint, 0);
  window.setTimeout(loadIdentityExpressionLifecycleCheckpoint, 0);
  window.setTimeout(loadCuriosityContinuityCheckpoint, 0);
  window.setTimeout(loadCuriosityQualityCheckpoint, 0);
  window.setTimeout(loadCuriosityLifecycleCheckpoint, 0);
  window.setTimeout(loadBehavioralEvidenceCheckpoint, 0);
  window.setTimeout(loadBehavioralSelfEvaluationCheckpoint, 0);
  window.setTimeout(loadBehavioralAdaptationCheckpoint, 0);
  window.setTimeout(loadReflectiveBehavioralLearningCheckpoint, 0);
  window.setTimeout(loadActiveInquiryCheckpoint, 0);
  window.setTimeout(loadInquiryEvidenceGovernanceCheckpoint, 0);
  window.setTimeout(loadBoundedInquiryCheckpoint, 0);
  window.setTimeout(loadDeliberativeContinuityCheckpoint, 0);
  window.setTimeout(loadDecisionCommitmentCheckpoint, 0);
  window.setTimeout(loadDeliberativeDecisionReviewCheckpoint, 0);
  window.setTimeout(loadReflectivePlanningDeliberativeChoiceCheckpoint, 0);
  window.setTimeout(loadInternalCoordinationCognitiveLoadGovernanceCheckpoint, 0);
  window.setTimeout(loadProspectiveMemoryContinuityCheckpoint, 0);
  window.setTimeout(loadEpistemicCoherenceKnowledgeBeliefIntegrationCheckpoint, 0);
  window.setTimeout(loadEpistemicCoherenceIntakeCheckpoint, 0);
  window.setTimeout(loadEpistemicCoherenceDeliberationCheckpoint, 0);
  window.setTimeout(loadBeliefReconsiderationIntakeCheckpoint, 0);
  window.setTimeout(loadReflectiveTemporalContinuityProspectiveMemoryCheckpoint, 0);
  window.setTimeout(loadCognitiveHomeostasisSustainableCognitionCheckpoint, 0);
  window.setTimeout(loadCognitiveRecoveryContinuityCheckpoint, 0);
  window.setTimeout(loadCognitiveHomeostasisContinuityCheckpoint, 0);
  window.setTimeout(loadEndogenousCuriosityCheckpoint, 0);
  window.setTimeout(loadPersistentSelfModelCheckpoint, 0);
  window.setTimeout(loadRealReflectiveCognitionCheckpoint, 0);
  window.setTimeout(loadReflectiveIntegrationReliabilityCheckpoint, 0);
  window.setTimeout(loadSelectedAttentionReflectiveFocusGovernanceCheckpoint, 0);
  window.setTimeout(loadMotivationalContinuityEndogenousDriveRegulationCheckpoint, 0);
  window.setTimeout(loadReflectiveAttentionSalienceGovernanceCheckpoint, 0);
  window.setTimeout(loadReflectiveAttentionContinuityReviewCheckpoint, 0);
  window.setTimeout(loadReflectiveAttentionDeliberationCheckpoint, 0);
  window.setTimeout(loadReflectiveAttentionSalienceIntakeCheckpoint, 0);
  window.setTimeout(loadMotivationalContinuityIntakeCheckpoint, 0);
  window.setTimeout(loadObjectiveCoherenceIntakeCheckpoint, 0);
  window.setTimeout(loadSelfModelIntegrityIdentityClaimGovernanceCheckpoint, 0);
  window.setTimeout(loadSelfModelContinuityReviewCheckpoint, 0);
  window.setTimeout(loadInitiativeCommunicationCheckpoint, 0);
  window.setTimeout(loadIntentionLifecycleReview, 0);
  window.setTimeout(loadAutonomousAttentionIntentionCheckpoint, 0);
  cognitionRefreshTimer=window.setInterval(() => {{ loadCognition(); loadInternalLifeCheckpoint(); loadCognitiveDevelopmentCheckpoint(); loadInquiryContinuity(); loadInquiryCognitionCheckpoint(); loadKnowledgeConfidenceCheckpoint(); loadKnowledgeReconsideration(); loadKnowledgeMaintenanceCheckpoint(); loadAttentionAgendaCheckpoint(); loadAttentionIntentionCheckpoint(); loadInitiativeLifecycleCheckpoint(); loadPersistentInitiativeConsolidationCheckpoint(); loadLongHorizonObjectiveCheckpoint(); loadLongHorizonFollowThroughCheckpoint(); loadSelfModelContinuityCheckpoint(); loadIdentityRevisionCheckpoint(); loadIdentityExpressionLifecycleCheckpoint(); loadPersistentSelfModelCheckpoint(); loadCuriosityContinuityCheckpoint(); loadCuriosityQualityCheckpoint(); loadCuriosityLifecycleCheckpoint(); loadBehavioralEvidenceCheckpoint(); loadBehavioralSelfEvaluationCheckpoint(); loadBehavioralAdaptationCheckpoint(); loadActiveInquiryCheckpoint();
    loadInquiryEvidenceGovernanceCheckpoint(); loadBoundedInquiryCheckpoint(); loadCognitiveLoadContinuityCheckpoint(); loadCognitiveWorkContinuityCheckpoint(); loadCognitiveCoordinationReviewCheckpoint(); loadInternalCoordinationCognitiveLoadGovernanceCheckpoint(); loadEpistemicMaintenanceBeliefRevisionGovernanceCheckpoint(); loadBeliefContinuityReviewCheckpoint(); loadBeliefRevisionDeliberationCheckpoint();
  loadGoalContinuityReviewCheckpoint();
  loadGoalCoherenceLongHorizonObjectiveGovernanceCheckpoint();
  loadObjectiveCoherenceDeliberationCheckpoint();
  loadRealReflectiveCognitionCheckpoint(); loadReflectiveIntegrationReliabilityCheckpoint(); loadSelectedAttentionReflectiveFocusGovernanceCheckpoint(); loadMotivationalContinuityEndogenousDriveRegulationCheckpoint(); loadReflectiveAttentionSalienceGovernanceCheckpoint(); loadReflectiveAttentionContinuityReviewCheckpoint(); loadReflectiveAttentionDeliberationCheckpoint(); loadReflectiveAttentionSalienceIntakeCheckpoint(); loadMotivationalContinuityIntakeCheckpoint(); loadObjectiveCoherenceIntakeCheckpoint(); loadSelfModelIntegrityIdentityClaimGovernanceCheckpoint(); loadSelfModelRevisionDeliberationCheckpoint(); loadSelfModelContinuityReviewCheckpoint(); loadSelfModelIntegrityIntakeCheckpoint(); loadEpistemicCoherenceKnowledgeBeliefIntegrationCheckpoint(); loadEpistemicCoherenceIntakeCheckpoint(); loadEpistemicCoherenceDeliberationCheckpoint(); loadKnowledgeBeliefIntegrationCheckpoint(); loadBeliefReconsiderationIntakeCheckpoint(); loadReflectiveTemporalContinuityProspectiveMemoryCheckpoint(); loadCognitiveHomeostasisSustainableCognitionCheckpoint(); loadCognitiveSustainabilityReviewCheckpoint();
  loadCognitiveRecoveryContinuityCheckpoint();
  loadCognitiveHomeostasisContinuityCheckpoint();
  loadDeliberativeContinuityCheckpoint(); loadDecisionCommitmentCheckpoint(); loadDeliberativeDecisionReviewCheckpoint(); loadReflectivePlanningDeliberativeChoiceCheckpoint(); loadEndogenousCuriosityCheckpoint(); loadInitiativeCommunicationCheckpoint(); loadIntentionLifecycleReview(); loadAutonomousAttentionIntentionCheckpoint(); }},60000);
  window.setTimeout(() => checkProvider('api_post'), 0);
  window.__eidolonFirstUseInteractiveAtMs = performance.now() - started;
}})();


  async function refreshReflectionQualityIntakeCheckpoint(){{
    const state=document.getElementById('reflection-quality-intake-checkpoint-state');
    const summary=document.getElementById('reflection-quality-intake-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/reflection-quality-intake-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=(payload&&payload.data)||{{}};
      state.dataset.state=report.ok?'ready':'warning'; state.textContent=report.ok?'ready':'review';
      summary.textContent=`${{report.passed||0}}/${{report.total||0}} checks; ${{(report.signals||{{}}).signal_count||0}} signals; ${{(report.candidates||{{}}).candidate_count||0}} candidates.`;
    }}catch(error){{state.dataset.state='warning';state.textContent='unavailable';summary.textContent='Reflection-quality checkpoint unavailable.';}}
  }}
  refreshReflectionQualityIntakeCheckpoint();

  async function refreshReflectionQualityDeliberationCheckpoint(){{
    const state=document.getElementById('reflection-quality-deliberation-checkpoint-state');
    const summary=document.getElementById('reflection-quality-deliberation-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/reflection-quality-deliberation-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=(payload&&payload.data)||{{}};
      state.dataset.state=report.ok?'ready':'warning'; state.textContent=report.ok?'ready':'review';
      summary.textContent=`${{report.passed||0}}/${{report.total||0}} checks; ${{(report.sessions||{{}}).session_count||0}} sessions; ${{(report.arbitration||{{}}).outcome_count||0}} outcomes.`;
    }}catch(error){{state.dataset.state='warning';state.textContent='unavailable';summary.textContent='Reflection-quality deliberation checkpoint unavailable.';}}
  }}
  refreshReflectionQualityDeliberationCheckpoint();

  async function loadReflectionQualityIntegrationCheckpoint() {{
    const state=document.getElementById('reflection-quality-integration-checkpoint-state');
    const summary=document.getElementById('reflection-quality-integration-checkpoint-summary');
    if(!state||!summary)return;
    try {{
      const response=await fetch('/api/cognition/reflection-quality-integration-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      state.textContent=data.ok?'ready':'degraded'; state.dataset.state=data.ok?'ready':'warning';
      summary.textContent=data.headline||'Reflection quality integration checkpoint inspected.';
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='warning'; summary.textContent='Reflection quality integration checkpoint unavailable.'; }}
  }}
  loadReflectionQualityIntegrationCheckpoint();

  async function loadReflectionQualityGovernanceCheckpoint() {{
    const state=document.getElementById('reflection-quality-governance-checkpoint-state');
    const summary=document.getElementById('reflection-quality-governance-checkpoint-summary');
    if(!state||!summary)return;
    try {{
      const response=await fetch('/api/cognition/reflection-quality-governance-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=payload.data||payload;
      state.textContent=data.ok?'ready':'degraded'; state.dataset.state=data.ok?'ready':'warning';
      summary.textContent=data.headline||'Reflection quality governance checkpoint inspected.';
    }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='warning'; summary.textContent='Reflection quality governance checkpoint unavailable.'; }}
  }}
  loadReflectionQualityGovernanceCheckpoint();



  async function refreshContinuousThoughtGovernanceCheckpoint(){{
    const state=document.getElementById('continuous-thought-governance-checkpoint-state');
    const summary=document.getElementById('continuous-thought-governance-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/continuous-thought-governance-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; continuous-thought governance remains content-free, read-only, and authority-inert.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Continuous thought governance checkpoint unavailable.';}}
  }}
  refreshContinuousThoughtGovernanceCheckpoint();

  async function refreshContinuousThoughtIntegrationCheckpoint(){{
    const state=document.getElementById('continuous-thought-integration-checkpoint-state');
    const summary=document.getElementById('continuous-thought-integration-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/continuous-thought-integration-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; continuous-thought reliability remains content-free and authority-inert.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
  }}
  refreshContinuousThoughtIntegrationCheckpoint();

  async function refreshContinuousThoughtDeliberationCheckpoint(){{
    const state=document.getElementById('continuous-thought-deliberation-checkpoint-state');
    const summary=document.getElementById('continuous-thought-deliberation-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/continuous-thought-deliberation-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; bounded thread deliberation remains authority-inert.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
  }}

  refreshContinuousThoughtDeliberationCheckpoint();





  async function loadReflectiveCommunicationGovernanceCheckpoint(){{
    const state=document.getElementById('reflective-communication-governance-checkpoint-state');
    const summary=document.getElementById('reflective-communication-governance-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/reflective-communication-governance-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; reflective communication remains content-free, read-only, considerate, and authority-inert.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Reflective communication governance checkpoint unavailable.';}}
  }}
  loadReflectiveCommunicationGovernanceCheckpoint();

  async function loadReflectionSupportedRevisionGovernanceCheckpoint(){{
    const integrationState=document.getElementById('reflective-communication-integration-checkpoint-state');
    const integrationSummary=document.getElementById('reflective-communication-integration-checkpoint-summary');
    try {{
      const response=await fetch('/api/cognition/reflective-communication-integration-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      integrationState.dataset.state=report.ok?'ready':'blocked'; integrationState.textContent=report.ok?'ready':'blocked';
      integrationSummary.textContent=`${{(report.lineage||{{}}).outcome_count||0}} outcomes; ${{(report.reliability||{{}}).review_count||0}} reliability reviews; ${{report.checks?.filter(x=>x.status==='pass').length||0}}/${{report.checks?.length||0}} checks.`;
    }} catch (error) {{ integrationState.dataset.state='blocked'; integrationState.textContent='blocked'; integrationSummary.textContent='Reflective communication integration inspection unavailable.'; }}

    const deliberationState=document.getElementById('reflective-communication-deliberation-checkpoint-state');
    const deliberationSummary=document.getElementById('reflective-communication-deliberation-checkpoint-summary');
    try {{
      const response=await fetch('/api/cognition/reflective-communication-deliberation-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      deliberationState.dataset.state=report.ok?'ready':'blocked'; deliberationState.textContent=report.ok?'ready':'blocked';
      deliberationSummary.textContent=`${{(report.sessions||{{}}).session_count||0}} sessions; ${{(report.arbitration||{{}}).outcome_count||0}} outcomes; ${{report.passed||0}}/${{report.total||0}} checks.`;
    }} catch (error) {{ deliberationState.dataset.state='blocked'; deliberationState.textContent='blocked'; deliberationSummary.textContent='Reflective communication deliberation inspection unavailable.'; }}




    async function loadReadOnlyPerceptionGovernanceCheckpoint(){{
      const state=document.getElementById('read-only-perception-governance-checkpoint-state');
      const summary=document.getElementById('read-only-perception-governance-checkpoint-summary');
      if(!state||!summary)return;
      try {{
        const response=await fetch('/api/cognition/read-only-perception-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; perception remains content-free, read-only, and authority-inert.`;
      }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='warning'; summary.textContent='Read-only perception governance checkpoint unavailable.'; }}
    }}
    loadReadOnlyPerceptionGovernanceCheckpoint();

    async function loadGenuineInquiryGovernanceCheckpoint(){{
      const state=document.getElementById('genuine-inquiry-governance-checkpoint-state');
      const summary=document.getElementById('genuine-inquiry-governance-checkpoint-summary');
      if(!state||!summary)return;
      try {{
        const response=await fetch('/api/cognition/genuine-inquiry-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; inquiry remains content-free, read-only, and authority-inert.`;
      }} catch(error) {{ state.textContent='unavailable'; state.dataset.state='warning'; summary.textContent='Genuine inquiry governance checkpoint unavailable.'; }}
    }}
    loadGenuineInquiryGovernanceCheckpoint();

    const inquiryIntegrationState=document.getElementById('genuine-inquiry-integration-checkpoint-state');
    const inquiryIntegrationSummary=document.getElementById('genuine-inquiry-integration-checkpoint-summary');
    if(inquiryIntegrationState&&inquiryIntegrationSummary){{
      try {{
        const response=await fetch('/api/cognition/genuine-inquiry-integration-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const data=payload&&payload.data?payload.data:{{}};
        inquiryIntegrationState.textContent=data.ok?'ready':'review'; inquiryIntegrationState.dataset.state=data.ok?'ready':'warning';
        inquiryIntegrationSummary.textContent=`${{data.lineage?.outcome_count||0}} outcomes; ${{data.reliability?.review_count||0}} reliability reviews; desktop verification ${{data.desktop_verification||'pending'}}.`;
      }} catch(error) {{ inquiryIntegrationState.textContent='unavailable'; inquiryIntegrationState.dataset.state='warning'; }}
    }}
    const inquiryDeliberationState=document.getElementById('genuine-inquiry-deliberation-checkpoint-state');
    const inquiryDeliberationSummary=document.getElementById('genuine-inquiry-deliberation-checkpoint-summary');
    if(inquiryDeliberationState&&inquiryDeliberationSummary){{
      try {{
        const response=await fetch('/api/cognition/genuine-inquiry-deliberation-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const data=payload&&payload.data?payload.data:{{}};
        inquiryDeliberationState.textContent=data.ok?'ready':'review'; inquiryDeliberationState.dataset.state=data.ok?'ready':'warning';
        inquiryDeliberationSummary.textContent=`${{data.sessions?.session_count||0}} sessions; ${{data.arbitration?.outcome_count||0}} outcomes; desktop verification ${{data.desktop_verification||'pending'}}.`;
      }} catch(error) {{ inquiryDeliberationState.textContent='unavailable'; inquiryDeliberationState.dataset.state='warning'; }}
    }}


    const perceptionIntegrationState=document.getElementById('read-only-perception-integration-checkpoint-state');
    const perceptionIntegrationSummary=document.getElementById('read-only-perception-integration-checkpoint-summary');
    if(perceptionIntegrationState&&perceptionIntegrationSummary){{try{{
      const response=await fetch('/api/cognition/read-only-perception-integration-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=(payload&&payload.data)||{{}}; const visible=data.visible_status||{{}};
      perceptionIntegrationState.textContent=data.ok?'ready':'review'; perceptionIntegrationState.dataset.state=data.ok?'ready':'warning';
      perceptionIntegrationSummary.textContent=`${{visible.recorded_outcomes||0}} outcomes; ${{visible.active_reviews||0}} reviews; ${{visible.prioritized_failure_count||0}} failures; ${{visible.prioritized_change_count||0}} changes; ${{visible.deliberate_no_perception_count||0}} deliberate non-perception.`;
    }} catch(error) {{ perceptionIntegrationState.textContent='unavailable'; perceptionIntegrationState.dataset.state='warning'; }}}}

    const perceptionDeliberationState=document.getElementById('read-only-perception-deliberation-checkpoint-state');
    const perceptionDeliberationSummary=document.getElementById('read-only-perception-deliberation-checkpoint-summary');
    if(perceptionDeliberationState&&perceptionDeliberationSummary){{try{{
      const response=await fetch('/api/cognition/read-only-perception-deliberation-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=(payload&&payload.data)||{{}};
      perceptionDeliberationState.textContent=data.ok?'ready':'review'; perceptionDeliberationState.dataset.state=data.ok?'ready':'warning';
      perceptionDeliberationSummary.textContent=`${{(data.sessions||{{}}).session_count||0}} sessions; ${{(data.arbitration||{{}}).outcome_count||0}} outcomes; Desktop verification ${{data.desktop_verification||'pending'}}.`;
    }}catch(error){{perceptionDeliberationState.textContent='unavailable'; perceptionDeliberationState.dataset.state='warning';}}}}

    const goalIntakeState=document.getElementById('internally-generated-goal-intake-checkpoint-state');
    const goalIntakeSummary=document.getElementById('internally-generated-goal-intake-checkpoint-summary');
    if(goalIntakeState){{
      fetch('/api/cognition/internally-generated-goal-intake-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; goalIntakeState.dataset.state=data.ok?'ready':'blocked'; goalIntakeState.textContent=data.ok?'ready':'blocked'; goalIntakeSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; content-free goal-formation intake.`;}}).catch(()=>{{goalIntakeState.dataset.state='blocked';goalIntakeState.textContent='unavailable';}});
    }}
    const planningDeliberationState=document.getElementById('prospective-planning-deliberation-checkpoint-state');
    const planningDeliberationSummary=document.getElementById('prospective-planning-deliberation-checkpoint-summary');
    if(planningDeliberationState&&planningDeliberationSummary){{
      fetch('/api/cognition/prospective-planning-deliberation-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; planningDeliberationState.dataset.state=data.ok?'ready':'blocked'; planningDeliberationState.textContent=data.ok?'ready':'blocked'; planningDeliberationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; prospective plans remain content-free and authority-inert.`;}}).catch(()=>{{planningDeliberationState.dataset.state='blocked';planningDeliberationState.textContent='unavailable';}});
    }}
    const planningIntegrationState=document.getElementById('prospective-planning-integration-checkpoint-state');
    const planningIntegrationSummary=document.getElementById('prospective-planning-integration-checkpoint-summary');
    if(planningIntegrationState&&planningIntegrationSummary){{
      fetch('/api/cognition/prospective-planning-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; planningIntegrationState.dataset.state=data.ok?'ready':'blocked'; planningIntegrationState.textContent=data.ok?'ready':'blocked'; planningIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; planning outcomes remain content-free and authority-inert.`;}}).catch(()=>{{planningIntegrationState.dataset.state='blocked';planningIntegrationState.textContent='unavailable';}});
    }}

    async function loadProspectivePlanningGovernanceCheckpoint(){{
      const state=document.getElementById('prospective-planning-governance-checkpoint-state');
      const summary=document.getElementById('prospective-planning-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/prospective-planning-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; prospective-planning governance remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Prospective planning governance checkpoint unavailable.';}}
    }}
    loadProspectivePlanningGovernanceCheckpoint();

    async function loadSupervisedDeficiencyGovernanceCheckpoint(){{
      const state=document.getElementById('supervised-deficiency-governance-checkpoint-state');
      const summary=document.getElementById('supervised-deficiency-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-deficiency-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; deficiency identification remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised deficiency governance checkpoint unavailable.';}}
    }}
    loadSupervisedDeficiencyGovernanceCheckpoint();

    async function loadSupervisedDevelopmentProposalGovernanceCheckpoint(){{
      const state=document.getElementById('supervised-development-proposal-governance-checkpoint-state');
      const summary=document.getElementById('supervised-development-proposal-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-development-proposal-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; development-proposal governance remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised development proposal governance checkpoint unavailable.';}}
    }}
    loadSupervisedDevelopmentProposalGovernanceCheckpoint();


    async function loadSupervisedTestPlanningGovernanceCheckpoint(){{
      const state=document.getElementById('supervised-test-planning-governance-checkpoint-state');
      const summary=document.getElementById('supervised-test-planning-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-test-planning-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; test-planning governance remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised test-planning governance checkpoint unavailable.';}}
    }}
    loadSupervisedTestPlanningGovernanceCheckpoint();

    async function loadSupervisedSandboxChangeDeliberationCheckpoint(){{
      const state=document.getElementById('supervised-sandbox-change-deliberation-checkpoint-state');
      const summary=document.getElementById('supervised-sandbox-change-deliberation-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-sandbox-change-deliberation-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        const checks=report.checks||[]; summary.textContent=`${{checks.filter(x=>x.ok).length}}/${{checks.length}} checks; sandbox-change deliberation remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Sandbox-change deliberation checkpoint unavailable.';}}
    }}
    loadSupervisedSandboxChangeDeliberationCheckpoint();

    async function loadSupervisedSandboxChangeIntakeCheckpoint(){{
      const state=document.getElementById('supervised-sandbox-change-intake-checkpoint-state');
      const summary=document.getElementById('supervised-sandbox-change-intake-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-sandbox-change-intake-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        const checks=report.checks||[]; summary.textContent=`${{checks.filter(x=>x.status==='pass').length}}/${{checks.length}} checks; sandbox-change intake remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Sandbox-change intake checkpoint unavailable.';}}
    }}
    loadSupervisedSandboxChangeIntakeCheckpoint();

    async function loadSupervisedTestPlanIntakeCheckpoint(){{
      const state=document.getElementById('supervised-test-plan-intake-checkpoint-state');
      const summary=document.getElementById('supervised-test-plan-intake-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-test-plan-intake-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        const checks=report.checks||[]; summary.textContent=`${{checks.filter(x=>x.status==='pass').length}}/${{checks.length}} checks; test-plan intake remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised test-plan intake checkpoint unavailable.';}}
    }}
    loadSupervisedTestPlanIntakeCheckpoint();

    async function loadSupervisedSpecificationGovernanceCheckpoint(){{
      const state=document.getElementById('supervised-specification-governance-checkpoint-state');
      const summary=document.getElementById('supervised-specification-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-specification-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; specification governance remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised specification governance checkpoint unavailable.';}}
    }}
    loadSupervisedSpecificationGovernanceCheckpoint();

    const deficiencyDeliberationState=document.getElementById('supervised-deficiency-deliberation-checkpoint-state');
    const deficiencyDeliberationSummary=document.getElementById('supervised-deficiency-deliberation-checkpoint-summary');
    if(deficiencyDeliberationState){{
      fetch('/api/cognition/supervised-deficiency-deliberation-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; deficiencyDeliberationState.dataset.state=data.ok?'ready':'blocked'; deficiencyDeliberationState.textContent=data.ok?'ready':'blocked'; deficiencyDeliberationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; outcomes remain structural and authority-inert.`;}}).catch(()=>{{deficiencyDeliberationState.dataset.state='blocked';deficiencyDeliberationState.textContent='unavailable';}});
    const deficiencyIntegrationState=document.getElementById('supervised-deficiency-integration-checkpoint-state');
    const deficiencyIntegrationSummary=document.getElementById('supervised-deficiency-integration-checkpoint-summary');
    if(deficiencyIntegrationState&&deficiencyIntegrationSummary){{
      fetch('/api/cognition/supervised-deficiency-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; deficiencyIntegrationState.dataset.state=data.ok?'ready':'blocked'; deficiencyIntegrationState.textContent=data.ok?'ready':'blocked'; deficiencyIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; lineage and reliability findings remain authority-inert.`;}}).catch(()=>{{deficiencyIntegrationState.dataset.state='blocked';deficiencyIntegrationState.textContent='unavailable';}});
    }}
    }}
    async function loadSupervisedSandboxChangeGovernanceCheckpoint(){{
      const state=document.getElementById('supervised-sandbox-change-governance-checkpoint-state');
      const summary=document.getElementById('supervised-sandbox-change-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-sandbox-change-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; sandbox-change governance remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised sandbox-change governance checkpoint unavailable.';}}
    }}
    loadSupervisedSandboxChangeGovernanceCheckpoint();

    async function loadSupervisedIsolatedSandboxExecutionGovernanceCheckpoint(){{
      const state=document.getElementById('supervised-isolated-sandbox-execution-governance-checkpoint-state');
      const summary=document.getElementById('supervised-isolated-sandbox-execution-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-isolated-sandbox-execution-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; isolated sandbox execution governance remains content-free, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised isolated sandbox execution governance checkpoint unavailable.';}}
    }}
    loadSupervisedIsolatedSandboxExecutionGovernanceCheckpoint();

    async function loadSupervisedRepairImplementationIntakeCheckpoint(){{
      const state=document.getElementById('supervised-repair-implementation-intake-checkpoint-state');
      const summary=document.getElementById('supervised-repair-implementation-intake-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/supervised-repair-implementation-intake-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        const counts=report.summary||{{}};
        summary.textContent=`${{report.passed||0}}/${{report.total||24}} checks; ${{counts.eligibility_record_count||0}} eligibility record(s), ${{counts.work_order_count||0}} work order(s), and no materialization authority.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Supervised repair implementation intake checkpoint unavailable.';}}
    }}
    loadSupervisedRepairImplementationIntakeCheckpoint();

    const sandboxChangeIntegrationState=document.getElementById('supervised-sandbox-change-integration-checkpoint-state');
    const sandboxChangeIntegrationSummary=document.getElementById('supervised-sandbox-change-integration-checkpoint-summary');
    if(sandboxChangeIntegrationState&&sandboxChangeIntegrationSummary){{fetch('/api/cognition/supervised-sandbox-change-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}};sandboxChangeIntegrationState.dataset.state=data.ok?'ready':'blocked';sandboxChangeIntegrationState.textContent=data.ok?'ready':'blocked';sandboxChangeIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; sandbox-change lineage and reliability findings remain authority-inert.`;}}).catch(()=>{{sandboxChangeIntegrationState.dataset.state='blocked';sandboxChangeIntegrationState.textContent='unavailable';}});}}
    const testPlanIntegrationState=document.getElementById('supervised-test-plan-integration-checkpoint-state');
    const testPlanIntegrationSummary=document.getElementById('supervised-test-plan-integration-checkpoint-summary');
    if(testPlanIntegrationState&&testPlanIntegrationSummary){{fetch('/api/cognition/supervised-test-plan-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}};testPlanIntegrationState.dataset.state=data.ok?'ready':'blocked';testPlanIntegrationState.textContent=data.ok?'ready':'blocked';testPlanIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; test-plan lineage and reliability findings remain authority-inert.`;}}).catch(()=>{{testPlanIntegrationState.dataset.state='blocked';testPlanIntegrationState.textContent='unavailable';}});}}
    const specificationIntegrationState=document.getElementById('supervised-specification-integration-checkpoint-state');
    const specificationIntegrationSummary=document.getElementById('supervised-specification-integration-checkpoint-summary');
    if(specificationIntegrationState&&specificationIntegrationSummary){{fetch('/api/cognition/supervised-specification-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}};specificationIntegrationState.dataset.state=data.ok?'ready':'blocked';specificationIntegrationState.textContent=data.ok?'ready':'blocked';specificationIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; outcome lineage and reliability findings remain authority-inert.`;}}).catch(()=>{{specificationIntegrationState.dataset.state='blocked';specificationIntegrationState.textContent='unavailable';}});}}
    const developmentProposalIntegrationState=document.getElementById('supervised-development-proposal-integration-checkpoint-state');
    const developmentProposalIntegrationSummary=document.getElementById('supervised-development-proposal-integration-checkpoint-summary');
    if(developmentProposalIntegrationState&&developmentProposalIntegrationSummary){{fetch('/api/cognition/supervised-development-proposal-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}};developmentProposalIntegrationState.dataset.state=data.ok?'ready':'blocked';developmentProposalIntegrationState.textContent=data.ok?'ready':'blocked';developmentProposalIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; outcome lineage and reliability findings remain authority-inert.`;}}).catch(()=>{{developmentProposalIntegrationState.dataset.state='blocked';developmentProposalIntegrationState.textContent='unavailable';}});}}
    const developmentProposalIntakeState=document.getElementById('supervised-development-proposal-intake-checkpoint-state');
    const developmentProposalIntakeSummary=document.getElementById('supervised-development-proposal-intake-checkpoint-summary');
    if(developmentProposalIntakeState){{fetch('/api/cognition/supervised-development-proposal-intake-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}};developmentProposalIntakeState.dataset.state=data.ok?'ready':'blocked';developmentProposalIntakeState.textContent=data.ok?'ready':'blocked';developmentProposalIntakeSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; proposal candidates remain structural and authority-inert.`;}}).catch(()=>{{developmentProposalIntakeState.dataset.state='blocked';developmentProposalIntakeState.textContent='unavailable';}});}}
    const deficiencyIntakeState=document.getElementById('supervised-deficiency-intake-checkpoint-state');
    const deficiencyIntakeSummary=document.getElementById('supervised-deficiency-intake-checkpoint-summary');
    if(deficiencyIntakeState){{
      fetch('/api/cognition/supervised-deficiency-intake-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; deficiencyIntakeState.dataset.state=data.ok?'ready':'blocked'; deficiencyIntakeState.textContent=data.ok?'ready':'blocked'; deficiencyIntakeSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; deficiency records remain structural and authority-inert.`;}}).catch(()=>{{deficiencyIntakeState.dataset.state='blocked';deficiencyIntakeState.textContent='unavailable';}});
    }}
    const planningIntakeState=document.getElementById('prospective-planning-intake-checkpoint-state');
    const planningIntakeSummary=document.getElementById('prospective-planning-intake-checkpoint-summary');
    if(planningIntakeState&&planningIntakeSummary){{
      fetch('/api/cognition/prospective-planning-intake-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; planningIntakeState.dataset.state=data.ok?'ready':'blocked'; planningIntakeState.textContent=data.ok?'ready':'blocked'; planningIntakeSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; prospective plans remain content-free and authority-inert.`;}}).catch(()=>{{planningIntakeState.dataset.state='blocked';planningIntakeState.textContent='unavailable';}});
    }}
    const worldModelState=document.getElementById('revisable-world-model-intake-checkpoint-state');
    const worldModelSummary=document.getElementById('revisable-world-model-intake-checkpoint-summary');
    if(worldModelState&&worldModelSummary){{
      fetch('/api/cognition/revisable-world-model-intake-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; worldModelState.dataset.state=data.ok?'ready':'blocked'; worldModelState.textContent=data.ok?'ready':'blocked'; worldModelSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; content-free revisable world-model intake.`;}}).catch(()=>{{worldModelState.dataset.state='blocked';worldModelState.textContent='unavailable';}});
    }}
    const goalDeliberationState=document.getElementById('internally-generated-goal-deliberation-checkpoint-state');
    const goalDeliberationSummary=document.getElementById('internally-generated-goal-deliberation-checkpoint-summary');
    if(goalDeliberationState&&goalDeliberationSummary){{
      fetch('/api/cognition/internally-generated-goal-deliberation-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; goalDeliberationState.dataset.state=data.ok?'ready':'blocked'; goalDeliberationState.textContent=data.ok?'ready':'blocked'; goalDeliberationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; bounded goal deliberation remains advisory.`;}}).catch(()=>{{goalDeliberationState.dataset.state='blocked';goalDeliberationState.textContent='unavailable';}});
    }}
    const worldModelDeliberationState=document.getElementById('revisable-world-model-deliberation-checkpoint-state');
    const worldModelDeliberationSummary=document.getElementById('revisable-world-model-deliberation-checkpoint-summary');
    if(worldModelDeliberationState&&worldModelDeliberationSummary){{
      fetch('/api/cognition/revisable-world-model-deliberation-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; worldModelDeliberationState.dataset.state=data.ok?'ready':'blocked'; worldModelDeliberationState.textContent=data.ok?'ready':'blocked'; worldModelDeliberationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; bounded world-model deliberation remains advisory.`;}}).catch(()=>{{worldModelDeliberationState.dataset.state='blocked';worldModelDeliberationState.textContent='unavailable';}});
    }}
    const goalIntegrationState=document.getElementById('internally-generated-goal-integration-checkpoint-state');
    const goalIntegrationSummary=document.getElementById('internally-generated-goal-integration-checkpoint-summary');
    if(goalIntegrationState&&goalIntegrationSummary){{
      fetch('/api/cognition/internally-generated-goal-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; goalIntegrationState.dataset.state=data.ok?'ready':'blocked'; goalIntegrationState.textContent=data.ok?'ready':'blocked'; goalIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; goal lifecycle outcomes remain advisory.`;}}).catch(()=>{{goalIntegrationState.dataset.state='blocked';goalIntegrationState.textContent='unavailable';}});
    }}
    async function loadInternallyGeneratedGoalGovernanceCheckpoint(){{
      const state=document.getElementById('internally-generated-goal-governance-checkpoint-state');
      const summary=document.getElementById('internally-generated-goal-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/internally-generated-goal-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; goal governance remains content-free, revisable, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Internally generated goal governance checkpoint unavailable.';}}
    }}
    loadInternallyGeneratedGoalGovernanceCheckpoint();
    const worldModelIntegrationState=document.getElementById('revisable-world-model-integration-checkpoint-state');
    const worldModelIntegrationSummary=document.getElementById('revisable-world-model-integration-checkpoint-summary');
    if(worldModelIntegrationState&&worldModelIntegrationSummary){{
      fetch('/api/cognition/revisable-world-model-integration-checkpoint',{{cache:'no-store'}}).then(r=>r.json()).then(payload=>{{const data=payload.data||{{}}; worldModelIntegrationState.dataset.state=data.ok?'ready':'blocked'; worldModelIntegrationState.textContent=data.ok?'ready':'blocked'; worldModelIntegrationSummary.textContent=`${{(data.checks||[]).filter(x=>x.status==='pass').length}}/${{(data.checks||[]).length}} checks passed; world-model outcomes remain advisory.`;}}).catch(()=>{{worldModelIntegrationState.dataset.state='blocked';worldModelIntegrationState.textContent='unavailable';}});
    }}
    async function loadRevisableWorldModelGovernanceCheckpoint(){{
      const state=document.getElementById('revisable-world-model-governance-checkpoint-state');
      const summary=document.getElementById('revisable-world-model-governance-checkpoint-summary');
      if(!state||!summary)return;
      try{{
        const response=await fetch('/api/cognition/revisable-world-model-governance-checkpoint',{{cache:'no-store'}});
        const payload=await response.json(); const report=payload&&payload.data?payload.data:{{}};
        state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
        summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; world-model governance remains content-free, revisable, read-only, and authority-inert.`;
      }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Revisable world model governance checkpoint unavailable.';}}
    }}
    loadRevisableWorldModelGovernanceCheckpoint();
    const perceptionState=document.getElementById('read-only-perception-intake-checkpoint-state');
    const perceptionSummary=document.getElementById('read-only-perception-intake-checkpoint-summary');
    if(perceptionState&&perceptionSummary){{try{{
      const response=await fetch('/api/cognition/read-only-perception-intake-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const data=(payload&&payload.data)||{{}};
      perceptionState.textContent=data.ok?'ready':'review'; perceptionState.dataset.state=data.ok?'ready':'warning';
      perceptionSummary.textContent=`${{(data.signals||{{}}).signal_count||0}} signals; ${{(data.candidates||{{}}).candidate_count||0}} candidates; Desktop verification ${{data.desktop_verification||'pending'}}.`;
    }}catch(error){{perceptionState.textContent='unavailable'; perceptionState.dataset.state='warning';}}}}

    const inquiryState=document.getElementById('genuine-inquiry-intake-checkpoint-state');
    const inquirySummary=document.getElementById('genuine-inquiry-intake-checkpoint-summary');
    try {{
      const response=await fetch('/api/cognition/genuine-inquiry-intake-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      inquiryState.dataset.state=report.ok?'ready':'blocked'; inquiryState.textContent=report.ok?'ready':'blocked';
      inquirySummary.textContent=`${{(report.signals||{{}}).signal_count||0}} eligibility signals; ${{(report.candidates||{{}}).candidate_count||0}} candidates; ${{report.checks?.filter(x=>x.status==='pass').length||0}}/${{report.checks?.length||0}} checks.`;
    }} catch (error) {{ inquiryState.dataset.state='blocked'; inquiryState.textContent='blocked'; inquirySummary.textContent='Genuine inquiry intake inspection unavailable.'; }}

    const communicationState=document.getElementById('reflective-communication-intake-checkpoint-state');
    const communicationSummary=document.getElementById('reflective-communication-intake-checkpoint-summary');
    try {{
      const response=await fetch('/api/cognition/reflective-communication-intake-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      communicationState.dataset.state=report.ok?'ready':'blocked'; communicationState.textContent=report.ok?'ready':'blocked';
      communicationSummary.textContent=`${{(report.signals||{{}}).signal_count||0}} eligibility signals; ${{(report.candidates||{{}}).candidate_count||0}} candidates; ${{report.checks?.filter(x=>x.status==='pass').length||0}}/${{report.checks?.length||0}} checks.`;
    }} catch (error) {{ communicationState.dataset.state='blocked'; communicationState.textContent='blocked'; communicationSummary.textContent='Reflective communication intake inspection unavailable.'; }}

    const state=document.getElementById('reflection-supported-revision-governance-checkpoint-state');
    const summary=document.getElementById('reflection-supported-revision-governance-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/reflection-supported-revision-governance-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; reflection-supported revision governance remains content-free, read-only, and authority-inert.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';summary.textContent='Reflection-supported revision governance checkpoint unavailable.';}}
  }}
  loadReflectionSupportedRevisionGovernanceCheckpoint();

  async function refreshReflectionSupportedRevisionIntegrationCheckpoint(){{
    const state=document.getElementById('reflection-supported-revision-integration-checkpoint-state');
    const summary=document.getElementById('reflection-supported-revision-integration-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/reflection-supported-revision-integration-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; revision outcomes remain unapplied and content-free.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
  }}
  refreshReflectionSupportedRevisionIntegrationCheckpoint();

  async function refreshReflectionSupportedRevisionDeliberationCheckpoint(){{
    const state=document.getElementById('reflection-supported-revision-deliberation-checkpoint-state');
    const summary=document.getElementById('reflection-supported-revision-deliberation-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/reflection-supported-revision-deliberation-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      summary.textContent=`${{report.passed||0}}/${{report.total||18}} checks; revision recommendations remain unapplied.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
  }}
  refreshReflectionSupportedRevisionDeliberationCheckpoint();

  async function refreshReflectionSupportedRevisionIntakeCheckpoint(){{
    const state=document.getElementById('reflection-supported-revision-intake-checkpoint-state');
    const summary=document.getElementById('reflection-supported-revision-intake-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/reflection-supported-revision-intake-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      const signals=(report.signals||{{}}).signal_count||0; const candidates=(report.candidates||{{}}).candidate_count||0;
      summary.textContent=`${{signals}} revision signal(s); ${{candidates}} candidate(s). Content-free and authority-inert.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
  }}

  refreshReflectionSupportedRevisionIntakeCheckpoint();

  async function refreshContinuousThoughtIntakeCheckpoint(){{
    const state=document.getElementById('continuous-thought-intake-checkpoint-state');
    const summary=document.getElementById('continuous-thought-intake-checkpoint-summary');
    if(!state||!summary)return;
    try{{
      const response=await fetch('/api/cognition/continuous-thought-intake-checkpoint',{{cache:'no-store'}});
      const payload=await response.json(); const report=payload.data||{{}};
      state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
      const threads=(report.threads||{{}}).thread_count||0; const reviews=(report.continuity||{{}}).thread_count||0;
      summary.textContent=`${{threads}} durable thread(s); ${{reviews}} continuity review(s). Content-free and authority-inert.`;
    }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
  }}

  refreshContinuousThoughtIntakeCheckpoint();



async function loadOperatorCorrectionAcceptanceLearningGovernanceCheckpoint(){{
  const state=document.getElementById('operator-correction-acceptance-learning-governance-checkpoint-state');
  const summary=document.getElementById('operator-correction-acceptance-learning-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/operator-correction-acceptance-learning-governance-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const report=payload.data||{{}}; const counts=report.summary||{{}};
    state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
    summary.textContent=`${{report.passed||0}}/${{report.total||0}} governance checks; ${{counts.eligibility_record_count||0}} eligibility, ${{counts.guidance_record_count||0}} guidance, ${{counts.application_record_count||0}} application, ${{counts.reliability_review_count||0}} review, and ${{counts.visible_evidence_count||0}} evidence record(s).`;
  }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
}}

async function loadOperatorCorrectionReliabilityVisibleBehaviorCheckpoint(){{
  const state=document.getElementById('operator-correction-reliability-visible-behavior-checkpoint-state');
  const summary=document.getElementById('operator-correction-reliability-visible-behavior-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/operator-correction-reliability-visible-behavior-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const report=payload.data||{{}};
    state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
    summary.textContent=`${{report.passed||0}}/${{report.total||0}} structural checks; review records ${{(report.reliability_review||{{}}).record_count||0}}; visible evidence ${{(report.visible_behavior_evidence||{{}}).record_count||0}}.`;
  }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
}}

async function loadOperatorCorrectionReasoningIntegrationCheckpoint(){{
  const state=document.getElementById('operator-correction-reasoning-integration-checkpoint-state');
  const summary=document.getElementById('operator-correction-reasoning-integration-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/operator-correction-reasoning-integration-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const data=payload.data||{{}};
    state.textContent=data.ok?'ready':'review'; state.dataset.state=data.ok?'ready':'warning';
    const applications=(data.application||{{}}).record_count||0; const continuity=(data.continuity||{{}}).record_count||0;
    summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{applications}} application record(s), ${{continuity}} continuity record(s); historical truth preserved.`;
  }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
}}
loadOperatorCorrectionReasoningIntegrationCheckpoint();
loadOperatorCorrectionReliabilityVisibleBehaviorCheckpoint();
loadOperatorCorrectionAcceptanceLearningGovernanceCheckpoint();
async function loadWorkloadCoordinationIntakeCheckpoint(){{
  const state=document.getElementById('workload-coordination-intake-checkpoint-state');
  const summary=document.getElementById('workload-coordination-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/workload-coordination-intake-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const report=payload.data||{{}};
    state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
    summary.textContent=`${{report.passed||0}}/${{report.total||0}} checks; ${{(report.eligibility||{{}}).record_count||0}} eligibility and ${{(report.candidates||{{}}).record_count||0}} coordination candidate record(s).`;
  }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
}}
loadWorkloadCoordinationIntakeCheckpoint();
async function loadWorkloadCoordinationExecutionCheckpoint(){{
  const state=document.getElementById('workload-coordination-execution-checkpoint-state');
  const summary=document.getElementById('workload-coordination-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/workload-coordination-execution-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const report=payload.data||{{}};
    state.textContent=report.ok?'ready':'review'; state.dataset.state=report.ok?'ready':'warning';
    summary.textContent=`${{report.passed||0}}/${{report.total||0}} checks; ${{(report.arbitration||{{}}).record_count||0}} arbitration and ${{(report.continuity||{{}}).record_count||0}} continuity record(s).`;
  }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
}}
loadWorkloadCoordinationExecutionCheckpoint();
loadWorkloadCoordinationReliabilityCheckpoint();

async function loadOperatorCorrectionAcceptanceIntakeCheckpoint(){{
  const state=document.getElementById('operator-correction-acceptance-intake-checkpoint-state');
  const summary=document.getElementById('operator-correction-acceptance-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/operator-correction-acceptance-intake-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const data=payload.data||{{}};
    state.textContent=data.ok?'ready':'review'; state.dataset.state=data.ok?'ready':'warning';
    const eligibility=(data.eligibility||{{}}).record_count||0; const guidance=(data.guidance||{{}}).record_count||0;
    summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{eligibility}} eligibility record(s), ${{guidance}} guidance record(s); historical truth preserved.`;
  }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
}}
loadOperatorCorrectionAcceptanceIntakeCheckpoint();

async function loadSupervisedSandboxRepairImplementationGovernanceCheckpoint(){{
  const state=document.getElementById('supervised-sandbox-repair-implementation-governance-checkpoint-state');
  const summary=document.getElementById('supervised-sandbox-repair-implementation-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/supervised-sandbox-repair-implementation-governance-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const data=payload.data||{{}}; const counts=data.summary||{{}};
    state.textContent=data.ok?'ready':'review'; state.dataset.state=data.ok?'ready':'warning';
    summary.textContent=`${{data.passed||0}}/${{data.total||0}} governance checks; ${{counts.execution_count||0}} execution(s), ${{counts.reliability_review_count||0}} reliability review(s); Desktop verification ${{data.desktop_verification||'pending'}}.`;
  }}catch(error){{state.textContent='unavailable';state.dataset.state='warning';}}
}}
loadSupervisedSandboxRepairImplementationGovernanceCheckpoint();

async function loadSupervisedRepairExecutionCheckpoint(){{const state=document.getElementById('supervised-repair-execution-checkpoint-state');const summary=document.getElementById('supervised-repair-execution-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/supervised-repair-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'blocked';state.dataset.state=data.ok?'ready':'blocked';summary.textContent=`${{data.passed||0}}/${{data.total||0}} structural checks; Desktop verification ${{data.desktop_verification||'pending'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='blocked';}}}}
loadSupervisedRepairExecutionCheckpoint();

async function loadWorkloadCoordinationReliabilityCheckpoint(){{
  const state=document.getElementById('workload-coordination-reliability-checkpoint-state');
  const summary=document.getElementById('workload-coordination-reliability-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/workload-coordination-reliability-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const report=payload.data||payload;
    state.dataset.state=report.ok?'ready':'attention'; state.textContent=report.ok?'ready':'review';
    summary.textContent=`${{report.passed||0}}/${{report.total||0}} checks; ${{(report.review&&report.review.review_count)||0}} reliability reviews and ${{(report.evidence&&report.evidence.evidence_count)||0}} visible evidence records.`;
  }}catch(error){{state.dataset.state='attention';state.textContent='unavailable';}}
}}

async function loadWorkloadCoordinationGovernanceCheckpoint(){{
  const state=document.getElementById('workload-coordination-governance-checkpoint-state');
  const summary=document.getElementById('workload-coordination-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/workload-coordination-governance-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const report=payload.data||payload; const counts=report.summary||{{}};
    state.dataset.state=report.ok?'ready':'attention'; state.textContent=report.ok?'ready':'review';
    summary.textContent=`${{report.passed||0}}/${{report.total||0}} governance checks; ${{counts.arbitration_record_count||0}} arbitration, ${{counts.continuity_record_count||0}} continuity, ${{counts.reliability_review_count||0}} review, and ${{counts.visible_evidence_count||0}} evidence record(s).`;
  }}catch(error){{state.dataset.state='attention';state.textContent='unavailable';}}
}}
loadWorkloadCoordinationGovernanceCheckpoint();


async function loadMultiDayContinuitySoakExecutionCheckpoint(){{
  const state=document.getElementById('multi-day-continuity-soak-execution-checkpoint-state');
  const summary=document.getElementById('multi-day-continuity-soak-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/multi-day-continuity-soak-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{data.executions?.record_count||0}} executions; ${{data.receipts?.record_count||0}} receipts.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Execution checkpoint unavailable.';}}
}}
async function loadMultiDayContinuitySoakReliabilityCheckpoint(){{
  const state=document.getElementById('multi-day-continuity-soak-reliability-checkpoint-state');
  const summary=document.getElementById('multi-day-continuity-soak-reliability-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/multi-day-continuity-soak-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{data.reviews?.review_count||0}} reviews; ${{data.evidence?.evidence_count||0}} evidence records.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Reliability checkpoint unavailable.';}}
}}


async function loadMultiDayContinuitySoakGovernanceCheckpoint(){{
  const state=document.getElementById('multi-day-continuity-soak-governance-checkpoint-state');
  const summary=document.getElementById('multi-day-continuity-soak-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/multi-day-continuity-soak-governance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.campaign_candidate_count||0}} campaigns; ${{counts.execution_record_count||0}} executions; ${{counts.reliability_review_count||0}} reviews.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Governance checkpoint unavailable.';}}
}}

async function loadConversationCognitionUnificationIntakeCheckpoint(){{
  const state=document.getElementById('conversation-cognition-unification-intake-checkpoint-state');
  const summary=document.getElementById('conversation-cognition-unification-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/conversation-cognition-unification-intake-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.eligibility_record_count||0}} eligibility records; ${{counts.context_candidate_count||0}} context candidates; silence eligible.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversation-cognition intake checkpoint unavailable.';}}
}}
async function loadConversationCognitionUnificationExecutionCheckpoint(){{
  const state=document.getElementById('conversation-cognition-unification-execution-checkpoint-state');
  const summary=document.getElementById('conversation-cognition-unification-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/conversation-cognition-unification-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.communication_arbitration_count||0}} arbitrations; ${{counts.generation_receipt_count||0}} generation receipts; ${{counts.deliberate_silence_count||0}} silence decisions.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversation-cognition execution checkpoint unavailable.';}}
}}
async function loadConversationCognitionUnificationReliabilityCheckpoint(){{
  const state=document.getElementById('conversation-cognition-unification-reliability-checkpoint-state');
  const summary=document.getElementById('conversation-cognition-unification-reliability-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/conversation-cognition-unification-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.continuity_record_count||0}} continuity records; ${{counts.reliability_review_count||0}} reliability reviews; ${{counts.stale_context_count||0}} stale contexts.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversation-cognition reliability checkpoint unavailable.';}}
}}
async function loadUnderstandableCognitiveControlsReliabilityCheckpoint(){{
  const state=document.getElementById('understandable-cognitive-controls-reliability-checkpoint-state');
  const summary=document.getElementById('understandable-cognitive-controls-reliability-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/understandable-cognitive-controls-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.continuity_record_count||0}} continuity records; ${{counts.reliability_review_count||0}} reviews; ${{counts.drift_count||0}} drift findings; ${{counts.review_required_count||0}} requiring review.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive control reliability checkpoint unavailable.';}}
}}
async function loadArchitectureConsolidationExecutionCheckpoint(){{
  const state=document.getElementById('architecture-consolidation-execution-checkpoint-state');
  const summary=document.getElementById('architecture-consolidation-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/architecture-consolidation-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.registered_checkpoint_count||0}} registry-dispatched checkpoints; ${{counts.startup_tier_count||0}} startup tiers; ${{counts.deferred_domain_count||0}} deferred domains remain lazy.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Architecture consolidation execution checkpoint unavailable.';}}
}}

async function loadArchitectureConsolidationIntakeCheckpoint(){{
  const state=document.getElementById('architecture-consolidation-intake-checkpoint-state');
  const summary=document.getElementById('architecture-consolidation-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/architecture-consolidation-intake-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.ownership_domain_count||0}} owned domains; ${{counts.checkpoint_count||0}} registered checkpoints; ${{counts.startup_tier_count||0}} startup tiers.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Architecture consolidation intake checkpoint unavailable.';}}
}}

async function loadUnderstandableCognitiveControlsGovernanceCheckpoint(){{
  const state=document.getElementById('understandable-cognitive-controls-governance-checkpoint-state');
  const summary=document.getElementById('understandable-cognitive-controls-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/understandable-cognitive-controls-governance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} governance checks; ${{counts.control_domain_count||0}} domains; ${{counts.active_control_count||0}} active controls; ${{counts.enforcement_receipt_count||0}} enforcement receipts; ${{counts.reliability_review_count||0}} reliability reviews.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive controls governance checkpoint unavailable.';}}
}}
async function loadUnderstandableCognitiveControlsExecutionCheckpoint(){{
  const state=document.getElementById('understandable-cognitive-controls-execution-checkpoint-state');
  const summary=document.getElementById('understandable-cognitive-controls-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/understandable-cognitive-controls-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.active_control_count||0}} active controls; ${{counts.activation_receipt_count||0}} activation receipts; ${{counts.enforcement_receipt_count||0}} enforcement receipts.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive control execution checkpoint unavailable.';}}
}}
async function loadUnderstandableCognitiveControlsIntakeCheckpoint(){{
  const state=document.getElementById('understandable-cognitive-controls-intake-checkpoint-state');
  const summary=document.getElementById('understandable-cognitive-controls-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/understandable-cognitive-controls-intake-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.control_domain_count||0}} control domains; ${{counts.configuration_preview_count||0}} preview records; ${{counts.safe_default_count||0}} safe defaults.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Understandable cognitive controls checkpoint unavailable.';}}
}}
async function loadConversationCognitionUnificationGovernanceCheckpoint(){{
  const state=document.getElementById('conversation-cognition-unification-governance-checkpoint-state');
  const summary=document.getElementById('conversation-cognition-unification-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/conversation-cognition-unification-governance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} governance checks; ${{counts.context_candidate_count||0}} context candidates; ${{counts.communication_arbitration_count||0}} arbitrations; ${{counts.generation_receipt_count||0}} generation receipts; ${{counts.reliability_review_count||0}} reliability reviews.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversation-cognition governance checkpoint unavailable.';}}
}}
async function loadMultiDayContinuitySoakIntakeCheckpoint(){{
  const state=document.getElementById('multi-day-continuity-soak-intake-checkpoint-state');
  const summary=document.getElementById('multi-day-continuity-soak-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{
    const response=await fetch('/api/cognition/multi-day-continuity-soak-intake-checkpoint',{{cache:'no-store'}});
    const payload=await response.json(); const report=payload.data||payload; const counts=report.summary||{{}};
    state.dataset.state=report.ok?'ready':'attention'; state.textContent=report.ok?'ready':'review';
    summary.textContent=`${{report.passed||0}}/${{report.total||0}} checks; ${{counts.eligibility_record_count||0}} eligibility and ${{counts.campaign_candidate_count||0}} campaign candidate record(s) across ${{counts.recognized_scenario_count||0}} scenario classes.`;
  }}catch(error){{state.dataset.state='attention';state.textContent='unavailable';}}
}}
loadMultiDayContinuitySoakIntakeCheckpoint();
loadMultiDayContinuitySoakExecutionCheckpoint();
loadMultiDayContinuitySoakReliabilityCheckpoint();
loadMultiDayContinuitySoakGovernanceCheckpoint();
loadConversationCognitionUnificationIntakeCheckpoint();
loadConversationCognitionUnificationExecutionCheckpoint();
loadConversationCognitionUnificationReliabilityCheckpoint();
loadConversationCognitionUnificationGovernanceCheckpoint();
loadUnderstandableCognitiveControlsIntakeCheckpoint();
loadUnderstandableCognitiveControlsReliabilityCheckpoint();
loadArchitectureConsolidationIntakeCheckpoint();
loadArchitectureConsolidationExecutionCheckpoint();
loadUnderstandableCognitiveControlsGovernanceCheckpoint();
loadUnderstandableCognitiveControlsExecutionCheckpoint();

async function loadArchitectureConsolidationReliabilityCheckpoint(){{
  const state=document.getElementById('architecture-consolidation-reliability-checkpoint-state');
  const summary=document.getElementById('architecture-consolidation-reliability-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/architecture-consolidation-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.ownership_domain_count||0}} ownership domains; ${{counts.registered_checkpoint_count||0}} registered checkpoints; reliability ${{counts.reliability_score||0}}; ${{counts.issue_count||0}} issues.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Architecture consolidation reliability checkpoint unavailable.';}}
}}
loadArchitectureConsolidationReliabilityCheckpoint();


async function loadArchitectureConsolidationGovernanceCheckpoint(){{
  const state=document.getElementById('architecture-consolidation-governance-checkpoint-state');
  const summary=document.getElementById('architecture-consolidation-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/architecture-consolidation-governance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.ownership_domain_count||0}} ownership domains; ${{counts.registered_checkpoint_count||0}} registered checkpoints; ${{counts.startup_tier_count||0}} startup tiers; reliability ${{counts.reliability_score||0}}; ${{counts.continuity_issue_count||0}} issues.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Architecture consolidation governance checkpoint unavailable.';}}
}}
loadArchitectureConsolidationGovernanceCheckpoint();

async function loadPrivacySecurityHardeningIntakeCheckpoint(){{
  const state=document.getElementById('privacy-security-hardening-intake-checkpoint-state');
  const summary=document.getElementById('privacy-security-hardening-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/privacy-security-hardening-intake-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.threat_category_count||0}} threat classes; ${{counts.scenario_count||0}} bounded scenarios; ${{counts.execution_eligible_count||0}} execution-eligible.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Privacy and security hardening intake checkpoint unavailable.';}}
}}
loadPrivacySecurityHardeningIntakeCheckpoint();

async function loadPrivacySecurityHardeningExecutionCheckpoint(){{
  const state=document.getElementById('privacy-security-hardening-execution-checkpoint-state');
  const summary=document.getElementById('privacy-security-hardening-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/privacy-security-hardening-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.execution_count||0}} executions; ${{counts.finding_count||0}} findings; ${{counts.contained_count||0}} contained; ${{counts.recovered_count||0}} recovered.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Privacy and security hardening execution checkpoint unavailable.';}}
}}
loadPrivacySecurityHardeningExecutionCheckpoint();
async function loadPrivacySecurityHardeningReliabilityCheckpoint(){{
  const state=document.getElementById('privacy-security-hardening-reliability-checkpoint-state');
  const summary=document.getElementById('privacy-security-hardening-reliability-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/privacy-security-hardening-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.continuity_record_count||0}} continuity records; reliability ${{counts.reliability_score||0}}; ${{counts.classification||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Privacy and security hardening reliability checkpoint unavailable.';}}
}}
loadPrivacySecurityHardeningReliabilityCheckpoint();
async function loadPrivacySecurityHardeningGovernanceCheckpoint(){{
  const state=document.getElementById('privacy-security-hardening-governance-checkpoint-state');
  const summary=document.getElementById('privacy-security-hardening-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/privacy-security-hardening-governance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.threat_category_count||0}} threat classes; ${{counts.scenario_count||0}} scenarios; reliability ${{counts.reliability_score||0}}; ${{counts.classification||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Privacy and security hardening governance checkpoint unavailable.';}}
}}
loadPrivacySecurityHardeningGovernanceCheckpoint();


async function refreshCognitiveAlphaFeatureFreezeIntakeCheckpoint(){{
  const state=document.getElementById('cognitive-alpha-feature-freeze-intake-checkpoint-state');
  const summary=document.getElementById('cognitive-alpha-feature-freeze-intake-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/cognitive-alpha-feature-freeze-intake-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.feature_count||0}} frozen feature domains; ${{counts.readiness_path_count||0}} readiness paths; new feature intake ${{counts.new_feature_intake_open?'open':'closed'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive Alpha feature freeze intake checkpoint unavailable.';}}
}}
refreshCognitiveAlphaFeatureFreezeIntakeCheckpoint();

async function refreshCognitiveAlphaFeatureFreezeExecutionCheckpoint(){{
  const state=document.getElementById('cognitive-alpha-feature-freeze-execution-checkpoint-state');
  const summary=document.getElementById('cognitive-alpha-feature-freeze-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/cognitive-alpha-feature-freeze-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.execution_count||0}} bounded checks; ${{counts.continuity_record_count||0}} continuity records; ${{counts.stable_count||0}} stable.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive Alpha feature freeze execution checkpoint unavailable.';}}
}}
refreshCognitiveAlphaFeatureFreezeExecutionCheckpoint();

async function refreshCognitiveAlphaFeatureFreezeReliabilityCheckpoint(){{
  const state=document.getElementById('cognitive-alpha-feature-freeze-reliability-checkpoint-state');
  const summary=document.getElementById('cognitive-alpha-feature-freeze-reliability-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/cognitive-alpha-feature-freeze-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.continuity_record_count||0}} continuity records; ${{counts.stable_recovery_count||0}} stable recoveries; reliability ${{counts.reliability_score||0}}; ${{counts.classification||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive Alpha feature freeze reliability checkpoint unavailable.';}}
}}
refreshCognitiveAlphaFeatureFreezeReliabilityCheckpoint();

async function refreshCognitiveAlphaFeatureFreezeGovernanceCheckpoint(){{
  const state=document.getElementById('cognitive-alpha-feature-freeze-governance-checkpoint-state');
  const summary=document.getElementById('cognitive-alpha-feature-freeze-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/cognitive-alpha-feature-freeze-governance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.feature_count||0}} frozen domains; ${{counts.readiness_path_count||0}} release paths; ${{counts.stable_recovery_count||0}} stable recoveries; reliability ${{counts.reliability_score||0}}; v1150 benchmark pending.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive Alpha feature freeze governance checkpoint unavailable.';}}
}}
refreshCognitiveAlphaFeatureFreezeGovernanceCheckpoint();

async function refreshReasoningAlphaCheckpoint(){{
  const state=document.getElementById('reasoning-alpha-checkpoint-state');
  const summary=document.getElementById('reasoning-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/reasoning-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.resolved_integration_finding_count||0}} resolved integration findings; ${{counts.registered_checkpoint_count||0}} registered checkpoints; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review pending.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Reasoning Alpha checkpoint unavailable.';}}
}}
refreshReasoningAlphaCheckpoint();

async function refreshReflectionAlphaCheckpoint(){{
  const state=document.getElementById('reflection-alpha-checkpoint-state');
  const summary=document.getElementById('reflection-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/reflection-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable reflection contracts; ${{counts.runtime_reflection_count||0}} runtime reflections inspected structurally; ${{counts.runtime_quarantined_count||0}} quarantined; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review pending.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Reflection Alpha checkpoint unavailable.';}}
}}
refreshReflectionAlphaCheckpoint();

async function refreshBeliefRevisionAlphaCheckpoint(){{
  const state=document.getElementById('belief-revision-alpha-checkpoint-state');
  const summary=document.getElementById('belief-revision-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/belief-revision-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable belief contracts; ${{counts.runtime_belief_count||0}} runtime beliefs inspected structurally; ${{counts.runtime_active_conflict_count||0}} active conflicts; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review pending.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Belief Revision Alpha checkpoint unavailable.';}}
}}
refreshBeliefRevisionAlphaCheckpoint();

async function refreshMultiStepDeliberationAlphaCheckpoint(){{
  const state=document.getElementById('multi-step-deliberation-alpha-checkpoint-state');
  const summary=document.getElementById('multi-step-deliberation-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/multi-step-deliberation-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable deliberation contracts; ${{counts.runtime_session_count||0}} continuity sessions inspected structurally; ${{counts.runtime_pending_count||0}} pending recoveries; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review pending.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Multi-Step Deliberation Alpha checkpoint unavailable.';}}
}}
refreshMultiStepDeliberationAlphaCheckpoint();

async function refreshDecisionBoundaryAlphaCheckpoint(){{
  const state=document.getElementById('decision-boundary-alpha-checkpoint-state');
  const summary=document.getElementById('decision-boundary-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/decision-boundary-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable boundary contracts; ${{counts.runtime_review_record_count||0}} review records inspected structurally; ${{counts.runtime_integrity_mismatch_count||0}} integrity mismatches; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review pending.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Decision-Boundary Alpha checkpoint unavailable.';}}
}}
refreshDecisionBoundaryAlphaCheckpoint();

async function refreshReasoningAlphaConsolidationCheckpoint(){{
  const state=document.getElementById('reasoning-alpha-consolidation-checkpoint-state');
  const summary=document.getElementById('reasoning-alpha-consolidation-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/reasoning-alpha-consolidation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable consolidation contracts; ${{counts.runtime_reasoning_record_count||0}} reasoning records inspected structurally; ${{counts.runtime_reasoning_integrity_mismatch_count||0}} integrity mismatches; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Reasoning Alpha Consolidation checkpoint unavailable.';}}
}}
refreshReasoningAlphaConsolidationCheckpoint();
async function refreshConversationIntentSelectionCheckpoint(){{
  const state=document.getElementById('conversation-intent-selection-checkpoint-state');
  const summary=document.getElementById('conversation-intent-selection-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/conversation-intent-selection-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable intent contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.ordinary_selector_call_site_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversation Intent Selection checkpoint unavailable.';}}
}}
refreshConversationIntentSelectionCheckpoint();

async function refreshContextualConversationBehaviorCheckpoint(){{
  const state=document.getElementById('contextual-conversation-behavior-checkpoint-state');
  const summary=document.getElementById('contextual-conversation-behavior-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/contextual-conversation-behavior-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable behavior contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.ordinary_behavior_call_site_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Contextual Conversation Behavior checkpoint unavailable.';}}
}}
refreshContextualConversationBehaviorCheckpoint();

async function refreshFollowUpSilenceCheckpoint(){{
  const state=document.getElementById('follow-up-silence-checkpoint-state');
  const summary=document.getElementById('follow-up-silence-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/follow-up-silence-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable follow-up and silence contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.ordinary_policy_call_site_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Follow-Up and Intentional Silence checkpoint unavailable.';}}
}}
refreshFollowUpSilenceCheckpoint();

async function refreshCognitiveIntegrationAlphaCheckpoint(){{
  const state=document.getElementById('cognitive-integration-alpha-checkpoint-state');
  const summary=document.getElementById('cognitive-integration-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/cognitive-integration-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable policy contracts; ${{counts.persistence_contract_check_count||0}} continuity contracts; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.runtime_integrity_mismatch_count||0}} runtime integrity mismatches; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Cognitive Integration Alpha checkpoint unavailable.';}}
}}
refreshCognitiveIntegrationAlphaCheckpoint();

async function refreshConversationPolicyCheckpoint(){{
  const state=document.getElementById('conversation-policy-checkpoint-state');
  const summary=document.getElementById('conversation-policy-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/conversation-policy-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable discourse contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversation Policy checkpoint unavailable.';}}
}}
refreshConversationPolicyCheckpoint();

async function refreshNaturalConversationContinuityCheckpoint(){{
  const state=document.getElementById('natural-conversation-continuity-checkpoint-state');
  const summary=document.getElementById('natural-conversation-continuity-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/natural-conversation-continuity-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable continuity contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Natural Conversation Continuity checkpoint unavailable.';}}
}}
refreshNaturalConversationContinuityCheckpoint();

async function refreshNaturalFollowUpCheckpoint(){{
  const state=document.getElementById('natural-follow-up-checkpoint-state');
  const summary=document.getElementById('natural-follow-up-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/natural-follow-up-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable follow-up contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.runtime_diagnostics_integrity_check_count||0}} diagnostics integrity checks; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Natural Follow-Up checkpoint unavailable.';}}
}}
refreshNaturalFollowUpCheckpoint();

async function refreshGovernedSpeechCheckpoint(){{
  const state=document.getElementById('governed-speech-checkpoint-state');
  const summary=document.getElementById('governed-speech-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/governed-speech-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable speech contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.response_audit_case_count||0}} response-audit cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Governed Proactive Speech checkpoint unavailable.';}}
}}
refreshGovernedSpeechCheckpoint();

async function refreshDailyCompanionCognitionCheckpoint(){{
  const state=document.getElementById('daily-companion-cognition-checkpoint-state');
  const summary=document.getElementById('daily-companion-cognition-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/daily-companion-cognition-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable companion contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.response_audit_case_count||0}} response-audit cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Daily Companion Cognition checkpoint unavailable.';}}
}}
refreshDailyCompanionCognitionCheckpoint();

async function refreshUnifiedMemoryCheckpoint(){{
  const state=document.getElementById('unified-memory-checkpoint-state');
  const summary=document.getElementById('unified-memory-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/unified-memory-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable memory contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.selection_audit_case_count||0}} selection-audit cases; ${{counts.memory_domain_count||0}} memory domains; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Unified Memory checkpoint unavailable.';}}
}}
refreshUnifiedMemoryCheckpoint();

async function refreshMemoryRetrievalRelevanceCheckpoint(){{
  const state=document.getElementById('memory-retrieval-relevance-checkpoint-state');
  const summary=document.getElementById('memory-retrieval-relevance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/memory-retrieval-relevance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable retrieval contracts; ${{counts.synthetic_case_count||0}} bounded cases; ${{counts.selection_audit_case_count||0}} selection-audit cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Retrieval Relevance checkpoint unavailable.';}}
}}
refreshMemoryRetrievalRelevanceCheckpoint();

async function refreshImmediateMemoryLearningCheckpoint(){{
  const state=document.getElementById('immediate-memory-learning-checkpoint-state');
  const summary=document.getElementById('immediate-memory-learning-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/immediate-memory-learning-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable learning contracts; ${{counts.projection_case_count||0}} projections; ${{counts.handoff_case_count||0}} handoffs; ${{counts.receipt_case_count||0}} receipt cases; ${{counts.learning_audit_case_count||0}} audit cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Immediate Learning checkpoint unavailable.';}}
}}
refreshImmediateMemoryLearningCheckpoint();

async function refreshBoundedExperientialLessonsCheckpoint(){{
  const state=document.getElementById('bounded-experiential-lessons-checkpoint-state');
  const summary=document.getElementById('bounded-experiential-lessons-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/bounded-experiential-lessons-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable lesson contracts; ${{counts.projection_case_count||0}} projections; ${{counts.handoff_case_count||0}} handoffs; ${{counts.receipt_case_count||0}} receipt cases; ${{counts.lesson_audit_case_count||0}} audit cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Bounded Experiential Lessons checkpoint unavailable.';}}
}}
refreshBoundedExperientialLessonsCheckpoint();

async function refreshMemoryExperientialLearningAlphaCheckpoint(){{
  const state=document.getElementById('memory-experiential-learning-alpha-checkpoint-state');
  const summary=document.getElementById('memory-experiential-learning-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/memory-experiential-learning-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable alpha contracts; ${{counts.projection_case_count||0}} projections; ${{counts.handoff_case_count||0}} handoffs; ${{counts.audit_case_count||0}} audits; ${{counts.reliability_case_count||0}} reliability cases; ${{counts.receipt_case_count||0}} receipt cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Memory and Experiential Learning Alpha checkpoint unavailable.';}}
}}
refreshMemoryExperientialLearningAlphaCheckpoint();

async function refreshHierarchicalPlanningCheckpoint(){{
  const state=document.getElementById('hierarchical-planning-checkpoint-state');
  const summary=document.getElementById('hierarchical-planning-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/hierarchical-planning-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} structural checks; ${{counts.projection_case_count||0}} hierarchy cases; ${{counts.review_case_count||0}} review cases; ${{counts.handoff_case_count||0}} handoffs; ${{counts.reliability_case_count||0}} reliability cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Hierarchical Planning checkpoint unavailable.';}}
}}

async function refreshPlanSimulationCheckpoint(){{
  const state=document.getElementById('plan-simulation-checkpoint-state');
  const summary=document.getElementById('plan-simulation-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/plan-simulation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} structural checks; ${{counts.projection_case_count||0}} simulation cases; ${{counts.review_case_count||0}} review cases; ${{counts.handoff_case_count||0}} handoffs; ${{counts.reliability_case_count||0}} reliability cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Plan Simulation checkpoint unavailable.';}}
}}

async function refreshPersistentFollowThroughCheckpoint(){{
  const state=document.getElementById('persistent-follow-through-checkpoint-state');
  const summary=document.getElementById('persistent-follow-through-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/persistent-follow-through-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} structural checks; ${{counts.projection_case_count||0}} continuity cases; ${{counts.review_case_count||0}} review cases; ${{counts.handoff_case_count||0}} handoffs; ${{counts.reliability_case_count||0}} reliability cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Persistent Follow-Through checkpoint unavailable.';}}
}}

async function refreshNaturalLanguageActionExecutionCheckpoint(){{
  const state=document.getElementById('natural-language-action-execution-checkpoint-state');
  const summary=document.getElementById('natural-language-action-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/natural-language-action-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.intent_projection_case_count||0}} intent cases; ${{counts.proposal_handoff_case_count||0}} proposal handoffs; ${{counts.execution_admission_case_count||0}} admission cases; ${{counts.synthetic_result_case_count||0}} synthetic result contracts; ${{counts.execution_eligible_capability_count||0}} eligible low-risk capabilities; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Natural-Language Action and Supervised Execution checkpoint unavailable.';}}
}}
async function refreshClarificationArgumentRoutingCheckpoint(){{
  const state=document.getElementById('clarification-argument-routing-checkpoint-state');
  const summary=document.getElementById('clarification-argument-routing-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/clarification-argument-routing-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.projection_case_count||0}} routing cases; ${{counts.argument_schema_count||0}} registered schemas; ${{counts.clarification_answer_case_count||0}} answer cases; ${{counts.proposal_binding_case_count||0}} proposal bindings; ${{counts.continuity_case_count||0}} continuity cases; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Clarification and Argument Routing checkpoint unavailable.';}}
}}
async function refreshNaturalLanguageActionApprovalGovernanceCheckpoint(){{
  const state=document.getElementById('natural-language-action-approval-governance-checkpoint-state');
  const summary=document.getElementById('natural-language-action-approval-governance-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/natural-language-action-approval-governance-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.retained_checkpoint_count||0}} retained checkpoints; ${{counts.lifecycle_case_count||0}} lifecycle cases; ${{counts.negative_boundary_case_count||0}} boundary cases; ${{counts.terminal_state_case_count||0}} terminal states; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Natural-Language Action and Approval Governance checkpoint unavailable.';}}
}}
async function refreshNaturalLanguageActionAuthoritativeResultCheckpoint(){{
  const state=document.getElementById('natural-language-action-authoritative-result-checkpoint-state');
  const summary=document.getElementById('natural-language-action-authoritative-result-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/natural-language-action-authoritative-result-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.terminal_result_case_count||0}} terminal result cases; ${{counts.negative_boundary_case_count||0}} boundary cases; ${{counts.presentation_case_count||0}} presentation cases; ${{counts.recovery_case_count||0}} recovery cases; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Natural-Language Action and Authoritative Result checkpoint unavailable.';}}
}}
async function refreshNaturalLanguageActionCheckpoint(){{
  const state=document.getElementById('natural-language-action-checkpoint-state');
  const summary=document.getElementById('natural-language-action-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/natural-language-action-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.lifecycle_state_case_count||0}} lifecycle states; ${{counts.exact_status_case_count||0}} exact status cases; ${{counts.follow_up_continuity_case_count||0}} continuity cases; ${{counts.reliability_case_count||0}} reliability cases; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Natural-Language Action checkpoint unavailable.';}}
}}
async function refreshSupervisedProjectInspectionPlanningCheckpoint(){{
  const state=document.getElementById('supervised-project-inspection-planning-checkpoint-state');
  const summary=document.getElementById('supervised-project-inspection-planning-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-project-inspection-planning-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.inspected_file_case_count||0}} inspected files; ${{counts.deficiency_candidate_case_count||0}} deficiency candidates; ${{counts.specification_case_count||0}} specifications; ${{counts.implementation_plan_case_count||0}} implementation/test plans; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised Project Inspection and Planning checkpoint unavailable.';}}
}}
async function refreshSupervisedImplementationCheckpoint(){{
  const state=document.getElementById('supervised-implementation-checkpoint-state');
  const summary=document.getElementById('supervised-implementation-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-implementation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.preparation_case_count||0}} preparations; ${{counts.private_draft_case_count||0}} private drafts; ${{counts.review_decision_case_count||0}} review decisions; ${{counts.sandbox_materialization_case_count||0}} sandbox materialization cases; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised Implementation checkpoint unavailable.';}}
}}
async function refreshSupervisedSandboxTestingRepairCheckpoint(){{
  const state=document.getElementById('supervised-sandbox-testing-repair-checkpoint-state');
  const summary=document.getElementById('supervised-sandbox-testing-repair-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-sandbox-testing-repair-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.sandbox_execution_case_count||0}} sandbox execution cases; ${{counts.evidence_outcome_case_count||0}} evidence outcomes; ${{counts.diagnosis_case_count||0}} diagnosis cases; ${{counts.repair_plan_case_count||0}} repair plans; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised Sandbox Testing and Repair checkpoint unavailable.';}}
}}

async function refreshSupervisedSandboxRepairDraftCheckpoint(){{
  const state=document.getElementById('supervised-sandbox-repair-draft-checkpoint-state');
  const summary=document.getElementById('supervised-sandbox-repair-draft-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-sandbox-repair-draft-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.valid_repair_draft_case_count||0}} private draft cases; ${{counts.negative_boundary_case_count||0}} boundary cases; ${{counts.public_summary_case_count||0}} content-free summaries; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised Sandbox Repair Draft Foundations checkpoint unavailable.';}}
}}


async function refreshSupervisedSandboxRepairMaterializationCheckpoint(){{
  const state=document.getElementById('supervised-sandbox-repair-materialization-checkpoint-state');
  const summary=document.getElementById('supervised-sandbox-repair-materialization-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-sandbox-repair-materialization-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; explicit repair review, isolated sandbox materialization, and rollback evidence verified; retesting remains separately governed; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator Repair Review and Sandbox Materialization checkpoint unavailable.';}}
}}
async function refreshSupervisedSandboxRetestingCheckpoint(){{
  const state=document.getElementById('supervised-sandbox-retesting-checkpoint-state');
  const summary=document.getElementById('supervised-sandbox-retesting-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-sandbox-retesting-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; governed retesting, before/after evidence, regression detection, and bounded repair results verified; consolidated by v1183.9.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Governed Sandbox Retesting checkpoint unavailable.';}}
}}

async function refreshSupervisedProjectDevelopmentFoundations(){{
  const state=document.getElementById('supervised-project-development-foundations-state');
  const summary=document.getElementById('supervised-project-development-foundations-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-project-development-foundations-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.stage_count||0}} governed stages linked; content-free and authority-free. Next bounded unit: v1184.3-v1184.5.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised Project-Development Foundations unavailable.';}}
}}

async function refreshSupervisedSandboxRepairRetestCheckpoint(){{
  const state=document.getElementById('supervised-sandbox-repair-retest-checkpoint-state');
  const summary=document.getElementById('supervised-sandbox-repair-retest-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-sandbox-repair-retest-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.successful_repair_case_count||0}} successful repairs; ${{counts.persistent_failure_case_count||0}} persistent failure case; ${{counts.regression_case_count||0}} regression case; ${{counts.rollback_evidence_case_count||0}} rollback evidence cases; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200. Next bounded unit: v1184.0-v1184.2.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised Sandbox Repair and Retest checkpoint unavailable.';}}
}}

async function refreshGoalAndPlanningAlphaCheckpoint(){{
  const state=document.getElementById('goal-and-planning-alpha-checkpoint-state');
  const summary=document.getElementById('goal-and-planning-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/goal-and-planning-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} structural checks; ${{counts.projection_case_count||0}} alpha cases; ${{counts.review_case_count||0}} review cases; ${{counts.handoff_case_count||0}} handoffs; ${{counts.reliability_case_count||0}} reliability cases; ${{counts.consolidated_stage_count||0}} consolidated stages; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Goal and Planning Alpha checkpoint unavailable.';}}
}}

async function refreshInternallyGeneratedGoalCandidateCheckpoint(){{
  const state=document.getElementById('internally-generated-goal-candidate-checkpoint-state');
  const summary=document.getElementById('internally-generated-goal-candidate-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/internally-generated-goal-candidate-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.synthetic_contract_check_count||0}} executable goal contracts; ${{counts.projection_case_count||0}} projections; ${{counts.review_case_count||0}} review cases; ${{counts.handoff_case_count||0}} handoffs; ${{counts.reliability_case_count||0}} reliability cases; ${{counts.receipt_case_count||0}} receipt cases; ${{counts.authoritative_conversation_path_count||0}} authoritative conversation paths; ${{counts.open_limitation_count||0}} explicit limitations; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Internally Generated Goal Candidate checkpoint unavailable.';}}
}}
refreshInternallyGeneratedGoalCandidateCheckpoint();
refreshHierarchicalPlanningCheckpoint();
refreshPlanSimulationCheckpoint();
refreshPersistentFollowThroughCheckpoint();
refreshGoalAndPlanningAlphaCheckpoint();
refreshNaturalLanguageActionExecutionCheckpoint();
refreshClarificationArgumentRoutingCheckpoint();
refreshNaturalLanguageActionApprovalGovernanceCheckpoint();
refreshNaturalLanguageActionAuthoritativeResultCheckpoint();
refreshNaturalLanguageActionCheckpoint();
refreshSupervisedProjectInspectionPlanningCheckpoint();
refreshSupervisedImplementationCheckpoint();
refreshSupervisedSandboxTestingRepairCheckpoint();
refreshSupervisedSandboxRepairDraftCheckpoint();
refreshSupervisedSandboxRepairMaterializationCheckpoint();
refreshSupervisedSandboxRetestingCheckpoint();
refreshSupervisedSandboxRepairRetestCheckpoint();
refreshSupervisedProjectDevelopmentFoundations();


async function refreshSupervisedProjectOutcomeLearning(){{
  const state=document.getElementById('supervised-project-outcome-learning-state');
  const summary=document.getElementById('supervised-project-outcome-learning-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-project-outcome-learning-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; accepted, rejected, failed, and repaired outcomes remain content-free and authority-free.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Project outcome learning unavailable.';}}
}}
refreshSupervisedProjectOutcomeLearning();

async function refreshSupervisedProjectReliabilityRecovery(){{
  const state=document.getElementById('supervised-project-reliability-recovery-state');
  const summary=document.getElementById('supervised-project-reliability-recovery-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-project-reliability-recovery-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; drift, recovery, rollback, and privacy boundaries remain authority-free.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Project reliability and recovery unavailable.';}}
}}
refreshSupervisedProjectReliabilityRecovery();

async function refreshSupervisedProjectDevelopmentAlphaCheckpoint(){{
  const state=document.getElementById('supervised-project-development-alpha-checkpoint-state');
  const summary=document.getElementById('supervised-project-development-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/supervised-project-development-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.governed_stage_count||0}} governed stages; ${{counts.outcome_case_count||0}} outcome classes; ${{counts.interruption_state_case_count||0}} recovery states; ${{counts.negative_boundary_case_count||0}} adversarial boundaries; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised Project Development Alpha checkpoint unavailable.';}}
}}
refreshSupervisedProjectDevelopmentAlphaCheckpoint();

async function refreshPersistentSupervisedDeveloperAlphaCheckpoint(){{
  const state=document.getElementById('persistent-supervised-developer-alpha-checkpoint-state');
  const summary=document.getElementById('persistent-supervised-developer-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/persistent-supervised-developer-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.valid_transition_case_count||0}} governed transitions; ${{counts.budget_exhaustion_case_count||0}} budget boundaries; ${{counts.stale_work_case_count||0}} stale/drift cases; ${{counts.recovery_reason_case_count||0}} recovery reasons; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Persistent Supervised Developer Alpha checkpoint unavailable.';}}
}}
refreshPersistentSupervisedDeveloperAlphaCheckpoint();
async function refreshDurableCampaignContinuationCheckpoint(){{
  const state=document.getElementById('durable-campaign-continuation-checkpoint-state');
  const summary=document.getElementById('durable-campaign-continuation-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/durable-campaign-continuation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.storage_generation_case_count||0}} storage generations; ${{counts.restoration_decision_case_count||0}} restoration decisions; ${{counts.eligibility_decision_case_count||0}} resume decisions; ${{counts.stale_takeover_case_count||0}} stale-lease cases; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Durable Campaign Continuation checkpoint unavailable.';}}
}}
refreshDurableCampaignContinuationCheckpoint();

async function refreshPersistentCampaignWorkExecutionCheckpoint(){{
  const state=document.getElementById('persistent-campaign-work-execution-checkpoint-state');
  const summary=document.getElementById('persistent-campaign-work-execution-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/persistent-campaign-work-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.successful_execution_case_count||0}} successful execution cases; ${{counts.failed_execution_case_count||0}} failed execution case; ${{counts.continuation_action_case_count||0}} continuation actions; ${{counts.negative_boundary_case_count||0}} negative boundaries; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Persistent Campaign Work Execution checkpoint unavailable.';}}
}}
refreshPersistentCampaignWorkExecutionCheckpoint();

async function refreshPersistentSupervisedDeveloperAlphaHardeningCheckpoint(){{
  const state=document.getElementById('persistent-supervised-developer-alpha-hardening-checkpoint-state');
  const summary=document.getElementById('persistent-supervised-developer-alpha-hardening-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/persistent-supervised-developer-alpha-hardening-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.session_state_case_count||0}} session states; ${{counts.reliability_review_case_count||0}} review cases; ${{counts.blocked_boundary_case_count||0}} blocked boundaries; ${{counts.durable_nonce_case_count||0}} durable nonce cases; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Persistent Supervised Developer Alpha Hardening checkpoint unavailable.';}}
}}
refreshPersistentSupervisedDeveloperAlphaHardeningCheckpoint();

async function refreshUnifiedExperienceCheckpoint(){{
  const state=document.getElementById('unified-experience-checkpoint-state');
  const summary=document.getElementById('unified-experience-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/unified-experience-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.domain_count||0}} domains; ${{counts.approved_navigation_domain_count||0}} approved navigation targets; ${{counts.reliability_review_case_count||0}} reliability reviews; ${{counts.blocked_boundary_case_count||0}} blocked boundaries; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Unified Experience checkpoint unavailable.';}}
}}
refreshUnifiedExperienceCheckpoint();

async function refreshUnifiedExperienceFoundationsCheckpoint(){{
  const reliabilityState=document.getElementById('unified-experience-reliability-checkpoint-state');
  const reliabilitySummary=document.getElementById('unified-experience-reliability-checkpoint-summary');
  if(reliabilityState&&reliabilitySummary){{try{{const response=await fetch('/api/cognition/unified-experience-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};reliabilityState.textContent=data.ok?'ready':'review';reliabilityState.dataset.state=data.ok?'ready':'attention';reliabilitySummary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.approved_reliability_count||0}} approved; ${{counts.rejected_reliability_count||0}} rejected; ${{counts.deferred_reliability_count||0}} deferred; ${{counts.blocked_boundary_case_count||0}} blocked boundaries.`;}}catch(error){{reliabilityState.textContent='unavailable';reliabilityState.dataset.state='attention';reliabilitySummary.textContent='Unified Experience Reliability checkpoint unavailable.';}}}}
  const navState=document.getElementById('unified-experience-navigation-checkpoint-state');
  const navSummary=document.getElementById('unified-experience-navigation-checkpoint-summary');
  if(navState&&navSummary){{
  try{{const response=await fetch('/api/cognition/unified-experience-navigation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};navState.textContent=data.ok?'ready':'review';navState.dataset.state=data.ok?'ready':'attention';navSummary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.approved_navigation_count||0}} approved; ${{counts.rejected_navigation_count||0}} rejected; ${{counts.deferred_navigation_count||0}} deferred; ${{counts.blocked_boundary_case_count||0}} blocked boundaries; focus ${{counts.from_domain||'none'}}→${{counts.presented_domain||'none'}}.`;}}catch(error){{navState.textContent='unavailable';navState.dataset.state='attention';navSummary.textContent='Unified Experience Navigation checkpoint unavailable.';}}
  }}
  const state=document.getElementById('unified-experience-foundations-checkpoint-state');
  const summary=document.getElementById('unified-experience-foundations-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/unified-experience-foundations-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.domain_count||0}} unified domains; ${{counts.blocked_boundary_case_count||0}} blocked boundaries; focus ${{counts.selected_domain||'none'}}; ${{counts.review_required_surface_count||0}} review-required surface; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Unified Experience Foundations checkpoint unavailable.';}}
}}
refreshUnifiedExperienceFoundationsCheckpoint();

async function refreshCompleteCampaignDevelopmentLoopAlphaCheckpoint(){{
  const state=document.getElementById('complete-campaign-development-loop-alpha-checkpoint-state');
  const summary=document.getElementById('complete-campaign-development-loop-alpha-checkpoint-summary');
  if(!state||!summary)return;
  try{{const response=await fetch('/api/cognition/complete-campaign-development-loop-alpha-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.complete_loop_case_count||0}} loop outcomes; ${{counts.interruption_case_count||0}} interruption cases; ${{counts.recovery_decision_case_count||0}} recovery decisions; ${{counts.learning_case_count||0}} bounded learning cases; Desktop review deferred to v1200.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Complete Campaign Development Loop checkpoint unavailable.';}}
}}
refreshCompleteCampaignDevelopmentLoopAlphaCheckpoint();



(async()=>{{const state=document.getElementById('responsive-work-queue-review-checkpoint-state');const summary=document.getElementById('responsive-work-queue-review-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/responsive-work-queue-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.approved_action_count||0}} reviewed actions; cancelled state ${{counts.cancel_presented_state||'unavailable'}}; no real work cancelled.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator Queue Review checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('responsive-work-queue-reliability-checkpoint-state');const summary=document.getElementById('responsive-work-queue-reliability-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/responsive-work-queue-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.event_count||0}} reliability classes; foreground-first ${{counts.foreground_first_count||0}}; no work executed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Responsive Work Reliability checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('responsiveness-background-work-checkpoint-state');const summary=document.getElementById('responsiveness-background-work-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/responsiveness-background-work-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.software_development_routing_case_count||0}} chat-routing cases; CRLF rollback preserved ${{counts.raw_crlf_rollback_preserved===true?'yes':'no'}}; next v1192.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Responsiveness and Background Work checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('responsive-work-queue-checkpoint-state');const summary=document.getElementById('responsive-work-queue-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/responsive-work-queue-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.item_count||0}} bounded items; foreground unblocked ${{counts.foreground_unblocked===true?'yes':'no'}}; no work executed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Responsive Work Queue checkpoint unavailable.';}}}})();

(async()=>{{const state=document.getElementById('bounded-evidence-compaction-checkpoint-state');const summary=document.getElementById('bounded-evidence-compaction-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/bounded-evidence-compaction-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.record_count||0}} records; exact expansion ${{counts.equivalent===true?'yes':'no'}}; next v1192.3.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Bounded Evidence Compaction checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('evidence-compaction-review-checkpoint-state');const summary=document.getElementById('evidence-compaction-review-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/evidence-compaction-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; approved ${{counts.approved_count||0}}, rejected ${{counts.rejected_count||0}}, deferred ${{counts.deferred_count||0}}; originals preserved ${{counts.original_evidence_preserved===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator Evidence Compaction Review unavailable.';}}}})();

(async()=>{{const state=document.getElementById('evidence-compaction-reliability-checkpoint-state');const summary=document.getElementById('evidence-compaction-reliability-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/evidence-compaction-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; records ${{counts.record_count||0}}; replay ${{counts.replay_detected===true?'detected':'clear'}}; originals preserved ${{counts.original_evidence_preserved===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Evidence Compaction Reliability unavailable.';}}}})();
(async()=>{{const state=document.getElementById('evidence-compaction-checkpoint-state');const summary=document.getElementById('evidence-compaction-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/evidence-compaction-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.evidence_record_count||0}} evidence records across ${{counts.unified_domain_count||0}} domains; exact expansion ${{counts.exact_expansion_verified===true?'yes':'no'}}; originals preserved ${{counts.original_evidence_preserved===true?'yes':'no'}}; next v1193.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Bounded Evidence Compaction checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('verifier-ownership-checkpoint-state');const summary=document.getElementById('verifier-ownership-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/verifier-ownership-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const counts=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; ${{counts.owner_count||0}} owners; ${{counts.current_regression_count||0}} current; ${{counts.historical_debt_count||0}} inherited debt; next v1193.3.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Verifier ownership checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('verifier-profile-reconciliation-checkpoint-state');const summary=document.getElementById('verifier-profile-reconciliation-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/verifier-profile-reconciliation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const quick=(data.summaries||{{}}).quick||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; quick current=${{quick.current_regressions_passed===true?'pass':'review'}}; inherited non-pass=${{quick.inherited_nonpass_count||0}}; global pass not claimed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Verifier profile reconciliation unavailable.';}}}})();
(async()=>{{const state=document.getElementById('fixture-historical-debt-consolidation-checkpoint-state');const summary=document.getElementById('fixture-historical-debt-consolidation-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/fixture-historical-debt-consolidation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; aliases=${{view.alias_count||0}}; deferred=${{view.deferred_count||0}}; historical truth preserved=${{view.historical_truth_preserved===true?'yes':'review'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Fixture consolidation unavailable.';}}}})();
(async()=>{{const state=document.getElementById('verifier-historical-debt-checkpoint-state');const summary=document.getElementById('verifier-historical-debt-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/verifier-historical-debt-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; owners=${{view.owner_count||0}}; inherited non-pass=${{view.inherited_nonpass_count||0}}; aliases=${{view.alias_count||0}}; deferred=${{view.deferred_count||0}}; global pass not claimed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Verifier ownership and historical-debt checkpoint unavailable.';}}}})();

(async()=>{{const state=document.getElementById('unified-cognitive-developer-experience-state');const summary=document.getElementById('unified-cognitive-developer-experience-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/unified-cognitive-developer-experience-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; domains=${{view.domain_count||0}}; foreground=${{view.foreground_path_available===true?'available':'blocked'}}; evidence preserved=${{view.original_evidence_preserved===true?'yes':'no'}}; inherited debt visible=${{view.inherited_debt_visible===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Unified Cognitive and Developer Experience unavailable.';}}}})();

(async()=>{{const state=document.getElementById('unified-cognitive-developer-coordination-state');const summary=document.getElementById('unified-cognitive-developer-coordination-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/unified-cognitive-developer-coordination-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; decision=${{view.decision||'none'}}; focus changed=${{view.focus_changed===true?'yes':'no'}}; evidence preserved=${{view.original_evidence_preserved===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator coordination unavailable.';}}}})();
(async()=>{{const state=document.getElementById('unified-cognitive-developer-reliability-state');const summary=document.getElementById('unified-cognitive-developer-reliability-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/unified-cognitive-developer-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; events=${{view.event_class_count||0}}; latency=${{view.latency_within_budget===true?'bounded':'review'}}; recovery executed=${{view.recovery_executed===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Unified reliability unavailable.';}}}})();
(async()=>{{const state=document.getElementById('unified-cognitive-developer-checkpoint-state');const summary=document.getElementById('unified-cognitive-developer-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/unified-cognitive-developer-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; domains=${{view.domain_count||0}}; decisions=${{view.decision_count||0}}; events=${{view.reliability_event_class_count||0}}; evidence preserved=${{view.original_evidence_preserved===true?'yes':'review'}}; global pass not claimed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Unified Cognitive and Developer Experience checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('general-test-adapter-consolidation-checkpoint-state');const summary=document.getElementById('general-test-adapter-consolidation-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/general-test-adapter-consolidation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; adapters=${{view.adapter_count||0}}; project kinds=${{view.concrete_project_kind_count||0}}; dispatch states=${{view.dispatch_error_class_count||0}}; no project tests executed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='General Test Adapter Consolidation checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('conversational-build-test-loop-checkpoint-state');const summary=document.getElementById('conversational-build-test-loop-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/conversational-build-test-loop-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; project kinds=${{view.supported_project_kind_count||0}}; separate authorization=${{view.separate_loop_authorization?'yes':'no'}}; checkpoint executed no builds or tests.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversational Build-and-Test Loop checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('operator-build-test-results-checkpoint-state');const summary=document.getElementById('operator-build-test-results-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/operator-build-test-results-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; outcomes=${{view.outcome_count||0}}; decisions=${{view.decision_count||0}}; continuation=${{view.continuation_preparation_only?'prepared only':'review'}}; no builds or tests executed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator build-and-test results checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('conversational-build-test-continuation-checkpoint-state');const summary=document.getElementById('conversational-build-test-continuation-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/conversational-build-test-continuation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; outcomes=${{view.continuation_outcome_count||0}}; lineage=${{view.attempt_lineage_length||0}} attempts; separate authorization=${{view.separate_authorization_required?'required':'review'}}; no builds or tests executed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversational build-and-test continuation checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('bounded-automatic-diagnosis-checkpoint-state');const summary=document.getElementById('bounded-automatic-diagnosis-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/bounded-automatic-diagnosis-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; diagnosable outcomes=${{view.diagnosable_outcome_count||0}}; root cause proven=${{view.root_cause_proven===true?'yes':'no'}}; repair authorized=${{view.repair_authorized===true?'yes':'no'}}; checkpoint executed no diagnosis or tests.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Bounded automatic diagnosis checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('operator-diagnosis-review-checkpoint-state');const summary=document.getElementById('operator-diagnosis-review-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/operator-diagnosis-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; decisions=${{view.review_decision_count||0}}; repair proposal=${{view.repair_proposal_preparation_present===true?'review-gated':'unavailable'}}; repair executed=${{view.repair_executed===true?'yes':'no'}}; authority=${{view.authority_preserved===true?'preserved':'review'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator diagnosis review checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('conversational-supervised-repair-execution-checkpoint-state');const summary=document.getElementById('conversational-supervised-repair-execution-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/conversational-supervised-repair-execution-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; repair attempt limit=${{view.repair_attempt_limit||0}}; outcomes=${{view.result_outcome_count||0}}; operator review=${{view.operator_review_required===true?'required':'review'}}; apply=${{view.apply_authorized===true?'authorized':'blocked'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Conversational supervised repair execution checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('operator-repair-result-review-checkpoint-state');const summary=document.getElementById('operator-repair-result-review-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/operator-repair-result-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; outcomes=${{view.repair_result_outcome_count||0}}; passing decisions=${{view.passing_decision_count||0}}; separate apply authorization=${{view.separate_apply_authorization_required===true?'required':'review'}}; apply executed=${{view.apply_executed===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator repair-result review checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('supervised-repaired-candidate-apply-checkpoint-state');const summary=document.getElementById('supervised-repaired-candidate-apply-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/supervised-repaired-candidate-apply-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; outcomes=${{view.apply_result_outcome_count||0}}; apply attempt limit=${{view.apply_attempt_limit||0}}; rollback evidence=${{view.rollback_evidence_required_before_write===true?'required':'review'}}; checkpoint apply executed=${{view.checkpoint_apply_executed===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised repaired-candidate apply checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('operator-repaired-candidate-apply-result-review-checkpoint-state');const summary=document.getElementById('operator-repaired-candidate-apply-result-review-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/operator-repaired-candidate-apply-result-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; outcomes=${{view.apply_result_outcome_count||0}}; rollback decisions=${{view.rollback_eligible_decision_count||0}}; separate rollback authorization=${{view.separate_rollback_authorization_required===true?'required':'review'}}; checkpoint rollback executed=${{view.checkpoint_rollback_executed===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator repaired-candidate apply-result review checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('supervised-repaired-candidate-rollback-checkpoint-state');const summary=document.getElementById('supervised-repaired-candidate-rollback-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/supervised-repaired-candidate-rollback-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; outcomes=${{view.rollback_result_outcome_count||0}}; rollback attempt limit=${{view.rollback_attempt_limit||0}}; sealed manifest=${{view.sealed_v1217_manifest_required===true?'required':'review'}}; checkpoint rollback executed=${{view.checkpoint_rollback_executed===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Supervised repaired-candidate rollback checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('operator-repaired-candidate-rollback-result-review-checkpoint-state');const summary=document.getElementById('operator-repaired-candidate-rollback-result-review-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/operator-repaired-candidate-rollback-result-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; outcomes=${{view.rollback_result_outcome_count||0}}; dispositions=${{view.rollback_result_decision_count||0}}; terminal-only=${{view.terminal_disposition_only===true?'yes':'review'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Rollback-result review checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('unified-supervised-development-transaction-history-checkpoint-state');const summary=document.getElementById('unified-supervised-development-transaction-history-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/unified-supervised-development-transaction-history-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; stage specs=${{view.stage_spec_count||0}}; synthetic events=${{view.synthetic_event_count||0}}; page limit=${{view.maximum_page_size||0}}; receipts authoritative=${{view.authoritative_receipts_preserved===true?'yes':'review'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Unified transaction-history checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('transaction-resumption-abandoned-work-reconciliation-checkpoint-state');const summary=document.getElementById('transaction-resumption-abandoned-work-reconciliation-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/transaction-resumption-abandoned-work-reconciliation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; classes=${{view.assessment_class_count||0}}; decisions=${{view.operator_decision_count||0}}; old authority reusable=${{view.old_authority_reuse_forbidden===true?'no':'review'}}; fresh approval required=${{view.new_approval_required_before_continuation===true?'yes':'review'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Transaction-resumption checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('long-session-multi-day-soak-checkpoint-state');const summary=document.getElementById('long-session-multi-day-soak-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/long-session-multi-day-soak-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; mode=${{view.soak_mode||'unknown'}}; intervals=${{view.interval_count||0}}; days=${{view.day_count||0}}; sessions=${{view.session_count||0}}; no real waiting; execution=${{view.execution_invoked===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Long-session and multi-day soak foundations unavailable.';}}}})();
(async()=>{{const state=document.getElementById('operator-reviewed-soak-progression-state');const summary=document.getElementById('operator-reviewed-soak-progression-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/operator-reviewed-soak-progression-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; decisions=${{view.decision_count||0}}; actions=${{view.action_count||0}}; lineage=${{view.multi_session_lineage_verified===true?'exact':'blocked'}}; execution=${{view.execution_invoked===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Operator-reviewed soak progression unavailable.';}}}})();
(async()=>{{const state=document.getElementById('soak-reliability-adversarial-state');const summary=document.getElementById('soak-reliability-adversarial-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/soak-reliability-adversarial-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; events=${{view.event_class_count||0}}; blocked=${{view.blocked_count||0}}; recovery=${{view.automatic_recovery===true?'yes':'no'}}; execution=${{view.execution_invoked===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Soak reliability hardening unavailable.';}}}})();
(async()=>{{const state=document.getElementById('long-session-multi-day-soak-consolidated-checkpoint-state');const summary=document.getElementById('long-session-multi-day-soak-consolidated-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/long-session-multi-day-soak-consolidated-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; modes=${{view.soak_mode_count||0}}; domains=${{view.domain_count||0}}; actions=${{view.progression_action_count||0}}; events=${{view.reliability_event_class_count||0}}; no real waiting; global pass not claimed.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Long-session and multi-day soak checkpoint unavailable.';}}}})();

(async()=>{{const state=document.getElementById('adversarial-privacy-authority-state');const summary=document.getElementById('adversarial-privacy-authority-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/adversarial-privacy-authority-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; attacks=${{view.attack_class_count||0}}; domains=${{view.authority_domain_count||0}}; authority=${{view.authority_state||'unknown'}}; execution=${{view.execution_invoked===true?'yes':'no'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Adversarial privacy and authority checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('adversarial-replay-recovery-review-state');const summary=document.getElementById('adversarial-replay-recovery-review-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/adversarial-replay-recovery-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; events=${{view.event_class_count||0}}; decisions=${{view.decision_count||0}}; recovery=${{view.recovery_executed===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Adversarial replay and recovery review unavailable.';}}}})();
(async()=>{{const state=document.getElementById('adversarial-reliability-integration-state');const summary=document.getElementById('adversarial-reliability-integration-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/adversarial-reliability-integration-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; events=${{view.event_class_count||0}}; surfaces=${{view.surface_count||0}}; recovery=${{view.automatic_recovery_executed===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Adversarial reliability and integration unavailable.';}}}})();
(async()=>{{const state=document.getElementById('adversarial-privacy-authority-replay-recovery-checkpoint-state');const summary=document.getElementById('adversarial-privacy-authority-replay-recovery-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/adversarial-privacy-authority-replay-recovery-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; attacks=${{view.attack_class_count||0}}; review=${{view.review_event_class_count||0}}; reliability=${{view.reliability_event_class_count||0}}; execution=${{view.execution_invoked===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Adversarial privacy, authority, replay, and recovery checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('runtime-lifecycle-migration-checkpoint-state');const summary=document.getElementById('runtime-lifecycle-migration-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/runtime-lifecycle-migration-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; operations=${{view.operation_count||0}}; backup=${{view.backup_created===true?'created':'evidence-only'}}; rollback=${{view.rollback_applied===true?'applied':'not applied'}}; install=${{view.fresh_install_performed===true?'performed':'not performed'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Runtime lifecycle foundations unavailable.';}}}})();
(async()=>{{const state=document.getElementById('runtime-lifecycle-application-review-checkpoint-state');const summary=document.getElementById('runtime-lifecycle-application-review-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/runtime-lifecycle-application-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; operations=${{view.operation_count||0}}; decisions=${{view.decision_count||0}}; executed=${{view.operation_executed===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Runtime lifecycle application review unavailable.';}}}})();
(async()=>{{const state=document.getElementById('runtime-lifecycle-reliability-adversarial-checkpoint-state');const summary=document.getElementById('runtime-lifecycle-reliability-adversarial-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/runtime-lifecycle-reliability-adversarial-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; events=${{view.event_class_count||0}}; operations=${{view.operation_count||0}}; mutated=${{view.runtime_mutated===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Runtime lifecycle reliability evidence unavailable.';}}}})();
(async()=>{{const state=document.getElementById('runtime-lifecycle-checkpoint-state');const summary=document.getElementById('runtime-lifecycle-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/runtime-lifecycle-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; operations=${{view.operation_count||0}}; reviews=${{view.review_count||0}}; reliability events=${{view.reliability_event_class_count||0}}; mutated=${{view.runtime_mutated===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Runtime lifecycle checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('feature-freeze-architecture-consolidation-state');const summary=document.getElementById('feature-freeze-architecture-consolidation-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/feature-freeze-architecture-consolidation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; components=${{view.component_count||0}}; candidates=${{view.candidate_count||0}}; startup=${{view.startup_total_ms||0}}/${{view.startup_budget_ms||0}}ms; files moved=${{view.files_moved===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Feature freeze and architecture consolidation unavailable.';}}}})();

(async()=>{{const state=document.getElementById('performance-documentation-verifier-hardening-state');const summary=document.getElementById('performance-documentation-verifier-hardening-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/performance-documentation-verifier-hardening-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; classes=${{data.evidence_class_count||0}}; global pass=${{data.global_profile_pass_claimed===true?'claimed':'not claimed'}}; profiling=${{data.profiling_executed===true?'yes':'no'}}; authority=${{data.authority_granted===true?'granted':'separate'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Performance, documentation, and verifier hardening unavailable.';}}}})();
(async()=>{{const state=document.getElementById('feature-freeze-architecture-consolidated-state');const summary=document.getElementById('feature-freeze-architecture-consolidated-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/feature-freeze-architecture-consolidated-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; areas=${{view.architecture_area_count||0}}; reviews=${{view.review_count||0}}; hardening classes=${{view.hardening_evidence_class_count||0}}; global pass=${{view.global_profile_pass_claimed===true?'claimed':'not claimed'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Feature Freeze and Architecture Consolidation checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('feature-freeze-consolidation-review-state');const summary=document.getElementById('feature-freeze-consolidation-review-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/feature-freeze-consolidation-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; reviews=${{data.review_count||0}}; actions=${{data.action_count||0}}; decisions=${{data.decision_count||0}}; files moved=${{data.files_moved===true?'yes':'no'}}; authority=${{data.authority_granted===true?'granted':'separate'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Freeze exception and consolidation review unavailable.';}}}})();


(async()=>{{const state=document.getElementById('final-source-candidate-checkpoint-state');const summary=document.getElementById('final-source-candidate-checkpoint-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/final-source-candidate-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; manifest=${{view.manifest_count||0}}; reviews=${{view.review_count||0}}; reliability events=${{view.reliability_event_count||0}}; gate=${{view.v1200_gate_required===true?'required':'missing'}}; global pass=${{view.global_profile_pass_claimed===true?'claimed':'not claimed'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Final Source-Only Candidate checkpoint unavailable.';}}}})();
(async()=>{{const state=document.getElementById('final-candidate-reliability-state');const summary=document.getElementById('final-candidate-reliability-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/final-candidate-reliability-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; events=${{view.event_count||0}}; preserved=${{view.original_candidate_preserved===true?'yes':'no'}}; accepted=${{view.candidate_accepted===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Final candidate reliability unavailable.';}}}})();
(async()=>{{const state=document.getElementById('final-candidate-review-state');const summary=document.getElementById('final-candidate-review-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/final-candidate-review-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; reviews=${{view.review_count||0}}; approve=${{view.approve_count||0}}; accepted=${{view.candidate_accepted===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Final candidate review unavailable.';}}}})();
(async()=>{{const state=document.getElementById('final-source-candidate-preparation-state');const summary=document.getElementById('final-source-candidate-preparation-summary');if(!state||!summary)return;try{{const response=await fetch('/api/cognition/final-source-candidate-preparation-checkpoint',{{cache:'no-store'}});const payload=await response.json();const data=payload.data||{{}};const view=data.summary||{{}};state.textContent=data.ok?'ready':'review';state.dataset.state=data.ok?'ready':'attention';summary.textContent=`${{data.passed||0}}/${{data.total||0}} checks; manifest=${{view.manifest_count||0}}; verification=${{view.verification_count||0}}; risks=${{view.risk_count||0}}; prepared=${{view.candidate_prepared===true?'yes':'no'}}; authority=${{view.authority_state||'unknown'}}.`;}}catch(error){{state.textContent='unavailable';state.dataset.state='attention';summary.textContent='Final candidate preparation unavailable.';}}}})();
</script>

<div id="supervised-isolated-sandbox-execution-integration-checkpoint-panel" data-endpoint="/api/cognition/supervised-isolated-sandbox-execution-integration-checkpoint" hidden></div>
</body>
</html>"""

# dashboard endpoint: /api/cognition/reflective-execution-continuity-checkpoint
