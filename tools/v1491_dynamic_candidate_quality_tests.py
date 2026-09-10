from __future__ import annotations
import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1491-');os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.dynamic_candidate_quality import compare_dynamic_candidates
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 hard={'hardening_digest':'h','eligible_candidates':[
  {'candidate_id':'a','eligibility_digest':'ea','evidence_digest':'da','source_module':'m','proposed_destination_module':'x','source_symbols':['a','b'],'test_reference_file_count':4,'estimated_dependency_count':2,'reversibility_classification':'high_reversible','confidence':.9,'uncertainty':'low'},
  {'candidate_id':'b','eligibility_digest':'eb','evidence_digest':'db','source_module':'m','proposed_destination_module':'y','source_symbols':['c','d','e'],'test_reference_file_count':1,'estimated_dependency_count':20,'reversibility_classification':'medium','confidence':.65,'uncertainty':'medium'}]}
 r=compare_dynamic_candidates(hard);r2=compare_dynamic_candidates(hard)
 ck('quality comparison orders stronger evidence first',r['ordered_comparison'][0]['candidate_id']=='a',r)
 ck('quality comparison is deterministic',r['comparison_digest']==r2['comparison_digest'],(r,r2))
 ck('comparison ranks but does not select',r['ranking_performed'] and not r['selection_made'] and r['operator_selection_required'],r)
 ck('comparison grants no downstream authority',not any(r[k] for k in ('proposal_created','workspace_prepared','provider_contacted','source_modified','authority_granted')),r)
 tie={'hardening_digest':'h2','eligible_candidates':[dict(hard['eligible_candidates'][0],candidate_id='a'),dict(hard['eligible_candidates'][0],candidate_id='z',eligibility_digest='ez',evidence_digest='dz',proposed_destination_module='z')]}
 t=compare_dynamic_candidates(tie)
 ck('near-equal candidates expose tie rather than false precision',len(t['tie_groups'])==1 and not t['top_candidate_is_unique'],t)
 empty=compare_dynamic_candidates({'hardening_digest':'h3','eligible_candidates':[]})
 ck('no eligible candidates yields honest empty comparison',empty['candidate_count']==0 and not empty['ranking_performed'] and not empty['operator_selection_required'],empty)
 ck('public scoring evidence is content free',all(x['content_free'] and 'source_text' not in x for x in r['ordered_comparison']),r)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1491-dynamic-candidate-quality','content_free':True})
finally:
 import shutil;shutil.rmtree(os.environ['EIDOLON_DATA_DIR'],ignore_errors=True)
if f:raise SystemExit(1)
