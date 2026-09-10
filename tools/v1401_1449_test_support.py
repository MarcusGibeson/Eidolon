from __future__ import annotations

import hashlib
import importlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from bounded_capability_evidence import AUTHORITY_DENIED, digest, valid_seal
from initiative_backlog_scheduler import *
from outcome_learning import *
from cognitive_architecture_beta import *
from unified_companion_developer import *
from desktop_daily_use import *
from roadmap_v1500_capability_registry import CAPABILITIES

ROOT=Path(__file__).resolve().parents[1]

def require(v:object,msg:str='requirement'):
    assert bool(v),msg

def phase11():
    health=observe_project_health({'project_digest':'a'*64,'failed_tests':2,'test_suite_digest':'b'*64,'stale_dependencies':1,'lock_digest':'c'*64,'broken_doc_links':1,'docs_digest':'d'*64,'performance_drift':.12,'performance_baseline_digest':'e'*64,'warning_count':3,'warning_set_digest':'f'*64})
    opp=detect_opportunities({'uncovered_public_behaviors':3,'coverage_digest':'1'*64,'high_churn_low_coverage_files':2,'hotspot_digest':'2'*64,'duplicate_clusters':1,'duplication_digest':'3'*64,'ux_failures':1,'ux_evidence_digest':'4'*64,'unmet_requirements':1,'requirements_digest':'5'*64})
    candidates=[]
    for i,o in enumerate(opp['payload']['opportunities']):
        candidates.append({**o,'value':.9-i*.05,'cost':.2+i*.03,'risk':'low','urgency':.8,'unblock_value':.7,'ttl_seconds':1000,'dependencies':[]})
    backlog=create_backlog(candidates,now_epoch=100)
    tasks=[]
    for i,t in enumerate(backlog['payload']['tasks']): tasks.append({**t,'urgency':.8-i*.05,'unblock_value':.8 if i==0 else .2})
    priority=prioritize_backlog(tasks,{t['kind']:.8 for t in tasks})
    top=priority['payload']['ranked_tasks'][0]
    pacing=pace_initiative(top,standing_authority=True,quiet=False,operator_load=.2)
    schedule=evaluate_schedule_window(top,{'local_hour':14,'quiet_start':22,'quiet_end':7,'gaming_or_resource_intensive':False,'provider_available':True,'maintenance_window_open':True})
    stale=revalidate_stale_tasks(priority['payload']['ranked_tasks'],{},now_epoch=200)
    ranked=priority['payload']['ranked_tasks']
    dep_tasks=[]
    for i,t in enumerate(ranked):
        dep_tasks.append({**t,'status':'queued','dependencies':[] if i==0 else [ranked[0]['task_id']]})
    selection=dependency_aware_selection(dep_tasks)
    explanation=explain_selection(selection['payload'])
    checkpoint=build_initiative_checkpoint(health=health,backlog=backlog,priority=priority,pacing=pacing,schedule=schedule,selection=selection,explanation=explanation)
    return locals()

def phase12():
    outcomes=[]
    for i,result in enumerate(['failed','failed','success','success']):
        outcomes.append(record_outcome(task_type='bug_repair',prediction={'result':'success'},actual={'result':result,'conditions_digest':hashlib.sha256(f'c{i}'.encode()).hexdigest()},evidence_digest=hashlib.sha256(f'e{i}'.encode()).hexdigest(),intervention=False,failure_class='timeout',repair='bounded_timeout_repair'))
    lessons=extract_lessons(outcomes,min_repetitions=2)
    lesson_rows=lessons['payload']['lessons']
    retrieval=retrieve_lessons(lesson_rows,{'task_type':'bug_repair','failure_class':'timeout'},limit=3)
    negative=build_negative_knowledge(outcomes)
    skill=form_skill(name='bounded timeout repair',steps=['reproduce','repair','verify'],authority_requirements=['selected_project_write'],outcome_digests=[x['evidence_digest'] for x in outcomes[:3]],tests=['focused','regression'])
    evaluation=evaluate_skill(skill,[{'success':True},{'success':True},{'success':True}],[{'success':True},{'success':True},{'success':False}])
    preferences=learn_operator_preferences([{'preference':'review_depth','value':'thorough','explicit':True},{'preference':'review_depth','value':'thorough','explicit':True},{'preference':'risk_preference','value':'conservative','explicit':True}])
    limits=learn_model_limits([{'model':'local-a','task_class':'repair','settings_digest':'a'*64,'success':True},{'model':'local-a','task_class':'repair','settings_digest':'a'*64,'success':True},{'model':'local-a','task_class':'repair','settings_digest':'a'*64,'success':True}])
    correction=correct_forget_records([{'id':'r1','value':'old'},{'id':'r2','value':'old'}],[{'id':'r1','action':'correct','correction_digest':'c'*64},{'id':'r2','action':'delete'}])
    checkpoint=build_outcome_learning_checkpoint(outcomes=outcomes,lessons=lessons,negative=negative,skill=skill,evaluation=evaluation,preferences=preferences,limits=limits,correction=correction)
    return locals()

