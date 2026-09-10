from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from epistemic_self_correction import *
checks=[]
def req(v,n): checks.append(n); assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v1799-9-') as td:
 rt=Path(td)/'runtime'
 req(classify_epistemic_state({'source_kind':'measurement','evidence_count':1})=='measured','measured_class')
 req(classify_epistemic_state({'source_kind':'memory'})=='remembered','memory_class')
 req(classify_epistemic_state({'source_kind':'assumption'})=='assumed','assumption_class')
 req(classify_epistemic_state({})=='unknown','unknown_class')
 over=calibrate_claim({'claim_code':'x','source_kind':'assumption','asserted_confidence':.95,'evidence_count':0,'freshness':.5})
 req(over['unsupported_certainty'] and over['overconfidence_gap']>=.2,'overconfidence_detected')
 measured=calibrate_claim({'claim_code':'m','source_kind':'measurement','asserted_confidence':.85,'evidence_count':3,'evidence_quality':.9,'independence':.9,'freshness':.9})
 req(measured['calibrated_confidence']>over['calibrated_confidence'],'evidence_calibration')
 score=score_calibration([{'confidence':.9,'outcome':True},{'confidence':.8,'outcome':True},{'confidence':.2,'outcome':False}])
 req(score['ok'] and score['brier_score']<.1,'calibration_score')
 health=assess_reasoning_health(
   claims=[{'claim_code':'certain_guess','source_kind':'assumption','asserted_confidence':.99}],
   plan_steps=[{'step_code':'a','depends_on':['b']},{'step_code':'b','depends_on':['a']}],
   tactic_history=[{'tactic_code':'retry_same','outcome':'failed'},{'tactic_code':'retry_same','outcome':'failed'}],
   context_freshness=.1,response_signatures=['same','same','same','same'],uncertainty=.85)
 req(health['circular_plan_detected'],'circular')
 req(health['repeated_failed_tactic_codes']==['retry_same'],'repeated_failure')
 req(health['stale_context_detected'],'stale')
 req(health['answer_pattern_collapse_detected'],'collapse')
 req(health['unsupported_certainty_count']==1,'certainty_issue')
 req(health['recommended_epistemic_action']=='change_strategy','change_strategy')
 req(not health['private_chain_of_thought_exposed'] and not health['action_executed'],'no_hidden_reasoning')
 session=create_epistemic_session('debug_case',claims=[{'claim_code':'guess','source_kind':'assumption','asserted_confidence':.9}],plan_steps=[],runtime_root=rt)
 req(session['ok'] and session['epistemic_session_id'],'session_ready')
 sid=session['epistemic_session_id'];d=session['epistemic_session_digest']
 one=record_reasoning_outcome(sid,d,tactic_code='retry',outcome='failed',evidence_digest='1'*64,response_signature='same',runtime_root=rt)
 two=record_reasoning_outcome(sid,one['epistemic_session_digest'],tactic_code='retry',outcome='failed',evidence_digest='2'*64,response_signature='same',runtime_root=rt)
 three=record_reasoning_outcome(sid,two['epistemic_session_digest'],tactic_code='alternate',outcome='no_progress',evidence_digest='3'*64,response_signature='same',runtime_root=rt)
 four=record_reasoning_outcome(sid,three['epistemic_session_digest'],tactic_code='alternate2',outcome='no_progress',evidence_digest='4'*64,response_signature='same',runtime_root=rt)
 req('retry' in four['repeated_failed_tactic_codes'],'session_repeat_detected')
 req(four['answer_pattern_collapse_detected'],'session_collapse')
 stale=record_reasoning_outcome(sid,d,tactic_code='bad',outcome='failed',evidence_digest='5'*64,runtime_root=rt)
 req(not stale['ok'] and stale['status']=='stale_epistemic_session_digest','stale_digest_rejected')
 replay=record_reasoning_outcome(sid,four['epistemic_session_digest'],tactic_code='alternate2',outcome='no_progress',evidence_digest='4'*64,response_signature='same',runtime_root=rt)
 req(replay['status']=='reasoning_outcome_replay','replay')
 legacy=legacy_metacognition_projection(sid,runtime_root=rt)
 req(legacy.get('kind')=='metacognition' and legacy.get('payload',{}).get('hidden_chain_of_thought_exposed') is False,'legacy_meta')
 ctl=process_epistemic_self_correction_control('show metacognitive requirements',runtime_root=rt)
 req(ctl['active'] and ctl['ok'] and 'failed_tactic_nonrepetition' in ctl['requirements'],'requirements_control')
 show=process_epistemic_self_correction_control(f'show epistemic session {sid}',runtime_root=rt)
 req(show['active'] and show['ok'],'show_control')
 compound=process_epistemic_self_correction_control(f'show epistemic session {sid} and execute',runtime_root=rt)
 req(compound['active'] and not compound['ok'],'compound_rejected')
print(json.dumps({'suite':'v1799.9-metacognition-epistemic-control-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
