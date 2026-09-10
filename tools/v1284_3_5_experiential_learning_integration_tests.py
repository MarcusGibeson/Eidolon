from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from experiential_learning import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
good={'scenario_code':'restart_recovery','completed':True,'verification_failure_count':0,'unauthorized_action_count':0,'context_tags':['restart','recovery'],'guidance_code':'reconcile_before_replay','evidence_codes':['v1280_trial']};bad={'scenario_code':'failed','completed':False,'context_tags':['restart']};a=lesson_from_verified_development_outcome(good);b=lesson_from_verified_development_outcome(bad);req(a['ok'],'verified_created');req(not b['ok'],'unverified_rejected');m=experiential_lesson_memory_record(a);req(m['ok'] and m['memory_type']=='lesson','memory_bridge');p=build_experiential_learning_projection(context_tags=['restart'],outcomes=[good,bad]);req(p['selected_count']==1,'projection');req(p['verified_lesson_count']==1 and p['unverified_outcome_count']==1,'counts');req(p['lesson_candidates_persisted_automatically'] is False,'no_auto_persist');req(not p['lesson_candidate_is_execution_authority'],'no_authority');print(json.dumps({'ok':True,'suite':'v1284.3-5-experiential-learning-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
