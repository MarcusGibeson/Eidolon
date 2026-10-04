import sys, os, json, hashlib, subprocess, re, unicodedata, copy, random
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from itertools import combinations

ROOT = Path(r'C:\Users\marcu\Eidolon-g4adj')
OUT = Path(__file__).resolve().parent
HEAD = 'dbea3241abb8e798b62783b7135b74967db924ea'
BASE = '1757155387af122d126f6db9fd03477e2823c2bb'
sys.path.insert(0, str(ROOT/'tools'))
def audit_hook(event, args):
    if event in ('socket.connect','socket.getaddrinfo','socket.bind'):
        raise RuntimeError('NETWORK_FORBIDDEN_BY_AUDIT')
sys.addaudithook(audit_hook)
import g_cal1_contract as C
import g_cal1_lab as L
import g_cal1_stage as S
import g_cal1_pilot as P
from g_extract1_contract import IntegrityError
from g_extract1_journal import Journal, write_once, verify_checkpoint, SCHEMA
from g_extract1_scoring import evaluate, synthetic_gold

def enc(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',',':'),allow_nan=False).encode()
def sha(x): return hashlib.sha256(x).hexdigest()
def fh(p): return sha(Path(p).read_bytes())
def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise ValueError('duplicate key:'+k)
        d[k]=v
    return d
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'),object_pairs_hook=unique,parse_float=Decimal)
def plain(p): return json.loads(Path(p).read_text(encoding='utf-8'),object_pairs_hook=unique)
def git(*args):
    r=subprocess.run(['git','-c','safe.directory='+ROOT.as_posix(),*args],cwd=ROOT,capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode(errors='replace'))
    return r.stdout
checks=[]; findings=[]; detail={}
def ck(ok, name, data=None):
    checks.append({'test':name,'passed':bool(ok),'detail':data})
    if not ok: print('FAILED',name,data,flush=True)
def tree(p): return {x.relative_to(p).as_posix():fh(x) for x in sorted(p.rglob('*')) if x.is_file()}
def snapshot():
    return {p.relative_to(ROOT).as_posix():fh(p) for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts}
before=snapshot()
(OUT/'before.json').write_bytes(enc(before))
ck(git('rev-parse','HEAD').decode().strip()==HEAD,'HEAD')
ck(git('branch','--show-current').decode().strip()=='g-extract1/design','branch')
status=git('status','--porcelain').decode()
p=C.Package(); DATA=C.DATA; design=p.design; hc=p.historical.design
for rel,h in p.pins.items(): ck(fh(ROOT/rel)==h,'manifest_actual_bytes',rel)
tracked=set(git('ls-files','-z').decode().split('\0'))
git_pins=0; untracked_pins=[]
for rel,h in p.pins.items():
    if rel in tracked:
        ck(sha(git('show',HEAD+':'+rel))==h,'pin_vs_git',rel);git_pins+=1
    else: untracked_pins.append(rel)
candidate=plain(DATA/'preexecution/final/EXECUTION_FREEZE_CANDIDATE.json')
ck(fh(DATA/'preexecution/final/EXECUTION_FREEZE_CANDIDATE.json')=='f036f3380d51dd80d627d2e641ad7e40a123d2ae23d4d472588c3732e61f0692','current_candidate_identity')
ck(candidate['protected_artifacts']==p.pins and candidate['binding']==p.binding,'candidate_bindings')
ck(candidate['schedule']=={'count':80,'sha256':sha(enc(p.schedule))},'candidate_schedule')
ck(candidate['journal_checkpoint_schema']==SCHEMA and candidate['journal_checkpoint_schema_sha256']==sha(enc(SCHEMA)),'candidate_schema')
for name,key in [('PILOT_REPORT.json','pilot_report_sha256'),('PRESERVATION_REPORT.json','preservation_report_sha256')]:
    ck(fh(DATA/'preexecution/final'/name)==candidate[key],'candidate_report_hash',name)
