import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from autonomous_developer_gamma_checkpoint import *
from v1400_test_support import *
passed=0
arch=build_gamma_architecture_review(source_root=ROOT,changed_paths_since_windows_review=CHANGED);require(arch['ok'],'architecture');passed+=1
require(arch['module_count']==9 and all(x['syntax_ok'] for x in arch['module_rows']),'modules');passed+=1
require(arch['protected_core_review_required'] and arch['protected_core_review_complete'],'protected core review');passed+=1
win=build_windows_review_carryforward(validated_version='1396.9',current_version='1400.9',validation_receipt=windows_validation_receipt(),architecture_review=arch);require(win['ok'] and win['version_age']==4 and win['validation_receipt_sealed'],'windows carryforward');passed+=1
require(scorecard()['gamma_ready'],'scorecard input');passed+=1
print({'ok':passed==5,'passed':passed,'total':5,'suite':'v1400-foundations'})
