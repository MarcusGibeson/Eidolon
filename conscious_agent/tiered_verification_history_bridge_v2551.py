from __future__ import annotations
"""v2551 optional runtime-history bridge for tiered verification receipts."""
from pathlib import Path
from typing import Any,Sequence
from tiered_verification_runtime_v2541 import run_tiered_verification
from verification_history_v2547 import observations_from_tiered_receipt, append_observations
CONTRACT_VERSION='v2551.0'
AUTHORITY={'source_mutation_authorized':False,'required_test_waiver_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def run_tiered_verification_with_history(source_root:str|Path,changed_paths:Sequence[str],*,history_path:str|Path,through_tier:int=1,observed_at:str='',timeout_each_tier1:float=20.0,timeout_each_tier2:float=30.0)->dict[str,Any]:
    receipt=run_tiered_verification(source_root,changed_paths,through_tier=through_tier,timeout_each_tier1=timeout_each_tier1,timeout_each_tier2=timeout_each_tier2)
    obs=observations_from_tiered_receipt(receipt,observed_at=observed_at)
    history=append_observations(history_path,obs) if obs else {'ok':True,'test_count':0,'observation_count':0,'history_digest':''}
    return {'ok':bool(receipt.get('ok')),'contract_version':CONTRACT_VERSION,'verification_receipt':receipt,'history_update':history,'observation_count':len(obs),'history_path_exposed':False,'raw_output_stored':False,**AUTHORITY}
__all__=['CONTRACT_VERSION','run_tiered_verification_with_history']
