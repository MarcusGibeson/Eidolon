import sys,json,subprocess,hashlib,random,re
from pathlib import Path
from datetime import date,timedelta
from decimal import Decimal
ROOT=Path(r'C:\Users\marcu\Eidolon-g4adj');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import g_cal1_contract as C
import g_cal1_stage as S
from g_extract1_contract import canonical,digest
p=C.Package();checks=[]
def ck(ok,name,data=None):
    checks.append({'test':name,'passed':bool(ok),'detail':data})
    if not ok:print('FAILED',name,data,flush=True)
def git(*args):
    return subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),*args],cwd=ROOT)
tracked=set(git('ls-files','-z').decode().split('\0'));direct=0;conversion=[];untracked=[]
for rel,h in p.pins.items():
    if rel not in tracked:untracked.append(rel);continue
    blob=git('show','HEAD:'+rel);actual=(ROOT/rel).read_bytes()
    if blob==actual:direct+=1
    else:
        ok=blob.replace(b'\n',b'\r\n')==actual
        conversion.append({'path':rel,'git_sha256':digest(blob),'checkout_sha256':h,'LF_to_CRLF_only':ok})
        ck(ok,'legacy_git_newline_conversion_only',rel)
ck(all(not x['path'].startswith(('tools/g_cal1_','experiments/G-CAL1-candidate/')) for x in conversion),'all_current_GCAL_source_bytes_equal_git')
primary,ind=S.old_checkers();hist,pins,hs,hg,counts=S.history_records(p.historical,primary,ind)
byid={h['id']:h for h in hist};legacy=0;currency=0;exactnumeric=0
tags={'string':'STRING','number':'NUMBER','integer':'INTEGER','boolean':'BOOLEAN','YYYY-MM-DD':'DATE','HH:MM':'TIME'}
for folder,corpus,gold in [('G-ROUTE1-candidate','corpus.json','gold.json'),('G-ROUTE3-candidate','corpus_a.json','gold_a.json'),('G-ROUTE3-candidate','corpus_b.json','gold_b.json'),*[('G-ROUTE4-candidate/sealed',a,b) for a,b in [('corpus_a.json','gold_a.json'),('corpus_b.json','gold_b.json'),('reserve_corpus_a.json','reserve_gold_a.json'),('reserve_corpus_b.json','reserve_gold_b.json')]]]:
    d=ROOT/'experiments'/folder;golddata=json.loads((d/gold).read_bytes(),parse_float=Decimal);expected={x['fixture_id']:x['expected'] for x in golddata['items']}
    for f in json.loads((d/corpus).read_bytes())['fixtures']:
        if f['task_class']!='structured_extraction':continue
        schema=f['input']['schema'];g=expected[f['fixture_id']];rows=[]
        for k in sorted(schema,key=lambda x:x.encode()):
            s=schema[k];v=g[k];tag=tags.get(s,'ENUM')
            if tag=='ENUM':
                ck(type(v) is str and v in s.split('|'),'legacy_actual_enum',s)
                if any(x in s.split('|') for x in ('EUR','USD','GBP')):currency+=1
            if tag=='BOOLEAN':v='true' if v else 'false'
            if tag in ('INTEGER','NUMBER'):
                ck(not isinstance(v,float),'legacy_no_binary_float');v=format(Decimal(str(v)),'f')
                if '.' in v:v=v.rstrip('0').rstrip('.')
                if Decimal(v)==0:v='0'
                exactnumeric+=1
            rows.append([k,s,[tag,v]])
        independent=json.dumps(rows,ensure_ascii=True,separators=(',',':')).encode()
        h=byid[folder+'/'+corpus+'/'+f['fixture_id']]
        ck(independent==h['answer'],'independent_legacy_whole_answer',h['id']);legacy+=1
members=list(p.members.values());allreq={canonical(h['request']) for h in hist}
for m in members:ck(canonical(m['request']) not in allreq,'complete_historical_request_freshness',m['fixture_id'])

# Reconstruct every deterministic search attempt from independent RNG logic.
def candidate(st,slot,n):
    fid=f'G-CAL1-{st}-{slot:02d}';rng=random.Random(int(hashlib.sha256(f'G-CAL1/{fid}/{n}'.encode()).hexdigest(),16));year=rng.randint(2051,2099)
    if st=='C1':return date(year,p.design['allocation'][st]['months'][slot-1],rng.randint(1,28)).isoformat()
    if st=='C2':return date(year,12 if slot<=5 else 1,rng.randint(19,31) if slot<=5 else rng.randint(1,12)).isoformat()
    if st=='C3':
        leap=lambda y:(y%4==0 and y%100!=0) or y%400==0
        if slot in (6,7):year=rng.choice(p.design['allocation'][st]['century_common_year_pool'])
        elif slot in (8,9):year=rng.choice(p.design['allocation'][st]['century_leap_year_pool'])
        elif slot in (1,2,3,10):year=rng.choice([y for y in range(2051,2100) if leap(y)])
        else:year=rng.choice([y for y in range(2051,2100) if not leap(y)])
        md=[(2,28),(2,29),(3,1),(2,28),(3,1),(2,28),(3,1),(2,28),(3,1),(2,29)][slot-1]
        return date(year,*md).isoformat()
    return date(year,rng.randint(1,12),rng.randint(1,28)).isoformat()
