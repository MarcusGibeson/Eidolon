import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_scorecard import *
from v1399_test_support import *
passed=0
r=build_gamma_scorecard(records());s=r['gamma_scorecard'];require(s['thresholds_passed']==s['thresholds_total']==7,'thresholds');passed+=1
require(s['metrics']['rework_rate']==0.125 and s['metrics']['intervention_rate']==0.0,'rework/intervention');passed+=1
require(s['metrics']['evidence_quality']==1.0,'evidence');passed+=1
c=process_gamma_scorecard_control('show gamma scorecard',project_state={'gamma_scorecard':s});require(c['active'] and c['ok'] and not c['action_executed'],'inspection');passed+=1
require(not s['release_authorized'] and not s['authority_expansion_authorized'],'authority');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1399-integration'})