ck(candidate['activated'] is False and candidate['execution_authorized'] is False and candidate['status']=='EXECUTION_FREEZE_CANDIDATE_ONLY','candidate_inactive')
ck(not (DATA/'execution/ACTIVE_FREEZE.json').exists(),'no_GCAL_active_pointer')
ck(fh(DATA/'preexecution/EXECUTION_FREEZE_CANDIDATE.json')==candidate['supersedes_unactivated_initial_candidate_sha256'],'superseded_draft_identity')
pres=plain(DATA/'preexecution/final/PRESERVATION_REPORT.json')
ck(pres['before']==pres['after']==plain(DATA/'PRESERVATION_BEFORE.json'),'preservation_sets')
for rel,h in pres['after'].items(): ck(fh(ROOT/rel)==h,'preservation_actual_bytes',rel)
ck(S.preservation_snapshot()==pres['after'],'preservation_coverage_actual_set')
changed=git('diff','--name-only',BASE,HEAD).decode().splitlines()
ck(all(x=='.gitattributes' or x.startswith('experiments/G-CAL1-candidate/') or x.startswith('tools/g_cal1_') for x in changed),'historical_git_preservation')
protected_old=[x for x in tracked if x.startswith(('experiments/G-EXTRACT1-candidate/','experiments/G-ROUTE4-candidate/'))]
ck(git('diff','--name-only',BASE,HEAD,'--','experiments/G-EXTRACT1-candidate','experiments/G-ROUTE4-candidate')==b'','old_science_closure_execution_git_unchanged',len(protected_old))
detail['pins']={'protected':len(p.pins),'git_byte_verified':git_pins,'untracked_protected':untracked_pins,'preservation_files':len(pres['after']),'old_tracked_files_unchanged':len(protected_old)}

# Third arithmetic path: component-only signed Gregorian stepping.
def independent_date(text,n):
    y,m,d=map(int,text.split('-'))
    def days(y,m):
        return [31,28+int((y%4==0 and y%100!=0) or y%400==0),31,30,31,30,31,31,30,31,30,31][m-1]
    for _ in range(abs(n)):
        if n>0:
            if d<days(y,m): d+=1
            else:
                d=1;m+=1
                if m>12: y+=1;m=1
        else:
            if d>1: d-=1
            else:
                m-=1
                if m<1:y-=1;m=12
                d=days(y,m)
    return '%04d-%02d-%02d'%(y,m,d)
members=list(p.members.values()); goldrows=plain(DATA/'corpus/GOLD_DERIVATION_REPORT.json')['rows']
sources=set();golds=set();signed=set();cases=set();requests=set()
for m in members:
    s,o=m['source_date'],m['offset']; g=next(iter(m['gold'].values())); sd=date.fromisoformat(s);gd=date.fromisoformat(g)
    ck(g==independent_date(s,o)==(sd+timedelta(days=o)).isoformat()==C.manual_date(s,o),'independent_gold',m['fixture_id'])
    r=next(x for x in goldrows if x['fixture_id']==m['fixture_id'])
    ck(r['primary']==r['independent']==g,'gold_report',m['fixture_id'])
    st=m['stratum'];slot=m['slot'];a=design['allocation'][st]
    valid=type(o) is int and o!=0 and abs(o)<=367 and a['offsets'][slot-1]==o
    if st=='C1':valid &= (sd.year,sd.month)==(gd.year,gd.month) and sd.month==a['months'][slot-1]
    if st=='C2':valid &= ((sd.month,gd.month,gd.year-sd.year)==((12,1,1) if o>0 else (1,12,-1)))
    if st=='C3':
        md=[(2,28),(2,29),(3,1),(2,28),(3,1),(2,28),(3,1),(2,28),(3,1),(2,29)][slot-1]
        ly=(sd.year%4==0 and sd.year%100!=0) or sd.year%400==0
        valid &= (sd.month,sd.day)==md
        valid &= (sd.year in a['century_common_year_pool'] if slot in (6,7) else sd.year in a['century_leap_year_pool'] if slot in (8,9) else ly if slot in (1,2,3,10) else not ly)
    if st=='C4':
        walk=[sd+timedelta(days=i*(1 if o>0 else -1)) for i in range(abs(o)+1)]
        valid &= sd.year!=gd.year and any(x.month==2 and x.day==29 for x in walk)==a['path_contains_feb29'][slot-1]
    if st!='C3' or slot not in (6,7,8,9):valid &= 2051<=sd.year<=2099
    ck(valid,'independent_allocation',m['fixture_id'])
    ck(m['ordinal']==4*(slot-1)+int(st[1]),'ordinal',m['fixture_id'])
    sources.add(s);golds.add(g);signed.add((s,o));cases.add((s,o,g));requests.add(enc(m['request']))
