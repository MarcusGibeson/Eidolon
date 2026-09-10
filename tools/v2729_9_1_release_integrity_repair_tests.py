from __future__ import annotations
import importlib.util, json, os, subprocess, sys
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from conscious_agent.combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog
from conscious_agent.combined_trial_campaign_plan_v2721 import build_combined_trial_plan
from conscious_agent.combined_trial_evidence_ledger_v2722 import build_trial_evidence_record,build_campaign_evidence_ledger
from conscious_agent.combined_trial_campaign_readiness_v2724 import build_combined_trial_campaign_readiness
from conscious_agent.combined_trial_campaign_state_v2725 import prepare_combined_trial_campaign_state,load_combined_trial_campaign_state
from conscious_agent.combined_trial_campaign_observability_v2727 import build_combined_trial_campaign_observability

def raises(fn):
    try: fn()
    except (ValueError,TypeError): return True
    return False

def run():
    checks=[]
    def ck(n,v): checks.append((n,bool(v)))
    cat=build_combined_trial_catalog(); plan=build_combined_trial_plan(cat)
    # Unknown dependency must fail closed, not be treated as already satisfied.
    badcat={**cat,'trials':[dict(r) for r in cat['trials']]}
    badcat['trials'][0]['dependencies']=['ghost_trial']
    ck('unknown_dependency_rejected',raises(lambda:build_combined_trial_plan(badcat)))
    # Evidence records must be canonical, schema-closed, and digest-bound.
    rec=build_trial_evidence_record(trial_id='research',status='passed',evidence_codes=['ok'])
    forged=dict(rec); forged['raw_secret']='do not retain'
    ck('evidence_extra_field_rejected',raises(lambda:build_campaign_evidence_ledger(cat,[forged])))
    forged2=dict(rec); forged2['status']='failed'
    ck('evidence_digest_tamper_rejected',raises(lambda:build_campaign_evidence_ledger(cat,[forged2])))
    ck('canonical_evidence_accepted',build_campaign_evidence_ledger(cat,[rec])['completed_count']==1)
    # Same count is insufficient: plan identity and membership must exactly match catalog.
    unrelated={**plan,'plan':[dict(r) for r in plan['plan']]}
    for i,row in enumerate(unrelated['plan']): row['trial_id']=f'unrelated_{i}'
    rd=build_combined_trial_campaign_readiness(cat,unrelated,current_checkpoint='v2729.9.1',release_certified=True,daily_use_engineering_ready=True)
    ck('same_count_unrelated_plan_rejected',not rd['ready_for_operator_campaign_review'] and 'trial_plan_catalog_mismatch' in rd['blockers'])
    # Not-ready campaign cannot be persisted as prepared.
    not_ready=build_combined_trial_campaign_readiness(cat,plan,current_checkpoint='v2729.9.1',release_certified=False,daily_use_engineering_ready=True)
    with TemporaryDirectory() as td:
        ck('not_ready_persistence_rejected',raises(lambda:prepare_combined_trial_campaign_state(cat,plan,not_ready,runtime_root=td)))
    # Persisted state is digest-bound and corruption fails closed/observable.
    ready=build_combined_trial_campaign_readiness(cat,plan,current_checkpoint='v2729.9.1',release_certified=True,daily_use_engineering_ready=True)
    with TemporaryDirectory() as td:
        prepare_combined_trial_campaign_state(cat,plan,ready,runtime_root=td)
        p=Path(td)/'combined_trial_campaign_state_v2725.json'
        data=json.loads(p.read_text()); data['campaign_state']='running'; p.write_text(json.dumps(data))
        loaded=load_combined_trial_campaign_state(td); obs=build_combined_trial_campaign_observability(td)
        ck('tampered_state_rejected',loaded.get('ok') is False and loaded.get('campaign_state')=='corrupt_state_rejected')
        ck('tampered_state_observable',obs.get('ok') is False and obs.get('state')=='corrupt_state_rejected' and not obs.get('campaign_started'))
    # Clean production launcher parity: no verifier PYTHONPATH assistance.
    env=dict(os.environ); env.pop('PYTHONPATH',None); env['PYTHONDONTWRITEBYTECODE']='1'
    a=subprocess.run([sys.executable,str(ROOT/'conscious_agent/main.py'),'--status'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=90)
    b=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'status'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=90)
    ck('direct_main_clean_env',a.returncode==0)
    ck('operator_launcher_clean_env',b.returncode==0)
    # Verifier production-launch environment must omit PYTHONPATH.
    spec=importlib.util.spec_from_file_location('rv',ROOT/'tools/release_verify.py'); rv=importlib.util.module_from_spec(spec); sys.modules['rv']=rv; spec.loader.exec_module(rv)
    with TemporaryDirectory() as td:
        base,_=rv._runtime_environment(Path(td)); prod=rv._production_launcher_environment(base); ck('runtime_status_env_omits_pythonpath','PYTHONPATH' not in prod and base.get('PYTHONPATH')==str(ROOT))
    result={'ok':all(v for _,v in checks),'passed':sum(v for _,v in checks),'total':len(checks),'checks':checks}
    print(json.dumps(result,sort_keys=True)); return result
if __name__=='__main__': raise SystemExit(0 if run()['ok'] else 1)
