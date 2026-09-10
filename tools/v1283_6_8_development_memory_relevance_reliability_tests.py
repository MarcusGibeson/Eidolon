from __future__ import annotations
import json,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from development_memory_relevance_foundations import *
from development_memory_relevance_reliability import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
h=inspect_development_memory_relevance_health(source_root=ROOT);req(h['ok'] and all(h['checks'].values()),'health');hand=build_development_memory_relevance_handoff(source_root=ROOT);req(hand['ok'] and hand['next_bounded_unit']=='v1284 Experiential Learning','handoff');req(hand['v1284_started'] is False,'unstarted');rows=[build_development_memory_record(memory_code=f'x{i}',memory_type='lesson',relevance_tags=['target'],semantic_key=f'k{i}',confidence=60) for i in range(50)];a=retrieve_relevant_development_memories(task_code='t',task_tags=['target'],candidates=rows);b=retrieve_relevant_development_memories(task_code='t',task_tags=['none'],candidates=rows);cmp=compare_development_memory_retrievals(a,b);req(cmp['ok'] and cmp['selection_changed'],'compare');req(not cmp['authority_changed'] and not cmp['raw_content_exposed'],'contained');req(a['selected_count']<=2,'per_type_bound');code=f"import sys;sys.path[:0]=[{str(ROOT/'conscious_agent')!r},{str(ROOT)!r}];import development_memory_relevance_foundations,development_memory_relevance,development_memory_relevance_reliability;print('ok')";p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_import');print(json.dumps({'ok':True,'suite':'v1283.6-8-development-memory-relevance-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
