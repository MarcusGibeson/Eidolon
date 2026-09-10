from pathlib import Path
import tempfile
from conscious_agent.verification_history_v2547 import *

def main():
    receipt={'status':'tiered_verification_failed','receipt_digest':'a'*64,'receipts':[{'tier':1,'tests':[{'test':'tools/a_tests.py','ok':True,'status':'completed','timed_out':False,'elapsed_seconds':1.25},{'test':'tools/b_tests.py','ok':False,'status':'timeout','timed_out':True,'elapsed_seconds':20.0}]}]}
    obs=observations_from_tiered_receipt(receipt,observed_at='2026-09-02T00:00:00Z')
    checks=[len(obs)==2,obs[0]['raw_output_stored'] is False,obs[1]['timed_out'] is True,obs[0]['parent_receipt_digest']=='a'*64,obs[0]['required_test_waiver_authorized'] is False]
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'history.json'; r=append_observations(p,obs); h=load_history(p)
        checks += [r['ok'],r['test_count']==2,len(h['tools/a_tests.py'])==1,'stdout' not in p.read_text(), 'stderr' not in p.read_text()]
        for i in range(70): append_observations(p,[obs[0]])
        checks += [len(load_history(p)['tools/a_tests.py'])==MAX_HISTORY_PER_TEST]
    try: observations_from_tiered_receipt({'status':'x'}); checks.append(False)
    except ValueError: checks.append(True)
    try: _=append_observations(Path('/tmp/x'),[{'contract_version':'bad'}]); checks.append(False)
    except ValueError: checks.append(True)
    print({'suite':'v2547-verification-history','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)})
    raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
