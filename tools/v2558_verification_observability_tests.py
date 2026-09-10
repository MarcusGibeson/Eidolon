from pathlib import Path
import tempfile
from conscious_agent.verification_observability_v2558 import build_verification_observability
from conscious_agent.verification_history_v2547 import append_observations, CONTRACT_VERSION

def main():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'history.json'
        rows=[]
        for i,ok in enumerate([True,False,True,False]):
            r={'contract_version':CONTRACT_VERSION,'test':'tools/example.py','tier':1,'ok':ok,'status':'passed' if ok else 'failed','timed_out':False,'observed_at':str(i),'parent_receipt_digest':'','elapsed_seconds':1.0,'raw_output_stored':False,'observation_digest':f'{i:064x}'}
            rows.append(r)
        append_observations(p,rows)
        out=build_verification_observability(history_path=p)
        checks=[out['ok'],out['history_present'],out['health']['state']=='attention',len(out['concerns'])==1,out['concerns'][0]['required_test_still_required'],
                out['history_path_exposed'] is False,out['raw_test_output_stored'] is False,out['authority_boundary']['read_only'],not out['authority_boundary']['can_suppress_test'],not out['authority_boundary']['can_certify_release'],len(out['snapshot_digest'])==64]
    print({'suite':'v2558-verification-observability','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
