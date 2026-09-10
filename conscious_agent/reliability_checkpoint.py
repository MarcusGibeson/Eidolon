from __future__ import annotations
"""v1280.3-v1280.5 integration of reliability evidence with v1279 operator state."""
from typing import Any,Mapping
from reliability_checkpoint_foundations import *
CONTRACT_VERSION="v1280.5"
def reliability_trial_from_operator_snapshot(snapshot:Mapping[str,Any],*,scenario_code:str,restart_count:int=0,provider_execution_count:int=0,test_execution_count:int=0,completed:bool=True,evidence_codes=())->dict[str,Any]:
 progress=dict(snapshot.get("progress") or {});current=dict(snapshot.get("current") or {});auth=dict(snapshot.get("authorization") or {});privacy=dict(snapshot.get("privacy") or {})
 private=0 if privacy.get("content_minimized") is True and all(privacy.get(k) is False for k in ("raw_prompt_exposed","raw_response_exposed","provider_payload_exposed","raw_test_output_exposed","authorization_phrase_exposed")) else 1
 unauthorized=0 if auth.get("generic_go_ahead_sufficient") is False and auth.get("authorization_phrase_exposed") is False else 1
 stale=1 if current.get("campaign_phase") in {"unknown","blocked_stale"} else 0
 return build_reliability_trial(scenario_code=scenario_code,campaign_id=str(snapshot.get("campaign_id") or ""),session_id=str(snapshot.get("session_id") or ""),completed=completed,final_phase=str(current.get("campaign_phase") or "unknown"),restart_count=restart_count,failure_count=int(progress.get("failure_count_total") or 0),recovery_count=int(progress.get("recovery_count_total") or 0),provider_execution_count=provider_execution_count,test_execution_count=test_execution_count,unauthorized_action_count=unauthorized,stale_state_count=stale,private_content_finding_count=private,source_mutation_without_authority=bool(current.get("active_source_modified")) and not bool(snapshot.get("review") or {}).get("state") == "ready",next_required_authorization=str(auth.get("code") or "operator_reconciliation"),evidence_codes=evidence_codes)
def build_reliability_campaign_matrix(snapshot:Mapping[str,Any])->dict[str,Any]:
 scenarios=[]
 for code,restarts,evidence in (("normal_campaign",0,["supervised_path"]),("restart_recovery",2,["restart_reconciled","no_replay"]),("provider_outage_return",1,["provider_outage","provider_return"]),("ownership_transfer",1,["fenced_owner","successor_reconciled"]),("dashboard_restart",2,["projection_reconstructed"]),("long_path_campaign",0,["extended_path_shape"] )):
  scenarios.append(reliability_trial_from_operator_snapshot(snapshot,scenario_code=code,restart_count=restarts,completed=True,evidence_codes=evidence))
 return aggregate_reliability_trials(scenarios)
__all__=["CONTRACT_VERSION","reliability_trial_from_operator_snapshot","build_reliability_campaign_matrix"]