ck(len(members)==len(sources)==len(golds)==len(signed)==len(cases)==len(requests)==40 and sources.isdisjoint(golds),'new_freshness_distinctness')
for st in ('C1','C2','C3','C4'):
    ms=[m for m in members if m['stratum']==st]
    ck(len(ms)==10 and sum(m['offset']>0 for m in ms)==5,'independent_stratum_balance',st)
for y in range(2001,2401):
    for md in ('02-28','03-01','12-31'):
        for o in (-367,-366,-365,-2,-1,0,1,2,365,366,367):
            s=f'{y:04d}-{md}'
            ck(independent_date(s,o)==C.manual_date(s,o)==C.primary_date(s,o),'400_year_gold_reference')
config={'temperature':0.45,'top_p':0.9,'top_k':40,'repeat_penalty':1.1,'num_ctx':8192,'num_predict':350,'stream':False,'think':False,'fallback':False,'retry_limit':0,'repair_calls':0,'fresh_session_per_call':True}
ck(design['generation_configuration']==config==p.historical.receipts()['generation_configuration'],'exact_historical_configuration')
ck(candidate['provider_binding']==dict(p.historical.receipts(),models=[p.historical.receipts()['models'][2]]),'exact_provider_binding')
wiremanifest=plain(DATA/'schedule/REQUEST_MANIFEST.json')['wire_requests']
expected=[]
for repeat in (1,2):
    ordered=sorted(members,key=lambda m:(sha(f'G-CAL1/order/{repeat}/{m["fixture_id"]}'.encode()),m['fixture_id']))
    for m in ordered:expected.append((m['fixture_id'],repeat,820000+10*m['ordinal']+repeat))
for row,(fid,rep,seed),wm in zip(p.schedule,expected,wiremanifest):
    m=p.members[fid]; ordinal=m['ordinal'];out=f'd{ordinal:03d}_01';field=f'f{ordinal:03d}_01';code=f'f{ordinal:03d}_02'
    subject=f'Extract the record record. {out} is {field} plus {m["offset"]} calendar days'
    prompt=p.baseline['structured_extraction_assembled_template'].replace('{SUBJECT}',subject)
    inp={'schema':{out:'YYYY-MM-DD'},'text':f'{field} is {m["source_date"]}. {code} is "code_{ordinal:03d}_99".'}
    body={'model':'qwen3.8:27b','system':p.baseline['system_text'],'prompt':prompt+'\n\nINPUT:\n'+enc(inp).decode(),'stream':False,'think':False,'options':{k:config[k] for k in ('temperature','top_p','top_k','repeat_penalty','num_ctx','num_predict')}}
    body['options']['seed']=seed
    ck((row['fixture_id'],row['repeat'],row['seed'])==(fid,rep,seed) and row['schedule_position']==len([x for x in p.schedule if x['schedule_position']<row['schedule_position']])+1,'independent_schedule_row')
    ck(m['request']=={'prompt':prompt,'input':inp} and body==wm['body'] and enc(body)==p.wire(row) and sha(enc(body))==row['request_sha256']==wm['sha256'] and wm['call_id']==row['call_id'],'independent_wire_bytes')
    ck(next(iter(m['gold'].values())) not in enc(body).decode() and not re.search(r'G-CAL1|WITHIN_MONTH|YEAR_BOUNDARY|LEAP_BOUNDARY|LONG_YEAR_OFFSET|gold|difficulty',enc(body).decode()),'no_gold_or_labels')
ck(len(p.schedule)==len(wiremanifest)==len({r['call_id'] for r in p.schedule})==len({r['seed'] for r in p.schedule})==80,'schedule_80')
ck(plain(DATA/'schedule/SCHEDULE.json')['schedule_sha256']==sha(enc(p.schedule))==p.manifest['schedule_sha256'],'schedule_hash')
detail['science']={'fixtures':40,'gold_agreement':40,'strata':{s:{'fixtures':10,'positive':5,'negative':5,'observations':20} for s in ('C1','C2','C3','C4')},'gold_cycle_vectors':13200,'wire_requests':80}
print('STATIC_SCIENCE_COMPLETE',len(checks),flush=True)

