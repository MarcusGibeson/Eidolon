from __future__ import annotations
import argparse,json,os,socket,subprocess,sys,tempfile,time
from contextlib import contextmanager
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';TOOLS=ROOT/'tools';sys.path.insert(0,str(AGENT))
import chat_action_router as router
from conversation_action_portal import build_action_portal_state,running_claim_is_interrupted
import post_review_development_verify as isolated_verify

def require(v,m):
    if not v:raise AssertionError(m)

@contextmanager
def store():
    with tempfile.TemporaryDirectory(prefix='eidolon-v1082-8-') as raw:
        old=(router.CHAT_ACTIONS_DIR,router.CHAT_ACTIONS_README,router.store_memory)
        router.CHAT_ACTIONS_DIR=Path(raw)/'chat_actions';router.CHAT_ACTIONS_README=router.CHAT_ACTIONS_DIR/'README.md';router.store_memory=lambda *_a,**_k:None
        try:yield Path(raw)
        finally:router.CHAT_ACTIONS_DIR,router.CHAT_ACTIONS_README,router.store_memory=old

def action(action_id='chat_action_lease'):
    return {'id':action_id,'created_at':'2026-07-20T00:00:00','updated_at':'2026-07-20T00:00:00','intent':'diagnostics','title':'Diagnostics','summary':'Run diagnostics.','execution_mode':router.DIRECT_COMMAND,'risk_level':'low','status':'proposed','command':'python conscious_agent/main.py --status','execution_attempt':0,'execution_attempts':[],'result':{}}

def test_claim_has_bounded_lease_and_private_token():
    with store():
        value=action();router.save_chat_action(value);claimed=router._claim_execution_attempt(router.load_chat_action(value['id']),claimant='dashboard',lease_seconds=30)
        owner=claimed['claim_owner'];require(len(owner['claim_token'])==64 and owner['lease_expires_epoch']>owner['claimed_epoch'],'claim lease missing')
        portal=build_action_portal_state(claimed);require(portal['claim_expires_at'] and portal['claim_generation']==1,'portal lease evidence missing')
        require('claim_token' not in json.dumps(portal),'portal exposed claim token')

def test_exact_owner_can_renew():
    with store():
        value=action();router.save_chat_action(value);claimed=router._claim_execution_attempt(router.load_chat_action(value['id']),claimant='cli',lease_seconds=10);token=claimed['claim_owner']['claim_token'];before=claimed['claim_owner']['lease_expires_epoch']
        renewed=router.renew_chat_action_claim(value['id'],token,claimant='cli',lease_seconds=20,now_epoch=before)
        current=router.load_chat_action(value['id']);require(renewed['ok'] and current['claim_owner']['lease_expires_epoch']>before,'claim did not renew')

def test_stale_owner_cannot_renew_or_complete_new_attempt():
    with store():
        value=action();router.save_chat_action(value);first=router._claim_execution_attempt(router.load_chat_action(value['id']),claimant='cli',lease_seconds=10);old=first['claim_owner']['claim_token']
        interrupted=router._complete_execution_attempt(value['id'],status='interrupted',result_data={'ok':False},expected_claim_token=old)
        second=router._claim_execution_attempt(interrupted,claimant='dashboard',lease_seconds=10);new=second['claim_owner']['claim_token']
        denied=router.renew_chat_action_claim(value['id'],old,claimant='cli',lease_seconds=20)
        stale=router._complete_execution_attempt(value['id'],status='completed',result_data={'ok':True},expected_claim_token=old)
        current=router.load_chat_action(value['id']);require(not denied['ok'] and denied['status']=='stale_claim','stale owner renewed')
        require(stale.get('stale_completion_ignored') and current['status']=='running' and current['claim_owner']['claim_token']==new,'stale completion overwrote newer claim')

def test_expired_remote_claim_is_interrupted():
    value=action();value['status']='running';value['claim_owner']={'scope':'api','pid':999999,'host':'remote-host','claimed_epoch':time.time()-20,'lease_expires_epoch':time.time()-1,'lease_expires_at':'expired'}
    interrupted,reason=running_claim_is_interrupted(value);require(interrupted and 'expired' in reason.lower(),'expired lease not interrupted')