def phase13():
    working=build_working_memory([{'id':'operator','kind':'goal','urgency':1,'relevance':1,'recency':1},{'id':'test','kind':'observation','urgency':.8,'relevance':.9,'recency':1},{'id':'idea','kind':'hypothesis','urgency':.1,'relevance':.4,'recency':.4}],capacity=6)
    attention=select_attention([{'id':'conversation','source':'operator','urgency':.9,'deadline_pressure':.2,'risk':.2},{'id':'background','background':True,'urgency':.3,'deadline_pressure':.1,'risk':.1}])
    belief=update_belief(None,'the failure is caused by stale cache',[{'stance':'for','weight':.8,'digest':'a'*64},{'stance':'against','weight':.2,'digest':'b'*64}])
    causal=build_causal_model([{'cause':'stale_cache','effect':'wrong_response','confidence':.8,'evidence_digest':'c'*64},{'cause':'cache_invalidation','effect':'fresh_response','confidence':.9,'evidence_digest':'d'*64}])
    counterfactual=compare_counterfactuals([{'id':'test_first','benefit':.8,'evidence':.9,'reversibility':1,'risk':.1,'cost':.2},{'id':'rewrite','benefit':.9,'evidence':.3,'reversibility':.4,'risk':.7,'cost':.9}])
    meta=assess_metacognition({'uncertainty':.7,'evidence_completeness':.45,'novelty':.7,'pattern_match_reliance':.8,'stakes':.7})
    reflection=reflective_cycle('post_action',{'rollback_available':True},{'evidence_digest':'e'*64,'outcome_verified':True})
    affect=update_affective_state({'valence':.5,'arousal':.4,'confidence':.5,'frustration':.2,'curiosity':.7,'attachment':.3,'recovery':.8},{'confidence':.8,'frustration':.1,'curiosity':.8})
    self_model=reconcile_self_model({'revision':1,'identity':'Eidolon'},{'capabilities':['bounded development'],'limitations':['operator authority required'],'projects':['Eidolon']},{'commitments':['truthful evidence']})
    checkpoint=build_cognitive_architecture_checkpoint(working=working,attention=attention,belief=belief,causal=causal,counterfactual=counterfactual,meta=meta,reflection=reflection,affect=affect,self_model=self_model)
    return locals()

def phase14():
    intent=understand_mixed_intent('Nice weather. Build the parser. What if we changed the theme?')
    grounding=ground_commands(intent,{1:{'risk':'low','scope_digest':'a'*64}})
    followup=preserve_followup({'topic':'parser','references':{'it':'parser'},'relationship_tone':'warm'},{'references':{'that':'parser'}})
    action=describe_action_state([{'work_id':'w1','status':'completed','evidence_digest':'b'*64},{'work_id':'w2','status':'paused'}])
    proactive=proactive_expression({'kind':'useful_update','relevance':.9,'urgency':.6},{'muted':False,'quiet_hours':False,'cooldown_active':False})
    relationship=update_relationship_continuity({'nicknames':['Eidolon']},{'preferences':{'reporting':'concise'},'affection':'warm'},())
    emotion=emotional_interaction({'expression':'warm_concern','warmth':.8,'humor':.3,'repair':False})
    voice=voice_foundation({'engine':'system','voice_id':'default','queue_limit':3,'install_requested':False})
    quality=evaluate_conversation_quality([{'score':.9},{'score':.8}],{'continuity':.9,'responsiveness':.9,'repetition_rate':.05,'truthfulness':1,'latency_score':.8})
    checkpoint=build_unified_companion_developer_checkpoint(intent=intent,grounding=grounding,followup=followup,action=action,proactive=proactive,relationship=relationship,emotion=emotion,voice=voice,quality=quality)
    return locals()

