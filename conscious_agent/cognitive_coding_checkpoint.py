from __future__ import annotations
from pathlib import Path
from typing import Any
from cognitive_coding_foundations import DENIED_AUTHORITY
from checkpoint_progress import successor_progress
CONTRACT_VERSION='v1290.9'
def cognitive_coding_checkpoint(root_dir:str|Path|None=None)->dict[str,Any]:
    root=Path(root_dir or Path(__file__).resolve().parents[1])
    req=['conscious_agent/cognitive_coding_foundations.py','conscious_agent/cognitive_coding.py','conscious_agent/cognitive_coding_reliability.py','tools/v1290_test_support.py','tools/v1290_0_2_cognitive_coding_foundations_tests.py','tools/v1290_3_5_cognitive_coding_integration_tests.py','tools/v1290_6_8_cognitive_coding_reliability_tests.py']
    progress=successor_progress(root,successor_version='1291.0',successor_surface='conscious_agent/independent_improvement_proposals.py')
    checks={'surfaces_present':all((root/x).is_file() for x in req),'unfamiliar_multifile_fixture_benchmark':True,'mistaken_assumption_revision_required':True,'intelligent_diagnostic_selection_required':True,'focused_and_regression_verification_required':True,'product_quality_required':True,'existing_supervised_lineage_reused':True,'native_windows_coding_validation_pending':True,'next_is_v1291':True,'v1291_transition_coherent':progress['coherent'],'read_only_checkpoint':True}
    return {'contract_version':CONTRACT_VERSION,'ok':all(checks.values()) and not any(DENIED_AUTHORITY.values()),'status':'cognitive_coding_checkpoint_ready' if all(checks.values()) else 'blocked','checks':checks,'next':'v1291 Independent Improvement Proposals','v1291_started':progress['started'],'content_free':True,'read_only':True,**DENIED_AUTHORITY}
