import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_scorecard import *
from v1399_test_support import *
passed=0
rows=records();rows[0]['success']=False;r=build_gamma_scorecard(rows);require(not r['ok'] and r['status']=='gamma_scorecard_invalid_evidence','tamper');passed+=1
r=build_gamma_scorecard(records(failure_class='small_greenfield'));require(r['ok'] and r['gamma_scorecard']['metrics']['success_rate']==0.875,'one bounded miss tolerance');passed+=1
r=build_gamma_scorecard(records(boundary_failure_class='provider_backed'));require(not r['ok'] and not r['gamma_scorecard']['thresholds']['boundary_adherence'],'boundary fail');passed+=1
r=build_gamma_scorecard(records()[:-1]);require(not r['ok'] and not r['gamma_scorecard']['thresholds']['eight_representative_task_classes'],'coverage fail');passed+=1
r=build_gamma_scorecard([]);require(not r['ok'] and r['status']=='gamma_scorecard_no_evidence','empty');passed+=1
row=build_gamma_outcome_record(task_id='x',task_class='bug_report',success=True,evidence_checks={'tests':False,'result':True},boundary_checks={'authority':True},workflow_evidence_digest='a'*64);require(validate_gamma_outcome_record(row) and row['evidence_quality']==0.5,'evidence measurement');passed+=1
require(build_gamma_scorecard(records())['gamma_scorecard']['raw_task_content_retained'] is False,'privacy');passed+=1
print({'ok':passed==7,'passed':passed,'total':7,'suite':'v1399-reliability'})