attempts=json.loads((C.DATA/'corpus/AUTHORING_ATTEMPTS.json').read_text())['attempts'];useds=set(hs);usedg=set(hg);accepted=[]
for row in attempts:
    st,slottext=row['fixture_id'].rsplit('-',2)[1:];slot=int(slottext);source=candidate(st,slot,row['attempt']);off=p.design['allocation'][st]['offsets'][slot-1];gold=(date.fromisoformat(source)+timedelta(days=off)).isoformat()
    ck((source,off,gold)==(row['source_date'],row['offset'],row['gold']),'deterministic_authoring_attempt',row['fixture_id']+'/'+str(row['attempt']))
    reason=None
    if not C.allocation_ok(p.design,st,slot,source,off):reason='allocation'
    if reason is None and source in useds|usedg:reason='source_date_reuse'
    if reason is None and gold in useds|usedg:reason='answer_date_reuse'
    if reason is None:
        m=C.make_member(p.design,p.baseline,st,slot,source);ev=S.evidence(m,p.historical.design,primary,ind)
        for h in hist:
            r=S.historical_rejection(ev,h)
            if r:reason=r+':'+h['id'];break
    ck(reason==row['reason'] and row['decision']==('ACCEPT' if reason is None else 'REJECT'),'authoring_rejection_retained',row['fixture_id'])
    if reason is None:useds.add(source);usedg.add(gold);accepted.append(m)
ck(accepted==members and len(accepted)==40,'authoring_replay_matches_frozen_corpus')

# Protected-byte drift fault injection is memory-only and restores the function.
from g_cal1_lab import Run
from g_extract1_contract import IntegrityError
fault=[]
for contacted in (False,True):
    d=OUT/('manifest-drift-post' if contacted else 'manifest-drift-pre');r=Run(p,d,'DRIFT-'+str(contacted))
    def good(req,row):return {'raw_output':json.dumps(p.members[row['fixture_id']]['gold']),'provider_truncated':False,'receipt':{'call_id':row['call_id'],'request_sha256':row['request_sha256'],'synthetic_only':True}}
    if contacted:r.perform(p.schedule[0],good)
    original=C.file_digest;target=next(iter(p.pins));C.file_digest=lambda path:('0'*64 if Path(path)==ROOT/target else original(path));calls=[]
    try:
        try:r.perform(p.schedule[int(contacted)],lambda *a:(calls.append(1) or good(*a)))
        except IntegrityError as e:event=e.event
        else:event=None
    finally:C.file_digest=original
    expected='PROTECTED_ARTIFACT_DIGEST_MISMATCH' if contacted else 'PRE_ARTIFACT_DIGEST_MISMATCH'
    ck(event==expected and not calls and bool(r.incidents.read()),'actual_runner_protected_byte_drift',event)
    fault.append({'contacted':contacted,'event':event,'state':r.state()})

result={'checks':len(checks),'failures':[x for x in checks if not x['passed']],'git':{'direct_blob_matches':direct,'legacy_newline_only':len(conversion),'untracked_protected':len(untracked),'conversion_rows':conversion},'legacy_answers':legacy,'uppercase_currency_fields':currency,'exact_numeric_fields':exactnumeric,'authoring_attempts':len(attempts),'authoring_accepts':len(accepted),'authoring_rejects':len(attempts)-len(accepted),'manifest_drift':fault}
(OUT/'finish_result.json').write_bytes(canonical(result));print('FINISH_CHECKS_COMPLETE',json.dumps({k:v for k,v in result.items() if k!='git'}),flush=True)

before=json.loads((OUT/'before.json').read_text());after={q.relative_to(ROOT).as_posix():hashlib.sha256(q.read_bytes()).hexdigest() for q in ROOT.rglob('*') if q.is_file() and '.git' not in q.parts}
changes=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
check={'repo_file_count_before':len(before),'repo_file_count_after':len(after),'repo_byte_changes':changes,'git_status_unchanged':git('status','--porcelain').decode()==''.join('?? '+x+'\n' for x in sorted(untracked)),'HEAD':git('rev-parse','HEAD').decode().strip(),'branch':git('branch','--show-current').decode().strip(),'provider_modules_loaded':[x for x in sys.modules if x.split('.')[0] in ('ollama','openai','requests','httpx','aiohttp')],'provider_calls':0,'repo_edits':0}
(OUT/'readonly_result.json').write_bytes(canonical(check));print('READONLY_COMPLETE',json.dumps(check),flush=True)
