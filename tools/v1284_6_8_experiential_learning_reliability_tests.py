from __future__ import annotations
import json,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from experiential_learning_foundations import *
from experiential_learning_reliability import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
h=inspect_experiential_learning_health(source_root=ROOT);req(h['ok'] and all(h['checks'].values()),'health');hand=build_experiential_learning_handoff(source_root=ROOT);req(hand['ok'] and hand['next_bounded_unit']=='v1285 Hierarchical Goal Management','handoff');req(hand['v1285_started'] is False,'unstarted');l=build_experiential_lesson(lesson_code='x',outcome_code='x',guidance_code='x',applicability_tags=['a'],evidence_codes=['e'],verified_outcome=True,confidence=80);a=revise_experiential_lesson(l,evidence_kind='observed_contradiction',evidence_code='c');cmp=compare_lessons(l,a);req(cmp['ok'] and cmp['state_changed'] and cmp['confidence_delta']<0,'revision');req(not cmp['authority_changed'] and not cmp['raw_content_exposed'],'contained');code=f"import sys;sys.path[:0]=[{str(ROOT/'conscious_agent')!r},{str(ROOT)!r}];import experiential_learning_foundations,experiential_learning,experiential_learning_reliability;print('ok')";p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_import');print(json.dumps({'ok':True,'suite':'v1284.6-8-experiential-learning-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
