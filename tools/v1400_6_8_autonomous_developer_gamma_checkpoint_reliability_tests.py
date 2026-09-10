import hashlib
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_checkpoint import *
from autonomous_developer_gamma_scorecard import EXPECTED_TASK_CLASSES
from v1400_test_support import *

passed=0
arch=build_gamma_architecture_review(source_root=ROOT,changed_paths_since_windows_review=CHANGED)
receipt=windows_validation_receipt()
stale=build_windows_review_carryforward(validated_version='1380.9',current_version='1400.9',validation_receipt=receipt,architecture_review=arch);require(not stale['ok'],'stale windows');passed+=1
arch_ui=build_gamma_architecture_review(source_root=ROOT,changed_paths_since_windows_review=CHANGED+['conscious_agent/dashboard_app.py']);win=build_windows_review_carryforward(validated_version='1396.9',current_version='1400.9',validation_receipt=receipt,architecture_review=arch_ui);require(not arch_ui['ok'] and not win['ok'],'windows-sensitive change');passed+=1
tampered=dict(receipt);tampered['manual_validation_performed']=False;win=build_windows_review_carryforward(validated_version='1396.9',current_version='1400.9',validation_receipt=tampered,architecture_review=arch);require(not win['ok'] and not win['validation_receipt_sealed'],'manual receipt tamper');passed+=1

def fixture(i, fail_at=-1):
    rows=[{'task_class':task_class,'ok':i!=fail_at,'evidence_digest':hashlib.sha256(f'{i}-{task_class}'.encode()).hexdigest()} for task_class in EXPECTED_TASK_CLASSES]
    return {'ok':i!=fail_at,'completed_tasks':len(rows) if i!=fail_at else 0,'task_evidence':rows,'evidence_digest':hashlib.sha256(f'iteration-{i}'.encode()).hexdigest(),'failure_class':'fixture' if i==fail_at else None}

soak=run_gamma_long_soak(iteration_runner=lambda i:fixture(i,3),iterations=64);require(not soak['long_soak_complete'] and soak['failed_iterations']==1,'soak failure');passed+=1
short=run_gamma_long_soak(iteration_runner=fixture,iterations=8);require(not short['long_soak_complete'] and short['completed_tasks']==64,'short soak');passed+=1
empty=run_gamma_long_soak(iteration_runner=lambda i:{'ok':True},iterations=64);require(not empty['long_soak_complete'] and empty['completed_tasks']==0,'empty evidence rejected');passed+=1
card=scorecard();card['gamma_ready']=False;win=build_windows_review_carryforward(validated_version='1396.9',current_version='1400.9',validation_receipt=receipt,architecture_review=arch);r=build_autonomous_developer_gamma_checkpoint(scorecard=card,architecture_review=arch,windows_review=win,soak=run_gamma_long_soak(iteration_runner=fixture,iterations=64));require(not r['ok'],'tampered scorecard');passed+=1
require(not r['authority_expansion_authorized'] and not r['independent_authority_granted'],'authority');passed+=1
print({'ok':passed==8,'passed':passed,'total':8,'suite':'v1400-reliability'})
