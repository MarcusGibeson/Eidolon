"""Deterministic offline G-CAL1 authoring and contamination certification."""
from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import unicodedata

from g_cal1_contract import DATA, ROOT, allocation_ok, build_schedule, fingerprint, leap, make_member, manual_date, primary_date, typed_tuple, wire_bytes
from g_extract1_contract import Package as History, canonical, digest, file_digest, load, require, source_pins
from g_extract1_journal import write_once


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def check(condition, detail):
    if not condition:
        raise ValueError(detail)


def preservation_snapshot():
    history = History()
    paths = set(history.pins) | set(source_pins())
    # Prior synthetic audit trees are not opened or modified. Protect the actual
    # closed scientific package and complete real execution tree by actual bytes.
    for directory in ('experiments/G-EXTRACT1-candidate/execution',
                      'experiments/G-EXTRACT1-candidate/closure',
                      'experiments/G-ROUTE4-candidate/closure'):
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/directory).rglob('*') if p.is_file())
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'experiments/G-EXTRACT1-candidate/corpus').glob('*.json'))
    return {p:file_digest(ROOT/p) for p in sorted(paths)}


def old_checkers():
    directory = ROOT/'experiments/G-EXTRACT1-candidate/corpus'
    return (module('g_cal1_frozen_primary',directory/'validate_corpus.py'),
            module('g_cal1_frozen_independent',directory/'independent_contamination.py'))


def legacy_projection(request, c, independent=False):
    """Older prompt scaffolds have no full suffix; observe bytes, not semantics."""
    adapter = c['historical_fingerprint_adapter_contract']
    schema = request['input']['schema']
    tags = {'string':'STRING','number':'NUMBER','integer':'INTEGER','boolean':'BOOLEAN','YYYY-MM-DD':'DATE','HH:MM':'TIME'}
    signature = []
    for s in schema.values():
        check(s in tags or ('|' in s and len(s.split('|'))>=2 and len(set(s.split('|')))==len(s.split('|')) and
                           all(re.fullmatch('[A-Za-z][A-Za-z0-9_]*',v) for v in s.split('|'))),'legacy schema')
        signature.append([tags.get(s,'ENUM'),len(s.split('|')) if '|' in s else 0])
    signature.sort(key=lambda x:json.dumps(x,separators=(',',':')).encode())
    normal = lambda text:' '.join(unicodedata.normalize('NFC',text.replace('\r\n','\n').replace('\r','\n')).casefold().split())
    kinds = []
    tokens = re.findall(c['contamination_contract']['tokenizer']['pattern'],normal(request['input']['text']),re.ASCII)
    if independent:
        for token in tokens:
            classification = 'IDENTIFIER'
            for tag in ('DATE','TIME','NUMBER'):
                if re.fullmatch(adapter['source_kind_regex'][tag],token,re.ASCII):
                    classification = tag
                    break
            kinds.append(classification)
    else:
        kinds = [next((tag for tag in ('DATE','TIME','NUMBER') if re.fullmatch(adapter['source_kind_regex'][tag],token,re.ASCII)),'IDENTIFIER') for token in tokens]
    subject = normal(request['prompt'].split('. Copy names',1)[0])
    catalog = adapter['surface_catalog']
    regex = '|'.join(f'(?P<C{i}>{r["regex"]})' for i,r in enumerate(catalog))
    surfaces = [catalog[int(m.lastgroup[1:])]['id'] for m in re.finditer(regex,subject,re.ASCII)]
    return [signature,kinds,surfaces]


def legacy_answer(schema,values,c,primary,independent,second=False):
    rows=[]
    for key in sorted(schema,key=lambda x:x.encode('utf-8')):
        s,v=schema[key],values[key]
        if '|' in s:
            check(type(v) is str and v in s.split('|'),'legacy enum gold')
            rows.append([key,s,['ENUM',v]])
        else:
            encoded = (independent.whole_answer_bytes([[key,s,v]],c) if second else primary.whole_answer_bytes([[key,s,v]]))
            rows.extend(json.loads(encoded))
    return json.dumps(rows,ensure_ascii=True,separators=(',',':')).encode('utf-8')


