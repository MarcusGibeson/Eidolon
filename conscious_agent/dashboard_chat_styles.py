from __future__ import annotations

"""Lightweight CSS contract for the companion conversation surface."""

COMPANION_CHAT_STYLES = """
.chat-date-divider { text-align:center; color:#a89f9f; font-size:12px; margin:18px 0; padding:6px 0; border-bottom:1px solid rgba(160,150,150,.18); }
/* v1079.7.0 conversational responsiveness and companion quality. */
.companion-chat-header { display:grid; grid-template-columns:minmax(0,1fr) auto auto; gap:12px; align-items:center; padding:4px 2px 2px; }
.companion-chat-header h2 { margin:2px 0 0; font-size:20px; color:#f7eeee; letter-spacing:.01em; }
.chat-eyebrow { color:#a99593; letter-spacing:.12em; text-transform:uppercase; }
.companion-status-card { display:flex; gap:9px; align-items:center; max-width:360px; border:1px solid rgba(255,54,45,.18); border-radius:14px; background:rgba(16,9,10,.76); padding:8px 11px; color:#d7c9c7; }
.companion-status-card span:nth-child(2) { display:grid; gap:2px; }
.companion-status-card small { color:#9d8e8c; line-height:1.3; }
.companion-status-dot { width:10px; height:10px; border-radius:50%; background:#ff4b42; box-shadow:0 0 14px rgba(255,54,45,.62); flex:0 0 auto; }
.companion-status-card[data-state='ready'] .companion-status-dot,
.companion-status-card[data-state='recovered'] .companion-status-dot { background:#b9d7bd; box-shadow:0 0 12px rgba(185,215,189,.46); }
.companion-status-card[data-state='responding'] .companion-status-dot,
.companion-status-card[data-state='thinking'] .companion-status-dot,
.companion-status-card[data-state='connecting'] .companion-status-dot,
.companion-status-card[data-state='saving'] .companion-status-dot,
.companion-status-card[data-state='draft_saving'] .companion-status-dot,
.companion-status-card[data-state='switching'] .companion-status-dot,
.companion-status-card[data-state='creating'] .companion-status-dot,
.companion-status-card[data-state='archiving'] .companion-status-dot,
.companion-status-card[data-state='restoring'] .companion-status-dot { animation:eidolonPulse 1s infinite alternate; }
.companion-status-card[data-state='cancelled'] .companion-status-dot,
.companion-status-card[data-state='attention'] .companion-status-dot,
.companion-status-card[data-state='disconnected'] .companion-status-dot { background:#ffb05e; box-shadow:0 0 12px rgba(255,176,94,.5); }
.companion-status-card[data-state='offline'] .companion-status-dot { background:#8f8584; box-shadow:none; }
.chat-mode-pill { justify-self:end; border:1px solid rgba(255,54,45,.14); border-radius:999px; padding:6px 10px; color:#aa9b99; background:rgba(18,10,11,.5); font-size:12px; }
.chat-tab-coordination { grid-column:1 / -1; display:flex; flex-wrap:wrap; gap:8px; align-items:center; min-width:0; color:#a99b99; font-size:12px; }
.chat-tab-coordination[data-owner='true'] { color:#b9d7bd; }
.chat-tab-coordination[data-conflict='true'] { color:#ffb05e; }
.chat-tab-coordination button { padding:4px 9px; font-size:11px; }
.chat-primary-conversation-bar { display:flex; flex-wrap:wrap; gap:8px; align-items:end; min-width:0; border:1px solid rgba(255,54,45,.14); border-radius:13px; padding:8px 10px; background:rgba(12,8,9,.58); }
.chat-primary-conversation-bar form { margin:0; min-width:0; }
.realtime-chat-shell,.realtime-chat-shell * { box-sizing:border-box; }
.realtime-chat-shell { width:100%; max-width:100%; min-width:0; overflow-x:clip; }
.realtime-chat-shell textarea,.realtime-chat-shell input,.realtime-chat-shell select { max-width:100%; }
.chat-primary-conversation-bar label { min-width:min(420px,70vw); margin:0; }
.chat-primary-conversation-bar select { width:100%; min-width:0; }
.chat-session-toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:end; min-width:0; }
.chat-tools-drawer,.chat-diagnostics-drawer { border:1px solid rgba(255,54,45,.14); border-radius:13px; padding:8px 10px; background:rgba(12,8,9,.58); color:#bbaead; }
.chat-tools-drawer > summary,.chat-diagnostics-drawer > summary { cursor:pointer; color:#d7c8c6; font-weight:700; }
.chat-tools-drawer[open],.chat-diagnostics-drawer[open] { display:grid; gap:10px; }
.chat-working-context-control,.chat-offline-intent-control { display:block; min-width:0; max-width:100%; border:1px solid rgba(255,54,45,.14); border-radius:12px; padding:8px 10px; overflow-wrap:anywhere; }
.chat-working-context-control > summary,.chat-offline-intent-control > summary { cursor:pointer; color:#d7c8c6; font-weight:700; }
.chat-working-context-editor,.chat-offline-intent-editor { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:8px; align-items:end; min-width:0; margin:9px 0; }
.chat-pin-content-label { grid-column:1 / -1; min-width:0; }
.chat-pinned-context-list { display:grid; gap:7px; margin:8px 0; padding:0; list-style:none; min-width:0; }
.chat-pinned-context-item { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:6px 10px; align-items:center; min-width:0; padding:7px 8px; border:1px solid rgba(255,255,255,.08); border-radius:9px; }
.chat-pinned-context-item small { grid-column:1 / -1; overflow-wrap:anywhere; }
.chat-turn { display:grid; gap:4px; max-width:88%; min-width:0; overflow-wrap:anywhere; }
.chat-turn.user-turn { justify-self:end; justify-items:end; }
.chat-turn.eidolon-turn { justify-self:start; justify-items:start; }
.chat-speaker { color:#8f8180; letter-spacing:0; text-transform:none; font-size:10px; padding:0 5px; }
.chat-turn .chat-bubble { max-width:100%; min-width:0; overflow-wrap:anywhere; word-break:break-word; }
.chat-turn-state { color:#c99867; padding:0 6px; }
.chat-bubble.failed { display:grid; gap:5px; border-color:rgba(255,176,94,.38); background:rgba(43,26,11,.58); }
.chat-turn-state.recovered { color:#b9d7bd; }
.chat-recovery-actions { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:2px 0 8px 5px; }
.chat-recovery-actions a,.chat-recovery-actions button { font-size:12px; }
.chat-turn-diagnostics { max-width:760px; margin:0 0 10px 5px; border:1px solid rgba(255,176,94,.18); border-radius:11px; padding:7px 9px; background:rgba(18,12,9,.45); }
.chat-turn-diagnostics > summary { cursor:pointer; color:#bda998; }
.chat-diagnostic-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:7px 14px; margin:9px 0; }
.chat-diagnostic-evidence { margin:5px 0 8px; }
.chat-recovery-note,.chat-recovery-history { display:block; margin:2px 0 6px 5px; overflow-wrap:anywhere; }
.chat-explicit-resend-presentation { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:6px 0 8px 5px; padding:8px 10px; border:1px solid var(--line); border-radius:10px; max-width:100%; }
.chat-explicit-resend-presentation small { flex:1 1 280px; overflow-wrap:anywhere; }
.chat-explicit-resend-presentation button { flex:0 0 auto; }
.chat-action-portal { display:grid; gap:7px; width:min(760px,calc(100% - 10px)); max-width:100%; min-width:0; margin:2px 0 10px 5px; padding:11px 12px; border:1px solid rgba(255,54,45,.24); border-radius:13px; background:rgba(21,12,13,.74); overflow-wrap:anywhere; }
.chat-action-portal[data-action-status='completed'] { border-color:rgba(185,215,189,.34); }
.chat-action-portal[data-action-status='failed'],.chat-action-portal[data-action-status='timed_out'],.chat-action-portal[data-action-status='blocked'],.chat-action-portal[data-action-status='cancelled'] { border-color:rgba(255,176,94,.38); }
.chat-action-portal-head { display:flex; flex-wrap:wrap; gap:7px; align-items:center; min-width:0; }
.chat-action-portal p { margin:0; }
.chat-action-portal-actions { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
.chat-action-portal form { margin:0; }
.chat-action-portal .badge { white-space:normal; }
.chat-research-progress { display:grid; gap:6px; padding:9px 0 2px; border-top:1px solid rgba(255,255,255,.08); }
.chat-research-progress-head { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.chat-research-progress progress { width:100%; height:8px; accent-color:#5dd6d0; }
.chat-research-progress small { color:var(--muted); }
.chat-research-review { min-width:0; border-top:1px solid rgba(255,255,255,.08); padding-top:7px; }
.chat-research-review > summary { cursor:pointer; color:#c7d9d7; font-size:12px; font-weight:700; }
.chat-research-review-body { display:grid; gap:6px; min-width:0; padding-top:8px; }
.chat-research-review-counts { color:#d8e4e2; font-size:12px; overflow-wrap:anywhere; }
.chat-research-review small { color:var(--muted); overflow-wrap:anywhere; }
.chat-research-citations { display:grid; gap:6px; min-width:0; margin:2px 0; padding-left:20px; }
.chat-research-citations li { min-width:0; }
.chat-research-citations a { display:block; width:fit-content; max-width:100%; overflow-wrap:anywhere; }
.chat-research-citations small { display:block; margin-top:2px; }
.chat-research-confidence { display:grid; gap:4px; min-width:0; padding:6px 0; }
.chat-research-confidence ul { display:grid; gap:3px; margin:0; padding-left:20px; }
.chat-research-confidence li { min-width:0; overflow-wrap:anywhere; }
.chat-research-confidence li small { display:block; margin-top:1px; }
.chat-research-matrix-wrap { max-width:100%; overflow-x:auto; border:1px solid rgba(255,255,255,.08); border-radius:6px; }
.chat-research-matrix { width:100%; min-width:640px; border-collapse:collapse; font-size:11px; }
.chat-research-matrix caption { text-align:left; padding:6px; font-weight:700; color:#d8e4e2; }
.chat-research-matrix th,.chat-research-matrix td { padding:6px; border-top:1px solid rgba(255,255,255,.07); text-align:left; vertical-align:top; }
.chat-research-matrix td small { display:block; margin-top:2px; }
.chat-research-comparison { display:grid; gap:6px; max-width:100%; min-width:0; overflow-wrap:anywhere; }
.chat-research-comparison summary { cursor:pointer; font-weight:650; }
.chat-research-comparison-counts { font-size:0.88rem; line-height:1.45; }
.chat-research-comparison small { display:block; overflow-wrap:anywhere; }
.chat-research-history { min-width:0; border-top:1px solid rgba(255,255,255,.08); padding-top:7px; }
.chat-research-history > summary { cursor:pointer; color:#c7d9d7; font-size:12px; font-weight:700; }
.chat-research-history-list { display:grid; gap:7px; min-width:0; margin:7px 0; padding-left:20px; }
.chat-research-history-item { display:grid; gap:2px; min-width:0; overflow-wrap:anywhere; }
.chat-research-history-item code,.chat-research-history-item small,.chat-research-history > small { max-width:100%; overflow-wrap:anywhere; }
.chat-research-history-warning { color:#f3c982; }
.chat-action-timeline { border-top:1px solid rgba(255,255,255,.08); padding-top:6px; min-width:0; }
.chat-action-timeline > summary { cursor:pointer; color:#c7b8b6; font-size:12px; }
.chat-action-timeline ol { display:grid; gap:5px; margin:7px 0 0; padding-left:20px; min-width:0; }
.chat-action-timeline li { min-width:0; overflow-wrap:anywhere; color:#a99b99; font-size:12px; }
.chat-action-timeline li b { color:#d4c7c5; }
.chat-composer-label { min-width:0; margin:0; }
.chat-composer-actions { display:flex; gap:8px; align-items:end; }
.chat-composer-actions button { min-width:104px; }
.chat-jump-latest { justify-self:center; position:sticky; bottom:116px; z-index:4; min-width:0; padding:7px 12px; border-radius:999px; box-shadow:0 8px 24px rgba(0,0,0,.38); }
.realtime-chat-shell.compact .chat-history-window-controls { display:flex; align-items:center; justify-content:space-between; gap:10px; min-width:0; }
.chat-history-window-controls small { overflow-wrap:anywhere; }
.realtime-chat-log { height:clamp(180px,32dvh,300px); min-height:180px; max-height:300px; overscroll-behavior:contain; scrollbar-gutter:stable; overflow-anchor:none; }
.realtime-chat-shell.compact .realtime-chat-form { display:grid; grid-template-columns:minmax(0,1fr); position:sticky; bottom:8px; z-index:5; min-width:0; padding:8px; border:1px solid rgba(255,54,45,.16); border-radius:14px; background:rgba(7,6,7,.98); box-shadow:0 -10px 24px rgba(0,0,0,.42); }
.realtime-chat-shell.compact .chat-composer-label { display:block; width:100%; min-width:0; }
.realtime-chat-shell.compact .realtime-chat-form textarea { display:block; width:100%; min-width:0; }
.realtime-chat-shell.compact .chat-composer-actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; align-items:center; min-width:0; }
.realtime-chat-shell.compact .chat-draft-status { grid-column:1 / -1; min-width:0; margin:0; overflow-wrap:anywhere; }
.realtime-chat-shell.compact .chat-composer-actions button { width:100%; min-width:0; }
.chat-console-primary .realtime-chat-shell { min-height:calc(100dvh - 190px); }
.chat-console-primary .realtime-chat-log { height:min(62dvh,720px); min-height:360px; max-height:none; overscroll-behavior:contain; scrollbar-gutter:stable; overflow-anchor:none; }
.chat-console-primary .realtime-chat-form { position:sticky; bottom:0; z-index:3; padding-top:8px; background:linear-gradient(180deg,rgba(7,6,7,0),rgba(7,6,7,.98) 22%); }
.chat-console-secondary { margin-top:14px; }
.chat-console-secondary > summary { cursor:pointer; color:#cdbfbd; font-weight:700; padding:10px 2px; }
.realtime-chat-shell button:focus-visible,.realtime-chat-shell a:focus-visible,.realtime-chat-shell select:focus-visible,.realtime-chat-shell textarea:focus-visible,.realtime-chat-shell input:focus-visible { outline:2px solid rgba(255,176,94,.9); outline-offset:2px; }
.conversation-session-row { display:grid; gap:7px; min-width:0; }
.conversation-session-row > div { min-width:0; }
.conversation-session-row .inline { display:flex; flex-wrap:wrap; min-width:0; }
.conversation-session-row input { flex:1 1 180px; min-width:120px; max-width:100%; }
.conversation-session-group { list-style:none; margin:10px 0 2px; padding:5px 2px; color:#d4c7c5; font-size:12px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; border-bottom:1px solid rgba(255,255,255,.08); }
.conversation-session-snippet { display:block; max-width:100%; color:#9f9190; overflow-wrap:anywhere; }
.conversation-catalog-pager { display:flex; justify-content:space-between; gap:8px; align-items:center; }
.conversation-catalog-pager button { min-width:96px; }
.chat-session-organizer form.inline { flex-wrap:wrap; }
.chat-session-organizer input[name='q'] { min-width:min(340px,70vw); max-width:100%; }
.chat-session-organizer ul { min-width:0; }
.chat-attention-center { border:1px solid rgba(255,176,94,.16); border-radius:12px; padding:8px 10px; background:rgba(20,14,9,.38); }
.chat-attention-center > summary { cursor:pointer; color:#d4c7c5; font-weight:700; }
.attention-center-counts { display:flex; flex-wrap:wrap; gap:7px; margin:9px 0; }
.attention-center-list { display:grid; gap:7px; margin:8px 0; padding:0; list-style:none; min-width:0; }
.attention-center-item { display:grid; gap:3px; min-width:0; padding:8px 9px; border:1px solid rgba(255,255,255,.08); border-radius:10px; background:rgba(10,8,8,.5); overflow-wrap:anywhere; }
.attention-center-item[data-requires-operator='true'] { border-color:rgba(255,176,94,.32); }
.attention-center-item-head { display:flex; flex-wrap:wrap; gap:7px; align-items:center; min-width:0; }
.attention-center-item-head b { min-width:0; overflow-wrap:anywhere; }
.attention-center-item a { justify-self:start; font-size:12px; }
.attention-center-empty { color:#9f9190; }
@media (max-width:620px) { .conversation-catalog-pager { display:grid; grid-template-columns:1fr 1fr; } .conversation-catalog-pager button { width:100%; min-width:0; } }
.chat-draft-status { margin-right:auto; align-self:center; color:#9d8e8c; }
.chat-draft-status[data-state='saving'] { color:#d4a66f; }
.chat-draft-status[data-state='saved'] { color:#b9d7bd; }
.chat-draft-status[data-state='error'] { color:#ffb05e; }
.chat-offline-session-durability { display:flex; flex-wrap:wrap; gap:8px 12px; align-items:center; padding:9px 11px; border:1px solid rgba(185,215,189,.2); border-radius:12px; background:rgba(12,18,14,.55); color:#cfe1d1; }
.chat-offline-session-durability small { flex:1 1 320px; color:#aebdaf; overflow-wrap:anywhere; }
.chat-draft-conflict { display:grid; gap:8px; padding:10px 11px; border:1px solid rgba(255,176,94,.4); border-radius:12px; background:rgba(45,27,12,.45); }
.chat-draft-conflict[hidden] { display:none; }
.chat-draft-conflict-actions { display:flex; flex-wrap:wrap; gap:8px; }
.chat-draft-conflict-actions button { min-width:0; }
.chat-jump-latest[data-unread-count]:not([data-unread-count='0'])::after { content:' (' attr(data-unread-count) ')'; }
.chat-diagnostics-drawer .chat-latency-panel { margin-top:8px; }
.conversation-reentry-panel { margin:8px 0 2px; border:1px solid rgba(255,54,45,.12); border-radius:13px; background:rgba(12,8,9,.42); padding:7px 10px; }
.conversation-reentry-panel > small { color:#948684; }
.conversation-reentry-cues { display:grid; gap:5px; margin:6px 0 0; padding:0; list-style:none; }
.conversation-reentry-cue { display:flex; align-items:center; gap:8px; min-width:0; color:#b8aaa8; }
.conversation-reentry-cue b { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#d4c8c6; font-size:13px; }
.conversation-reentry-cue-state { margin-left:auto; border:1px solid rgba(255,176,94,.2); border-radius:999px; padding:3px 8px; color:#c7aa88; background:rgba(36,22,12,.35); font-size:11px; white-space:nowrap; }
.conversation-reentry-cue[data-cue-kind='still_responding'] .conversation-reentry-cue-state { color:#c9b9b7; border-color:rgba(255,54,45,.18); }
.conversation-reentry-cue[data-cue-kind='reply_ready'] .conversation-reentry-cue-state { color:#b9d7bd; border-color:rgba(185,215,189,.2); }
.conversation-reentry-cue form { margin:0; }
.conversation-reentry-cue button { padding:4px 8px; font-size:11px; }
.provider-recovery-resume-cue { margin:8px 0 2px; display:grid; gap:6px; border:1px solid rgba(255,176,94,.22); border-radius:13px; background:rgba(20,13,9,.45); padding:9px 10px; min-width:0; }
.provider-recovery-resume-cue[data-state='ready'],.provider-recovery-resume-cue[data-state='recovering'] { border-color:rgba(185,215,189,.24); background:rgba(10,22,13,.42); }
.provider-recovery-resume-cue strong,.provider-recovery-resume-cue span,.provider-recovery-resume-cue small { overflow-wrap:anywhere; }
.provider-recovery-resume-cue .provider-recovery-actions { display:flex; flex-wrap:wrap; gap:7px; }
.chat-recovery-contract { margin:8px 0 2px; display:grid; gap:5px; border:1px solid rgba(126,170,210,.24); border-radius:13px; background:rgba(10,16,24,.46); padding:9px 10px; min-width:0; }
.chat-recovery-contract[data-state='accepted_recovery_available'],.chat-recovery-contract[data-state='explicit_resend_available'],.chat-recovery-contract[data-state='explicit_resend_claimed'],.chat-recovery-contract[data-state='provider_unavailable'] { border-color:rgba(255,176,94,.28); background:rgba(20,13,9,.45); }
.chat-recovery-contract[data-state='accepted_recovered'],.chat-recovery-contract[data-state='provider_recovered'] { border-color:rgba(185,215,189,.28); background:rgba(10,22,13,.42); }
.chat-recovery-contract strong,.chat-recovery-contract span,.chat-recovery-contract small { overflow-wrap:anywhere; }
@media (max-width:900px) { .companion-chat-header { grid-template-columns:1fr; } .chat-mode-pill { justify-self:start; } .companion-status-card { max-width:none; } .chat-turn { max-width:96%; } .chat-composer-actions { justify-content:flex-start; flex-wrap:wrap; } .chat-console-primary { padding-bottom:230px; } .chat-console-primary .realtime-chat-shell { min-height:auto; } .chat-console-primary .realtime-chat-shell > * { order:4; } .chat-console-primary .companion-chat-header { order:0; } .chat-console-primary .chat-primary-conversation-bar { order:1; } .chat-console-primary .realtime-chat-log,.chat-console-primary .chat-history-window-controls,.chat-console-primary .chat-jump-latest { order:2; } .chat-console-primary .realtime-chat-form { position:fixed; left:12px; right:12px; bottom:8px; z-index:30; max-height:calc(100dvh - 16px); overflow-y:auto; padding:8px; border:1px solid rgba(255,54,45,.28); border-radius:14px; background:rgba(7,6,7,.99); box-shadow:0 -10px 28px rgba(0,0,0,.52); } .chat-console-primary .realtime-chat-log { height:clamp(180px,34dvh,300px); min-height:180px; } .realtime-chat-shell button,.realtime-chat-shell select,.realtime-chat-shell input:not([type='checkbox']) { min-height:44px; } }
@media (max-width:620px) { html,body { max-width:100%; overflow-x:hidden; } .realtime-chat-shell,.realtime-chat-shell .panel,.realtime-chat-shell .card,.realtime-chat-shell .page-band,.realtime-chat-shell form,.realtime-chat-shell fieldset { max-width:100%; min-width:0; } .realtime-chat-shell textarea { width:100%; min-width:0; }  .chat-primary-conversation-bar { align-items:stretch; } .chat-primary-conversation-bar form,.chat-primary-conversation-bar label,.chat-primary-conversation-bar select,.chat-primary-conversation-bar button { width:100%; min-width:0; } .conversation-reentry-cue { flex-wrap:wrap; } .conversation-reentry-cue-state { margin-left:0; } .provider-recovery-resume-cue .provider-recovery-actions > * { flex:1 1 100%; text-align:center; } .chat-composer-actions { display:grid; grid-template-columns:1fr 1fr; align-items:center; } .chat-draft-status { grid-column:1 / -1; margin:0; } .chat-composer-actions button { min-width:0; width:100%; } .chat-recovery-actions > *,.chat-explicit-resend-presentation > *,.chat-draft-conflict-actions > * { flex:1 1 100%; text-align:center; } .chat-turn-diagnostics { max-width:100%; margin-left:0; overflow-wrap:anywhere; } .chat-action-timeline ol,.chat-research-citations,.chat-research-history-list { padding-left:18px; } .chat-research-review-body,.chat-research-history { max-width:100%; min-width:0; } .chat-working-context-editor,.chat-offline-intent-editor { grid-template-columns:1fr; } .chat-pinned-context-item { grid-template-columns:1fr; } .chat-pinned-context-item button { width:100%; min-width:0; } }
"""


