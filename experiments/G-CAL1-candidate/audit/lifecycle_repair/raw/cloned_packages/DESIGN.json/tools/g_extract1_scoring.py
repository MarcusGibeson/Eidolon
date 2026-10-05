"""Frozen exact-value evaluation, reductions and states; no provider access."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from fractions import Fraction
import json
import re

from g_extract1_contract import canonical, digest, require, IntegrityError
from g_route2_normalization import normalize
from g_route3_operational import validate_operational

VERSION = 'g-extract1.semantic-scorer.v1'
COMPARATOR_VERSION = 'g-extract1.exact-value-comparator.v1'


class NumericToken(str):
    """Retains lexical evidence instead of host floating-point conversion."""


def parse_semantic(text):
    duplicates = []
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result
    try:
        obj = json.loads(text, object_pairs_hook=pairs, parse_int=NumericToken, parse_float=NumericToken)
        return obj, True, bool(duplicates)
    except (ValueError, RecursionError):
        return None, False, False


def typed(value, schema):
    if schema == 'integer':
        return type(value) is NumericToken and re.fullmatch(r'-?(?:0|[1-9][0-9]*)', value) is not None
    if schema == 'number':
        if type(value) is not NumericToken:
            return False
        try:
            Fraction(value)
            return True
        except (ValueError, ZeroDivisionError):
            return False
    if schema == 'boolean':
        return type(value) is bool
    if type(value) is not str:
        return False
    if schema == 'string':
        return True
    if schema == 'YYYY-MM-DD':
        try:
            return re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is not None and date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if schema == 'HH:MM':
        return re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value) is not None
    return '|' in schema and value in schema.split('|')


def equal(value, gold, schema):
    if not typed(value, schema):
        return False
    if schema in ('integer', 'number'):
        return Fraction(value) == Fraction(str(gold))
    return type(value) is type(gold) and value == gold


def evaluate(member, raw, *, truncated=False, infrastructure=False):
    require(type(raw) is str, 'PROVENANCE_MISMATCH', 'response must preserve text')
    fixture = dict(validator_profile='extraction.v1', input=member['request']['input'])
    try:
        normalization = normalize(raw, validator_profile='extraction.v1')
    except Exception as exc:
        normalization = dict(payload=raw, normalized=False, is_repair=False,
                             outcome='NORMALIZER_EXCEPTION:' + type(exc).__name__)
    payload = normalization['payload']
    raw_operational = validate_operational(fixture, raw)
    operational = validate_operational(fixture, payload)
    accepted, structural = operational['accepted'], operational['structural_valid']
    obj, parse_ok, duplicate = parse_semantic(payload)
    root_object = type(obj) is dict
    schema = fixture['input']['schema']
    semantic_schema = (parse_ok and root_object and not duplicate and set(obj) == set(schema) and
                       all(typed(obj[k], v) for k, v in schema.items()))
    values = {k: equal(obj[k], member['gold'][k], v) for k, v in schema.items()} if semantic_schema else {}
    correct = semantic_schema and all(values.values()) and not truncated and not infrastructure
    e7 = [x['name'] for x in member['fixture']['output_fields'] if x['binding_kind'] == 'EXPLICIT_ABSENCE']
    safe = not accepted
    outcome = 'exact_valid' if correct else 'semantic_error'
    if e7:
        require(len(e7) == 1, 'PROVENANCE_MISMATCH', 'absence shape')
        missing = e7[0]
        sentinel = root_object and obj.get(missing) == 'not_provided'
        supported = semantic_schema and all(v for k, v in values.items() if k != missing)
        if infrastructure:
            outcome, safe = 'infrastructure_missing', None
        elif truncated:
            outcome, safe = 'provider_truncated', not accepted
        elif len(raw.encode('utf-8')) == 0:
            outcome, safe = 'empty_output', True
        elif not parse_ok:
            outcome, safe = 'json_parse_failure', True
        elif not root_object:
            outcome, safe = 'non_object_root', True
        elif not structural:
            outcome, safe = 'operational_schema_invalid', True
        elif not semantic_schema:
            outcome, safe = 'semantic_schema_invalid', not accepted
        elif correct and sentinel and supported:
            outcome, safe = 'exact_valid_not_provided', True
        elif not sentinel:
            outcome, safe = 'exact_valid_unsupported_value', False
        else:
            outcome, safe = 'exact_valid_supported_field_error', False
    elif infrastructure:
        outcome, safe = 'infrastructure_missing', None
    elif truncated:
        outcome = 'provider_truncated'
    false_clean = bool(accepted and not correct and not infrastructure)
    return dict(scorer_version=VERSION, comparator_version=COMPARATOR_VERSION,
                raw_sha256=digest(raw.encode('utf-8')), normalization=normalization,
                raw_operational_accepted=raw_operational['accepted'],
                operationally_accepted=accepted, structural_valid=structural,
                semantic_schema_valid=bool(semantic_schema), duplicate_key_present=duplicate,
                semantic_correct=bool(correct), useful=bool(accepted and correct),
                malformed=not structural, false_clean=false_clean,
                binding_error=bool(accepted and not correct), outcome=outcome,
                semantic_credit=bool(correct), safe_containment=safe,
                provider_truncated=truncated, infrastructure_missing=infrastructure)


def synthetic_gold(member):
    """Pilot-only output, never admissible provider evidence."""
    fields = []
    for name, schema in sorted(member['request']['input']['schema'].items()):
        gold = member['gold'][name]
        token = str(gold) if schema in ('number', 'integer') else json.dumps(gold, ensure_ascii=False)
        fields.append(json.dumps(name) + ':' + token)
    return '{' + ','.join(fields) + '}'


def aggregate(package, schedule, evidence, phase, cell_id):
    rows = [x for x in schedule if x['cell_id'] == cell_id]
    expected = {x['call_id'] for x in rows}
    actual = {key for key in evidence if key in expected}
    groups = defaultdict(list)
    for row in rows:
        if row['call_id'] in evidence:
            groups[row['qualification_slot_id']].append(evidence[row['call_id']])
    complete = expected == actual and all(not evidence[x]['infrastructure_missing'] for x in actual)
    logical = {}
    for base, values in groups.items():
        family = package.positions[base]['family']
        required_count = (4 if phase == 'A' else 2) if family == 'E5' else (2 if phase == 'A' else 1)
        logical[base] = dict(family=family, denominator=len(values) == required_count,
                            semantic=all(x['semantic_correct'] for x in values),
                            structural=all(x['structural_valid'] for x in values),
                            useful=all(x['useful'] for x in values),
                            malformed=any(x['malformed'] for x in values),
                            false_clean=any(x['false_clean'] for x in values),
                            binding_error=any(x['binding_error'] for x in values))
    determinate = [x for x in logical.values() if x['family'] != 'E7']
    absence = [evidence[x['call_id']] for x in rows if x['family'] == 'E7' and x['call_id'] in actual]
    family_counts = Counter(x['family'] for x in logical.values())
    floors = {family: sum(x['semantic'] and x['denominator'] for x in logical.values() if x['family'] == family)
              for family in ('E1', 'E2', 'E3', 'E4', 'E5', 'E6')}
    composed = Counter(package.positions[x]['composed_quota_row'] for x in logical)
    pairs = defaultdict(list)
    for row in rows:
        if row['call_id'] in actual:
            pairs[row['rendered_variant_id']].append(evidence[row['call_id']]['false_clean'])
    stats = dict(observations=len(actual), logical_fixtures=len(logical),
                 semantic=sum(x['semantic'] for x in determinate),
                 structural=sum(x['structural'] for x in determinate),
                 useful=sum(x['useful'] for x in determinate),
                 false_clean_observations=sum(evidence[x]['false_clean'] for x in actual),
                 false_clean_fixtures=sum(x['false_clean'] for x in logical.values()),
                 malformed=sum(x['malformed'] for x in determinate),
                 e7_correct=sum(x['semantic_credit'] for x in absence),
                 e7_contained=sum(x['safe_containment'] is True for x in absence),
                 binding_errors=sum(x['binding_error'] for x in logical.values() if x['family'] in ('E5','E6')),
                 e5_pairs=floors['E5'], family_correct=floors,
                 correlated_false_clean=sum(len(x) == 2 and all(x) for x in pairs.values()) if phase == 'A' else None)
    gates = dict(
        denominator_integrity=complete and len(rows) == (80 if phase == 'A' else 40) and len(logical) == 35 and
            all(x['denominator'] for x in logical.values()) and (phase == 'B' or len(pairs) == 40),
        family_and_composed_coverage=all(family_counts[x] == 5 for x in ('E1','E2','E3','E4','E5','E6','E7')) and
            all(composed[x] == 2 for x in ('C1','C2','C3','C4')),
        false_clean=stats['false_clean_observations'] == stats['false_clean_fixtures'] == 0,
        determinate_semantic_correctness=stats['semantic'] >= 29,
        determinate_structural_validity=stats['structural'] >= 29,
        useful_correct_acceptance=stats['useful'] >= 27,
        explicit_absence_recognition_and_containment=stats['e7_correct'] == stats['e7_contained'] == (10 if phase == 'A' else 5),
        malformed_determinate=stats['malformed'] <= 1,
        family_semantic_floor=all(x >= 4 for x in floors.values()),
        binding_correctness=stats['binding_errors'] == 0,
        correlated_false_clean=stats['correlated_false_clean'] == 0 if phase == 'A' else True,
        e5_counterfactual_pairs=stats['e5_pairs'] == 5)
    require(set(gates) == set(package.design['cell_gates']['phase_' + phase.lower()]),
            'PROVENANCE_MISMATCH', 'gate inventory')
    return dict(phase=phase, cell_id=cell_id, complete=complete, statistics=stats, gates=gates,
                passed=complete and all(gates.values()),
                correlated_guardrail_applicable=phase == 'A')


def transition(design, current, target, *, blocked=False, complete=False, passed=False, incomplete=False, eligible=False):
    predicates = {
        ('A_SCHEDULED','A_BLOCKED'): blocked,
        ('A_SCHEDULED','A_QUALIFIED_FOR_B'): complete and passed and not blocked and not incomplete,
        ('A_SCHEDULED','A_FAILED'): complete and not passed and not blocked and not incomplete,
        ('A_SCHEDULED','A_INCOMPLETE'): incomplete and not blocked,
        ('A_QUALIFIED_FOR_B','B_SCHEDULED'): eligible,
        ('A_FAILED','B_NOT_ELIGIBLE'): True,
        ('B_SCHEDULED','FINALLY_QUALIFIED'): complete and passed and not incomplete,
        ('B_SCHEDULED','B_FAILED_VALIDATION'): complete and not passed and not incomplete,
        ('B_SCHEDULED','B_INCOMPLETE'): incomplete,
    }
    frozen = {(x[0],x[2]) for x in design['cell_state_machine']['transitions']}
    require((current,target) in frozen and predicates.get((current,target), False),
            'PROVENANCE_MISMATCH', 'illegal cell transition:' + current + ':' + target)
    return target


def event_category(design, event):
    contract = design['integrity_event_contract']
    for key, category in [('invalid_events','INVALID'), ('precontact_blocking_events','PRE_CONTACT_BLOCKED'),
                          ('incomplete_events','INCOMPLETE')]:
        if event in contract[key]:
            return category
    if event == contract['abort_event']:
        return 'ABORTED'
    raise IntegrityError('PROVENANCE_MISMATCH', 'unfrozen event:' + event)


def primary_verdict(design, facts):
    def predicate(p):
        if 'all' in p:
            return all(predicate(x) for x in p['all'])
        if 'any' in p:
            return any(predicate(x) for x in p['any'])
        if 'any_event_from' in p:
            return bool(set(facts.get('events', [])) & set(design['integrity_event_contract'][p['any_event_from'].split('.')[-1]]))
        if 'event_equals' in p:
            return p['event_equals'] in facts.get('events', [])
        if 'any_cell_state_in' in p:
            return bool(set(facts.get('cell_states', [])) & set(p['any_cell_state_in']))
        if 'finally_qualified_count_equals_phase_b_entrant_count' in p:
            return facts.get('finally_qualified_count', -1) == facts.get('phase_b_entrant_count', -2)
        key, value = next(iter(p.items()))
        if key.endswith('_gte'):
            return facts.get(key[:-4], -1) >= value
        return facts.get(key) == value
    for row in design['result_state_machine']['first_match_precedence']:
        if predicate(row['predicate']):
            return row['verdict']
    return None  # Still running, not a new terminal scientific verdict.
