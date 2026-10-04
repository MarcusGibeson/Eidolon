"""G-CAL1-only science, immutable package and wire bytes. No provider adapter."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import re

from g_extract1_contract import ROOT, Package as HistoricalPackage, canonical, digest, file_digest, load, require
from g_extract1_scoring import evaluate, parse_semantic, typed

DATA = ROOT / 'experiments/G-CAL1-candidate'
VERSION = 'g-cal1.contract.v1'


def leap(year):
    return year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)


def month_days(year, month):
    return (31, 29 if leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month-1]


def manual_date(source, offset):
    """Independent gold path: component parsing and signed day stepping only."""
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', source):
        raise ValueError('date spelling')
    y, m, d = map(int, source.split('-'))
    if not (1 <= y <= 9999 and 1 <= m <= 12 and 1 <= d <= month_days(y, m)):
        raise ValueError('date domain')
    if type(offset) is not int or not -367 <= offset <= 367:
        raise ValueError('offset domain')
    direction = 1 if offset >= 0 else -1
    for _ in range(abs(offset)):
        d += direction
        if d > month_days(y, m):
            d = 1
            m += 1
            if m == 13:
                y, m = y+1, 1
        elif d == 0:
            m -= 1
            if m == 0:
                y, m = y-1, 12
            if not 1 <= y <= 9999:
                raise ValueError('date overflow')
            d = month_days(y, m)
        if not 1 <= y <= 9999:
            raise ValueError('date overflow')
    return f'{y:04d}-{m:02d}-{d:02d}'


def primary_date(source, offset):
    return (date.fromisoformat(source) + timedelta(days=offset)).isoformat()


def path_dates(source, offset):
    start = date.fromisoformat(source)
    sign = 1 if offset >= 0 else -1
    return [start + timedelta(days=sign*i) for i in range(abs(offset)+1)]


def temporal_pattern(source, offset):
    walk = path_dates(source, offset)
    if any((x.month, x.day) == (2, 29) for x in walk):
        return 'LEAP_DAY_BOUNDARY'
    if walk[0].year != walk[-1].year:
        return 'YEAR_BOUNDARY'
    if walk[0].month != walk[-1].month:
        return 'MONTH_BOUNDARY'
    return 'DATE_WITHIN_MONTH'


def allocation_ok(c, stratum, slot, source, offset):
    s, g = date.fromisoformat(source), date.fromisoformat(primary_date(source, offset))
    spec = c['allocation'][stratum]
    if offset != spec['offsets'][slot-1]:
        return False
    if stratum == 'C1':
        return s.month == spec['months'][slot-1] and (s.year, s.month) == (g.year, g.month)
    if stratum == 'C2':
        return ((s.month, g.month, g.year-s.year) == (12, 1, 1) if offset > 0 else
                (s.month, g.month, g.year-s.year) == (1, 12, -1))
    if stratum == 'C3':
        year_kind, md = {
            1: ('LEAP', (2,28)), 2: ('LEAP', (2,29)), 3: ('LEAP', (3,1)),
            4: ('COMMON', (2,28)), 5: ('COMMON', (3,1)),
            6: ('CENTURY_COMMON', (2,28)), 7: ('CENTURY_COMMON', (3,1)),
            8: ('CENTURY_LEAP', (2,28)), 9: ('CENTURY_LEAP', (3,1)),
            10: ('LEAP', (2,29)),
        }[slot]
        correct_year = (leap(s.year) if year_kind == 'LEAP' else not leap(s.year) if year_kind == 'COMMON'
                        else s.year in spec['century_common_year_pool'] if year_kind == 'CENTURY_COMMON'
                        else s.year in spec['century_leap_year_pool'])
        return (s.month, s.day) == md and correct_year
    if stratum == 'C4':
        has = any((d.month,d.day) == (2,29) for d in path_dates(source,offset))
        return s.year != g.year and has == spec['path_contains_feb29'][slot-1]
    return False


def make_member(c, baseline, stratum, slot, source):
    si = int(stratum[1:])
    ordinal = 4*(slot-1)+si
    fid = f'G-CAL1-{stratum}-{slot:02d}'
    offset = c['allocation'][stratum]['offsets'][slot-1]
    require(allocation_ok(c,stratum,slot,source,offset), 'PROVENANCE_MISMATCH', 'allocation')
    gold = primary_date(source,offset)
    require(gold == manual_date(source,offset), 'PRE_GOLD_DIGEST_MISMATCH', fid)
    field, nuisance, target = f'f{ordinal:03d}_01', f'f{ordinal:03d}_02', f'd{ordinal:03d}_01'
    subject = c['baseline']['opening'] + '. ' + c['baseline']['operation'].format(target=target,date_field=field,offset=offset)
    request = {'prompt': baseline['structured_extraction_assembled_template'].replace('{SUBJECT}',subject),
               'input': {'schema': {target:'YYYY-MM-DD'},
                         'text': f'{field} is {source}. {nuisance} is "code_{ordinal:03d}_99".'}}
    fixture = {'entities': [], 'source_fact_records': [
        {'template_id':'VALUE','field_identifier':field,'schema_type':'YYYY-MM-DD',
         'value':{'kind':'date_literal','value':source},'entity_selector_value':None},
        {'template_id':'VALUE','field_identifier':nuisance,'schema_type':'string',
         'value':{'kind':'string_literal','value':f'code_{ordinal:03d}_99'},'entity_selector_value':None}],
        'operation_nodes':[{'id':'CALENDAR_DAY_OFFSET','target':target,'arguments':{
            'date':{'kind':'field_identifier','value':field},'days':{'kind':'integer_literal','value':str(offset)}}}],
        'output_fields':[{'name':target,'schema_type':'YYYY-MM-DD','required':True,'binding_kind':'OPERATION_TARGET',
                          'source_field':None,'producer_target':target,'label_removal':False,'absence_capable':False}],
        'required_output_fields':[target],'gold_values':{target:gold}}
    return {'fixture_id':fid,'stratum':stratum,'slot':slot,'ordinal':ordinal,
            'source_date':source,'offset':offset,'subject':subject,'fixture':fixture,'request':request,'gold':{target:gold}}


def fingerprint(member):
    f = member['fixture']
    return [[['CALENDAR_DAY_OFFSET',['source_field','literal'],[]]],
            [['YYYY-MM-DD','derived_date']], 'NONE','NONE',
            temporal_pattern(member['source_date'],member['offset']),
            ['CONTIGUOUS_SINGLE_ENTITY', [['SUPPORT', f['source_fact_records'][0]['schema_type'],-1],
                                           ['DISTRACTOR', f['source_fact_records'][1]['schema_type'],-1]]]]


def typed_tuple(member):
    source, offset = member['source_date'], str(member['offset'])
    gold = next(iter(member['gold'].values()))
    return [['SOURCE_FACT','DATE',source], ['OPERATION_ARGUMENT','DATE',source],
            ['OPERATION_ARGUMENT','INTEGER',offset], ['GOLD','DATE',gold]]


def build_schedule(members, c, wire):
    rows = []
    for repeat in (1,2):
        ordered = sorted(members,key=lambda m:(digest(f'G-CAL1/order/{repeat}/{m["fixture_id"]}'.encode()),m['fixture_id']))
        for member in ordered:
            seed = 820000 + 10*member['ordinal'] + repeat
            row = {'schedule_position':len(rows)+1,'call_id':f'{member["fixture_id"]}:REPEAT{repeat}',
                   'fixture_id':member['fixture_id'],'stratum':member['stratum'],'repeat':repeat,
                   'cell_id':member['stratum'],'phase':'CAL','seed':seed,'model':c['model'],
                   'provider_version':c['provider_version'],'generation_configuration':c['generation_configuration']}
            row['request_sha256'] = digest(wire(row))
            rows.append(row)
    return rows


def wire_bytes(member, row, c, baseline):
    options = {k:c['generation_configuration'][k] for k in
               ('temperature','top_p','top_k','repeat_penalty','num_ctx','num_predict')}
    options['seed'] = row['seed']
    request = member['request']
    return canonical({'model':c['model'],'system':baseline['system_text'],
                      'prompt':request['prompt']+'\n\nINPUT:\n'+canonical(request['input']).decode('utf-8'),
                      'stream':False,'think':False,'options':options})


class Package:
    def __init__(self):
        self.data = DATA
        self.manifest = load(DATA/'LAB_MANIFEST.json')
        self.manifest_sha = file_digest(DATA/'LAB_MANIFEST.json')
        self.pins = self.manifest['protected_artifacts']
        self.verify()
        self.design = load(DATA/'DESIGN.json')
        self.historical = HistoricalPackage()
        self.baseline = self.historical.design['baseline_binding']
        self.members = {m['fixture_id']:m for m in load(DATA/'corpus/CORPUS.json')['members']}
        self.schedule = load(DATA/'schedule/SCHEDULE.json')['rows']
        expected = build_schedule(list(self.members.values()),self.design,self.wire)
        require(self.schedule == expected,'PRE_SCHEDULE_DIGEST_MISMATCH')
        for m in self.members.values():
            require(m == make_member(self.design,self.baseline,m['stratum'],m['slot'],m['source_date']),
                    'PRE_GOLD_DIGEST_MISMATCH','complete canonical member')
        self.binding = {'experiment':'G-CAL1','contract_version':VERSION,'manifest_sha256':self.manifest_sha,
                        'schedule_sha256':digest(canonical(self.schedule)),'journal_schema':'g-extract1.call-journal.v2'}

    def wire(self, row):
        return wire_bytes(self.members[row['fixture_id']],row,self.design,self.baseline)

    def verify(self, contacted=False):
        event = 'PROTECTED_ARTIFACT_DIGEST_MISMATCH' if contacted else 'PRE_ARTIFACT_DIGEST_MISMATCH'
        require(file_digest(DATA/'LAB_MANIFEST.json') == self.manifest_sha,event,'manifest drift')
        for path, expected in self.pins.items():
            require((ROOT/path).is_file() and file_digest(ROOT/path) == expected,event,path)


def diagnosis(member, raw, score):
    expected = next(iter(member['gold'].values()))
    obj, ok, duplicate = parse_semantic(score['normalization']['payload'])
    field = next(iter(member['gold']))
    returned = obj.get(field) if ok and type(obj) is dict else None
    labels = []
    if score['malformed'] or not score['semantic_schema_valid']:
        labels.append('MALFORMED_SCHEMA_INVALID')
    if score['provider_truncated']:
        labels.append('PROVIDER_TRUNCATED')
    if typed(returned,'YYYY-MM-DD') and returned != expected:
        r,g,s = map(date.fromisoformat,(returned,expected,member['source_date']))
        off = member['offset']; sign = 1 if off > 0 else -1
        if abs((r-g).days) == 1: labels.append('OFF_BY_ONE_DAY')
        if r.year != g.year: labels.append('WRONG_YEAR')
        if r.month != g.month: labels.append('WRONG_MONTH')
        if r == s: labels.append('UNCHANGED_INPUT_DATE')
        if r == s-timedelta(days=off): labels.append('SIGN_DIRECTION_ERROR')
        if abs(off) in (365,366) and r == s+timedelta(days=sign*(731-abs(off))):
            labels.append('365_366_CONFUSION_PATTERN')
        walk = path_dates(member['source_date'],off)
        if any((x.month,x.day)==(2,29) for x in walk) and r == g+timedelta(days=sign):
            labels.append('LEAP_DAY_OMISSION_PATTERN')
        common_feb = any(not leap(x.year) and (x.month,x.day)==(2,28) for x in walk)
        crosses_mar = any(x.month==3 for x in walk) and any(x.month==2 for x in walk)
        if common_feb and crosses_mar and r == g-timedelta(days=sign):
            labels.append('LEAP_DAY_INSERTION_PATTERN')
        if not labels: labels.append('OTHER_EXACT_MISMATCH')
    return {'source_date':member['source_date'],'signed_offset':member['offset'],
            'reference_date':expected,'returned_date':returned,'categories':labels,
            'interpretation':'observable patterns only; no cognitive-state or cause inference'}


def summarize(package, evidence):
    strata = {}
    for stratum in ('C1','C2','C3','C4'):
        members = [m for m in package.members.values() if m['stratum']==stratum]
        pairs = [[evidence.get(f'{m["fixture_id"]}:REPEAT{r}') for r in (1,2)] for m in members]
        scores = [x for p in pairs for x in p if x is not None]
        complete = len(scores)==20 and not any(x['infrastructure_missing'] for x in scores)
        strata[stratum] = {'fixtures':10,'expected_observations':20,'completed_observations':len(scores),
            'complete':complete,'both_repeat_correct':sum(all(x is not None and x['semantic_correct'] for x in p) for p in pairs),
            'semantic_observations':sum(x['semantic_correct'] for x in scores),
            'structural_observations':sum(x['structural_valid'] for x in scores),
            'both_repeat_structural':sum(all(x is not None and x['structural_valid'] for x in p) for p in pairs),
            'false_clean_observations':sum(x['false_clean'] for x in scores),
            'false_clean_fixtures':sum(any(x and x['false_clean'] for x in p) for p in pairs),
            'correlated_false_clean_pairs':sum(all(x and x['false_clean'] for x in p) for p in pairs),
            'malformed_observations':sum(x['malformed'] for x in scores),
            'repeat_correctness_disagreement':sum(all(x is not None for x in p) and p[0]['semantic_correct']!=p[1]['semantic_correct'] for p in pairs)}
    complete = all(x['complete'] for x in strata.values())
    rational = lambda x: {'numerator':x.numerator,'denominator':x.denominator}
    contrasts = None
    if complete:
        control = strata['C1']; boundary = [strata[x] for x in ('C2','C3','C4')]
        contrasts = {'control_minus_boundary_fixture_accuracy':rational(Fraction(control['both_repeat_correct'],10)-Fraction(sum(x['both_repeat_correct'] for x in boundary),30)),
                     'boundary_minus_control_false_clean_observation_rate':rational(Fraction(sum(x['false_clean_observations'] for x in boundary),60)-Fraction(control['false_clean_observations'],20)),
                     'boundary_minus_control_false_clean_fixture_rate':rational(Fraction(sum(x['false_clean_fixtures'] for x in boundary),30)-Fraction(control['false_clean_fixtures'],10))}
    return {'complete':complete,'interpretation':'DESCRIPTIVE_CALENDAR_DIAGNOSTIC' if complete else None,
            'strata':strata,'contrasts':contrasts,'qualification_gates':None,'phase_b':False}
