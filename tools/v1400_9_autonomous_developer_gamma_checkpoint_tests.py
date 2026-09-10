import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_checkpoint import *
from release_authority import WORKING_SOURCE_VERSION
from v1400_test_support import *
passed=0
require(WORKING_SOURCE_VERSION=='1400.9','release authority current');passed+=1
arch=build_gamma_architecture_review(source_root=ROOT,changed_paths_since_windows_review=CHANGED);win=build_windows_review_carryforward(validated_version='1396.9',current_version='1400.9',validation_receipt=windows_validation_receipt(),architecture_review=arch);soak=run_gamma_long_soak(iteration_runner=iteration_runner,iterations=64,max_workers=4);r=build_autonomous_developer_gamma_checkpoint(scorecard=scorecard(),architecture_review=arch,windows_review=win,soak=soak);require(r['ok'],'checkpoint');passed+=1
g=r['gamma_checkpoint'];require(g['gamma_checkpoint_ready'] and g['passed']==g['total']==11,'gate');passed+=1
require(soak['successful_iterations']==64 and soak['completed_tasks']==512 and soak['repeatability_rate']==1.0 and soak['all_task_classes_repeated'],'long soak');passed+=1
require(win['ok'] and arch['protected_core_review_complete'] and not g['authority_expansion_authorized'] and not g['independent_authority_granted'],'review authority');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1400-checkpoint'})
