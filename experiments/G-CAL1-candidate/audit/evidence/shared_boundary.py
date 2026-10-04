import sys,json,copy
from pathlib import Path
from datetime import date,timedelta
ROOT=Path(r'C:\Users\marcu\Eidolon-g4adj');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
def hook(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.bind'):raise RuntimeError('AUDIT_NETWORK_DENIED')
sys.addaudithook(hook)
import g_cal1_contract as C
from g_cal1_lab import Run
from g_extract1_contract import canonical,digest,IntegrityError
from g_extract1_journal import write_once
p=C.Package();results=[]
def good(req,row):
    return {'raw_output':json.dumps(p.members[row['fixture_id']]['gold']),'provider_truncated':False,'receipt':{'call_id':row['call_id'],'request_sha256':row['request_sha256'],'synthetic_only':True}}
def run(name):return Run(p,OUT/name,name)
def capture(action):
    try:
        result=action();return {'accepted':True,'result':result}
    except BaseException as e:return {'accepted':False,'exception':type(e).__name__,'event':getattr(e,'event',None),'detail':str(e)}
def state(r):return {'state':r.state(),'disk_incidents':[x['payload']['event'] for x in r.incidents.read()],'journal_kinds':[x['payload']['kind'] for x in r.journal.read()]}

original=run('shared-retained-invalidity');cp=original.checkpoint();resumed=Run(p,original.directory,original.run_id,resume=True)
bad=original.directory/'bad.json';write_once(bad,{'payload':[], 'sha256':digest(canonical([]))})
failure=capture(lambda:resumed.verify_resume(bad));before=state(original);calls=[]
def track(req,row):calls.append(row['call_id']);return good(req,row)
performed=capture(lambda:original.perform(p.schedule[0],track));after=state(original)
restart=capture(lambda:Run(p,original.directory,original.run_id,resume=True))
results.append({'id':'SHARED_RETAINED_INVALIDITY','malformed_verification':failure,'original_before':before,'original_perform':performed,'transport_calls':calls,'original_after':after,'new_restart':restart})

original=run('shared-journal-advancement');cp=original.checkpoint();resumed=Run(p,original.directory,original.run_id,resume=True);resumed.verify_resume(cp);resumed.perform(p.schedule[0],good)
before=state(original);calls=[];performed=capture(lambda:original.perform(p.schedule[0],track));after=state(original)
restart=capture(lambda:Run(p,original.directory,original.run_id,resume=True))
results.append({'id':'SHARED_STALE_DUPLICATE_CALL','original_before':before,'original_perform':performed,'transport_calls':calls,'original_after':after,'new_restart':restart})

original=run('shared-stale-checkpoint');cp=original.checkpoint();resumed=Run(p,original.directory,original.run_id,resume=True)
original.perform(p.schedule[0],good);verified=capture(lambda:resumed.verify_resume(cp));calls=[];performed=capture(lambda:resumed.perform(p.schedule[0],track))
results.append({'id':'SHARED_STALE_CHECKPOINT_VERIFIED','stale_resume_verification':verified,'stale_resume_perform':performed,'transport_calls':calls,'after':state(resumed),'new_restart':capture(lambda:Run(p,original.directory,original.run_id,resume=True))})

r=run('cached-gold-drift');row=p.schedule[0];m=p.members[row['fixture_id']];saved=copy.deepcopy(m);field=next(iter(m['gold']));frozen=m['gold'][field];wrong=(date.fromisoformat(frozen)+timedelta(days=1)).isoformat();wire_before=p.wire(row)
m['gold'][field]=wrong;verified=capture(lambda:p.verify());performed=capture(lambda:r.perform(row,good))
results.append({'id':'CACHED_MEMBER_GOLD_DRIFT','frozen_gold':frozen,'mutated_cached_gold':wrong,'package_verify':verified,'wire_unchanged':p.wire(row)==wire_before,'perform':performed,'after':state(r)})
p.members[row['fixture_id']]=saved

# A caller does not need package access to mutate the exposed schedule-row reference.
r=run('callback-row-alias');row=p.schedule[0];savedrow=copy.deepcopy(row)
def mutate_callback(req,actual):
    result=good(req,actual)
    actual['seed']=0
    return result
performed=capture(lambda:r.perform(row,mutate_callback));cache_changed=p.schedule[0]['seed']==0
nextperformed=capture(lambda:r.perform(p.schedule[1],good));report=capture(lambda:r.final_report())
results.append({'id':'CALLBACK_ROW_ALIAS_MUTATION','first_perform':performed,'cached_schedule_seed_mutated':cache_changed,'next_perform':nextperformed,'final_report':report,'after':state(r),'binding_schedule_sha256':p.binding['schedule_sha256'],'cached_schedule_sha256':digest(canonical(p.schedule))})
p.schedule[0]=savedrow

(OUT/'shared_boundary_result.json').write_bytes(canonical({'cases':len(results),'results':results,'no_provider_calls':True,'repo_files_changed':False}))
for x in results:print(json.dumps(x),flush=True)
