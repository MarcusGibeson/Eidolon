/* v2733.6.1 - the rendered research play/pause control.
 *
 * Loads the real conscious_agent/static/activity.js against a minimal DOM, so what is tested is the file the
 * dashboard ships rather than a copy of its logic. Covers the states the operator sees, the custom data-tip and
 * accessible label, keyboard activation, that a click sends exactly one governed request, that repeated clicks
 * cannot stack, and that a re-render follows backend state rather than anything the page remembers.
 *
 *   node tools/v2733_6_1_research_control_ui.test.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const CHECKS = [];
const require_ = (condition, name) => CHECKS.push([name, Boolean(condition)]);

// --- the smallest DOM these scripts actually use -------------------------------------------------------------
class Node {
  constructor(tag) {
    this.tagName = String(tag || '').toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.listeners = {};
    this.className = '';
    this.disabled = false;
    this.textContent = '';
    this.type = '';
  }
  append(...nodes) { for (const n of nodes) if (n) this.children.push(n); }
  replaceChildren(...nodes) { this.children = nodes.filter(Boolean); }
  setAttribute(k, v) { this.attributes[k] = String(v); }
  getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attributes, k) ? this.attributes[k] : null; }
  addEventListener(kind, fn) { (this.listeners[kind] = this.listeners[kind] || []).push(fn); }
  click() { for (const fn of this.listeners.click || []) fn({}); }
  get text() { return [this.textContent, ...this.children.map(c => c.text)].join(''); }
  find(pred) {
    if (pred(this)) return this;
    for (const child of this.children) { const hit = child.find(pred); if (hit) return hit; }
    return null;
  }
  findAll(pred, out = []) {
    if (pred(this)) out.push(this);
    for (const child of this.children) child.findAll(pred, out);
    return out;
  }
}

// The affordance the backend would send, mirrored here only so the DOM has something to draw.
const AFFORDANCE = {
  running: {visible: true, action: 'pause', icon: 'pause', label: 'Pause research', enabled: true, pending: false,
            tip: 'Finish the current step, save a checkpoint, and stop.'},
  pause_requested: {visible: true, action: 'pause', icon: 'pause', label: 'Pausing…', enabled: false,
                    pending: true, tip: 'Finishing the current step, then saving a checkpoint.'},
  paused: {visible: true, action: 'resume', icon: 'play', label: 'Resume research', enabled: true, pending: false,
           tip: 'Continue this research from its saved checkpoint.'},
  complete: {visible: true, action: '', icon: 'none', label: 'Research finished', enabled: false, pending: false,
             tip: 'This research is complete and cannot be resumed.'},
  failed: {visible: true, action: '', icon: 'none', label: 'Research finished', enabled: false, pending: false,
           tip: 'This research is failed and cannot be resumed.'},
};
function harness(activityState, {type = 'experiment_review', control = null} = {}) {
  const surface = new Node('section');
  surface.dataset.detail = 'false';
  const status = new Node('div');
  const current = new Node('div');
  const byId = {'activity-surface': surface, 'activity-status': status, 'activity-current': current};
  const posts = [];
  let resolvePost;
  const payloadFor = state => ({
    contract: 'activity.v1', observed_at: '2026-09-21T00:00:00Z', active_count: 1,
    current: {
      activity_id: 'job_ui', type, state, title: 'Independent experiment review', subject: 'Q-UI',
      stage: 'Observing', progress: {completed: 4, total: 10, unit: 'required parts', percent: 40},
      stage_progress: null, metrics: {model_calls: 4}, warnings: [], stages: [], events: [],
      elapsed_seconds: 65, governance: {read_only: true}, terminal: ['complete', 'failed'].includes(state),
      control: control || affordanceFor(state, type),
    },
    activities: [],
  });
  let state = activityState;
  const context = {
    document: {
      getElementById: id => byId[id] || null,
      createElement: tag => new Node(tag),
    },
    location: {search: ''},
    URLSearchParams: class { constructor() {} get() { return null; } },
    setInterval: () => 0,
    // activity.js reschedules poll() through window.setTimeout; swallow the reschedule so one pass runs.
    setTimeout: () => 0,
    console,
    fetch: async (url, options) => {
      if (String(url).startsWith('/api/research/control')) {
        posts.push(JSON.parse(options.body));
        return {json: async () => ({ok: true, expect_state: JSON.parse(options.body).action === 'pause'
          ? 'pause_requested' : 'running'})};
      }
      return {ok: true, json: async () => payloadFor(state)};
    },
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'conscious_agent', 'static', 'activity.js'), 'utf8'),
                  context);
  return {surface, current, posts, setState: s => { state = s; }, context};
}

function affordanceFor(state, type) {
  if (type !== 'experiment_review') return {visible: false};
  return AFFORDANCE[state] || {visible: true, action: '', icon: 'none', label: '', enabled: false, pending: false};
}

// render() mounts the summary into #activity-current, so search the node activity.js actually fills.
const button = h => h.current.find(n => n.className && n.className.includes('activity-control-button'));

async function settle() { await new Promise(r => setImmediate(r)); await new Promise(r => setImmediate(r)); }

(async () => {
  // --- 1. running shows an enabled pause -------------------------------------------------------------------
  let h = harness('running');
  await settle();
  let b = button(h);
  require_(b !== null, 'running_shows_the_control');
  require_(b.disabled === false, 'running_pause_is_enabled');
  require_(b.getAttribute('aria-label') === 'Pause research', 'running_has_the_accessible_pause_label');
  require_(b.getAttribute('data-tip') === 'Finish the current step, save a checkpoint, and stop.',
           'running_uses_the_custom_data_tip');
  require_(b.getAttribute('title') === null, 'no_native_title_tooltip_is_used');
  require_(b.type === 'button', 'the_control_is_a_real_button_so_keyboard_activation_works');
  require_(b.text.includes('❙❙'), 'running_shows_a_pause_glyph');

  // --- 2. a click sends exactly one governed request, and repeats cannot stack -------------------------------
  b.click(); b.click(); b.click();
  await settle();
  require_(h.posts.length === 1, 'three_rapid_clicks_send_exactly_one_request');
  require_(h.posts[0].action === 'pause' && h.posts[0].job_id === 'job_ui',
           'the_request_names_the_action_and_the_job');
  require_(b.disabled === true, 'the_button_disables_itself_while_the_request_is_in_flight');
  require_(b.getAttribute('data-tip') === 'Pausing…', 'the_in_flight_tip_says_pausing');

  // --- 3. pause_requested is pending and not clickable -------------------------------------------------------
  h = harness('pause_requested');
  await settle();
  b = button(h);
  require_(b.disabled === true, 'pause_requested_is_not_clickable');
  require_(b.getAttribute('aria-busy') === 'true', 'pause_requested_is_marked_busy');
  require_(b.getAttribute('data-tip') === 'Pausing…', 'pause_requested_communicates_pausing');
  b.click();
  await settle();
  require_(h.posts.length === 0, 'a_pending_control_sends_nothing_when_clicked');

  // --- 4. paused offers resume ------------------------------------------------------------------------------
  h = harness('paused');
  await settle();
  b = button(h);
  require_(b.disabled === false, 'paused_offers_an_enabled_resume');
  require_(b.getAttribute('aria-label') === 'Resume research', 'paused_has_the_accessible_resume_label');
  require_(b.text.includes('▶'), 'paused_shows_a_play_glyph');
  require_(b.className.includes('icon-play'), 'the_play_icon_class_is_applied');
  b.click();
  await settle();
  require_(h.posts.length === 1 && h.posts[0].action === 'resume', 'a_play_click_requests_exactly_one_resume');

  // --- 5. terminal states never offer a resume ---------------------------------------------------------------
  for (const state of ['complete', 'failed']) {
    h = harness(state);
    await settle();
    b = button(h);
    require_(b.disabled === true, `${state}_control_is_disabled`);
    require_(!b.text.includes('▶'), `${state}_never_shows_a_play_glyph`);
    require_(/cannot be resumed/.test(b.getAttribute('data-tip')), `${state}_says_it_cannot_be_resumed`);
    b.click();
    await settle();
    require_(h.posts.length === 0, `${state}_sends_nothing_when_clicked`);
  }

  // --- 6. non-research work shows no control -----------------------------------------------------------------
  h = harness('running', {type: 'chat'});
  await settle();
  require_(button(h) === null, 'non_research_activity_shows_no_research_control');

  // --- 7. a re-render follows backend state, not what the page remembers --------------------------------------
  h = harness('running');
  await settle();
  button(h).click();
  await settle();
  require_(h.posts.length === 1, 'the_pause_was_requested');
  h = harness('paused');                     // the backend moved on; a fresh render must follow it
  await settle();
  require_(button(h).getAttribute('aria-label') === 'Resume research',
           'after_the_backend_reports_paused_the_control_offers_resume');
  h = harness('running');
  await settle();
  require_(button(h).disabled === false,
           'a_fresh_render_of_running_work_is_clickable_again_rather_than_stuck_pending');

  // --- 8. the progress bar and counts survive alongside the control -------------------------------------------
  h = harness('paused');
  await settle();
  const meter = h.current.findAll(n => n.tagName === 'PROGRESS');
  require_(meter.length === 1, 'the_progress_bar_is_still_rendered');
  require_(h.current.find(n => n.className === 'activity-count') !== null, 'the_counts_are_still_rendered');
  require_(h.current.find(n => n.className === 'activity-time') !== null, 'the_elapsed_time_is_still_rendered');
  const blob = JSON.stringify(h.current);
  for (const leak of ['prompt', 'reply', 'thinking', 'chain-of-thought']) {
    require_(!blob.toLowerCase().includes(leak), `no_reasoning_content_is_rendered:${leak}`);
  }

  const failed = CHECKS.filter(([, ok]) => !ok).map(([name]) => name);
  console.log(JSON.stringify({suite: 'v2733.6.1-research-control-ui', checks: CHECKS.length,
                              passed: CHECKS.length - failed.length, failed}));
  process.exit(failed.length ? 1 : 0);
})();