# v1092.8 project recovery panel: content-free, responsive, and keyboard-visible.
PROJECT_RECOVERY_STYLES = r"""
.chat-project-recovery{display:grid;grid-template-columns:minmax(10rem,1fr) auto;gap:.45rem .8rem;align-items:center;padding:.72rem .85rem;border:1px solid var(--line);border-radius:.8rem;background:var(--panel);margin:.65rem 0}.chat-project-recovery>small{grid-column:1/-1}.chat-project-recovery-summary{display:flex;gap:.35rem;flex-wrap:wrap}.chat-project-recovery button{justify-self:end}.chat-project-recovery[data-status='stale_tab'],.chat-project-recovery[data-status='source_unavailable'],.chat-project-recovery[data-status='interrupted_switch']{border-style:dashed}.chat-project-recovery button:focus-visible{outline:2px solid currentColor;outline-offset:2px}@media(max-width:700px){.chat-project-recovery{grid-template-columns:1fr}.chat-project-recovery button{justify-self:stretch;min-height:2.75rem}}
"""
COMPANION_CHAT_STYLES += PROJECT_RECOVERY_STYLES


# v1093.8 metadata recovery panel: async, content-free, responsive, and keyboard-visible.
METADATA_RECOVERY_STYLES = r"""
.chat-metadata-recovery{display:grid;grid-template-columns:minmax(10rem,1fr) auto;gap:.45rem .8rem;align-items:center;padding:.72rem .85rem;border:1px solid var(--line);border-radius:.8rem;background:var(--panel);margin:.65rem 0}.chat-metadata-recovery>small{grid-column:1/-1}.chat-metadata-recovery-summary{display:flex;gap:.35rem;flex-wrap:wrap}.chat-metadata-recovery button{justify-self:end}.chat-metadata-recovery[data-status='busy'],.chat-metadata-recovery[data-status='recovery_required'],.chat-metadata-recovery[data-status='uncertain']{border-style:dashed}.chat-metadata-recovery button:focus-visible{outline:2px solid currentColor;outline-offset:2px}@media(max-width:700px){.chat-metadata-recovery{grid-template-columns:1fr}.chat-metadata-recovery button{justify-self:stretch;min-height:2.75rem}}
"""
COMPANION_CHAT_STYLES += METADATA_RECOVERY_STYLES
# v1094.5 process recovery panel: restart-safe, content-free, and accessible.
PROCESS_RECOVERY_STYLES = r"""
.chat-process-recovery-row[data-status='uncertain'],.chat-process-recovery-row[data-status='orphaned']{border-style:dashed}.chat-process-recovery-row small{overflow-wrap:anywhere}
.chat-process-recovery{display:grid;grid-template-columns:minmax(10rem,1fr) auto;gap:.45rem .8rem;align-items:center;padding:.72rem .85rem;border:1px solid var(--line);border-radius:.8rem;background:var(--panel);margin:.65rem 0}.chat-process-recovery>small,.chat-process-recovery-rows{grid-column:1/-1}.chat-process-recovery-summary{display:flex;gap:.35rem;flex-wrap:wrap}.chat-process-recovery button{justify-self:end}.chat-process-recovery[data-status='busy'],.chat-process-recovery[data-status='recovery_required'],.chat-process-recovery[data-status='uncertain']{border-style:dashed}.chat-process-recovery-rows{display:grid;gap:.35rem}.chat-process-recovery-row{display:flex;justify-content:space-between;align-items:center;gap:.75rem;padding:.45rem .55rem;border:1px solid var(--line);border-radius:.55rem}.chat-process-recovery-row span{display:grid}.chat-process-recovery button:focus-visible{outline:2px solid currentColor;outline-offset:2px}@media(max-width:700px){.chat-process-recovery{grid-template-columns:1fr}.chat-process-recovery button{justify-self:stretch;min-height:2.75rem}.chat-process-recovery-row{align-items:stretch;flex-direction:column}}
"""
COMPANION_CHAT_STYLES += PROCESS_RECOVERY_STYLES

