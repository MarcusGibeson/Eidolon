from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path:sys.path.insert(0,str(value))
import execution_outcome_reflection_learning_integration as subject
from ordinary_chat_development_campaign import _atomic_json,_digest
from v1229_outcome_fixture import build_outcome_fixture
checks=[]
def check(v):checks.append(bool(v))
# One real recovered lineage validates crash-recovery lesson selection.
f=build_outcome_fixture('reliability-recovered','recovered')
out=subject.prepare_execution_outcome(f['launch']['launch_id'],outcome_type='recovered',expected_launch_digest=f['launch']['launch_digest'],expected_monitor_digest=f['monitor']['monitor_digest'],expected_control_digest=f['control']['control_digest'],runtime_root=f['runtime'])
ref=subject.prepare_execution_outcome_reflection(out['outcome_id'],expected_outcome_digest=out['outcome_digest'],runtime_root=f['runtime'])
check('strengthen_recovery_checks' in ref.get('candidate_lesson_codes',[]));check('preserve_operator_intervention' in ref.get('candidate_lesson_codes',[]))
# Synthetic sealed reflection records exercise all review dispositions without rebuilding ancestry.
runtime=Path(tempfile.mkdtemp(prefix='v1229-reviews-'))
for index,decision in enumerate(('defer','suspend','reject','revise')):
    identity={'outcome_id':f'outcome_{index:024x}','outcome_digest':_digest({'o':index}),'codes':['require_more_evidence']}
    reflection={
      'ok':True,'status':'execution_outcome_reflection_ready_for_review','reflection_id':f'reflection_{index:024x}',
      'reflection_digest':_digest(identity),'reflection_status':'candidate_ready','outcome_id':identity['outcome_id'],
      'outcome_digest':identity['outcome_digest'],'outcome_type':'inconclusive','achievement_classification':'inconclusive',
      'project_reference':f'project_{index:016x}','candidate_lesson_codes':['require_more_evidence'],
      'supporting_fact_codes':['monitor_stage:blocked'],'uncertainty_codes':['terminal_outcome_not_established'],
      'lesson_review_required':True,'deliberate_silence':False,'operation_status':'created',**subject._base(),
    }
    reflection=subject._sealed(reflection,'execution_outcome_reflection_record_digest');_atomic_json(subject._reflection_path(reflection['reflection_id'],runtime),reflection)
    kwargs={'revised_lesson_codes':['strengthen_dependency_checks','require_more_evidence']} if decision=='revise' else {}
    row=subject.review_execution_outcome_lesson(reflection['reflection_id'],expected_reflection_digest=reflection['reflection_digest'],disposition=decision,runtime_root=runtime,**kwargs)
    check(row.get('ok'));check(row.get('disposition')==decision);check(row.get('project_mutation_authorized') is False)

# Later evidence can reconsider an accepted project-scoped lesson without mutating cognition.
project='project_reconsider0001'
reflection={
  'ok':True,'status':'execution_outcome_reflection_ready_for_review','reflection_id':'reflection_'+'a'*24,
  'reflection_digest':_digest({'r':'accepted'}),'reflection_status':'candidate_ready','outcome_id':'outcome_'+'b'*24,
  'outcome_digest':_digest({'o':'accepted'}),'outcome_type':'completed','achievement_classification':'achieved',
  'project_reference':project,'candidate_lesson_codes':['retain_bounded_approach'],
  'supporting_fact_codes':['monitor_stage:completed_pending_review'],'uncertainty_codes':[],
  'lesson_review_required':True,'deliberate_silence':False,'operation_status':'created',**subject._base(),
}
reflection=subject._sealed(reflection,'execution_outcome_reflection_record_digest');_atomic_json(subject._reflection_path(reflection['reflection_id'],runtime),reflection)
accepted=subject.review_execution_outcome_lesson(reflection['reflection_id'],expected_reflection_digest=reflection['reflection_digest'],disposition='accept',runtime_root=runtime)
check(accepted.get('ok'))
later_identity={'launch_id':'launch_'+'c'*24,'launch_digest':'d'*64,'monitor_digest':'e'*64,'control_digest':'f'*64,'outcome_type':'failed'}
later={
 'ok':True,'status':'execution_outcome_ready_for_reflection','outcome_id':'outcome_'+_digest(later_identity)[:24],
 'outcome_digest':_digest(later_identity),'outcome_type':'failed','achievement_classification':'failed',
 'launch_id':later_identity['launch_id'],'launch_digest':later_identity['launch_digest'],'monitor_id':'monitor_'+'1'*24,
 'monitor_digest':later_identity['monitor_digest'],'control_id':'control_'+'2'*24,'control_digest':later_identity['control_digest'],
 'project_reference':project,'queue_item_id':'work_'+'3'*24,'proposal_id':'devc_'+'4'*24,'source_session_id':'session_'+'5'*24,
 'observed_fact_codes':['monitor_stage:blocked','blocker:dependency_blocked'],'uncertainty_codes':[],
 'evidence_complete':True,'reflection_review_required':True,'operation_status':'created',**subject._base(),
}
later=subject._sealed(later,'execution_outcome_record_digest');_atomic_json(subject._outcome_path(later['outcome_id'],runtime),later)
reconsidered=subject.reconsider_execution_outcome_lesson(accepted['review_id'],expected_review_digest=accepted['review_digest'],later_outcome_id=later['outcome_id'],expected_later_outcome_digest=later['outcome_digest'],decision='revise',runtime_root=runtime)
for value in (reconsidered.get('ok'),reconsidered.get('decision')=='revise',reconsidered.get('new_operator_review_required') is True,reconsidered.get('cognition_written') is False):check(value)
replay=subject.reconsider_execution_outcome_lesson(accepted['review_id'],expected_review_digest=accepted['review_digest'],later_outcome_id=later['outcome_id'],expected_later_outcome_digest=later['outcome_digest'],decision='revise',runtime_root=runtime);check(replay.get('operation_status')=='replayed')
other=dict(later);other['outcome_id']='outcome_'+'6'*24;other['outcome_digest']=_digest({'other':1});other['project_reference']='project_other000000';other=subject._sealed({k:v for k,v in other.items() if k!='execution_outcome_record_digest'},'execution_outcome_record_digest');_atomic_json(subject._outcome_path(other['outcome_id'],runtime),other)
check(subject.reconsider_execution_outcome_lesson(accepted['review_id'],expected_review_digest=accepted['review_digest'],later_outcome_id=other['outcome_id'],expected_later_outcome_digest=other['outcome_digest'],decision='retain',runtime_root=runtime).get('ok') is False)

# Contradiction and stale/tamper closure.
check(subject._normalize_lesson_codes(['retain_bounded_approach'])==['retain_bounded_approach'])
try: subject._normalize_lesson_codes(['retain_bounded_approach','avoid_repeating_approach']);check(False)
except ValueError: check(True)
path=subject._outcome_path(out['outcome_id'],f['runtime']);tampered=dict(out);tampered['outcome_type']='completed';_atomic_json(path,tampered)
check(subject._load_outcome(out['outcome_id'],f['runtime'])=={});check(subject.prepare_execution_outcome_reflection(out['outcome_id'],expected_outcome_digest=out['outcome_digest'],runtime_root=f['runtime']).get('ok') is False)
public=subject.public_execution_outcome_lesson_reviews(runtime_root=runtime)
for value in (public.get('ok'),public.get('private_path_exposed') is False,public.get('cognition_written') is False,public.get('launch_authorized') is False,public.get('old_authority_reusable') is False):check(value)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
