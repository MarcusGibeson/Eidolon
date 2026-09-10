from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from development_memory_relevance_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
rows=[]
for typ in MEMORY_TYPES:rows.append(build_development_memory_record(memory_code=typ,memory_type=typ,relevance_tags=['parser','repair'],project_code='project_eidolon',semantic_key=typ,confidence=70,freshness='recent',verification_state='verified'))
req(all(validate_development_memory_record(x)['ok'] for x in rows),'records_valid');r=retrieve_relevant_development_memories(task_code='repair_parser',task_tags=['parser','repair'],candidates=rows,project_code='project_eidolon');req(r['ok'],'retrieval');req(r['selected_count']<=8,'bounded');req(set(x['memory_type'] for x in r['selected'])==set(MEMORY_TYPES),'all_types');req(not r['indiscriminate_memory_dump'] and not r['raw_memory_content_returned'],'privacy');weak=retrieve_relevant_development_memories(task_code='other',task_tags=['unrelated'],candidates=rows);req(weak['selected_count']==0,'weak_empty');stale=build_development_memory_record(memory_code='stale',memory_type='lesson',relevance_tags=['parser'],freshness='stale',confidence=90);rr=retrieve_relevant_development_memories(task_code='p',task_tags=['parser'],candidates=[stale]);req(rr['selected_count']==0,'stale_suppressed');bad=dict(rows[0]);bad['raw_content_stored']=True;rr=retrieve_relevant_development_memories(task_code='p',task_tags=['parser'],candidates=[bad]);req(not rr['ok'] and rr['invalid_candidate_count']==1,'tamper_rejected');dup=[build_development_memory_record(memory_code=f'd{i}',memory_type='decision',relevance_tags=['parser'],semantic_key='same',confidence=90) for i in range(3)];rr=retrieve_relevant_development_memories(task_code='p',task_tags=['parser'],candidates=dup);req(rr['selected_count']==1,'semantic_dedupe');req(all(v is False for k,v in AUTHORITY_FLAGS.items()),'no_authority');print(json.dumps({'ok':True,'suite':'v1283.0-2-development-memory-relevance-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
