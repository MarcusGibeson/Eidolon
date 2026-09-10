import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_scorecard import build_gamma_scorecard
from v1399_test_support import *
passed=0
r=build_gamma_scorecard(records());require(r['ok'],'ready');passed+=1;s=r['gamma_scorecard'];m=s['metrics']
require(s['gamma_ready'] and s['thresholds_passed']==7,'gate');passed+=1
require(m['task_class_coverage_count']==8 and m['success_rate']==1.0,'representative success');passed+=1
require(m['boundary_violation_count']==0 and m['evidence_quality']==1.0,'evidence/boundary');passed+=1
require(len(s['scorecard_digest'])==64 and not s['independent_authority_granted'],'receipt authority');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1399-checkpoint'})