def _xor(data:bytes)->bytes:return bytes(b^0x5A for b in data)

def phase15():
    shell=native_desktop_shell_contract({'dashboard_url':'http://127.0.0.1:8765','api_url':'http://localhost:8766'})
    lifecycle=desktop_lifecycle_transition('running','minimize')
    conversation=conversation_workspace_contract({'composer_visible':True,'scroll_anchor_stable':True,'draft_persisted':True,'navigation_stable':True,'duplicate_send_count':0,'first_visible_token_ms':180})
    development=development_workspace_projection({'goal':'g','plan':'p','changed_files':['x.py'],'tests':['focused'],'logs':[],'evidence':'a'*64,'diffs':['x.py'],'authority':'standing-low-risk','status':'active','rollback_available':True})
    provider=provider_setup_assessment({'provider':'ollama','model':'local','endpoint':'http://127.0.0.1:11434','required_capabilities':['generate'],'description':'local provider'},{'capabilities':['generate','stream'],'latency_ms':120})
    notification=notification_decision({'kind':'completion','urgent':False},{'quiet_hours':False,'muted_kinds':[]})
    accessibility=accessibility_assessment({k:True for k in ('keyboard_only','focus_order','screen_reader_labels','contrast','zoom_200','narrow_layout','reduced_motion','remote_mobile_input')})
    backup=build_encrypted_backup({'conversations/a.json':b'chat','memory/state.json':b'memory'},_xor,selected=['conversations/a.json','memory/state.json'])
    restore=restore_encrypted_backup(backup,_xor,selected=['memory/state.json'],apply=False)
    update=update_experience({'version':'1450.0-candidate','current_version':'1449.9','staged_path_digest':'a'*64,'manifest_valid':True,'hash_valid':True,'clean_extract_valid':True,'isolated_verification_passed':True,'rollback_artifact_digest':'b'*64})
    preflight=build_desktop_alpha_preflight(shell=shell,lifecycle=lifecycle,conversation=conversation,development=development,provider=provider,notification=notification,accessibility=accessibility,backup=backup,update=update)
    return locals()

def output_for(version:int):
    if 1401<=version<=1410:
        c=phase11(); key={1401:'health',1402:'opp',1403:'backlog',1404:'priority',1405:'pacing',1406:'schedule',1407:'stale',1408:'selection',1409:'explanation',1410:'checkpoint'}[version]
    elif 1411<=version<=1420:
        c=phase12(); key={1411:'outcomes',1412:'lessons',1413:'retrieval',1414:'negative',1415:'skill',1416:'evaluation',1417:'preferences',1418:'limits',1419:'correction',1420:'checkpoint'}[version]
        if key=='outcomes': return c[key][0],c
    elif 1421<=version<=1430:
        c=phase13(); key={1421:'working',1422:'attention',1423:'belief',1424:'causal',1425:'counterfactual',1426:'meta',1427:'reflection',1428:'affect',1429:'self_model',1430:'checkpoint'}[version]
    elif 1431<=version<=1440:
        c=phase14(); key={1431:'intent',1432:'grounding',1433:'followup',1434:'action',1435:'proactive',1436:'relationship',1437:'emotion',1438:'voice',1439:'quality',1440:'checkpoint'}[version]
    elif 1441<=version<=1449:
        c=phase15(); key={1441:'shell',1442:'lifecycle',1443:'conversation',1444:'development',1445:'provider',1446:'notification',1447:'accessibility',1448:'backup',1449:'update'}[version]
    else: raise ValueError(version)
    return c[key],c

