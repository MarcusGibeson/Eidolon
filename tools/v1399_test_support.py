import hashlib
from autonomous_developer_gamma_scorecard import EXPECTED_TASK_CLASSES,build_gamma_outcome_record

def require(c,m):
    if not c: raise AssertionError(m)

def records(*,failure_class='',boundary_failure_class=''):
    rows=[]
    for i,task_class in enumerate(EXPECTED_TASK_CLASSES,1):
        evidence_digest=hashlib.sha256(f'executed-{task_class}-{i}'.encode()).hexdigest()
        rows.append(build_gamma_outcome_record(task_id=f'gamma-task-{i}',task_class=task_class,success=task_class!=failure_class,intervention_count=1 if task_class==failure_class else 0,regression_count=1 if task_class==failure_class else 0,rework_count=1 if task_class=='bug_report' else 0,duration_ms=100+i*10,evidence_checks={'tests':True,'result':True,'lineage':True,'rollback':True},boundary_checks={'authority':task_class!=boundary_failure_class,'privacy':True,'source':True},workflow_evidence_digest=evidence_digest))
    return rows
