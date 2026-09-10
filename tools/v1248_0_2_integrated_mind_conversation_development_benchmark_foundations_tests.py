from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from integrated_mind_conversation_development_benchmark import *
from natural_language_action_routing import classify_natural_language_intent
c=[];ck=lambda v:c.append(bool(v))
reg=benchmark_registry(); run=run_ordinary_chat_integration_benchmark(); contract=build_integrated_mind_conversation_development_contract()
for v in (reg['ok'],reg['scenario_count']==12,reg['ordinary_chat_path_required'],reg['routing_metadata_alone_is_insufficient'],len(reg['outcomes'])==10,run['ok'],run['passed']==12,run['total']==12,run['ordinary_chat_path_exercised'],not run['routing_metadata_only'],contract['ok'],contract['mixed_conversation_action_distinguished'],contract['single_proposal_for_mixed_turn'],contract['conversation_wish_hypothetical_quote_suggestion_inert'],contract['natural_conversation_preserved'],contract['project_memory_requires_revalidation'],contract['reflection_does_not_create_authority'],contract['initiative_pacing_does_not_send'],contract['development_proposals_require_exact_review'],contract['privacy_preserved_across_systems']):ck(v)
for k,e in AUTHORITY_FLAGS.items():ck(reg.get(k) is e and run.get(k) is e and contract.get(k) is e)
by={x['case_id']:x for x in run['cases']}
for case in reg['scenarios']:
    row=by[case['case_id']]
    for v in (row['scenario_digest']==case['scenario_digest'],row['intent_category']==case['expected_intent'],row['development_path_active'] is case['expected_development_path_active'],row['event']==case['expected_event'],row['expected_behavior_met'],row['no_authority_granted'],not row['raw_text_returned'],row['content_free'],bool(row['message_digest']),bool(row['case_digest'])):ck(v)
for case_id in ('direct_development_command','mixed_conversation_and_command'):
    row=by[case_id]
    for v in (row['proposal_created_or_resumed'],row['proposal_id_present'],row['proposal_count_for_turn']==1,not row['conversation_path_preserved']):ck(v)
for case_id in ('emotional_conversation','wish_not_action','hypothetical_question','quoted_command','suggestion_not_action','planning_without_execution','stale_project_memory_question','privacy_bound_provider_question','ambiguous_go_ahead','dismissed_initiative_follow_up'):
    row=by[case_id]
    for v in (not row['proposal_created_or_resumed'],not row['proposal_id_present'],row['proposal_count_for_turn']==0,row['conversation_path_preserved']):ck(v)
mixed=classify_natural_language_intent('It would be nice to hear your voice. Build your own text-to-speech system with a voice you choose.')
for v in (mixed['category']=='action_request',mixed['embedded_action_present'],mixed['action_intent_present'],'mixed_conversation_and_action' in mixed['reason_codes'],not mixed['authorization_inferred'],not mixed['approval_created']):ck(v)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
