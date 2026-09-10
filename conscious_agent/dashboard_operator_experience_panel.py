from __future__ import annotations
"""v1279 dashboard operator-experience panel.

Pure HTML/JS presentation.  It performs no provider/test/update activity and
uses the dedicated v1279 API surfaces for bounded runtime controls.
"""

CONTRACT_VERSION = "v1279.8"


def _operator_experience_panel() -> str:
    return r"""
<section id="operator-experience" aria-labelledby="operator-experience-title">
  <h2 id="operator-experience-title">Supervised Development Operator View</h2>
  <p class="muted">One content-minimized view of plan, changed paths, verification, progress, recovery, uncertainty, review, and the next governed authorization.</p>
  <p><strong>Generic approval does not authorize execution.</strong> Exact authorization remains bound to the existing governed stage. Dashboard navigation, readiness, and review approval are not authority.</p>
  <div class="stack" role="status" aria-live="polite" id="operator-experience-status">Loading supervised development status…</div>
  <div id="operator-experience-list" class="stack"></div>
  <p><button type="button" id="operator-experience-refresh">Refresh operator view</button></p>
</section>
<script>
(() => {
  const list = document.getElementById('operator-experience-list');
  const status = document.getElementById('operator-experience-status');
  const refresh = document.getElementById('operator-experience-refresh');
  if (!list || !status || !refresh) return;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const label = (value) => esc(String(value ?? 'unknown').replaceAll('_',' '));
  const paths = (rows) => (rows || []).length ? `<ul>${(rows || []).slice(0,12).map(x => `<li><code>${esc(x.relative_path)}</code> · ${label(x.action)}</li>`).join('')}</ul>` : `<p class="muted">No reviewed changed paths yet.</p>`;
  const uncertainty = (rows) => (rows || []).length ? `<ul>${(rows || []).slice(0,10).map(x => `<li>${label(x.uncertainty_code)} · ${label(x.severity)} · ${label(x.state)}</li>`).join('')}</ul>` : `<p class="muted">No review-packet uncertainty rows are available yet.</p>`;
  const risks = (rows) => (rows || []).length ? `<ul>${(rows || []).slice(0,10).map(x => `<li>${label(x.risk_code)} · ${label(x.severity)}</li>`).join('')}</ul>` : `<p class="muted">No review-packet risks are available yet.</p>`;
  const events = (rows) => (rows || []).length ? `<ul>${(rows || []).slice(-8).map(x => `<li>${label(x.event_code)} · ${label(x.phase)} · ${label(x.outcome)} · ${esc(x.elapsed_ms || 0)} ms</li>`).join('')}</ul>` : `<p class="muted">No retained progress events yet.</p>`;
  const button = (snapshot, action, text) => `<button type="button" data-operator-control="${esc(action)}" data-observability-id="${esc(snapshot.observability_id)}">${esc(text)}</button>`;
  const render = (s) => {
    const current = s.current || {}, plan = s.plan || {}, changes = s.changes || {}, verification = s.verification || {}, progress = s.progress || {}, auth = s.authorization || {}, controls = s.controls || {}, recovery = s.recovery || {}, rollback = s.rollback || {}, review = s.review || {};
    const actions = (controls.available || []).map(a => button(s, a, a === 'reconcile_recovery' ? 'Reconcile recovery' : a[0].toUpperCase()+a.slice(1))).join(' ');
    return `<article class="development-proposal" data-state="${esc(current.session_state)}">
      <h3>${esc(s.campaign_id)} · ${label(current.current_phase)}</h3>
      <p><span class="badge">session: ${label(current.session_state)}</span> <span class="badge">campaign: ${label(current.campaign_phase)}</span> <span class="badge">recovery: ${label(recovery.state)}</span></p>
      <div class="grid">
        <section><h4>Plan</h4><dl><dt>Objective</dt><dd>${label(plan.objective_code)}</dd><dt>Strategy</dt><dd>${label(plan.strategy_code)}</dd><dt>Confidence</dt><dd>${label(plan.plan_confidence)}</dd></dl><p class="muted">Planning evidence is not execution authority.</p></section>
        <section><h4>Verification</h4><dl><dt>Tests executed</dt><dd>${verification.tests_executed ? 'yes' : 'no'}</dd><dt>Selected tests</dt><dd>${esc(verification.selected_test_count || 0)}</dd><dt>Runs</dt><dd>${esc(verification.test_run_count || 0)}</dd><dt>Passed</dt><dd>${verification.passed ? 'yes' : 'not yet demonstrated'}</dd></dl></section>
        <section><h4>Progress</h4><dl><dt>Events</dt><dd>${esc(progress.event_count_total || 0)}</dd><dt>Failures</dt><dd>${esc(progress.failure_count_total || 0)}</dd><dt>Retries</dt><dd>${esc(progress.retry_count_total || 0)}</dd><dt>Recoveries</dt><dd>${esc(progress.recovery_count_total || 0)}</dd><dt>Budget splits</dt><dd>${esc(progress.budget_split_count_total || 0)}</dd></dl>${events(progress.recent_events)}</section>
        <section><h4>Exact authorization</h4><p><strong>${esc(auth.label || 'Review required')}</strong></p><p>Exact authorization required: ${auth.exact_authorization_required ? 'yes' : 'no'}. Authorization phrase is not exposed by this passive view.</p><p class="muted">Generic “go ahead”, navigation, readiness, or review approval never substitutes for Exact authorization.</p></section>
      </div>
      <details><summary>Changed paths (${esc(changes.changed_file_count || 0)})</summary>${paths(changes.paths)}</details>
      <details><summary>Review packet</summary><p>Review state: ${label(review.state)} · decision: ${label(review.operator_decision)}</p>${risks(review.risks)}</details>
      <details><summary>Uncertainty (${esc(review.uncertainty_count || 0)})</summary>${uncertainty(s.uncertainty)}</details>
      <details><summary>Recovery and rollback</summary><p>Recovery generation: ${esc(recovery.restart_generation || 0)}. Provider/test replay on reconciliation: no.</p><p>Update phase: ${label(rollback.update_phase)}. Rollback is separately governed and, when available, requires its own exact authorization.</p></details>
      <div aria-label="Operator session controls">${actions || '<span class="muted">No runtime session control is currently applicable.</span>'}</div>
    </article>`;
  };
  async function control(button) {
    const action = button.dataset.operatorControl, observability_id = button.dataset.observabilityId;
    button.disabled = true;
    status.textContent = `Recording ${action.replaceAll('_',' ')} control…`;
    try {
      const response = await fetch('/api/operator-experience/control', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action, observability_id})});
      const payload = await response.json();
      status.textContent = payload.status || (payload.ok ? 'Control recorded.' : 'Control blocked.');
      await load();
    } catch (_) { status.textContent = 'Operator control could not be recorded.'; }
    finally { button.disabled = false; }
  }
  async function load() {
    refresh.disabled = true;
    try {
      const response = await fetch('/api/operator-experience/snapshots', {cache:'no-store'});
      const payload = await response.json();
      const snapshots = Array.isArray(payload.snapshots) ? payload.snapshots : [];
      list.innerHTML = snapshots.map(render).join('');
      list.querySelectorAll('[data-operator-control]').forEach(b => b.addEventListener('click', () => control(b)));
      status.textContent = snapshots.length ? `${snapshots.length} supervised development session${snapshots.length === 1 ? '' : 's'} available.` : 'No v1277 observability-backed self-development session is available yet.';
    } catch (_) {
      list.innerHTML = '';
      status.textContent = 'Operator experience status is unavailable.';
    } finally { refresh.disabled = false; }
  }
  refresh.addEventListener('click', load);
  load();
})();
</script>
"""


__all__ = ["CONTRACT_VERSION", "_operator_experience_panel"]
