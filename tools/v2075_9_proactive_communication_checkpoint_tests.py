from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2075-data-')
from proactive_communication_governance_v2000 import evaluate_communication_candidate,batch_queued_messages
from proactive_communication import ProactiveCommunicationStore
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2075-runtime-'))
store=ProactiveCommunicationStore(runtime)
summary=store.inspection_summary()
speak=evaluate_communication_candidate({'urgency':.9,'relevance':.9,'confidence':.9,'operator_priority':.8},store_snapshot=summary)
req(speak['action']=='speak','high_value_candidate_speaks')
ask=evaluate_communication_candidate({'urgency':.6,'relevance':.8,'confidence':.55,'needs_question':True},store_snapshot=summary)
req(ask['action']=='ask','uncertain_relevant_candidate_asks')
summary_action=evaluate_communication_candidate({'relevance':.8,'confidence':.9,'completion_summary':True},store_snapshot=summary)
req(summary_action['action']=='summarize','completion_summary_selected')
remind=evaluate_communication_candidate({'urgency':.75,'relevance':.75,'confidence':.9,'reminder_due':True},store_snapshot=summary)
req(remind['action']=='remind','due_reminder_selected')
wait=evaluate_communication_candidate({'urgency':.2,'relevance':.2,'confidence':.9},store_snapshot=summary)
req(wait['action']=='wait','low_value_candidate_silent')
ignored=evaluate_communication_candidate({'urgency':.7,'relevance':.9,'confidence':.9,'ignored_count':2},store_snapshot=summary)
req(ignored['action']=='wait' and 'ignored_cue_cooldown' in ignored['blocker_codes'],'ignored_cues_suppress_repetition')
quiet=dict(summary);quiet['preferences']=dict(summary['preferences']);quiet['preferences']['quiet_indefinite']=True
q=evaluate_communication_candidate({'urgency':1,'relevance':1,'confidence':1},store_snapshot=quiet)
req(q['action']=='wait' and 'explicit_quiet' in q['blocker_codes'],'quiet_boundary_wins')
unread=dict(summary);unread['unread_count']=1
u=evaluate_communication_candidate({'urgency':1,'relevance':1,'confidence':1},store_snapshot=unread)
req(u['action']=='wait' and 'prior_message_unread' in u['blocker_codes'],'unread_message_prevents_stacking')
req(speak['delivery_claimed'] is False and speak['message_delivered'] is False,'policy_never_delivers')
batch=batch_queued_messages(runtime_root=runtime)
req(batch['ok'] and batch['batch_count']==0,'empty_retained_queue_batches_cleanly')
req(batch['delivery_authorized'] is False and batch['raw_message_body_exposed'] is False,'batch_review_non_authorizing_content_minimized')
# Retained queue itself still exposes exactly-once delivery claims as separate operations.
req(hasattr(store,'claim_delivery') and hasattr(store,'mark_read') and hasattr(store,'withdraw_for_correction'),'retained_queue_lifecycle_reused')
print(json.dumps({'suite':'v2075.9-proactive-communication','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