# Independently implement accepted normalization, ordinal masking, projection and pair decisions.
def normal(s):return ' '.join(unicodedata.normalize('NFC',s.replace('\r\n','\n').replace('\r','\n')).casefold().split())
tokenpat=hc['contamination_contract']['tokenizer']['pattern']
def payload(req,new):
    schema=req['input']['schema'];text=req['input']['text']+'\n'+'\n'.join(k+'='+schema[k] for k in sorted(schema,key=lambda x:x.encode()))
    text=normal(text)
    if new:
        spec=hc['ordinal_neutral_similarity_contract']
        for row in spec['replacements']:text=re.sub(row['pattern'].replace('{ORDINAL}',spec['ordinal_pattern']),row['replacement'],text,flags=re.ASCII)
    return text
def grams(req,new,view='ordinary'):
    ts=re.findall(tokenpat,payload(req,new),re.ASCII)
    pattern=hc['ordinal_neutral_similarity_contract']['shape_view']['value_token_regex'] if view=='shape' else hc['ordinal_neutral_similarity_contract']['declared_template_content_view']['content_value_regex']
    mask=[bool(re.fullmatch(pattern,x,re.ASCII)) for x in ts]
    if view=='shape':ts=['value' if mark else t for mark,t in zip(mask,ts)]
    return {tuple(ts[i:i+5]) for i in range(len(ts)-4) if view!='content' or any(mask[i:i+5])}
tags={'string':'STRING','integer':'INTEGER','number':'NUMBER','boolean':'BOOLEAN','YYYY-MM-DD':'DATE','HH:MM':'TIME'}
def projection(req,older=False):
    schema=req['input']['schema'];sig=[]
    for s in schema.values():
        if s in tags:sig.append([tags[s],0])
        else:
            opts=s.split('|');assert len(opts)>=2 and len(opts)==len(set(opts)) and all(re.fullmatch('[A-Za-z][A-Za-z0-9_]*',x) for x in opts)
            sig.append(['ENUM',len(opts)])
    sig.sort(key=lambda x:json.dumps(x,separators=(',',':')).encode())
    adapter=hc['historical_fingerprint_adapter_contract'];kinds=[]
    for t in re.findall(tokenpat,normal(req['input']['text']),re.ASCII):
        kinds.append(next((tag for tag in ('DATE','TIME','NUMBER') if re.fullmatch(adapter['source_kind_regex'][tag],t,re.ASCII)),'IDENTIFIER'))
    if older:subject=req['prompt'].split('. Copy names',1)[0]
    else:
        suffix=p.baseline['structured_extraction_assembled_template'].replace('{SUBJECT}','');assert req['prompt'].endswith(suffix)
        subject=req['prompt'][:-len(suffix)]
    catalog=adapter['surface_catalog'];pat='|'.join('(?P<X%d>%s)'%(i,r['regex']) for i,r in enumerate(catalog))
    surfaces=[catalog[int(m.lastgroup[1:])]['id'] for m in re.finditer(pat,normal(subject),re.ASCII)]
    return [sig,kinds,surfaces]
def answer(schema,values):
    rows=[]
    for k in sorted(schema,key=lambda x:x.encode()):
        s= schema[k];v=values[k];tag=tags.get(s,'ENUM')
        if tag=='ENUM':assert type(v) is str and v in s.split('|')
        if tag=='BOOLEAN':v='true' if v else 'false'
        if tag in ('INTEGER','NUMBER'):
            assert not isinstance(v,float)
            exact=Decimal(str(v));v=format(exact,'f')
            if '.' in v:v=v.rstrip('0').rstrip('.')
            if Decimal(v)==0:v='0'
        rows.append([k,s,[tag,v]])
    return json.dumps(rows,ensure_ascii=True,separators=(',',':')).encode()
primary,ind=S.old_checkers()
hist,pins,hs,hg,hcounts=S.history_records(p.historical,primary,ind)
ck(hcounts=={'G-ROUTE1-candidate':4,'G-ROUTE3-candidate':16,'G-ROUTE4-candidate':106,'G-EXTRACT1-candidate':192},'historical_selection_counts',hcounts)
for h in hist:
    legacy=not h['id'].startswith('G-EXTRACT1/')
    req=h['request'];older=h['id'].startswith(('G-ROUTE1','G-ROUTE3'))
    ck(h['projection']==projection(req,older) and h['ordinary']==grams(req,not legacy),'independent_historical_encoding',h['id'])
    if not legacy:
        m=p.historical.variants[h['id'].split('/',1)[1]]
        ck(h['answer']==answer(req['input']['schema'],m['gold']),'independent_typed_answer',h['id'])
