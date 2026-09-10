from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from development_memory_relevance import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
p=[{'item_code':'parser_decision','item_type':'design_decision','relevance_tags':['parser','repair'],'project_code':'project_eidolon','confidence':'verified','classification':'still_valid'},{'item_code':'old_risk','item_type':'limitation_risk','relevance_tags':['parser'],'project_code':'project_eidolon','confidence':'high','classification':'contradicted'}];less=[{'lesson_code':'bounded_retry','relevance_tags':['parser','repair'],'project_code':'project_eidolon','confidence_score':80,'verified':True}];r=build_development_memory_projection(task_code='repair_parser',task_tags=['parser','repair'],project_items=p,lessons=less,project_code='project_eidolon');req(r['ok'],'projection');req(r['project_understanding_bridge_count']==2 and r['lesson_bridge_count']==1,'bridges');codes={x['memory_code'] for x in r['selected']};req('project_parser_decision' in codes,'decision_selected');req('project_old_risk' not in codes,'contradiction_suppressed');req('lesson_bounded_retry' in codes,'lesson_selected');req(r['memory_sources_are_evidence_only'],'evidence_only');req(not r['memory_retrieval_is_execution_authority'],'no_execution');print(json.dumps({'ok':True,'suite':'v1283.3-5-development-memory-relevance-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
