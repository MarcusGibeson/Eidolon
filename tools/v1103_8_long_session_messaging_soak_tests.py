from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
from messaging_resilience import build_long_session_soak_report
from messaging_soak import run_messaging_soak

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)

def test_sixty_turn_contract_soak_preserves_exactly_once_and_continuity():
    r=run_messaging_soak(iterations=60)
    require(r['passed'] and r['iterations']==60 and r['accepted_operations']==60,r)
    require(r['exactly_once_preserved'] and r['continuity_digest_count']==1,r)

def test_soak_exercises_cancel_retry_late_result_and_ownership_paths():
    r=run_messaging_soak(iterations=100)
    for key in ('cancellations','explicit_retries','late_results_ignored','ownership_transfers','stale_mutations_rejected'):
        require(r[key]>0,(key,r))
    require(r['automatic_retries']==0 and not r['automatic_replay'],r)

def test_automatic_retry_or_continuity_drift_blocks_soak():
    r=build_long_session_soak_report(iterations=20,accepted_operations=20,provider_requests=19,automatic_retries=1,continuity_digest_count=2)
    require(not r['passed'] and r['status']=='blocked',r)

def test_soak_report_is_content_free_and_private_path_free():
    r=run_messaging_soak(iterations=25); text=json.dumps(r).lower()
    require(r['content_free'] and not r['contains_message_text'] and not r['contains_response_text'],r)
    require('/mnt/' not in text and '\\users\\' not in text and 'provider_payload_included' in r and not r['provider_payload_included'],text)

def test_cli_runs_bounded_without_provider_or_runtime_content():
    run=subprocess.run([sys.executable,str(ROOT/'tools/messaging_soak.py'),'--iterations','40','--json'],cwd=ROOT,text=True,capture_output=True,timeout=30)
    require(run.returncode==0,run.stderr); payload=json.loads(run.stdout); require(payload['passed'] and payload['iterations']==40,payload)

def test_registration_exactly_once():
    src=(ROOT/'tools/post_review_development_verify.py').read_text(); require(src.count('"tools/v1103_8_long_session_messaging_soak_tests.py"')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.8-long-session-messaging-soak','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