def evidence(member, c, primary, independent):
    f, request = member['fixture'], member['request']
    source, offset = member['source_date'], member['offset']
    # Each implementation parses and renders its own values/tokens/answer bytes.
    a = {'raw_payload':primary.compact(request['input']),
         'raw_values':primary.freshness_from_source_facts(f['source_fact_records']),
         'answer':primary.whole_answer_bytes([[k,'YYYY-MM-DD',v] for k,v in member['gold'].items()]),
         'projection':json.loads(primary.D.historical_projection(request,c)),
         'ordinary':primary.D.comparison_grams(primary.D.ordinal_neutral_payload(request),c),
         'content':primary.D.comparison_grams(primary.D.ordinal_neutral_payload(request),c,'content'),
         'shape':primary.D.comparison_grams(primary.D.ordinal_neutral_payload(request),c,'shape'),
         'tuple':primary.compact(typed_tuple(member))}
    b = {'raw_payload':independent.dump(request['input']),
         'raw_values':independent.freshness_from_source_facts(f['source_fact_records'],c),
         'answer':independent.whole_answer_bytes([[k,'YYYY-MM-DD',v] for k,v in member['gold'].items()],c),
         'projection':independent.projection(request,c),
         'ordinary':independent.grams(request,c), 'content':independent.grams(request,c,'content'),
         'shape':independent.grams(request,c,'shape'),
         'tuple':independent.dump([['SOURCE_FACT','DATE',source],['OPERATION_ARGUMENT','DATE',source],
                                  ['OPERATION_ARGUMENT','INTEGER',str(int(f['operation_nodes'][0]['arguments']['days']['value']))],
                                  ['GOLD','DATE',manual_date(source,offset)]])}
    check(a==b,'independent contamination encoding mismatch:'+member['fixture_id'])
    a.update(id=member['fixture_id'],fp=fingerprint(member))
    return a


def history_records(history, primary, independent):
    records, pins, source_dates, gold_dates = [], {}, set(), set()
    pairs = [('G-ROUTE1-candidate','corpus.json','gold.json'),
             ('G-ROUTE3-candidate','corpus_a.json','gold_a.json'),('G-ROUTE3-candidate','corpus_b.json','gold_b.json'),
             *[('G-ROUTE4-candidate/sealed',c,g) for c,g in
               [('corpus_a.json','gold_a.json'),('corpus_b.json','gold_b.json'),
                ('reserve_corpus_a.json','reserve_gold_a.json'),('reserve_corpus_b.json','reserve_gold_b.json')]]]
    c = history.design
    counts = Counter()
    for folder, corpus, gold in pairs:
        parent = ROOT/'experiments'/folder
        for path in (parent/corpus,parent/gold): pins[path.relative_to(ROOT).as_posix()] = file_digest(path)
        load(parent/gold)  # independently reject duplicate artifact keys
        gold_exact = json.loads((parent/gold).read_text(encoding='utf-8'),parse_float=Decimal)
        expected = {r['fixture_id']:r['expected'] for r in gold_exact['items']}
        for f in load(parent/corpus)['fixtures']:
            if f['task_class'] != 'structured_extraction': continue
            schema = f['input']['schema']; values = expected[f['fixture_id']]
            check(set(schema)==set(values),'legacy gold shape')
            old = 'G-ROUTE4' not in folder
            pa = legacy_projection(f,c) if old else json.loads(primary.D.historical_projection(f,c))
            pb = legacy_projection(f,c,True) if old else independent.projection(f,c)
            ga = primary.D.comparison_grams(primary.D.ordinal_neutral_payload(f,True),c)
            gb = independent.grams(f,c,historical=True)
            answer_a = legacy_answer(schema,values,c,primary,independent)
            answer_b = legacy_answer(schema,values,c,primary,independent,True)
            check(pa==pb and ga==gb and answer_a==answer_b,'legacy checker disagreement')
            records.append({'id':folder+'/'+corpus+'/'+f['fixture_id'],'request':f,'projection':pa,'ordinary':ga,
                            'answer':answer_a,'raw_payload':primary.compact(f['input']),'tuple':None,'fp':None,
                            'tuple_applicability':'NOT_APPLICABLE_UNREPRESENTABLE_HISTORICAL_PROVENANCE'})
            source_dates.update(valid_dates(f['input']['text']+' '+f['prompt']))
            gold_dates.update(values[k] for k,s in schema.items() if s=='YYYY-MM-DD')
            counts[folder.split('/')[0]] += 1
    check(counts['G-ROUTE4-candidate']==106,'historical 106 adapter')
    for member in history.variants.values():
        f, request = member['fixture'], member['request']
        a = primary.differential_record(f,request,c)
        b = independent.differential_record(f,request,c)
        check(a==b,'historical G-EXTRACT1 differential')
        atoms = primary.D.extract_date_number_atoms(f,c['operation_definition_contract'],c['schema_type_contract'],c['operation_semantics_contract'],c['entity_population_contract'])
        ev = independent.evidence(f,request,c)
        eligible = any(x[1] in ('DATE','TIME') for x in atoms) and any(x[1] in ('INTEGER','NUMBER') for x in atoms)
        check((primary.compact(atoms) if eligible else None)==ev['tuple'],'historical typed tuple')
        check(primary.freshness_from_source_facts(f['source_fact_records']).decode()==ev['raw_values'],'historical freshness')
        ev.update(id='G-EXTRACT1/'+member['rendered_variant_id'],request=request,tuple_applicability='APPLIES')
        ev['raw_values'] = ev['raw_values'].encode()
        records.append(ev)
        source_dates.update(valid_dates(request['input']['text']+' '+request['prompt']))
        gold_dates.update(member['gold'][k] for k,s in request['input']['schema'].items() if s=='YYYY-MM-DD')
    counts['G-EXTRACT1-candidate'] = len(history.variants)
    check(len(records)==318,'historical total')
    return records,pins,source_dates,gold_dates,dict(counts)


