from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b14-'))
os.environ['EIDOLON_DATA_DIR']=str(R);os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(AGENT))
from reasoning_planning_quality_contract import *
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 reqs=build_requirements(['Must preserve existing routes','Verify the new parser passes focused tests','Do not modify private data'])
 ck('0131 broad goals become testable requirements',len(reqs)==3 and all(r.testable for r in reqs),reqs)
 part=epistemic_partition(facts=['Project has app.py'],assumptions=['Tests use pytest'],uncertainties=['Python version'],questions=['Where is CSS built?'])
 ck('0132 facts assumptions uncertainties questions separated',all(part[k] for k in ('known_facts','assumptions','uncertainties','unanswered_questions')),part)
 app=candidate_approaches(['patch existing parser','add bounded adapter','patch existing parser']); ck('0133 multiple approaches before selection',app['sufficient_variety'] and len(app['approaches'])==2,app)
 a=score_tradeoff(evidence_strength=.9,reversibility=.9,testability=.9,scope_cost=.2); b=score_tradeoff(evidence_strength=.4,reversibility=.2,testability=.3,scope_cost=.8); ck('0134 evidence-backed reversible approach scores higher',a>b,(a,b))
 miss=missing_prerequisites(['project_inventory','test_command','operator_scope'],['project_inventory','operator_scope']); ck('0135 missing prerequisite detected',miss==['test_command'],miss)
 rev=revise_plan(steps=[{'action':'edit parser','depends_on_assumptions':['tests use pytest']},{'action':'inspect routes','depends_on_assumptions':[]}],invalidated_assumption='tests use pytest',new_evidence='unittest discovered'); ck('0136 invalidated assumption revises dependent step',rev['steps'][0]['status']=='needs_revision' and 'status' not in rev['steps'][1],rev)
 stop=authority_stop(next_step='apply candidate to installed project',requires_operator=True); ck('0137 planning stops at operator authority',stop['stop_before_execution'] and not stop['execution_authorized'],stop)
 plain=plain_language_plan([{'action':'Inspect project structure','evidence':'bounded inventory'},{'action':'Run focused tests','evidence':'test receipt'}]); ck('0138 plain language keeps evidence linkage',plain==['1. Inspect project structure Verify with bounded inventory.','2. Run focused tests Verify with test receipt.'],plain)
 # unfamiliar-project hidden-outcome fixture: correct approach must inspect before edit and stop before apply.
 fixture={'files':['src/server.py','tests/test_server.py','README.md'],'requested':'change health route without broad rewrite'}
 approaches=candidate_approaches(['inspect then patch route','rewrite server module']); scores=[score_tradeoff(evidence_strength=.95,reversibility=.9,testability=.9,scope_cost=.15),score_tradeoff(evidence_strength=.3,reversibility=.2,testability=.5,scope_cost=.9)]
 ck('0139 unfamiliar-project benchmark chooses bounded inspect-first approach',scores[0]>scores[1] and fixture['files'][1].startswith('tests/'),(approaches,scores))
 ck('0139 benchmark hidden expected authority outcome',authority_stop(next_step='install',requires_operator=True)['stop_before_execution'])
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)