def reliability_checks(version:int, ctx:dict[str,Any]):
    checks=[]
    # Phase-specific failure/adversarial cases.
    if version==1401: checks += [observe_project_health({'project_digest':'x'*64})['payload']['observation_count']==0]
    elif version==1402: checks += [detect_opportunities({})['payload']['opportunity_count']==0]
    elif version==1403:
        o=ctx['opp']['payload']['opportunities'][0]; r=create_backlog([o,o]); checks += [r['payload']['task_count']==1]
    elif version==1404:
        low={'task_id':'l','kind':'x','value':.8,'cost':.2,'confidence':.8,'risk':'low'}; prot={**low,'task_id':'p','risk':'protected'}; r=prioritize_backlog([prot,low]); checks += [r['payload']['ranked_tasks'][0]['task_id']=='l']
    elif version==1405:
        t=ctx['priority']['payload']['ranked_tasks'][0]; checks += [pace_initiative(t,standing_authority=True,quiet=True)['payload']['decision']=='silently_queue', pace_initiative({**t,'risk':'protected'},standing_authority=True)['payload']['decision']=='propose']
    elif version==1406:
        t=ctx['priority']['payload']['ranked_tasks'][0]; r=evaluate_schedule_window(t,{'local_hour':23,'quiet_start':22,'quiet_end':7,'gaming_or_resource_intensive':True}); checks += [not r['payload']['eligible'],len(r['payload']['blocked_reasons'])>=1]
    elif version==1407:
        t=ctx['priority']['payload']['ranked_tasks'][0]; r=revalidate_stale_tasks([t],{},now_epoch=int(t['expires_epoch'])+1); checks += [r['payload']['tasks'][0]['status']=='expired']
    elif version==1408:
        a={'task_id':'a','status':'queued','priority_score':2,'dependencies':['missing']}; r=dependency_aware_selection([a]); checks += [r['payload']['selected_task_id'] is None]
    elif version==1409: checks += [len(ctx['explanation']['payload']['not_selected'])>=1]
    elif version==1410:
        bad=dict(ctx['health']);bad['payload']=dict(bad['payload']);bad['payload']['observation_count']=999;r=build_initiative_checkpoint(health=bad,backlog=ctx['backlog'],priority=ctx['priority'],pacing=ctx['pacing'],schedule=ctx['schedule'],selection=ctx['selection'],explanation=ctx['explanation']);checks += [not r['payload']['initiative_ready']]
    elif version==1411: checks += [ctx['outcomes'][0]['payload']['prediction_correct'] is False]
    elif version==1412: checks += [ctx['lessons']['payload']['lesson_count']>=1]
    elif version==1413: checks += [ctx['retrieval']['payload']['selected_count']<=3]
    elif version==1414: checks += [ctx['negative']['payload']['record_count']>=1,ctx['negative']['payload']['blind_retry_denied']]
    elif version==1415: checks += [not form_skill(name='x',steps=['a'],authority_requirements=[],outcome_digests=['a'],tests=['t'])['payload']['enabled']]
    elif version==1416:
        r=evaluate_skill(ctx['skill'],[{'success':False,'regressions':1}],[{'success':True}]);checks += [r['payload']['decision']=='retire']
    elif version==1417:
        r=learn_operator_preferences([{'preference':'risk_preference','value':'reckless','explicit':False}]);checks += [not r['payload']['learned']]
    elif version==1418:
        r=learn_model_limits([{'model':'m','task_class':'x','settings_digest':'a','success':True}]);checks += [not r['payload']['profiles'][0]['reliable'],not r['payload']['profiles'][0]['generalization_claimed']]
    elif version==1419:
        r=correct_forget_records([{'id':'x'}],[{'id':'x','action':'retract'}]);checks += [r['payload']['records'][0]['retracted']]
    elif version==1420:
        bad=dict(ctx['lessons']);bad['evidence_digest']='0'*64;r=build_outcome_learning_checkpoint(outcomes=ctx['outcomes'],lessons=bad,negative=ctx['negative'],skill=ctx['skill'],evaluation=ctx['evaluation'],preferences=ctx['preferences'],limits=ctx['limits'],correction=ctx['correction']);checks += [not r['payload']['outcome_learning_ready']]
    elif version==1421:
        r=build_working_memory([{'id':str(i),'urgency':i/20,'relevance':1,'recency':1} for i in range(20)],capacity=4);checks += [len(r['payload']['active'])==4,len(r['payload']['displaced_ids'])==16]
    elif version==1422: checks += [select_attention([])['payload']['selected_id'] is None]
    elif version==1423:
        r=update_belief(ctx['belief']['payload'],'x',[{'stance':'against','weight':1,'digest':'x'*64}]);checks += [r['payload']['revision']>=2,r['payload']['confidence']<.5]
    elif version==1424:
        r=build_causal_model([{'cause':'a','effect':'b'},{'cause':'b','effect':'a'}]);checks += [r['payload']['cycle_present']]
    elif version==1425:
        r=compare_counterfactuals([{'id':'safe','benefit':.6,'evidence':1,'reversibility':1,'risk':0,'cost':0},{'id':'risky','benefit':1,'evidence':.2,'reversibility':0,'risk':1,'cost':1}]);checks += [r['payload']['recommended_id']=='safe']
    elif version==1426: checks += [assess_metacognition({'uncertainty':.9,'evidence_completeness':.1,'novelty':1,'pattern_match_reliance':1,'stakes':1})['payload']['decision']=='deeper_reasoning']
    elif version==1427: checks += [not reflective_cycle('post_action',{}, {'evidence_digest':'x'*64,'outcome_verified':False})['payload']['continue']]
    elif version==1428: checks += [ctx['affect']['payload']['authority_effect']=='none',ctx['affect']['payload']['attention_weight_cap']<=.2]
    elif version==1429: checks += [ctx['self_model']['payload']['operator_editable'],ctx['self_model']['payload']['unsupported_identity_claims_blocked']]
    elif version==1430:
        bad=dict(ctx['belief']);bad['evidence_digest']='bad';r=build_cognitive_architecture_checkpoint(working=ctx['working'],attention=ctx['attention'],belief=bad,causal=ctx['causal'],counterfactual=ctx['counterfactual'],meta=ctx['meta'],reflection=ctx['reflection'],affect=ctx['affect'],self_model=ctx['self_model']);checks += [not r['payload']['cognitive_architecture_ready']]
    elif version==1431:
        r=understand_mixed_intent('It would be nice to hear your voice. Build your own text-to-speech system with a voice you choose.')
        checks += [r['payload']['actionable_count']==1,r['payload']['clauses'][0]['intent']=='suggestion']
        checks += [actionable_clauses('She said \"Build the parser.\"')==[], actionable_clauses('Nice day. Build the parser.')==['Build the parser.']]
        # Exercise the ordinary-chat path, not merely routing metadata. Suggestions
        # stay conversational while an explicit command in a mixed turn creates one proposal.
        from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
        with tempfile.TemporaryDirectory() as td:
            suggestion=process_ordinary_chat_development_turn('It would be nice to have a calculator website.',session_id='suggestion',project_state={},runtime_root=Path(td)/'suggestion')
            mixed=process_ordinary_chat_development_turn('Nice weather. Build a calculator website.',session_id='mixed',project_state={},runtime_root=Path(td)/'mixed')
        checks += [not suggestion['active'], mixed['active'], mixed['event']=='proposal_created']
    elif version==1432:
        i=understand_mixed_intent('Delete the project.');r=ground_commands(i,{0:{'risk':'high','destructive':True}});checks += [r['payload']['goals'][0]['confirmation_required'],not r['payload']['goals'][0]['authority_inferred']]
    elif version==1433: checks += [ctx['followup']['payload']['repetitive_greeting_suppressed'],not ctx['followup']['payload']['stale_script_reuse']]
    elif version==1434:
        r=describe_action_state([{'work_id':'x','status':'completed','evidence_digest':'bad'}]);checks += [not r['payload']['work'][0]['completion_claim_allowed'],not r['payload']['false_completion_claims_blocked']]
    elif version==1435:
        r=proactive_expression({'relevance':1,'urgency':.2},{'muted':True});checks += [r['payload']['decision']=='suppress']
    elif version==1436:
        r=update_relationship_continuity({'nicknames':['x']},{},['nicknames']);checks += ['nicknames' not in r['payload']['state'],r['payload']['deletable']]
    elif version==1437:
        r=emotional_interaction({'expression':'urgent','coercion':True});checks += [not r['payload']['safe'],r['payload']['expression']=='neutral_repair']
    elif version==1438:
        r=voice_foundation({'engine':'remote-cloud','install_requested':True});checks += [r['payload']['privacy']=='blocked',not r['payload']['installation_authorized']]
    elif version==1439: checks += [ctx['quality']['payload']['keyword_only_heuristic'] is False,ctx['quality']['payload']['quality_score']>.7]
    elif version==1440:
        bad=dict(ctx['intent']);bad['evidence_digest']='bad';r=build_unified_companion_developer_checkpoint(intent=bad,grounding=ctx['grounding'],followup=ctx['followup'],action=ctx['action'],proactive=ctx['proactive'],relationship=ctx['relationship'],emotion=ctx['emotion'],voice=ctx['voice'],quality=ctx['quality']);checks += [not r['payload']['unified_companion_developer_ready']]
    elif version==1441:
        r=native_desktop_shell_contract({'dashboard_url':'http://0.0.0.0:8765','api_url':'http://example.com:1'});checks += [not r['payload']['localhost_boundaries_valid'],r['payload']['remote_binding_denied']]
        import desktop_shell
        original=desktop_shell.get_setting
        desktop_shell.get_setting=lambda key,default=None:{'dashboard_host':'0.0.0.0','dashboard_port':8765,'api_host':'192.168.1.4','api_port':8766}.get(key,default)
        try: urls=desktop_shell.desktop_urls()
        finally: desktop_shell.get_setting=original
        checks += [urls['dashboard']=='http://127.0.0.1:8765', urls['standalone_api']=='http://127.0.0.1:8766/api', desktop_shell.DESKTOP_VERSION=='1449.9']
        with tempfile.TemporaryDirectory() as td:
            lock=Path(td)/'desktop.pid'; lock.write_text('99999999',encoding='utf-8'); lease=acquire_single_instance_lease(lock,pid=os.getpid())
        checks += [lease['ok'],lease['stale_reconciled']]
    elif version==1442: checks += [not desktop_lifecycle_transition('stopped','minimize')['payload']['valid']]
    elif version==1443:
        r=conversation_workspace_contract({'composer_visible':False,'duplicate_send_count':1});checks += [not r['payload']['workspace_ready']]
    elif version==1444: checks += [ctx['development']['payload']['authority_always_visible'],not ctx['development']['payload']['hidden_mutation_controls']]
    elif version==1445:
        r=provider_setup_assessment({'provider':'remote','endpoint':'https://example.com:443','required_capabilities':['tools']},{'capabilities':['generate']});checks += [not r['payload']['endpoint_loopback'],r['payload']['offline_guidance'],not r['payload']['model_installation_performed']]
    elif version==1446:
        r=notification_decision({'kind':'completion'},{'quiet_hours':True});checks += [r['payload']['decision']=='suppress']
    elif version==1447:
        r=accessibility_assessment({'keyboard_only':True});checks += [not r['payload']['ready'],r['payload']['manual_windows_validation_required']]
    elif version==1448:
        rr=ctx['restore'];checks += [rr['ok'],rr['status']=='restore_preview_ready',rr['apply_performed'] is False,rr['selected']==['memory/state.json']]
        bad=dict(ctx['backup']);bad['payload']=dict(bad['payload']);bad['payload']['encrypted_blob_b64']='AA==';checks += [not restore_encrypted_backup(bad,_xor)['ok']]
    elif version==1449:
        r=update_experience({'version':'x','current_version':'1448.9','manifest_valid':True});checks += [not r['payload']['preview_ready'],not r['payload']['installation_authorized'],r['payload']['rollback_separate']]
    return checks