def valid_dates(text):
    result = set()
    for value in re.findall(r'\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b',text):
        try: date.fromisoformat(value)
        except ValueError: continue
        result.add(value)
    return result


def historical_rejection(a,h):
    for key in ('raw_payload','answer'):
        if a[key]==h[key]: return key+'_reuse'
    if 'raw_values' in h and a['raw_values']==h['raw_values']: return 'freshness_sequence_reuse'
    if h['tuple'] is not None and a['tuple']==h['tuple']: return 'typed_date_number_tuple_reuse'
    i,u = len(a['ordinary']&h['ordinary']), len(a['ordinary']|h['ordinary'])
    matches = sum(x==y for x,y in zip(a['projection'],h['projection']))
    if not u or 5*i>=u: return 'historical_ordinary_jaccard'
    if matches==3: return 'historical_projection_collision'
    if matches>=2 and 25*i>=3*u: return 'historical_projection_near_replay'
    if h['fp'] is not None:
        n = sum(x==y for x,y in zip(a['fp'],h['fp']))
        if n==6 or (n>=5 and 25*i>=3*u): return 'typed_historical_fingerprint_replay'
    return None


def independent_historical_rejection(a,h):
    if a['raw_payload']==h['raw_payload']: return 'raw_payload_reuse'
    if a['answer']==h['answer']: return 'answer_reuse'
    if h.get('raw_values')==a['raw_values']: return 'freshness_sequence_reuse'
    if h['tuple'] is not None and h['tuple']==a['tuple']: return 'typed_date_number_tuple_reuse'
    union = a['ordinary'].union(h['ordinary']); common = a['ordinary'].intersection(h['ordinary'])
    same = sum(a['projection'][i]==h['projection'][i] for i in range(3))
    if len(union)==0 or len(common)*5>=len(union): return 'historical_ordinary_jaccard'
    if same==3: return 'historical_projection_collision'
    if same>1 and len(common)*25>=3*len(union): return 'historical_projection_near_replay'
    if h['fp'] is not None:
        same = sum(a['fp'][i]==h['fp'][i] for i in range(6))
        if same==6 or (same>=5 and len(common)*25>=len(union)*3): return 'typed_historical_fingerprint_replay'
    return None


def candidate_source(c,stratum,slot,attempt):
    rng = random.Random(int(digest(f'G-CAL1/G-CAL1-{stratum}-{slot:02d}/{attempt}'.encode()),16))
    year = rng.randint(*c['allocation']['ordinary_year_pool'])
    if stratum=='C1': return date(year,c['allocation'][stratum]['months'][slot-1],rng.randint(1,28)).isoformat()
    if stratum=='C2': return date(year,12 if slot<=5 else 1,rng.randint(19,31) if slot<=5 else rng.randint(1,12)).isoformat()
    if stratum=='C3':
        if slot in (6,7): year = rng.choice(c['allocation']['C3']['century_common_year_pool'])
        elif slot in (8,9): year = rng.choice(c['allocation']['C3']['century_leap_year_pool'])
        elif slot in (1,2,3,10): year = rng.choice([y for y in range(2051,2100) if leap(y)])
        else: year = rng.choice([y for y in range(2051,2100) if not leap(y)])
        month,day = {1:(2,28),2:(2,29),3:(3,1),4:(2,28),5:(3,1),6:(2,28),7:(3,1),8:(2,28),9:(3,1),10:(2,29)}[slot]
        return date(year,month,day).isoformat()
    return date(year,rng.randint(1,12),rng.randint(1,28)).isoformat()


