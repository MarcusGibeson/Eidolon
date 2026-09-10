from __future__ import annotations

import concurrent.futures, hashlib, json, os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for path in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(path) not in sys.path: sys.path.insert(0,str(path))

from conversational_command_integration import build_conversational_command_integration
from conversational_command_integration_foundations import classify_conversational_command_turn
from conversational_command_integration_reliability import build_conversational_command_operator_handoff, inspect_conversational_command_integration_health
from natural_language_action_routing import build_natural_language_action_projection
from ordinary_chat_development_campaign import load_development_campaign_proposal, process_ordinary_chat_development_turn

CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)

def source_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def turn(text,session,runtime):
    return process_ordinary_chat_development_turn(text,action_projection=build_natural_language_action_projection(text),session_id=session,runtime_root=runtime)

before=source_signature()

# Adversarial language matrix: action vocabulary inside non-actions must stay non-action.
non_actions={
    'The phrase “Build me an app” is only an example.':'discussion',
    'Suppose I asked you to build an app. What would happen?':'hypothetical',
    'Would you explain how you would build an app?':'information_request',
    'Maybe we should build an app later.':'discussion',
    'I hope someday you can build desktop applications.':'discussion',
}
for text,expected in non_actions.items():
    row=classify_conversational_command_turn(text)
    require(row['primary_act']==expected,f'adversarial_non_action:{text}:{row}')
    require(row['authorization_granted'] is False and row['execution_authorized'] is False,'adversarial_non_action_authority_denied')

# Oversized actionable text fails closed rather than executing a truncated instruction.
oversized='Build me a calculator webpage. '+'x'*13000
row=classify_conversational_command_turn(oversized)
require(row['primary_act']=='action_request' and row['requires_clarification'] is True,'oversized_action_requires_clarification')
projection=build_conversational_command_integration(oversized)
require(projection['status']=='ambiguous_action_blocked' and not projection['routing_text'],'oversized_action_not_routed')

# Case/punctuation variants remain deterministic.
for text in ('GO AHEAD!','Yes, proceed.','yes, do it!'):
    row=classify_conversational_command_turn(text)
    require(row['primary_act']=='authorization' and row['generic_authorization_shape'],'authorization_case_punctuation_normalized')
for text in ('ACTUALLY, make it blue.','Correction: use two columns.','Never mind, cancel it.'):
    row=classify_conversational_command_turn(text)
    require(row['primary_act'] in {'correction','cancellation'},'control_case_punctuation_normalized')

# Restart-safe persistence and session isolation.
with tempfile.TemporaryDirectory(prefix='eid-v1259-6-8-session-') as d:
    runtime=Path(d)/'runtime'
    a=turn('Build me a calculator webpage.','session-a',runtime); pa=a['proposal'];
    b=turn('Build me a notes webpage.','session-b',runtime); pb=b['proposal'];
    corrected=turn('Actually, make it dark mode.','session-a',runtime)
    require(corrected['event']=='conversational_correction_applied','session_scoped_correction_applies')
    require(load_development_campaign_proposal(pa['proposal_id'],runtime_root=runtime)['revision']==2,'session_a_revision_advanced')
    require(load_development_campaign_proposal(pb['proposal_id'],runtime_root=runtime)['revision']==1,'session_b_untouched')
    # A fresh call after the original Python objects are gone restores durable state.
    restored=load_development_campaign_proposal(pa['proposal_id'],runtime_root=runtime)
    require(restored['revision']==2 and restored['lifecycle_state']=='awaiting_approval','restart_safe_corrected_proposal_restoration')
    wrong_session=turn('Cancel that development proposal.','session-c',runtime)
    require(wrong_session['event']=='cancellation_target_ambiguous','unknown_session_cannot_cancel_other_session_proposal')
    require(load_development_campaign_proposal(pa['proposal_id'],runtime_root=runtime)['lifecycle_state']=='awaiting_approval','wrong_session_changes_nothing')

# Conversational corrections/stops must not accidentally mutate a pending development proposal.
with tempfile.TemporaryDirectory(prefix='eid-v1259-6-8-nondev-correction-') as d:
    runtime=Path(d)/'runtime'; session='nondev-correction'
    created=turn('Build me a calculator webpage.',session,runtime); pid=created['proposal']['proposal_id']
    for text in ('Actually, I meant Tuesday, not Thursday.','Stop calling me that.'):
        projection=build_conversational_command_integration(text,session_id=session,runtime_root=runtime)
        require(projection['status']=='conversation_only',f'nondevelopment_correction_not_proposal_control:{text}')
    final=load_development_campaign_proposal(pid,runtime_root=runtime)
    require(final['revision']==1 and final['lifecycle_state']=='awaiting_approval','nondevelopment_correction_leaves_pending_proposal_unchanged')