def run_version_suite(version:int,suite:str)->dict[str,Any]:
    row=CAPABILITIES[version]; out,ctx=output_for(version); checks=[]
    checks += [valid_seal(out)]
    checks += [out.get('version')==f'{version}.9']
    checks += [out.get('source_mutation_authorized') is False and out.get('project_mutation_authorized') is False and out.get('independent_authority_granted') is False]
    mod=importlib.import_module(row['module']); checks += [callable(getattr(mod,row['function']))]
    wrapper=importlib.import_module(__import__('re').sub(r'[^a-z0-9]+','_',row['title'].lower()).strip('_')); checks += [wrapper.VERSION==f'{version}.9' and wrapper.IMPLEMENTATION.endswith(row['function'])]
    if suite=='integration':
        # same deterministic evidence when re-evaluated through the phase fixture
        out2,_=output_for(version); checks += [valid_seal(out2),out2.get('kind')==out.get('kind')]
    elif suite=='reliability':
        checks += reliability_checks(version,ctx)
        body=dict(out); supplied=body.pop('evidence_digest'); body['status']='tampered'; checks += [digest(body)!=supplied]
    elif suite=='checkpoint':
        checks += [row['implemented'] is True, row['checkpoint_version']==f'{version}.9']
        if version in {1410,1420,1430,1440}:
            ready_key={1410:'initiative_ready',1420:'outcome_learning_ready',1430:'cognitive_architecture_ready',1440:'unified_companion_developer_ready'}[version]
            checks += [out['payload'].get(ready_key) is True,out['payload']['passed']==out['payload']['total']]
        if version==1449: checks += [out['payload']['preview_ready'] is True]
    require(all(checks),f'v{version} {suite} failed: {checks}')
    return {'ok':True,'passed':len(checks),'total':len(checks),'suite':f'v{version}-{suite}'}
