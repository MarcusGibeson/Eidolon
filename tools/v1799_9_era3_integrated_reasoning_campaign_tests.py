from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from era3_reasoning_integration import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n): checks.append(n); assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v1799-9-integration-') as td:
 rt=Path(td)/'runtime'
 case=build_integrated_reasoning_case(
   'Investigate why the service fails after restart. Preserve source. Verify the diagnosis with evidence before changing anything.',
   project_evidence={'workspace_digest':'f'*64},
   hypotheses=[
     {'id':'stale_state','prior_confidence':.5,'predictions':{'clean_restart':'works','provider_probe':'works'}},
     {'id':'provider_failure','prior_confidence':.5,'predictions':{'clean_restart':'fails','provider_probe':'fails'}},
   ],
   milestones=[
     {'milestone_code':'diagnose','tasks':[{'task_code':'inspect'},{'task_code':'discriminate','depends_on':['inspect']}]},
     {'milestone_code':'review','depends_on':['diagnose'],'tasks':[{'task_code':'handoff'}]},
   ],
   claims=[{'claim_code':'provider_is_cause','source_kind':'assumption','asserted_confidence':.9,'evidence_count':0}],
   plan_steps_for_meta=[{'step_code':'inspect','depends_on':[]}],runtime_root=rt)
 req(case['ok'] and case['status']=='era3_integrated_reasoning_ready','integrated_ready')
 req(case['problem_framing']['problem_frame_id'],'frame_link')
 req(case['causal_reasoning']['hypothesis_count']==2,'causal_link')
 req(case['long_horizon_plan']['milestone_count']==2,'plan_link')
 req(case['metacognition']['epistemic_session_id'],'meta_link')
 req(case['next_reasoning_move'] in {'self_correct_before_commitment','gather_discriminating_evidence','review_bounded_plan'},'next_move')
 req(not case['private_chain_of_thought_exposed'] and not case['action_executed'],'no_hidden_or_action')
 req(not case['execution_authorized'] and not case['provider_contact_authorized'],'authority_contained')
 # Ordinary-chat routing exposes all four read-only requirements surfaces.
 for text,status in [
   ('show causal reasoning requirements','causal_reasoning_requirements'),
   ('show long horizon planning requirements','long_horizon_planning_requirements'),
   ('show metacognitive requirements','metacognitive_requirements')]:
    out=process_ordinary_chat_development_turn(text,runtime_root=rt)
    req(out.get('active') and out.get('status')==status,'route_'+status)
print(json.dumps({'suite':'v1799.9-era3-integrated-reasoning-campaign','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