# Concurrent duplicate correction converges on one revision and one semantic correction.
with tempfile.TemporaryDirectory(prefix='eid-v1259-6-8-race-') as d:
    runtime=Path(d)/'runtime'; session='race-session'
    created=turn('Build me a calculator webpage.',session,runtime); pid=created['proposal']['proposal_id']
    def correct(_): return turn('Actually, make it dark mode instead.',session,runtime)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows=list(pool.map(correct,range(8)))
    final=load_development_campaign_proposal(pid,runtime_root=runtime)
    require(final['revision']==2,'concurrent_duplicate_correction_single_revision')
    require(final['request'].count('Operator correction: Actually, make it dark mode instead.')==1,'concurrent_duplicate_correction_single_semantic_append')
    require(all(row.get('event')=='conversational_correction_applied' for row in rows),'concurrent_duplicate_correction_idempotent_results')
    require(sum(bool(row.get('deduplicated')) for row in rows)>=7,'concurrent_duplicate_correction_reports_replays')

# Concurrent cancellation cannot create execution or approval authority.
with tempfile.TemporaryDirectory(prefix='eid-v1259-6-8-cancel-race-') as d:
    runtime=Path(d)/'runtime'; session='cancel-race'
    created=turn('Build me a calculator webpage.',session,runtime); pid=created['proposal']['proposal_id']
    def cancel(_): return turn('Cancel that development proposal.',session,runtime)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows=list(pool.map(cancel,range(8)))
    final=load_development_campaign_proposal(pid,runtime_root=runtime)
    require(final['lifecycle_state']=='cancelled','concurrent_cancellation_converges_terminal')
    require(final['approval_consumed'] is False,'concurrent_cancellation_never_consumes_approval')
    require(all(not bool(r.get('authorization_granted')) for r in rows),'concurrent_cancellation_never_grants_authorization')

# Generic authorization remains blocked even with exactly one pending target.
with tempfile.TemporaryDirectory(prefix='eid-v1259-6-8-authority-') as d:
    runtime=Path(d)/'runtime'; session='authority-session'
    created=turn('Build me a calculator webpage.',session,runtime); pid=created['proposal']['proposal_id']
    for text in ('Go ahead.','Yes, do it.','Proceed.'):
        blocked=turn(text,session,runtime)
        require(blocked['event']=='generic_authorization_blocked',f'generic_authority_blocked:{text}')
    final=load_development_campaign_proposal(pid,runtime_root=runtime)
    require(final['approval_consumed'] is False and final['revision']==1,'generic_authority_retries_change_nothing')

# Exact controls are passed to the original owner rather than duplicated by v1259.
exact='Approve development proposal devc_0123456789abcdef01234567 revision 1.'
projection=build_conversational_command_integration(exact)
require(projection['status']=='exact_authorization_passthrough','exact_authorization_owner_preserved')
exact_cancel='Cancel development proposal devc_0123456789abcdef01234567 revision 1.'
projection=build_conversational_command_integration(exact_cancel)
require(projection['status']=='exact_terminal_control_passthrough','exact_cancellation_owner_preserved')

health=inspect_conversational_command_integration_health(source_root=ROOT)
require(health['ok'] and all(health['checks'].values()),'read_only_health_passes')
require(health['read_only'] and health['provider_contacted'] is False and health['commands_executed'] is False,'health_inspection_executes_nothing')
handoff=build_conversational_command_operator_handoff(source_root=ROOT)
require(handoff['ok'] and handoff['operator_review_required'],'operator_handoff_ready')
require(len(handoff['desktop_focus'])>=6 and handoff['native_windows_multi_process_validation']=='desktop_review_required','desktop_focus_bounded')
require(handoff['release_authorized'] is False and handoff['independent_authority_granted'] is False,'handoff_grants_no_release_or_independent_authority')
require(source_signature()==before,'reliability_suite_preserves_source_immutability')

print(json.dumps({'ok':True,'suite':'v1259.6-v1259.8-conversational-command-integration-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'project_modified':False,'release_authorized':False,'independent_authority_granted':False},indent=2,sort_keys=True))