# v1489.0118 high-contrast chat accessibility.
COMPANION_CHAT_STYLES += r"""
@media (forced-colors: active) { .realtime-chat-shell button,.realtime-chat-shell a,.realtime-chat-shell textarea,.realtime-chat-shell input,.realtime-chat-shell select { forced-color-adjust:auto; } .realtime-chat-shell *:focus-visible { outline:2px solid CanvasText !important; outline-offset:2px; } }
"""

# v2502.5 bounded local research export surface.
COMPANION_CHAT_STYLES += r"""
.chat-research-export { display:grid; gap:5px; max-width:100%; min-width:0; overflow-wrap:anywhere; }
.chat-research-export code { overflow-wrap:anywhere; white-space:normal; }
.chat-research-export small { display:block; overflow-wrap:anywhere; }
"""

# v2503.3 research evidence matrix accessibility: preserve meaning without motion or color dependence.
RESEARCH_ACCESSIBILITY_STYLES = r"""
@media (prefers-reduced-motion: reduce) {
  .chat-research-review,.chat-research-confidence,.chat-research-matrix-wrap { scroll-behavior:auto; animation:none; transition:none; }
}
@media (forced-colors: active) {
  .chat-research-matrix-wrap,.chat-research-matrix th,.chat-research-matrix td { border-color:CanvasText; }
  .chat-research-matrix caption,.chat-research-confidence strong { color:CanvasText; }
}
"""
COMPANION_CHAT_STYLES += RESEARCH_ACCESSIBILITY_STYLES

# v2510 live cognitive activity feed: transient, bounded, and explicitly not chain-of-thought.
COMPANION_CHAT_STYLES += r"""
.chat-live-activity{grid-column:1/-1;display:none;gap:4px;padding:7px 10px;border:1px solid rgba(255,54,45,.13);border-radius:10px;background:rgba(12,8,9,.38);min-width:0}
.chat-live-activity[data-active='true']{display:grid}.chat-live-activity>small{color:#958886}.chat-live-activity-lines{display:grid;gap:3px;max-height:96px;overflow:auto;scrollbar-width:thin}
.chat-live-activity-line{display:grid;grid-template-columns:10px minmax(0,1fr);gap:6px;align-items:start;color:#bcaeac;font-size:12px;line-height:1.35}.chat-live-activity-line span:last-child{overflow-wrap:anywhere}
.chat-live-activity-dot{width:6px;height:6px;border-radius:999px;margin-top:.36em;background:currentColor;opacity:.65}.chat-live-activity-line[data-kind='milestone']{color:#d7c5c2}.chat-live-activity-line[data-kind='observation']{font-style:italic}
@media(max-width:620px){.chat-live-activity-lines{max-height:84px}.chat-live-activity{padding:6px 8px}}
"""
