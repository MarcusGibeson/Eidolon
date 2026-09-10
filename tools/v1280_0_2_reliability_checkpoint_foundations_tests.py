from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from reliability_checkpoint_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def trial(code,i,**kw):return build_reliability_trial(scenario_code=code,campaign_id=f'selfalpha_{i}',session_id=f'longwork_{i}',completed=True,final_phase='operator_review_required',evidence_codes=['bounded'],**kw)
rows=[trial(c,i,restart_count=(1 if i else 0),recovery_count=(1 if i in {1,2,3,4} else 0)) for i,c in enumerate(REQUIRED_SCENARIOS)]
for i,r in enumerate(rows):req(validate_reliability_trial(r)['ok'],f'valid_{i}');req(validate_reliability_trial(r)['clean'],f'clean_{i}');req(not r['native_windows_execution_claimed'],f'no_windows_claim_{i}')
a=aggregate_reliability_trials(rows);req(a['ok'],'aggregate');req(a['trial_count']==6 and a['scenario_count']==6,'counts');req(a['required_scenarios_present'],'required');req(a['all_trials_clean'] and a['all_trials_completed'],'clean_complete');req(a['duplicate_provider_count']==0 and a['duplicate_test_count']==0,'no_duplicates');req(a['unauthorized_action_count']==0 and a['stale_state_count']==0 and a['private_content_finding_count']==0,'no_integrity_failures');req(a['desktop_codex_native_windows_required'] and not a['native_windows_execution_claimed'],'windows_truth')
bad=trial('normal_campaign','bad',duplicate_provider_count=1);req(validate_reliability_trial(bad)['ok'],'bad_schema_valid');req(not validate_reliability_trial(bad)['clean'],'bad_not_clean');blocked=aggregate_reliability_trials(rows[:-1]+[bad]);req(not blocked['ok'],'aggregate_blocks_duplicate')
for k,v in AUTHORITY_FLAGS.items():req(a.get(k) is v,'auth_'+k)
print(json.dumps({'ok':True,'suite':'v1280.0-2-reliability-checkpoint-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
