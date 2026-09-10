import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_scorecard import *
from v1399_test_support import *
passed=0
rows=records();require(all(validate_gamma_outcome_record(x) for x in rows),'records');passed+=1
r=build_gamma_scorecard(rows);require(r['ok'],'scorecard');passed+=1;s=r['gamma_scorecard'];m=s['metrics']
require(m['task_count']==8 and m['task_class_coverage_count']==8,'coverage');passed+=1
require(m['success_rate']==1.0 and m['boundary_adherence_rate']==1.0,'rates');passed+=1
require(m['total_duration_ms']>m['median_duration_ms'] and m['p95_duration_ms']>=m['median_duration_ms'],'time');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1399-foundations'})
