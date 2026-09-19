/* Operational facts only. No mutation endpoints, provider calls, or model prose. */
(() => {
  'use strict';
  const host = document.getElementById('activity-surface');
  if (!host) return;
  const detail = host.dataset.detail === 'true';
  let selected = new URLSearchParams(location.search).get('id');
  let payload = null;
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = String(text);
    if (cls) n.className = cls;
    return n;
  };
  const pretty = s => String(s || '').replaceAll('_', ' ');
  const elapsed = seconds => seconds == null ? 'Elapsed unknown' : `${Math.floor(seconds / 60)}m ${seconds % 60}s elapsed`;
  function governance(a, parent) {
    const g = a.governance || {};
    const box = el('div', undefined, 'activity-governance');
    if (g.read_only === true) box.append(el('span', 'READ ONLY'));
    if (g.non_authoritative === true) box.append(el('span', 'NON-AUTHORITATIVE'));
    if (g.belief_effects === 'none') box.append(el('span', 'BELIEF EFFECTS NONE'));
    if (g.mutation_guard) box.append(el('span', `MUTATION GUARD: ${g.mutation_guard}`));
    parent.append(box);
  }
  function meter(p, parent) {
    if (!p) return;
    parent.append(el('div', p.total == null ? `${p.completed} ${p.unit}; total unknown` : `${p.completed} / ${p.total} ${p.unit}`, 'activity-count'));
    if (p.percent != null) {
      const bar = el('progress'); bar.max = 100; bar.value = p.percent;
      bar.setAttribute('aria-label', p.unit); parent.append(bar);
    } else parent.append(el('small', 'Indeterminate'));
  }
  function summary(a) {
    const box = el('div', undefined, 'activity-summary');
    const top = el('div', undefined, 'activity-heading');
    top.append(el('strong', pretty(a.state).toUpperCase(), `activity-state state-${a.state}`));
    top.append(el('small', pretty(a.type))); box.append(top);
    box.append(el('h2', a.title), el('div', a.subject), el('strong', a.stage || 'Queued'));
    meter(a.progress, box);
    box.append(el('div', elapsed(a.elapsed_seconds), 'activity-time'));
    governance(a, box);
    for (const w of a.warnings || []) box.append(el('p', pretty(w), 'activity-warning'));
    if (a.reason) box.append(el('p', pretty(a.reason), 'activity-warning'));
    const metrics = el('dl', undefined, 'activity-metrics');
    for (const [key, value] of Object.entries(a.metrics || {})) {
      metrics.append(el('dt', pretty(key)), el('dd', value));
    }
    box.append(metrics);
    return box;
  }
  function renderDetail(a) {
    const pane = document.getElementById('activity-detail');
    pane.replaceChildren();
    if (!a) { pane.append(el('p', selected ? 'Activity not found.' : 'No activity recorded.')); return; }
    pane.append(summary(a));
    pane.append(el('h3', 'Stages'));
    const stages = el('ol', undefined, 'activity-stages');
    for (const stage of a.stages || []) {
      const li = el('li', `${stage.name}: ${pretty(stage.state)}`, `state-${stage.state}`);
      stages.append(li);
    }
    pane.append(stages);
    meter(a.stage_progress, pane);
    pane.append(el('h3', 'Work breakdown'));
    for (const part of a.breakdown || []) pane.append(el('div', `${part.id} - ${part.label}: ${part.completed} / ${part.total}`, 'activity-work'));
    pane.append(el('h3', 'Identity and result'));
    const ids = el('dl', undefined, 'activity-metrics');
    ids.append(el('dt', 'Activity ID'), el('dd', a.activity_id));
    for (const [key, value] of Object.entries(a.identities || {})) ids.append(el('dt', pretty(key)), el('dd', value || 'Not recorded'));
    if (a.result) ids.append(el('dt', 'Result'), el('dd', pretty(a.result)));
    pane.append(ids, el('h3', 'Operational events'));
    if (a.events_omitted) pane.append(el('p', `${a.events_omitted} older events outside the retained window.`));
    const events = el('ol', undefined, 'activity-events');
    for (const event of [...(a.events || [])].reverse()) {
      const row = el('li');
      row.append(el('time', event.at), el('span', `#${event.sequence} ${pretty(event.event)} - ${event.stage}`));
      events.append(row);
    }
    pane.append(events);
  }
  function render(data) {
    payload = data;
    const current = document.getElementById('activity-current'); current.replaceChildren();
    const rows = data.activities || [];
    const a = data.current || rows[0];
    document.getElementById('activity-status').textContent = data.active_count ? `${data.active_count} active` : 'No active work';
    if (!detail) {
      if (a) current.append(summary(a));
      const link = el('a', 'Activity details and history', 'activity-link');
      link.href = '/activity' + (a ? '?id=' + encodeURIComponent(a.activity_id) : '');
      link.dataset.tip = 'Open activity history and operational events'; current.append(link);
    } else {
      const history = document.getElementById('activity-history'); history.replaceChildren(el('h2', 'History'));
      for (const row of rows) {
        const button = el('button', `${row.subject || row.title} - ${pretty(row.state)}`);
        button.type = 'button'; button.dataset.tip = 'Inspect this activity';
        button.setAttribute('aria-pressed', String(row.activity_id === selected));
        button.onclick = () => { selected = row.activity_id; history.replaceChildren(); render(payload); };
        history.append(button);
      }
      renderDetail(rows.find(r => r.activity_id === selected) || (!selected ? a : null));
    }
    for (const w of data.warnings || []) current.append(el('p', pretty(w), 'activity-warning'));
  }
  async function poll() {
    try {
      const response = await fetch('/api/activities', {cache: 'no-store'});
      if (!response.ok) throw new Error('unavailable');
      const envelope = await response.json();
      const data = envelope.data || envelope;
      if (data.contract !== 'activity.v1') throw new Error('contract');
      if (selected && !data.activities.some(r => r.activity_id === selected)) {
        const r = await fetch('/api/activities/' + encodeURIComponent(selected), {cache: 'no-store'});
        if (r.ok) { const x = await r.json(); data.activities.push(...(x.data || x).activities); }
      }
      render(data);
    } catch (_) {
      document.getElementById('activity-status').textContent = 'Activity unavailable. Displayed data may be stale.';
    } finally { window.setTimeout(poll, 3000); }
  }
  poll();
})();
