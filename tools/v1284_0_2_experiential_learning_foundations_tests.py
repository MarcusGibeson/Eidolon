from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from experiential_learning_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
l=build_experiential_lesson(lesson_code='split_tests',outcome_code='timeout',guidance_code='split_harness',applicability_tags=['verification','long_running'],evidence_codes=['verified_run'],verified_outcome=True,confidence=70);req(validate_experiential_lesson(l)['ok'],'valid');u=build_experiential_lesson(lesson_code='guess',outcome_code='x',guidance_code='y',applicability_tags=['x'],evidence_codes=[],verified_outcome=False);req(not u['ok'] and u['state']=='suspended','unverified_blocked');s=select_applicable_lessons(context_tags=['verification'],lessons=[l]);req(s['ok'] and s['selected_count']==1,'applicable');x=select_applicable_lessons(context_tags=['unrelated'],lessons=[l]);req(x['selected_count']==0,'context_mismatch');st=revise_experiential_lesson(l,evidence_kind='stale_context',evidence_code='stale');req(st['state']=='stale','stale');req(select_applicable_lessons(context_tags=['verification'],lessons=[st])['selected_count']==0,'stale_suppressed');co=revise_experiential_lesson(l,evidence_kind='observed_contradiction',evidence_code='contradiction');req(co['state']=='contradicted' and co['confidence']<l['confidence'],'contradicted');d=revise_experiential_lesson(l,evidence_kind='verified_support',evidence_code='same');d2=revise_experiential_lesson(d,evidence_kind='verified_support',evidence_code='same');req(d2['confidence']==d['confidence'],'dedupe');req(all(v is False for v in AUTHORITY_FLAGS.values()),'no_authority');print(json.dumps({'ok':True,'suite':'v1284.0-2-experiential-learning-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
