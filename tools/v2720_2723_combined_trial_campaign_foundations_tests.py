from conscious_agent.combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog
from conscious_agent.combined_trial_campaign_plan_v2721 import build_combined_trial_plan
from conscious_agent.combined_trial_evidence_ledger_v2722 import build_trial_evidence_record,build_campaign_evidence_ledger
from conscious_agent.combined_trial_stop_rollback_v2723 import build_trial_stop_rollback_matrix

def run():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 cat=build_combined_trial_catalog();ck('eight_trials',cat['trial_count']==8 and not cat['campaign_started'])
 plan=build_combined_trial_plan(cat);ck('all_planned',plan['trial_count']==8 and len({r['trial_id'] for r in plan['plan']})==8);ck('architecture_before_project_start',next(r['sequence'] for r in plan['plan'] if r['trial_id']=='architecture_project')<next(r['sequence'] for r in plan['plan'] if r['trial_id']=='project_start'))
 ck('no_auto_transition',not plan['automatic_transition_permitted'] and all(not r['automatic_start_permitted'] for r in plan['plan']))
 rec=build_trial_evidence_record(trial_id='research',status='passed',evidence_codes=['citation_quality_pass']);ledger=build_campaign_evidence_ledger(cat,[rec]);ck('ledger_partial',ledger['completed_count']==1 and not ledger['campaign_complete'])
 matrix=build_trial_stop_rollback_matrix(cat);ck('stop_conditions',len(matrix['rows'])==8 and matrix['global_stop_on_privacy_violation']);ck('no_auto_rollback',not matrix['automatic_rollback_permitted'])
 ck('content_minimized',not rec['raw_trial_content_stored'] and not ledger['raw_trial_content_stored']);ck('no_authority',not cat['authority_granted'] and not plan['authority_granted'] and not matrix['authority_granted'])
 return {'ok':all(v for _,v in c),'checks':c,'passed':sum(v for _,v in c),'total':len(c)}
if __name__=='__main__':
 r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
