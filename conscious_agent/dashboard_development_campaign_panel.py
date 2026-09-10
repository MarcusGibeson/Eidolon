from __future__ import annotations

"""Static ordinary-chat development campaign panel extracted in v1276.

The renderer is intentionally dependency-free: it emits the existing HTML/JS surface
without granting action authority or touching runtime/source state.
"""

CONTRACT_VERSION = "v1276.4"
AUTHORITY_FLAGS = {
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "release_authorized": False,
}

def _development_campaign_panel() -> str:
    return """
<style>
.development-campaign-shell{display:grid;gap:12px}
.development-campaign-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}
.development-proposal-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.development-proposal{border:1px solid var(--border);border-radius:10px;padding:14px;min-width:0;background:rgba(255,255,255,.02)}
.development-proposal h3{margin:0 0 8px;font-size:1rem;overflow-wrap:anywhere}
.development-proposal dl{display:grid;grid-template-columns:minmax(105px,.38fr) minmax(0,1fr);gap:5px 10px;margin:10px 0}
.development-proposal dt{color:var(--muted)}
.development-proposal dd{margin:0;overflow-wrap:anywhere}
.development-proposal-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.development-proposal-actions button{flex:1 1 120px}
.development-proposal code{overflow-wrap:anywhere}
@media(max-width:760px){.development-proposal-list{grid-template-columns:1fr}.development-proposal dl{grid-template-columns:1fr}.development-proposal dt{margin-top:4px}.development-proposal-actions button{width:100%;flex-basis:100%}}
</style>
<section class='development-campaign-shell' aria-labelledby='development-campaign-title'>
  <div class='development-campaign-head'>
    <div><h2 id='development-campaign-title'>Supervised Development Proposals</h2>
    <p class='muted'>Ordinary chat creates or resumes proposals in external runtime data. Public cards contain digests and lifecycle state only. No provider generation, implementation, commands, or source changes occur before exact approval.</p></div>
    <button type='button' id='development-campaign-refresh'>Refresh proposals</button>
  </div>
  <p id='development-campaign-status' class='muted'>Loading proposal lifecycle state…</p>
  <div id='development-proposal-list' class='development-proposal-list' aria-live='polite'></div>
</section>
<script>
(() => {
  'use strict';
  const list = document.getElementById('development-proposal-list');
  const status = document.getElementById('development-campaign-status');
  const refresh = document.getElementById('development-campaign-refresh');
  if (!list || !status || !refresh) return;
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const shortDigest = (value) => value ? `${String(value).slice(0,12)}…${String(value).slice(-8)}` : 'none';
  const control = async (proposal, action) => {
    const label = `${action} ${proposal.proposal_id} revision ${proposal.revision}`;
    if (!window.confirm(`Confirm ${label}? This does not start implementation.`)) return;
    const response = await fetch('/api/development-campaign/control', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action, proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest})
    });
    const payload = await response.json();
    status.textContent = payload.status || (payload.ok ? 'updated' : 'control failed');
    await load();
  };
  const preview = async (proposal) => {
    const response = await fetch('/api/development-campaign/preview', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest})
    });
    const payload = await response.json();
    status.textContent = payload.status || 'preview unavailable';
    if (payload.ok && payload.preview_url) window.open(payload.preview_url, '_blank', 'noopener,noreferrer');
  };
  const validate = async (proposal) => {
    const response = await fetch('/api/development-campaign/validate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest})
    });
    const payload = await response.json();
    const result = payload.passed ? 'passed' : 'did not pass';
    status.textContent = payload.ok ? `Bounded workspace validation ${result}. ${payload.command_count || 0} command check(s).` : (payload.status || 'validation unavailable');
    await load();
  };
  const browserRuntimeTest = async (proposal) => {
    const response = await fetch('/api/development-campaign/browser-runtime-test', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest})
    });
    const payload = await response.json();
    const result = payload.passed ? 'passed' : 'did not pass';
    status.textContent = payload.ok ? `Browser runtime test ${result}. ${payload.page_error_count || 0} page error(s); ${payload.blocked_external_request_count || 0} external request(s) blocked.` : (payload.status || 'browser runtime test unavailable');
    await load();
  };
  const finalizeBrowserRuntimeCheckpoint = async (proposal, runtimeResult) => {
    const response = await fetch('/api/development-campaign/finalize-browser-runtime-checkpoint', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest, browser_runtime_test_digest:runtimeResult.browser_runtime_test_digest})
    });
    const payload = await response.json();
    status.textContent = payload.ok ? `Browser runtime checkpoint sealed with ${payload.stage_count || 0} bound stages.` : (payload.status || 'browser runtime checkpoint unavailable');
    await load();
  };
  const nodeJavascriptTest = async (proposal) => {
    const response = await fetch('/api/development-campaign/node-javascript-test', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest})});
    const payload = await response.json(), result = payload.passed ? 'passed' : 'did not pass';
    status.textContent = payload.ok ? `Node and JavaScript tests ${result}. ${payload.command_count || 0} bounded command(s).` : (payload.status || 'Node and JavaScript tests unavailable'); await load();
  };
  const finalizeNodeJavascriptCheckpoint = async (proposal, testResult) => {
    const response = await fetch('/api/development-campaign/finalize-node-javascript-test-checkpoint', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest, node_javascript_test_digest:testResult.node_javascript_test_digest})});
    const payload = await response.json(); status.textContent = payload.ok ? `Node and JavaScript test checkpoint sealed with ${payload.stage_count || 0} bound stages.` : (payload.status || 'Node and JavaScript checkpoint unavailable'); await load();
  };
  const pythonProjectTest = async (proposal) => { const response=await fetch('/api/development-campaign/python-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proposal_id:proposal.proposal_id,revision:proposal.revision,revision_digest:proposal.revision_digest})}); const payload=await response.json(); status.textContent=payload.ok?`Python tests ${payload.passed?'passed':'did not pass'}. ${payload.command_count||0} bounded command(s).`:(payload.status||'Python tests unavailable'); await load(); }; const finalizePythonTestCheckpoint = async (proposal,result) => { const response=await fetch('/api/development-campaign/finalize-python-test-checkpoint',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proposal_id:proposal.proposal_id,revision:proposal.revision,revision_digest:proposal.revision_digest,python_test_adapter_digest:result.python_test_adapter_digest})}); const payload=await response.json(); status.textContent=payload.ok?`Python test checkpoint sealed with ${payload.stage_count||0} bound stages.`:(payload.status||'Python test checkpoint unavailable'); await load(); };
  const implement = async (proposal) => {
    if (!window.confirm(`Build isolated website for ${proposal.proposal_id} revision ${proposal.revision}? This contacts the configured local provider and writes only to an external isolated workspace.`)) return;
    status.textContent = 'Running the supervised small website checkpoint…';
    const response = await fetch('/api/development-campaign/implement-small-website', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest})
    });
    const payload = await response.json();
    status.textContent = payload.ok ? `Small website checkpoint ready. ${payload.change_summary?.file_count || 0} exact change(s); operator review remains required.` : (payload.status || 'small website implementation unavailable');
    await load();
  };
  const reviewJavascriptTool = async (proposal, checkpoint) => {
    const response = await fetch('/api/development-campaign/review-javascript-tool-result', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest, checkpoint_digest:checkpoint.checkpoint_digest})
    });
    const payload = await response.json();
    status.textContent = payload.ok ? 'JavaScript tool review packet ready; choose retain, revise, reject, or discard.' : (payload.status || 'review packet unavailable');
    await load();
  };
  const disposeJavascriptTool = async (proposal, packet, action) => {
    if (!window.confirm(`Confirm ${action} for ${proposal.proposal_id} revision ${proposal.revision}? No outcome applies files to the selected project.`)) return;
    const response = await fetch('/api/development-campaign/dispose-javascript-tool-result', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest, checkpoint_digest:packet.checkpoint_digest, review_packet_digest:packet.review_packet_digest, action})
    });
    const payload = await response.json();
    status.textContent = payload.status || (payload.ok ? 'disposition recorded' : 'disposition failed');
    await load();
  };
  const reviewPythonCli = async (proposal, checkpoint) => {
    const response = await fetch('/api/development-campaign/review-python-cli-result', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proposal_id:proposal.proposal_id,revision:proposal.revision,revision_digest:proposal.revision_digest,checkpoint_digest:checkpoint.checkpoint_digest})});
    const payload = await response.json(); status.textContent = payload.ok ? 'Python CLI review packet ready; choose retain, revise, reject, or discard.' : (payload.status || 'review packet unavailable'); await load();
  };
  const disposePythonCli = async (proposal, packet, action) => {
    if (!window.confirm(`Confirm ${action} for ${proposal.proposal_id} revision ${proposal.revision}? No outcome applies files to the selected project.`)) return;
    const response = await fetch('/api/development-campaign/dispose-python-cli-result', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proposal_id:proposal.proposal_id,revision:proposal.revision,revision_digest:proposal.revision_digest,checkpoint_digest:packet.checkpoint_digest,review_packet_digest:packet.review_packet_digest,action})});
    const payload = await response.json(); status.textContent = payload.status || (payload.ok ? 'disposition recorded' : 'disposition failed'); await load();
  };
  const finalizePythonCliCheckpoint = async (proposal, checkpoint, packet, disposition) => {
    const response = await fetch('/api/development-campaign/finalize-python-cli-checkpoint', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest, checkpoint_digest:checkpoint.checkpoint_digest, review_packet_digest:packet.review_packet_digest, disposition_digest:disposition.disposition_digest})
    });
    const payload = await response.json();
    status.textContent = payload.ok ? `Python CLI implementation checkpoint sealed with ${payload.stage_count || 0} bound stages.` : (payload.status || 'checkpoint recovery unavailable');
    await load();
  };
  const finalizeJavascriptToolCheckpoint = async (proposal, checkpoint, packet, disposition) => {
    const response = await fetch('/api/development-campaign/finalize-javascript-tool-checkpoint', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest, checkpoint_digest:checkpoint.checkpoint_digest, review_packet_digest:packet.review_packet_digest, disposition_digest:disposition.disposition_digest})
    });
    const payload = await response.json();
    status.textContent = payload.ok ? `JavaScript implementation checkpoint sealed with ${payload.stage_count || 0} bound stages.` : (payload.status || 'checkpoint recovery unavailable');
    await load();
  };
  const finalizeSelectedProjectCheckpoint = async (proposal, implementationCheckpoint, applyResult, rollbackRequest, rollbackResult) => {
    const response = await fetch('/api/development-campaign/finalize-selected-project-apply-rollback-checkpoint', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        proposal_id:proposal.proposal_id, revision:proposal.revision, revision_digest:proposal.revision_digest,
        implementation_checkpoint_digest:implementationCheckpoint.implementation_checkpoint_digest,
        apply_request_digest:applyResult.apply_request_digest, apply_result_digest:applyResult.apply_result_digest,
        rollback_request_digest:rollbackResult.rollback_result_digest ? rollbackRequest.rollback_request_digest : '',
        rollback_result_digest:rollbackResult.rollback_result_digest || ''
      })
    });
    const payload = await response.json();
    status.textContent = payload.ok ? `Selected-project ${payload.checkpoint_phase || 'apply'} checkpoint sealed with ${payload.stage_count || 0} bound stages.` : (payload.status || 'selected-project checkpoint unavailable');
    await load();
  };
  const render = (proposal) => {
    const target = proposal.target || {};
    const checkpoint = proposal.small_website_checkpoint || {};
    const javascriptCheckpoint = proposal.javascript_tool_test_checkpoint || {};
    const javascriptReview = proposal.javascript_tool_review_packet || {};
    const javascriptDisposition = proposal.javascript_tool_disposition || {};
    const javascriptFinalCheckpoint = proposal.javascript_tool_implementation_checkpoint || {};
    const pythonCheckpoint = proposal.python_cli_test_checkpoint || {};
    const pythonReview = proposal.python_cli_review_packet || {};
    const pythonDisposition = proposal.python_cli_disposition || {};
    const pythonFinalCheckpoint = proposal.python_cli_implementation_checkpoint || {};
    const selectedApplyResult = proposal.selected_project_apply_result || {};
    const selectedRollbackRequest = proposal.selected_project_rollback_request || {};
    const selectedRollbackResult = proposal.selected_project_rollback_result || {};
    const selectedProjectCheckpoint = proposal.selected_project_apply_rollback_checkpoint || {};
    const browserRuntimeResult = proposal.browser_runtime_test || {};
    const browserRuntimeCheckpoint = proposal.browser_runtime_test_adapter_checkpoint || {};
    const nodeJavascriptResult = proposal.node_javascript_test_result || {};
    const nodeJavascriptCheckpoint = proposal.node_javascript_test_adapter_checkpoint || {};
    const pythonTestResult = proposal.python_test_adapter_result || {}, pythonTestCheckpoint = proposal.python_test_adapter_checkpoint || {}, projectKind = proposal.grounded_planning?.project_kind || '';
    const nodeJavascriptEligible = ['new_javascript_tool_project','javascript_tool_project','javascript_or_web_project','new_small_web_project','static_web_project'].includes(projectKind), pythonTestEligible = ['new_python_cli_project','python_cli_project','python_project'].includes(projectKind);
    const selectedImplementationCheckpoint = pythonFinalCheckpoint.implementation_checkpoint_digest ? pythonFinalCheckpoint : javascriptFinalCheckpoint;
    const actions = pythonTestResult.python_test_adapter_digest && !pythonTestCheckpoint.checkpoint_digest ? `<div class="development-proposal-actions"><button type="button" data-python-test-finalize="run">Seal Python test checkpoint</button></div>` : nodeJavascriptResult.node_javascript_test_digest && !nodeJavascriptCheckpoint.checkpoint_digest
      ? `<div class="development-proposal-actions"><button type="button" data-node-finalize="run">Seal Node/JavaScript test checkpoint</button></div>`
      : selectedRollbackResult.rollback_result_digest && selectedProjectCheckpoint.checkpoint_phase !== 'rolled_back'
      ? `<div class="development-proposal-actions"><button type="button" data-selected-finalize="run">Seal apply and rollback checkpoint</button></div>`
      : selectedApplyResult.apply_result_digest && !selectedProjectCheckpoint.checkpoint_digest
      ? `<div class="development-proposal-actions"><button type="button" data-selected-finalize="run">Seal selected-project apply checkpoint</button></div>`
      : pythonDisposition.disposition_digest && !pythonFinalCheckpoint.implementation_checkpoint_digest
      ? `<div class="development-proposal-actions"><button type="button" data-py-finalize="run">Recover final Python CLI checkpoint</button></div>`
      : pythonReview.review_packet_digest && !pythonDisposition.disposition_digest
      ? `<div class="development-proposal-actions"><button type="button" data-py-disposition="retain">Retain</button><button type="button" data-py-disposition="revise">Revise</button><button type="button" data-py-disposition="reject">Reject</button><button type="button" data-py-disposition="discard">Discard</button></div>`
      : pythonCheckpoint.checkpoint_digest && !pythonDisposition.disposition_digest
      ? `<div class="development-proposal-actions"><button type="button" data-py-review="run">Review Python CLI result</button></div>`
      : javascriptDisposition.disposition_digest && !javascriptFinalCheckpoint.implementation_checkpoint_digest
      ? `<div class="development-proposal-actions"><button type="button" data-js-finalize="run">Recover final JavaScript checkpoint</button></div>`
      : javascriptReview.review_packet_digest && !javascriptDisposition.disposition_digest
      ? `<div class="development-proposal-actions"><button type="button" data-disposition="retain">Retain</button><button type="button" data-disposition="revise">Revise</button><button type="button" data-disposition="reject">Reject</button><button type="button" data-disposition="discard">Discard</button></div>`
      : javascriptCheckpoint.checkpoint_digest && !javascriptDisposition.disposition_digest
        ? `<div class="development-proposal-actions"><button type="button" data-js-review="run">Review JavaScript result</button></div>`
        : browserRuntimeResult.browser_runtime_test_digest && !browserRuntimeCheckpoint.checkpoint_digest
      ? `<div class="development-proposal-actions"><button type="button" data-browser-finalize="run">Seal browser runtime checkpoint</button></div>`
      : proposal.lifecycle_state === 'awaiting_approval'
          ? `<div class="development-proposal-actions"><button type="button" data-control="approve">Approve exact revision</button><button type="button" data-control="reject">Reject</button><button type="button" data-control="cancel">Cancel</button></div>`
          : proposal.approval_consumed ? `<div class="development-proposal-actions"><button type="button" data-implement="run">Build isolated website</button><button type="button" data-preview="open">Open isolated preview</button><button type="button" data-validate="run">Run bounded validation</button><button type="button" data-browser-runtime="run">Run browser runtime test</button>${nodeJavascriptEligible ? '<button type="button" data-node-javascript="run">Run Node/JavaScript tests</button>' : ''}${pythonTestEligible ? '<button type="button" data-python-test="run">Run Python tests</button>' : ''}</div>` : '';
    const checkpointSummary = checkpoint.checkpoint_digest
      ? `<p><span class="badge">small website checkpoint</span> <span class="badge">operator review required</span></p><dl><dt>Checkpoint</dt><dd><code>${escapeHtml(shortDigest(checkpoint.checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(checkpoint.stage_count || 0)} bound stages</dd><dt>Changes</dt><dd>${escapeHtml(checkpoint.change_summary?.file_count || 0)} file changes</dd><dt>Validation</dt><dd>${checkpoint.test_summary?.passed ? 'passed' : 'not passed'}</dd></dl>`
      : '';
    const pythonSummary = pythonFinalCheckpoint.implementation_checkpoint_digest
      ? `<p><span class="badge">Python CLI implementation checkpoint</span> <span class="badge">${escapeHtml(pythonFinalCheckpoint.status || 'complete')}</span></p><dl><dt>Final checkpoint</dt><dd><code>${escapeHtml(shortDigest(pythonFinalCheckpoint.implementation_checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(pythonFinalCheckpoint.stage_count || 0)} bound stages</dd><dt>Project tests</dt><dd>${pythonFinalCheckpoint.project_test_summary?.passed ? 'passed' : 'not passed'}</dd><dt>Disposition</dt><dd>${escapeHtml(pythonFinalCheckpoint.disposition_action || 'unknown')}</dd><dt>Apply authority</dt><dd>not granted</dd></dl>`
      : pythonCheckpoint.checkpoint_digest
        ? `<p><span class="badge">Python CLI result</span> <span class="badge">${escapeHtml(pythonDisposition.status || pythonReview.status || 'operator review required')}</span></p><dl><dt>Checkpoint</dt><dd><code>${escapeHtml(shortDigest(pythonCheckpoint.checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(pythonCheckpoint.stage_count || 0)} bound stages</dd><dt>Project tests</dt><dd>${pythonCheckpoint.project_test_summary?.passed ? 'passed' : 'not passed'}</dd><dt>Disposition</dt><dd>${escapeHtml(pythonDisposition.action || 'pending')}</dd></dl>` : '';
    const javascriptSummary = javascriptFinalCheckpoint.implementation_checkpoint_digest
      ? `<p><span class="badge">JavaScript implementation checkpoint</span> <span class="badge">${escapeHtml(javascriptFinalCheckpoint.status || 'complete')}</span></p><dl><dt>Final checkpoint</dt><dd><code>${escapeHtml(shortDigest(javascriptFinalCheckpoint.implementation_checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(javascriptFinalCheckpoint.stage_count || 0)} bound stages</dd><dt>Project tests</dt><dd>${javascriptFinalCheckpoint.project_test_summary?.passed ? 'passed' : 'not passed'}</dd><dt>Disposition</dt><dd>${escapeHtml(javascriptFinalCheckpoint.disposition_action || 'unknown')}</dd><dt>Apply authority</dt><dd>not granted</dd></dl>`
      : javascriptCheckpoint.checkpoint_digest
        ? `<p><span class="badge">JavaScript tool result</span> <span class="badge">${escapeHtml(javascriptDisposition.status || javascriptReview.status || 'operator review required')}</span></p><dl><dt>Checkpoint</dt><dd><code>${escapeHtml(shortDigest(javascriptCheckpoint.checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(javascriptCheckpoint.stage_count || 0)} bound stages</dd><dt>Project tests</dt><dd>${javascriptCheckpoint.project_test_summary?.passed ? 'passed' : 'not passed'}</dd><dt>Disposition</dt><dd>${escapeHtml(javascriptDisposition.action || 'pending')}</dd></dl>`
        : '';
    const nodeJavascriptSummary = nodeJavascriptCheckpoint.checkpoint_digest
      ? `<p><span class="badge">Node/JavaScript test checkpoint</span> <span class="badge">${escapeHtml(nodeJavascriptCheckpoint.status || 'complete')}</span></p><dl><dt>Checkpoint</dt><dd><code>${escapeHtml(shortDigest(nodeJavascriptCheckpoint.checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(nodeJavascriptCheckpoint.stage_count || 0)} bound stages</dd><dt>Tests</dt><dd>${nodeJavascriptCheckpoint.tests_passed ? 'passed' : 'did not pass'}</dd><dt>Commands</dt><dd>${escapeHtml(nodeJavascriptCheckpoint.command_count || 0)}</dd><dt>Repair authority</dt><dd>not granted</dd></dl>`
      : nodeJavascriptResult.node_javascript_test_digest
        ? `<p><span class="badge">Node/JavaScript test result</span> <span class="badge">operator checkpoint pending</span></p><dl><dt>Result</dt><dd><code>${escapeHtml(shortDigest(nodeJavascriptResult.node_javascript_test_digest))}</code></dd><dt>Tests</dt><dd>${nodeJavascriptResult.passed ? 'passed' : 'did not pass'}</dd><dt>Outcome</dt><dd>${escapeHtml(nodeJavascriptResult.outcome_class || 'unknown')}</dd></dl>` : '';
    const pythonTestSummary = pythonTestCheckpoint.checkpoint_digest ? `<p><span class="badge">Python test checkpoint</span> <span class="badge">${escapeHtml(pythonTestCheckpoint.status||'complete')}</span></p><dl><dt>Checkpoint</dt><dd><code>${escapeHtml(shortDigest(pythonTestCheckpoint.checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(pythonTestCheckpoint.stage_count||0)} bound stages</dd><dt>Tests</dt><dd>${pythonTestCheckpoint.tests_passed?'passed':'did not pass'}</dd><dt>Runner</dt><dd>${escapeHtml(pythonTestCheckpoint.runner||'unknown')}</dd><dt>Repair authority</dt><dd>not granted</dd></dl>` : pythonTestResult.python_test_adapter_digest ? `<p><span class="badge">Python test result</span> <span class="badge">operator checkpoint pending</span></p><dl><dt>Result</dt><dd><code>${escapeHtml(shortDigest(pythonTestResult.python_test_adapter_digest))}</code></dd><dt>Tests</dt><dd>${pythonTestResult.passed?'passed':'did not pass'}</dd><dt>Runner</dt><dd>${escapeHtml(pythonTestResult.runner||'unknown')}</dd></dl>` : '';
    const browserRuntimeSummary = browserRuntimeCheckpoint.checkpoint_digest
      ? `<p><span class="badge">browser runtime checkpoint</span> <span class="badge">${escapeHtml(browserRuntimeCheckpoint.status || 'complete')}</span></p><dl><dt>Checkpoint</dt><dd><code>${escapeHtml(shortDigest(browserRuntimeCheckpoint.checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(browserRuntimeCheckpoint.stage_count || 0)} bound stages</dd><dt>Runtime</dt><dd>${browserRuntimeCheckpoint.browser_runtime_passed ? 'passed' : 'did not pass'}</dd><dt>Cleanup</dt><dd>${browserRuntimeCheckpoint.cleanup_confirmed ? 'confirmed' : 'not confirmed'}</dd><dt>Repair authority</dt><dd>not granted</dd></dl>`
      : browserRuntimeResult.browser_runtime_test_digest
        ? `<p><span class="badge">browser runtime result</span> <span class="badge">operator checkpoint pending</span></p><dl><dt>Result</dt><dd><code>${escapeHtml(shortDigest(browserRuntimeResult.browser_runtime_test_digest))}</code></dd><dt>Runtime</dt><dd>${browserRuntimeResult.passed ? 'passed' : 'did not pass'}</dd></dl>` : '';
    const selectedProjectSummary = selectedProjectCheckpoint.checkpoint_digest
      ? `<p><span class="badge">selected-project apply/rollback checkpoint</span> <span class="badge">${escapeHtml(selectedProjectCheckpoint.checkpoint_phase || 'complete')}</span></p><dl><dt>Checkpoint</dt><dd><code>${escapeHtml(shortDigest(selectedProjectCheckpoint.checkpoint_digest))}</code></dd><dt>Stages</dt><dd>${escapeHtml(selectedProjectCheckpoint.stage_count || 0)} bound stages</dd><dt>Project state</dt><dd>${escapeHtml(selectedProjectCheckpoint.observed_project_scope || 'unknown')}</dd><dt>Apply authorization</dt><dd>${escapeHtml(selectedProjectCheckpoint.apply_authorization_consumption_count || 0)} consumed</dd><dt>Rollback authorization</dt><dd>${escapeHtml(selectedProjectCheckpoint.rollback_authorization_consumption_count || 0)} consumed</dd><dt>Release authority</dt><dd>not granted</dd></dl>`
      : '';
    const article = document.createElement('article');
    article.className = 'development-proposal';
    article.dataset.state = proposal.lifecycle_state || 'unknown';
    article.innerHTML = `<h3>${escapeHtml(proposal.proposal_id)} · revision ${escapeHtml(proposal.revision)}</h3>
      <p><span class="badge">${escapeHtml(proposal.current_stage || proposal.lifecycle_state)}</span> <span class="badge">risk: ${escapeHtml(proposal.risk_level)}</span></p>
      <dl>
        <dt>Request digest</dt><dd><code>${escapeHtml(shortDigest(proposal.request_digest))}</code></dd>
        <dt>Revision digest</dt><dd><code>${escapeHtml(shortDigest(proposal.revision_digest))}</code></dd>
        <dt>Target</dt><dd>${escapeHtml(String(target.mode || 'isolated_workspace').replaceAll('_',' '))}</dd>
        <dt>Support</dt><dd>${escapeHtml(proposal.support_status)}</dd>
        <dt>Next step</dt><dd>${escapeHtml(proposal.planned_next_step)}</dd>
        <dt>Approval</dt><dd>${proposal.approval_consumed ? 'consumed exactly once' : (proposal.approval_required ? 'required' : 'not available')}</dd>
      </dl>
      ${proposal.limitation ? `<p class="muted">${escapeHtml(proposal.limitation)}</p>` : ''}${checkpointSummary}${javascriptSummary}${pythonSummary}${nodeJavascriptSummary}${pythonTestSummary}${browserRuntimeSummary}${selectedProjectSummary}${actions}`;
    article.querySelectorAll('[data-control]').forEach((button) => button.addEventListener('click', () => control(proposal, button.dataset.control)));
    article.querySelectorAll('[data-implement]').forEach((button) => button.addEventListener('click', () => implement(proposal)));
    article.querySelectorAll('[data-preview]').forEach((button) => button.addEventListener('click', () => preview(proposal)));
    article.querySelectorAll('[data-validate]').forEach((button) => button.addEventListener('click', () => validate(proposal)));
    article.querySelectorAll('[data-browser-runtime]').forEach((button) => button.addEventListener('click', () => browserRuntimeTest(proposal)));
    article.querySelectorAll('[data-browser-finalize]').forEach((button) => button.addEventListener('click', () => finalizeBrowserRuntimeCheckpoint(proposal, browserRuntimeResult)));
    article.querySelectorAll('[data-node-javascript]').forEach((button) => button.addEventListener('click', () => nodeJavascriptTest(proposal)));
    article.querySelectorAll('[data-node-finalize]').forEach((button) => button.addEventListener('click', () => finalizeNodeJavascriptCheckpoint(proposal, nodeJavascriptResult)));
    article.querySelectorAll('[data-python-test]').forEach((button) => button.addEventListener('click', () => pythonProjectTest(proposal))); article.querySelectorAll('[data-python-test-finalize]').forEach((button) => button.addEventListener('click', () => finalizePythonTestCheckpoint(proposal, pythonTestResult)));
    article.querySelectorAll('[data-js-review]').forEach((button) => button.addEventListener('click', () => reviewJavascriptTool(proposal, javascriptCheckpoint)));
    article.querySelectorAll('[data-disposition]').forEach((button) => button.addEventListener('click', () => disposeJavascriptTool(proposal, javascriptReview, button.dataset.disposition)));
    article.querySelectorAll('[data-py-review]').forEach((button) => button.addEventListener('click', () => reviewPythonCli(proposal, pythonCheckpoint)));
    article.querySelectorAll('[data-py-disposition]').forEach((button) => button.addEventListener('click', () => disposePythonCli(proposal, pythonReview, button.dataset.pyDisposition)));
    article.querySelectorAll('[data-py-finalize]').forEach((button) => button.addEventListener('click', () => finalizePythonCliCheckpoint(proposal, pythonCheckpoint, pythonReview, pythonDisposition)));
    article.querySelectorAll('[data-js-finalize]').forEach((button) => button.addEventListener('click', () => finalizeJavascriptToolCheckpoint(proposal, javascriptCheckpoint, javascriptReview, javascriptDisposition)));
    article.querySelectorAll('[data-selected-finalize]').forEach((button) => button.addEventListener('click', () => finalizeSelectedProjectCheckpoint(proposal, selectedImplementationCheckpoint, selectedApplyResult, selectedRollbackRequest, selectedRollbackResult)));
    return article;
  };
  const load = async () => {
    refresh.disabled = true;
    try {
      const response = await fetch('/api/development-campaign/proposals', {cache:'no-store'});
      const payload = await response.json();
      const proposals = Array.isArray(payload.proposals) ? payload.proposals : [];
      list.replaceChildren(...proposals.map(render));
      status.textContent = proposals.length ? `${proposals.length} proposal${proposals.length === 1 ? '' : 's'} restored from external runtime state.` : 'No ordinary-chat development proposals yet.';
    } catch (error) {
      status.textContent = 'Proposal lifecycle state is unavailable.';
      list.replaceChildren();
    } finally { refresh.disabled = false; }
  };
  refresh.addEventListener('click', load);
  load();
})();
</script>
"""


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "_development_campaign_panel"]