def test_live_unexpired_claim_remains_owned():
    value=action();value['status']='running';value['claim_owner']={'scope':'process','pid':os.getpid(),'host':socket.gethostname(),'claimed_epoch':time.time(),'lease_expires_epoch':time.time()+30}
    interrupted,_=running_claim_is_interrupted(value);require(not interrupted,'live claim treated as abandoned')

def test_two_processes_create_one_attempt():
    with store() as root:
        value=action('chat_action_process_race');router.save_chat_action(value)
        calls=root/'calls.txt';barrier=root/'go';script=root/'race.py'
        script.write_text('''import sys,time,json\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nimport chat_action_router as r\nfrom types import SimpleNamespace\nr.CHAT_ACTIONS_DIR=Path(sys.argv[2]);r.CHAT_ACTIONS_README=r.CHAT_ACTIONS_DIR/'README.md';r.store_memory=lambda *_a,**_k:None\nbarrier=Path(sys.argv[3]);calls=Path(sys.argv[4])\nwhile not barrier.exists():time.sleep(.01)\ndef run(*_a,**_k):\n    with calls.open('a') as f:f.write('call\\n')\n    time.sleep(.25)\n    return SimpleNamespace(ok=True,message='done',error='',command='safe',return_code=0,stdout='',stderr='',timed_out=False)\nr.run_approved_command=run\nres=r.execute_chat_action('chat_action_process_race',claimant=sys.argv[5])\nprint(json.dumps({'status':res.status,'replayed':res.replayed,'ok':res.ok}))\n''')
        args=[sys.executable,str(script),str(AGENT),str(router.CHAT_ACTIONS_DIR),str(barrier),str(calls)]
        p1=subprocess.Popen(args+['cli'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);p2=subprocess.Popen(args+['dashboard'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);barrier.write_text('go')
        o1,e1=p1.communicate(timeout=20);o2,e2=p2.communicate(timeout=20);require(p1.returncode==0 and p2.returncode==0,e1+e2)
        current=router.load_chat_action(value['id']);count=len(calls.read_text().splitlines()) if calls.exists() else 0
        require(count==1,'competing processes executed more than once')
        require(current['execution_attempt']==1 and current['status']=='executed','process race created duplicate attempt')

def test_claim_token_not_preserved_after_completion():
    with store():
        value=action();router.save_chat_action(value);claimed=router._claim_execution_attempt(router.load_chat_action(value['id']),claimant='cli');token=claimed['claim_owner']['claim_token'];done=router._complete_execution_attempt(value['id'],status='completed',result_data={'ok':True},expected_claim_token=token)
        require(done['claim_owner']=={} and 'claim_token' not in done['last_claim_owner'],'terminal record preserved secret token')

def test_registration_and_privacy():
    require('v1082.8-cross-process-claim-lease' in {x.name for x in isolated_verify.select_suites('core')},'core registration missing')
    require((TOOLS/'release_verify.py').read_text().count('v1082_8_cross_process_claim_lease_tests.py')==1,'release registration wrong')
    files=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    require(not any(x.startswith('data/chat_actions/') for x in files),'runtime action data packaged')

TESTS=[('claim_has_bounded_lease_and_private_token',test_claim_has_bounded_lease_and_private_token),('exact_owner_can_renew',test_exact_owner_can_renew),('stale_owner_cannot_renew_or_complete_new_attempt',test_stale_owner_cannot_renew_or_complete_new_attempt),('expired_remote_claim_is_interrupted',test_expired_remote_claim_is_interrupted),('live_unexpired_claim_remains_owned',test_live_unexpired_claim_remains_owned),('two_processes_create_one_attempt',test_two_processes_create_one_attempt),('claim_token_not_preserved_after_completion',test_claim_token_not_preserved_after_completion),('registration_and_privacy',test_registration_and_privacy)]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1082.8-cross-process-claim-lease','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
