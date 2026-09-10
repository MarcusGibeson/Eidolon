from pathlib import Path
import tempfile, os
from conscious_agent.verification_history_v2547 import append_observations, CONTRACT_VERSION
from conscious_agent.api_server import handle_api_get
from conscious_agent import dashboard

def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        old=os.environ.get('EIDOLON_DATA_DIR'); os.environ['EIDOLON_DATA_DIR']=td
        try:
            p=Path(td)/'verification'/'tiered_verification_history.json'
            rows=[]
            for i,ok in enumerate([1,0,1,0]):
                rows.append({'contract_version':CONTRACT_VERSION,'test':'tools/example.py','tier':1,'ok':bool(ok),'status':'passed' if ok else 'failed','timed_out':False,'observed_at':str(i),'parent_receipt_digest':'','elapsed_seconds':1.0,'raw_output_stored':False,'observation_digest':f'{i:064x}'})
            append_observations(p,rows)
            status,payload=handle_api_get('/api/cognition/observability/verification?window=4')
            data=payload.get('data') or payload
            checks += [status==200,payload.get('ok') is True,data['health']['state']=='attention',data['authority_boundary']['read_only']]
        finally:
            if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
            else: os.environ['EIDOLON_DATA_DIR']=old
    html=dashboard.render_cognitive_observability_dashboard()
    checks += ['mind-verification-state' in html,'mind-verification' in html,'/api/cognition/observability/verification' in html,'verificationTrends.direction' in html,'verificationConcerns' in html]
    passed=sum(bool(x) for x in checks)
    print({'suite':'v2559-verification-health-dashboard','ok':passed==len(checks),'passed':passed,'total':len(checks)});raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()
