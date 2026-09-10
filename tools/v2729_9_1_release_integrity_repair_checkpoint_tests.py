from __future__ import annotations
import json
from v2729_9_1_release_integrity_repair_tests import run as run_repairs
from conscious_agent.combined_trial_campaign_checkpoint_v2729 import build_checkpoint

def run():
    old=build_checkpoint(); repair=run_repairs()
    checks={
        'retained_v2729_checkpoint': bool(old.get('ok')),
        'repair_adversarial_suite': bool(repair.get('ok')),
        'retained_campaign_not_started': bool((old.get('checks') or {}).get('prepared_not_started')),
        'no_authority': bool((old.get('checks') or {}).get('no_authority')),
    }
    out={'ok':all(checks.values()),'checkpoint_version':'2729.9.1','status':'runtime_import_trial_contract_integrity_repair_ready' if all(checks.values()) else 'blocked','checks':checks,'passed':sum(checks.values()),'total':len(checks)}
    print(json.dumps(out,sort_keys=True)); return out
if __name__=='__main__': raise SystemExit(0 if run()['ok'] else 1)