new=[]
for m in members:
    ev=S.evidence(m,hc,primary,ind)
    ck(ev['projection']==projection(m['request']) and all(ev[v]==grams(m['request'],True,v) for v in ('ordinary','shape','content')),'independent_new_encoding',m['fixture_id'])
    ck(ev['answer']==answer(m['request']['input']['schema'],m['gold']),'independent_new_answer')
    ck(m['source_date'] not in hs|hg and next(iter(m['gold'].values())) not in hs|hg,'historical_date_freshness',m['fixture_id'])
    new.append(ev)
report=plain(DATA/'corpus/CONTAMINATION_REPORT.json');rows=report['historical_pairs'];j=0;maxj=Fraction(0);maxnear=Fraction(0);pmatches={0:0,1:0,2:0,3:0}
for a in new:
    for h in hist:
        i=len(a['ordinary']&h['ordinary']);u=len(a['ordinary']|h['ordinary']);n=sum(x==y for x,y in zip(a['projection'],h['projection']))
        exact=(a['raw_payload']==h['raw_payload'] or a['answer']==h['answer'] or a['tuple']==h['tuple'] or ('raw_values' in h and a['raw_values']==h['raw_values']))
        fp_ok=h['fp'] is None or not (sum(x==y for x,y in zip(a['fp'],h['fp']))==6 or (sum(x==y for x,y in zip(a['fp'],h['fp']))>=5 and 25*i>=3*u))
        ck(u>0 and 5*i<u and n<3 and (n<2 or 25*i<3*u) and not exact and fp_ok,'independent_historical_pair',a['id']+'|'+h['id'])
        expected={'new':a['id'],'historical':h['id'],'ordinary_i_u':[i,u],'projection_matches':n,'tuple_applicability':h['tuple_applicability'],'gate':True}
        ck(rows[j]==expected,'historical_report_row');j+=1;pmatches[n]+=1;maxj=max(maxj,Fraction(i,u))
        if n>=2:maxnear=max(maxnear,Fraction(i,u))
