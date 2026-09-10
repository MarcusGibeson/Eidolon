import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_checkpoint import *
from v1400_test_support import *
passed=0
soak=run_gamma_long_soak(iteration_runner=iteration_runner,iterations=8,max_workers=4);require(soak['successful_iterations']==8 and soak['failed_iterations']==0 and soak['max_workers']==4,'repeatability sample');passed+=1
require(soak['completed_tasks']==64 and soak['repeatability_rate']==1.0 and soak['all_task_classes_repeated'],'end to end tasks');passed+=1
arch=build_gamma_architecture_review(source_root=ROOT,changed_paths_since_windows_review=CHANGED);win=build_windows_review_carryforward(validated_version='1396.9',current_version='1400.9',validation_receipt=windows_validation_receipt(),architecture_review=arch)
require(arch['ok'] and win['ok'],'review chain');passed+=1
c=process_gamma_checkpoint_control('show gamma checkpoint',project_state={'gamma_checkpoint':{'checkpoint_digest':'a'*64}});require(c['active'] and c['ok'] and not c['action_executed'],'inspection');passed+=1
require(not c['release_authorized'] and not c['independent_authority_granted'],'authority');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1400-integration'})
