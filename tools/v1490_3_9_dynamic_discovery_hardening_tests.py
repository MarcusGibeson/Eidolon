from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1490-hardening-')
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'conscious_agent'))
from conscious_agent.dynamic_improvement_eligibility import harden_dynamic_discovery

p=f=0
def check(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)

def candidate(cid,symbols,dest='conscious_agent/new_helpers.py',**kw):
 row={'candidate_id':cid,'evidence_digest':'e'+cid,'source_module':'conscious_agent/sample.py','source_symbols':symbols,'proposed_destination_module':dest,'estimated_dependency_count':4,'test_reference_file_count':3,'reversibility_classification':'high_reversible','eligible_for_later_planning':True,'rejection_codes':[]}
 row.update(kw);return row

try:
 base={'discovery_digest':'d1','candidates':[candidate('a',['alpha','beta']),candidate('b',['gamma','delta'],'conscious_agent/other_helpers.py')]}
 one=harden_dynamic_discovery(base);two=harden_dynamic_discovery(base)
 check('eligible evidence remains eligible for comparison',one['eligible_count']==2,one)
 check('hardening is restart deterministic',one['hardening_digest']==two['hardening_digest'],(one,two))
 check('hardening never ranks or selects',not one['ranking_performed'] and not one['selection_made'],one)
 check('hardening grants no proposal workspace provider or source authority',not any(one[k] for k in ('proposal_created','workspace_prepared','provider_contacted','source_modified','authority_granted')),one)
 overlap={'discovery_digest':'d2','candidates':[candidate('a',['alpha','beta']),candidate('b',['beta','gamma'],'conscious_agent/x.py')]}
 o=harden_dynamic_discovery(overlap)
 check('partial overlaps remain comparison-eligible but explicitly flagged',o['eligible_count']==2 and all(r['overlap_requires_quality_resolution'] for r in o['eligible_candidates']),o)
 dup={'discovery_digest':'d3','candidates':[candidate('a',['alpha']),candidate('b',['beta'])]}
 d=harden_dynamic_discovery(dup)
 check('duplicate destination is canonicalized to one candidate',d['eligible_count']==1 and d['rejected_count']==1 and 'duplicate_destination_in_discovery' in d['rejected_candidates'][0]['rejection_codes'],d)
 protected={'discovery_digest':'d4','candidates':[candidate('a',['source_apply'],protected_authority_boundary=True)]}
 q=harden_dynamic_discovery(protected)
 check('protected authority candidate remains ineligible',q['eligible_count']==0 and 'protected_authority_boundary' in q['rejected_candidates'][0]['rejection_codes'],q)
 weak={'discovery_digest':'d5','candidates':[candidate('a',['alpha'],test_reference_file_count=0,estimated_dependency_count=40,reversibility_classification='low')]}
 w=harden_dynamic_discovery(weak)
 check('weak ambiguous candidate fails closed',w['eligible_count']==0 and w['rejected_candidates'][0]['uncertainty']=='high',w)
 lineage=harden_dynamic_discovery({'discovery_digest':'d6','candidates':[candidate('a',['alpha'])]},completed_lineages=[{'destination_module':'conscious_agent/new_helpers.py'}])
 check('completed lineage duplicate is excluded',lineage['eligible_count']==0 and 'completed_lineage_duplicate' in lineage['rejected_candidates'][0]['rejection_codes'],lineage)
 check('eligibility evidence is content free',all(r['content_free'] and 'source_text' not in r for r in one['decisions']),one)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1490.3-v1490.9-dynamic-discovery-hardening','content_free':True})
finally:
 import shutil;shutil.rmtree(os.environ['EIDOLON_DATA_DIR'],ignore_errors=True)
if f: raise SystemExit(1)
