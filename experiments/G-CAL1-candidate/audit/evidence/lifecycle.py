import sys,json,copy,hashlib
from pathlib import Path
from datetime import date,timedelta
ROOT=Path(r'C:\Users\marcu\Eidolon-g4adj');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
def hook(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.bind'):raise RuntimeError('AUDIT_NETWORK_DENIED')
sys.addaudithook(hook)
import g_cal1_contract as C
import g_cal1_lab as L
import g_cal1_pilot as P
from g_extract1_contract import IntegrityError,canonical,digest
from g_extract1_journal import Journal,write_once
from g_extract1_scoring import evaluate
p=C.Package();rows=[];reproductions=[];index=0
def check(ok,name,detail=None):
    rows.append({'test':name,'passed':bool(ok),'detail':detail})
    if not ok:print('FAILED',name,detail,flush=True)
def fresh():
    global index
    index+=1
    return L.Run(p,OUT/f'independent-{index:03d}',f'INDEPENDENT-{index:03d}')
def good(request,row):
    m=p.members[row['fixture_id']]
    return {'raw_output':json.dumps(m['gold'],separators=(',',':')),'provider_truncated':False,
            'receipt':{'call_id':row['call_id'],'request_sha256':row['request_sha256'],'synthetic_only':True}}
def reject(action,name):
    try:action()
    except IntegrityError as exc:
        check(True,name,exc.event);return exc.event
    except BaseException as exc:
        check(False,name,'unexpected:'+type(exc).__name__);return type(exc).__name__
    check(False,name,'accepted');return None
def terminal(run,name):
    nstart=sum(x['payload'].get('kind')=='START' for x in run.journal.read());calls=[]
    def forbidden(*a):calls.append(1);return good(*a)
    reject(lambda:run.perform(p.schedule[min(len(run.attempted),79)],forbidden),name+'_postcatch')
    reject(lambda:run.checkpoint(),name+'_checkpoint_after_catch')
    reject(lambda:run.final_report(),name+'_report_after_catch')
    check(not calls and nstart==sum(x['payload'].get('kind')=='START' for x in run.journal.read()),name+'_no_later_START_or_transport')
    check(bool(run.incidents.read()),name+'_durable_incident')
    reject(lambda:L.Run(p,run.directory,run.run_id,resume=True),name+'_restart_retention')

# Malformed sealed envelope and payload domains through genuine verify_resume.
envelopes=[None,[],0,False,'text',{}, {'payload':{}}, {'sha256':'0'*64}, {'payload':{},'sha256':'0'*64,'extra':0}, {'payload':{},'sha256':False}]
payloads=[None,[],0,True,'text',{}, {'journal_prefix':{}}, {'next_schedule_position':'1'}]
for value in envelopes+[{'payload':v,'sha256':digest(canonical(v))} for v in payloads]:
    r=fresh();cp=r.checkpoint();resume=L.Run(p,r.directory,r.run_id,resume=True);bad=r.directory/'malformed.json';write_once(bad,value)
    reject(lambda:resume.verify_resume(bad),'malformed_checkpoint_envelope_or_payload')
    reject(lambda:resume.verify_resume(cp),'checkpoint_original_cannot_untaint');terminal(resume,'checkpoint_invalidity')
for mode in ('bool_position','float_count','bad_prefix_hash','wrong_binding','bad_state_qualified','bad_event_scope','wrong_state_counter','wrong_schedule_digest'):
    r=fresh();cp=r.checkpoint();resume=L.Run(p,r.directory,r.run_id,resume=True);v=json.loads(cp.read_text());q=v['payload']
    if mode=='bool_position':q['next_schedule_position']=True
    if mode=='float_count':q['journal_prefix']['record_count']=1.0
    if mode=='bad_prefix_hash':q['journal_prefix']['last_sha256']='bad'
    if mode=='wrong_binding':q['frozen_binding']['experiment']='G-EXTRACT1'
    if mode=='bad_state_qualified':q['state']['qualified']=[None]
    if mode=='bad_event_scope':q['state']['event_scopes']=[{'event':'x','phase':'CAL','cell':False}]
    if mode=='wrong_state_counter':q['state']['completed_observations']=1
    if mode=='wrong_schedule_digest':q['schedule_sha256']='0'*64
    v['sha256']=digest(canonical(q));bad=r.directory/'malformed-domain.json';write_once(bad,v)
    reject(lambda:resume.verify_resume(bad),'checkpoint_'+mode);terminal(resume,'checkpoint_'+mode)
print('CHECKPOINT_ATTACKS_COMPLETE',len(rows),flush=True)

# Transport failures and control-flow exceptions must be retained before return.
class Control(BaseException):pass
for error in (RuntimeError('ordinary'),ValueError('ordinary'),OSError('ordinary'),KeyboardInterrupt('k'),SystemExit(7),GeneratorExit('g'),Control('c')):
    r=fresh();calls=[]
    def raised(*args,error=error):calls.append(1);raise error
    try:r.perform(p.schedule[0],raised)
    except BaseException as exc:
        check(isinstance(exc,IntegrityError) if isinstance(error,Exception) else exc is error,'transport_exception_propagation',type(error).__name__)
    check(len(calls)==1 and r.state()['verdict']=='INVALID','transport_exception_invalidity',type(error).__name__)
    terminal(r,'transport_'+type(error).__name__)
base=good(b'',p.schedule[0])
malformed=[None,[],False,0,'x',object(),{}, {'failure':None}, {'failure':'unknown','receipt':None}, {'failure':'timeout','receipt':{}}, {'raw_output':3}, {'raw_output':'{}'}, {'raw_output':'{}','provider_truncated':0,'receipt':base['receipt']}, dict(base,receipt=None), dict(base,receipt=[]), dict(base,receipt=dict(base['receipt'],call_id='other')),dict(base,receipt=dict(base['receipt'],request_sha256='0'*64)), dict(base,failure='timeout'),dict(base,receipt=dict(base['receipt'],extra=float('nan')))]
for result in malformed:
    r=fresh();reject(lambda:r.perform(p.schedule[0],lambda *_:result),'malformed_transport_result')
    check(r.state()['verdict']=='INVALID' and r.journal.read()[-1]['payload']['kind']=='FAILURE','malformed_transport_closed_failure')
    terminal(r,'malformed_transport')
for kind,event in [('timeout','PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT'),('error','PROVIDER_ERROR_WITH_FAILURE_RECEIPT'),('missing','MISSING_RESPONSE_WITH_FAILURE_RECEIPT')]:
    r=fresh();row=p.schedule[0];receipt={'call_id':row['call_id'],'request_sha256':row['request_sha256'],'failure_kind':kind}
    check(reject(lambda:r.perform(row,lambda *_:{'failure':kind,'receipt':receipt}),'valid_failure_'+kind)==event,'valid_failure_event')
    check(r.state()['verdict']=='INCOMPLETE','receipted_failure_not_INVALID');terminal(r,'receipted_failure')
print('TRANSPORT_ATTACKS_COMPLETE',len(rows),flush=True)

# Schedule record mutations, unverified resumes, original sealed replay.
for key,value in [('schedule_position',2),('seed',0),('model','other'),('provider_version','other'),('generation_configuration',{}),('request_sha256','0'*64),('fixture_id','other'),('repeat',2),('phase','A'),('call_id','other')]:
    r=fresh();row=copy.deepcopy(p.schedule[0]);row[key]=value
    reject(lambda:r.perform(row,good),'schedule_row_'+key);terminal(r,'schedule_'+key)
for method in ('perform','checkpoint','final_report'):
    r=fresh();cp=r.checkpoint();res=L.Run(p,r.directory,r.run_id,resume=True)
    reject(lambda:(res.perform(p.schedule[0],good) if method=='perform' else getattr(res,method)()),'unverified_resume_'+method);terminal(res,'unverified_'+method)
r=fresh();r.perform(p.schedule[0],good);cp=r.checkpoint();res=L.Run(p,r.directory,r.run_id,resume=True);res.verify_resume(cp);res.perform(p.schedule[1],good);cp2=res.checkpoint();res2=L.Run(p,r.directory,r.run_id,resume=True);res2.verify_resume(cp2)
check(len(res2.evidence)==2 and not res2.events and res2.state()['verdict']=='RUNNING','valid_sealed_checkpoint_replay')
reject(lambda:res2.perform(p.schedule[0],good),'already_consumed_call');terminal(res2,'retry_invalidity')

# Inactive authority is tested without manufacturing any active authority.
for authorization in (None,{'status':'EXECUTION_FREEZE_CANDIDATE_ONLY'}, {'experiment':'G-EXTRACT1','phase':'A'}, {'experiment':'G-CAL1','phase':'CAL'}):
    reject(lambda:L.authority(p,'NOT-LIVE',None,authorization,None),'inactive_authority')
    target=OUT/('inactive-'+str(len(rows)))
    reject(lambda:L.Run(p,target,'NOT-LIVE',mechanical=False,authorization=authorization),'inactive_live_constructor')
    check(not target.exists(),'authority_denial_before_directory_creation')
for marked in ('unmarked',True,None,0,'false'):
    def f(*a):raise AssertionError('never invoke')
    if marked!='unmarked':f.synthetic_only=marked
    reject(lambda:L.transport_boundary(f,False),'live_transport_boundary_'+str(marked))
def allowed(*a):raise AssertionError('never invoke')
allowed.synthetic_only=False
L.transport_boundary(allowed,False);check(True,'explicit_nonsynthetic_boundary_only_no_invocation')
for mode in (None,0,1,'false'):
    reject(lambda:L.transport_boundary(allowed,mode),'nonBoolean_mode')
print('AUTHORITY_SCHEDULE_ATTACKS_COMPLETE',len(rows),flush=True)

# Independently score every fixture under eleven raw/schema conditions.
scoring_count=0
for m in p.members.values():
    field=next(iter(m['gold']));gold=m['gold'][field];wrong=(date.fromisoformat(gold)+timedelta(days=1)).isoformat()
    cases=[('gold',json.dumps({field:gold}),False,True),('wrong',json.dumps({field:wrong}),False,False),('truncated_gold',json.dumps({field:gold}),True,False),('empty','',False,False),('syntax','not JSON',False,False),('nonobject','[]',False,False),('wrongtype',json.dumps({field:3}),False,False),('invaliddate',json.dumps({field:'2025-02-30'}),False,False),('missing','{}',False,False),('extra',json.dumps({field:gold,'extra':'x'}),False,False),('duplicate','{"%s":"%s","%s":"%s"}'%(field,gold,field,gold),False,False)]
    for name,raw,truncated,correct in cases:
        score=evaluate(m,raw,truncated=truncated);scoring_count+=1
        check(score['semantic_correct']==correct,'scorer_'+name,m['fixture_id'])
        if name in ('wrong','truncated_gold'):check(score['false_clean'] and score['structural_valid'],'scorer_falseclean_separate_'+name)
        if name=='wrong':check('OFF_BY_ONE_DAY' in C.diagnosis(m,raw,score)['categories'],'diagnostic_noncausal_offbyone')
        if name=='duplicate':check(score['duplicate_key_present'],'duplicate_key_detected')
ev={}
for row in p.schedule:
    m=p.members[row['fixture_id']];field=next(iter(m['gold']));gold=m['gold'][field]
    if row['stratum']=='C2' and m['slot']<=4 and row['repeat']==1:gold=(date.fromisoformat(gold)+timedelta(days=1)).isoformat()
    if row['stratum']=='C3' and m['slot']<=3:gold=(date.fromisoformat(gold)+timedelta(days=1)).isoformat()
    raw=json.dumps({field:gold});ev[row['call_id']]=evaluate(m,raw)
summary=C.summarize(p,ev)
check(summary['strata']['C2']['both_repeat_correct']==6 and summary['strata']['C2']['false_clean_fixtures']==4 and summary['strata']['C2']['correlated_false_clean_pairs']==0 and summary['strata']['C2']['repeat_correctness_disagreement']==4,'one_repeat_failure_reduction')
check(summary['strata']['C3']['both_repeat_correct']==7 and summary['strata']['C3']['false_clean_fixtures']==3 and summary['strata']['C3']['correlated_false_clean_pairs']==3,'both_repeat_failure_reduction')
check(summary['contrasts']=={'control_minus_boundary_fixture_accuracy':{'numerator':7,'denominator':30},'boundary_minus_control_false_clean_observation_rate':{'numerator':1,'denominator':6},'boundary_minus_control_false_clean_fixture_rate':{'numerator':7,'denominator':30}} and summary['qualification_gates'] is None and summary['interpretation']=='DESCRIPTIVE_CALENDAR_DIAGNOSTIC','exact_descriptive_contrasts')
ev.pop(p.schedule[0]['call_id']);incomplete=C.summarize(p,ev)
check(incomplete['contrasts'] is None and incomplete['interpretation'] is None and set(incomplete['strata'])=={'C1','C2','C3','C4'},'incomplete_all_strata_no_contrasts')

# Genuine post-return validation failure with a non-plain nested receipt value.
for signal in (KeyboardInterrupt('receipt'),SystemExit(17),GeneratorExit('receipt'),Control('receipt')):
    class BadList(list):
        def __iter__(self):raise signal
    r=fresh();row=p.schedule[0];result=good(b'',row);result['receipt']['bad']=BadList([1]);thrown=None
    try:r.perform(row,lambda *_:result)
    except BaseException as exc:thrown=type(exc).__name__
    initial={'exception':thrown,'state':r.state(),'incidents':len(r.incidents.read()),'journal_kinds':[x['payload']['kind'] for x in r.journal.read()]}
    nextcalls=[]
    def later(req,rr):nextcalls.append(rr['call_id']);return good(req,rr)
    later_error=None
    try:r.perform(p.schedule[1],later)
    except BaseException as exc:later_error=type(exc).__name__
    observed={'signal':type(signal).__name__,'initial':initial,'later_transport_calls':nextcalls,'later_error':later_error,'later_journal_kinds':[x['payload']['kind'] for x in r.journal.read()]}
    reproductions.append({'id':'POST_RETURN_BASEEXCEPTION','detail':observed})
    print('POST_RETURN_REPRODUCTION',json.dumps(observed),flush=True)

# Actual in-memory frozen schedule mutation; no repository byte mutation.
r=fresh();original=copy.deepcopy(p.schedule[0]);mutated=copy.deepcopy(original);mutated['seed']=0;mutated['request_sha256']=digest(p.wire(mutated));p.schedule[0]=mutated;calls=[]
try:
    try:
        r.perform(mutated,lambda req,rr:(calls.append(json.loads(req)['options']['seed']) or good(req,rr)))
        observed={'accepted':True,'seed_received':calls,'state':r.state(),'frozen_binding_schedule_sha256':p.binding['schedule_sha256'],'runtime_schedule_sha256':digest(canonical(p.schedule))}
    except BaseException as exc:observed={'accepted':False,'error':str(exc),'seed_received':calls}
finally:p.schedule[0]=original
reproductions.append({'id':'IN_MEMORY_SCHEDULE_MUTATION','detail':observed});print('SCHEDULE_MUTATION_REPRODUCTION',json.dumps(observed),flush=True)

# Fresh external copies only: complete runner, checkpoint, replay, tree equality.
ch=P.Checks()
for name in ('external_pilot_one','external_pilot_two'):
    P.full_pilot(p,OUT/name,ch)
    check(P.tree(OUT/name)==P.tree(C.DATA/'preexecution/final/pilot_one'),'external_full_pilot_matches_frozen_tree',name)
check(P.tree(OUT/'external_pilot_one')==P.tree(OUT/'external_pilot_two'),'external_full_pilots_identical')
check(all(x['passed'] for x in ch.rows),'external_full_pilot_function_checks',len(ch.rows))
out={'independent_checks':len(rows),'failures':[x for x in rows if not x['passed']],'transport_attack_cases':26,'checkpoint_attack_cases':26,'scorer_cases':scoring_count,'full_synthetic_pilots':2,'synthetic_observations':160,'full_pilot_function_checks':len(ch.rows),'reproductions':reproductions,'checks':rows}
(OUT/'lifecycle_result.json').write_bytes(canonical(out))
print('LIFECYCLE_COMPLETE',json.dumps({k:v for k,v in out.items() if k not in ('checks','reproductions')}),flush=True)
