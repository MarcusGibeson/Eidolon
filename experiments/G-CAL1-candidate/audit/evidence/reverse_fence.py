import sys,json,hashlib,subprocess
from pathlib import Path
ROOT=Path(r'C:\Users\marcu\Eidolon-g4adj');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
def hook(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.bind'):raise RuntimeError('AUDIT_NETWORK_DENIED')
sys.addaudithook(hook)
from g_cal1_contract import Package
from g_cal1_lab import Run as CalRun,transport_boundary
from g_extract1_runner import Run as OldRun
from g_extract1_contract import canonical,IntegrityError
from g_extract1_scoring import synthetic_gold
p=Package();results=[]
def git(*args):return subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),*args],cwd=ROOT)
before=git('status','--porcelain');protected={k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in p.pins}
class Fake:
    def __init__(self,package,mark,modern):
        self.package=package;self.modern=modern;self.calls=[]
        if mark!='UNMARKED':self.synthetic_only=mark
    def __call__(self,request,row):
        self.calls.append({'call_id':row['call_id'],'request_bytes':len(request)})
        member=self.package.members[row['fixture_id']] if self.modern else self.package.variants[row['rendered_variant_id']]
        receipt={'call_id':row['call_id'],'request_sha256':row['request_sha256']}
        if hasattr(self,'synthetic_only'):receipt['synthetic_only']=self.synthetic_only
        return {'raw_output':synthetic_gold(member),'provider_truncated':False,'receipt':receipt}
for modern in (True,False):
    for name,mark in [('explicit_false',False),('unmarked','UNMARKED'),('explicit_true',True)]:
        experiment='G-CAL1' if modern else 'G-EXTRACT1';directory=OUT/('reverse-fence-'+experiment+'-'+name)
        package=p if modern else p.historical
        run=(CalRun if modern else OldRun)(package,directory,'AUDIT-REVERSE-FENCE-'+experiment+'-'+name,mechanical=True)
        row=p.schedule[0] if modern else run.a[0];transport=Fake(package,mark,modern)
        exception=None
        try:
            score=run.perform(row,transport) if modern else run.perform(row,transport,package.receipts())
        except IntegrityError as e:exception={'event':e.event,'detail':e.detail}
        kinds=[r['payload'].get('kind',r['payload'].get('type')) for r in run.journal.read()]
        report=run.final_report() if modern and exception is None else None
        results.append({'experiment':experiment,'transport_label':name,'mechanical':True,'activation':None,'grant':None,'accepted':exception is None,'exception':exception,'local_counter':len(transport.calls),'START_records':sum(k=='START' for k in kinds),'COMPLETE_records':sum(k=='COMPLETE' for k in kinds),'report_mode':report['mode'] if report else None,'reported_provider_model_calls':report['provider_model_calls'] if report else None,'state':report['state'] if report else None})

live_checks=[]
for name,mark in [('explicit_false',False),('unmarked','UNMARKED'),('explicit_true',True)]:
    fake=Fake(p,mark,True);exception=None
    try:transport_boundary(fake,False)
    except IntegrityError as e:exception=e.event
    live_checks.append({'label':name,'live_boundary_accepted':exception is None,'event':exception,'counter':len(fake.calls),'scope':'boundary check only; no authority created and no callable invoked'})
out={'same_audit_addendum':True,'results':results,'live_direction_boundary_checks':live_checks,'real_provider_calls':0,'provider_modules_loaded':[x for x in sys.modules if x.split('.')[0] in ('ollama','openai','requests','httpx','aiohttp')],'protected_hashes_unchanged':protected=={k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in p.pins},'git_status_unchanged':before==git('status','--porcelain'),'HEAD':git('rev-parse','HEAD').decode().strip()}
path=OUT/'reverse_fence_result.json';path.write_bytes(canonical(out))
print(json.dumps(out,indent=2));print('RESULT_SHA256',hashlib.sha256(path.read_bytes()).hexdigest())