def prepare():
    check(not (DATA/'corpus/CORPUS.json').exists(),'corpus already exists: never regenerate')
    before = preservation_snapshot()
    if (DATA/'PRESERVATION_BEFORE.json').exists():
        check(load(DATA/'PRESERVATION_BEFORE.json')==before,'preflight restart changed historical bytes')
    else:
        write_once(DATA/'PRESERVATION_BEFORE.json',before)
    c = load(DATA/'DESIGN.json'); history = History(); p,ind = old_checkers()
    check(c['generation_configuration']==history.receipts()['generation_configuration'],'configuration drift')
    check(c['model']==history.receipts()['models'][2]['model'],'model drift')
    hist,pins,used_sources,used_gold,hist_counts = history_records(history,p,ind)
    attempts,members,cached = [],[],[]
    comparisons = []
    for slot in range(1,11):
        for stratum in ('C1','C2','C3','C4'):
            accepted = False
            offset = c['allocation'][stratum]['offsets'][slot-1]
            for attempt in range(1,10001):
                source = candidate_source(c,stratum,slot,attempt)
                reason = None
                if not allocation_ok(c,stratum,slot,source,offset): reason='allocation'
                gold = primary_date(source,offset)
                check(gold==manual_date(source,offset),'gold paths disagree')
                if reason is None and (source in used_sources or source in used_gold): reason='source_date_reuse'
                if reason is None and (gold in used_gold or gold in used_sources): reason='answer_date_reuse'
                if reason is None:
                    member = make_member(c,history.baseline if hasattr(history,'baseline') else history.design['baseline_binding'],stratum,slot,source)
                    ev = evidence(member,history.design,p,ind)
                    for h in hist:
                        ra,rb = historical_rejection(ev,h),independent_historical_rejection(ev,h)
                        check(ra==rb,'historical decision disagreement')
                        if ra:
                            reason=ra+':'+h['id']; break
                    for old in cached:
                        if reason: break
                        if ev['raw_payload']==old['raw_payload'] or ev['answer']==old['answer'] or ev['tuple']==old['tuple'] or ev['raw_values']==old['raw_values']:
                            reason='new_exact_reuse'
                attempts.append({'fixture_id':f'G-CAL1-{stratum}-{slot:02d}','attempt':attempt,'source_date':source,
                                 'offset':offset,'gold':gold,'decision':'ACCEPT' if reason is None else 'REJECT','reason':reason})
                if reason is None:
                    members.append(member);cached.append(ev);used_sources.add(source);used_gold.add(gold);accepted=True;break
            if not accepted:
                write_once(DATA/'corpus/AUTHORING_ATTEMPTS.json',{'attempts':attempts,'status':'STOPPED'})
                raise ValueError('fresh corpus search exhausted:'+stratum+str(slot))
    # Fixed lexical scaffold is determined symbolically, never from candidate overlap.
    dummy = make_member(c,history.design['baseline_binding'],'C1',1,'2060-01-10')['request']
    sentinel = json.loads(json.dumps(dummy))
    sentinel['input']['text'] = sentinel['input']['text'].replace('2060-01-10','SCaffoldDATE')
    invariant = ind.grams(sentinel,history.design)
    invariant = {g for g in invariant if not any('scaffolddate' in t for t in g)}
    for a,b in combinations(cached,2):
        ordinary = [len(a['ordinary']&b['ordinary']),len(a['ordinary']|b['ordinary'])]
        shape = [len(a['shape']&b['shape']),len(a['shape']|b['shape'])]
        left,right = a['ordinary']-invariant,b['ordinary']-invariant
        i,u = len(left&right),len(left|right)
        content = [len(a['content']&b['content']),len(a['content']|b['content'])]
        check(left and right and 25*i<3*u,'new scaffold residual similarity')
        check(a['tuple']!=b['tuple'] and a['raw_values']!=b['raw_values'] and a['answer']!=b['answer'],'new reuse')
        comparisons.append({'left':a['id'],'right':b['id'],'mode':'DECLARED_SCAFFOLD_RESIDUAL',
                            'ordinary_i_u':ordinary,'shape_i_u':shape,'content_i_u':content,
                            'residual_i_u':[i,u],'residual_gate':True,'ordinary_gate_credited':False,
                            'full_fingerprint_equal':a['fp']==b['fp'],'tuple_applicability':'APPLIES'})
    historical_pairs=[]
    for a in cached:
        for h in hist:
            check(historical_rejection(a,h) is None,'historical accepted pair changed')
            historical_pairs.append({'new':a['id'],'historical':h['id'],'ordinary_i_u':
                [len(a['ordinary']&h['ordinary']),len(a['ordinary']|h['ordinary'])],
                'projection_matches':sum(x==y for x,y in zip(a['projection'],h['projection'])),
                'tuple_applicability':h['tuple_applicability'],'gate':True})
    write_once(DATA/'corpus/CORPUS.json',{'schema_version':'g-cal1.corpus.v1','members':members,'model_input_contains_gold':False})
    write_once(DATA/'corpus/AUTHORING_ATTEMPTS.json',{'attempts':attempts,'status':'COMPLETE','provider_model_calls':0})
    write_once(DATA/'corpus/GOLD_DERIVATION_REPORT.json',{'agreement':'40/40','paths':['datetime','manual Gregorian day stepping'],
        'rows':[{'fixture_id':m['fixture_id'],'source_date':m['source_date'],'offset':m['offset'],
                 'primary':next(iter(m['gold'].values())),'independent':manual_date(m['source_date'],m['offset'])} for m in members]})
    write_once(DATA/'corpus/CONTAMINATION_REPORT.json',{'verdict':'PASS_APPLICABLE_CONTROLS','historical_counts':hist_counts,
        'historical_adaptation':{'G-ROUTE4':{'adapted':106,'rejected':0},'all_legacy':{'adapted':126,'rejected':0}},
        'historical_comparisons':len(historical_pairs),'new_new_comparisons':len(comparisons),
        'historical_tuple_not_applicable_comparisons':40*126,'typed_historical_tuple_comparisons':40*192,
        'independent_encoding_and_decision_agreement':True,'offset_atom_reuse_prohibited':False,
        'invariant_five_grams':[list(x) for x in sorted(invariant)],'new_pairs':comparisons,'historical_pairs':historical_pairs,
        'source_and_gold_dates_unique_and_disjoint':True,'not_applicable_credited_as_pass':False})
    write_once(DATA/'corpus/TEMPLATE_RECURRENCE_LEDGER.json',{'positions':40,'scaffold_classes':1,
        'rows':[{'fixture_id':m['fixture_id'],'stratum':m['stratum'],'fingerprint':fingerprint(m)} for m in members],
        'fingerprint_classes':len({canonical(fingerprint(m)) for m in members}),
        'rationale':'fixed two-fact calendar template; recurrence explicitly allocated before contact; residual tests retain DATE content'})
    by_id = {m['fixture_id']:m for m in members}
    wire = lambda row:wire_bytes(by_id[row['fixture_id']],row,c,history.design['baseline_binding'])
    schedule = build_schedule(members,c,wire)
    write_once(DATA/'schedule/SCHEDULE.json',{'rows':schedule,'schedule_sha256':digest(canonical(schedule)),'maximum_calls':80})
    write_once(DATA/'schedule/REQUEST_MANIFEST.json',{'wire_requests':[{'call_id':r['call_id'],'sha256':r['request_sha256'],
        'body':json.loads(wire(r))} for r in schedule],'request_count':80,'difficulty_labels_model_facing':False,'gold_model_facing':False})
    pins.update(history.pins);pins.update(source_pins())
    for path in (ROOT/'experiments/G-EXTRACT1-candidate/closure').glob('*'):
        if path.is_file(): pins[path.relative_to(ROOT).as_posix()] = file_digest(path)
    for path in (ROOT/'experiments/G-ROUTE4-candidate/closure').glob('*'):
        if path.is_file(): pins[path.relative_to(ROOT).as_posix()] = file_digest(path)
    for path in DATA.rglob('*'):
        if path.is_file() and path.name not in {'PRESERVATION_BEFORE.json'}:
            pins[path.relative_to(ROOT).as_posix()] = file_digest(path)
    for name in ('g_cal1_contract.py','g_cal1_stage.py','g_cal1_lab.py','g_cal1_pilot.py'):
        path = ROOT/'tools'/name; pins[path.relative_to(ROOT).as_posix()] = file_digest(path)
    write_once(DATA/'LAB_MANIFEST.json',{'schema_version':'g-cal1.protected-manifest.v1','protected_artifacts':pins,
        'historical_closure_commit':'1757155387af122d126f6db9fd03477e2823c2bb','schedule_sha256':digest(canonical(schedule)),
        'provider_model_calls':0,'freeze_active':False,'execution_authorized':False})
    print(json.dumps({'prepared':True,'fixtures':40,'historical_comparisons':len(historical_pairs),
                      'new_pairs':len(comparisons),'schedule_sha256':digest(canonical(schedule))}))


if __name__ == '__main__':
    if sys.argv[1:] != ['prepare']:
        raise SystemExit('usage: g_cal1_stage.py prepare (offline, write-once)')
    prepare()