dummy=copy.deepcopy(members[0]['request']);dummy['input']['text']=re.sub(r'\d{4}-\d{2}-\d{2}','AUDIT_SYMBOLIC_DATE',dummy['input']['text'])
invariant={g for g in grams(dummy,True) if not any('audit_symbolic_date' in t for t in g)}
ck(invariant==set(tuple(g) for g in report['invariant_five_grams']),'symbolic_invariant_grams',sorted(invariant))
pairrows=report['new_pairs'];maxres=Fraction(0);ordinaryfails=0;maxordinary=Fraction(0)
for j,(a,b) in enumerate(combinations(new,2)):
    left=a['ordinary']-invariant;right=b['ordinary']-invariant;i=len(left&right);u=len(left|right)
    ck(bool(left) and bool(right) and 25*i<3*u,'independent_scaffold_residual',a['id']+'|'+b['id'])
    ck(all(not any(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',t) for t in g) for g in invariant),'invariant_never_removes_DATE')
    ck(all(a[k]!=b[k] for k in ('raw_payload','raw_values','answer','tuple')),'new_pair_exact_freshness')
    r=pairrows[j]
    ck(r['left']==a['id'] and r['right']==b['id'] and r['residual_i_u']==[i,u] and r['ordinary_gate_credited'] is False and r['mode']=='DECLARED_SCAFFOLD_RESIDUAL' and r['full_fingerprint_equal']==(a['fp']==b['fp']) and all(r[v+'_i_u']==[len(a[v]&b[v]),len(a[v]|b[v])] for v in ('ordinary','shape','content')),'new_pair_report_row')
    maxres=max(maxres,Fraction(i,u));oi,ou=len(a['ordinary']&b['ordinary']),len(a['ordinary']|b['ordinary']);ordinaryfails+=5*oi>=ou;maxordinary=max(maxordinary,Fraction(oi,ou))
ledger=plain(DATA/'corpus/TEMPLATE_RECURRENCE_LEDGER.json')
ck(ledger['rows']==[{'fixture_id':m['fixture_id'],'stratum':m['stratum'],'fingerprint':C.fingerprint(m)} for m in members] and ledger['fingerprint_classes']==4,'recurrence_ledger')
detail['contamination']={'historical':hcounts,'historical_pairs':len(rows),'new_pairs':len(pairrows),'legacy_tuple_NA_pairs':5040,'GEXTRACT_typed_applicability_pairs':7680,'max_historical_jaccard':str(maxj),'max_two_projection_jaccard':str(maxnear),'projection_matches':pmatches,'invariant_grams':sorted(invariant),'max_new_residual_jaccard':str(maxres),'max_new_ordinary_jaccard':str(maxordinary),'ordinary_nonpasses_not_credited':ordinaryfails}
print('CONTAMINATION_COMPLETE',len(checks),flush=True)

# Every byte in both supplied final trees is checked independently.
storedtrees=[]
for name in ('pilot_one','pilot_two'):
    d=DATA/'preexecution/final'/name;t=tree(d);manifest=plain(d/'EVIDENCE_MANIFEST.json')
    ck(len(t)==327 and manifest['member_count']==326 and manifest['files']=={k:v for k,v in t.items() if k!='EVIDENCE_MANIFEST.json'},'pilot_manifest_actual_bytes',name)
    ck(all(sha(git('show',HEAD+':'+(d/rel).relative_to(ROOT).as_posix()))==h for rel,h in t.items()),'pilot_tree_vs_git',name)
    records=Journal.__new__(Journal);records.directory=d/'journal';rs=records.read()
    ck(len(rs)==244 and sum(r['payload']['kind']=='START' for r in rs)==80 and sum(r['payload']['kind']=='COMPLETE' for r in rs)==80 and sum(r['payload']['kind']=='CHECKPOINT_CREATED' for r in rs)==81,'pilot_journal_counts',name)
    scores={};attempted=0
    for i,r in enumerate(rs):
        q=r['payload']
        if q['kind']=='START':
            ck(q['row']==p.schedule[attempted] and q['request_sha256']==sha(p.wire(q['row'])),'stored_START_lineage');attempted+=1
        if q['kind']=='COMPLETE':
            row=p.schedule[attempted-1];m=p.members[row['fixture_id']];s=evaluate(m,q['result']['raw_output'],truncated=q['result']['provider_truncated'])
            ck(q['call_id']==row['call_id'] and s==q['score'] and C.diagnosis(m,q['result']['raw_output'],s)==q['diagnostic'],'stored_scorer_replay');scores[q['call_id']]=s
        if q['kind']=='CHECKPOINT_CREATED':
            state={'qualified':[],'integrity_events':[],'event_scopes':[],'verdict':'VALID_COMPLETE' if len(scores)==80 else 'RUNNING','completed_observations':len(scores),'attempted_calls':attempted}
            cp=d/q['path'];prefix=records.prefix(rs[:i]);loaded=verify_checkpoint(cp,run_id='G-CAL1-SYNTHETIC-REPLAY',binding=dict(p.binding,lab_version=L.VERSION),schedule=p.schedule,journal=records,reconstructed_state=state,next_position=attempted+1,prefix=prefix)
            ck(fh(cp)==q['file_sha256'] and loaded['payload']==q['payload'],'stored_checkpoint_lineage')
    ck(C.summarize(p,scores)==plain(d/'FINAL_REPORT.json')['summary'],'stored_final_reduction')
    storedtrees.append(t)
ck(storedtrees[0]==storedtrees[1]==plain(DATA/'preexecution/final/PILOT_REPORT.json')['pilot_tree'],'two_supplied_final_trees_identical')
detail['pilot_trees']={'files_each':327,'manifest_members_each':326,'journal_records_each':244,'sealed_checkpoints_each':81,'scored_observations_each':80,'tree_sha256':sha(enc(storedtrees[0]))}
print('STORED_PILOTS_COMPLETE',len(checks),flush=True)

(OUT/'static_result.json').write_bytes(enc({'checks':len(checks),'failures':[x for x in checks if not x['passed']],'detail':detail}))

