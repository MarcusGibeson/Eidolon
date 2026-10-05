"""Offline closure diagnostics, not a scorer, runner, or provider adapter.

Default mode verifies existing closure bytes. --write exclusively creates new
reports after checking the committed inputs and replaying the frozen evaluator.
"""
from collections import Counter, defaultdict
from datetime import date
from fractions import Fraction
from pathlib import Path
import argparse
import base64
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from g_extract1_contract import Package, canonical, digest, file_digest, load, source_pins
from g_extract1_journal import Journal, write_once
from g_extract1_runner import Run
from g_extract1_scoring import equal, evaluate, parse_semantic, primary_verdict, typed, NumericToken

COMMIT = '672e86f9bf1ca3d449ff47371d0c00df0909c120'
RUN_ID = 'G-EXTRACT1-PHASE-A-7d655fa9285d41b1938dd342bef053f6'
VERDICT = 'NO_PHASE_A_CELL_QUALIFIED'
OUT = Path(__file__).resolve().parent
CELLS = ['small:R2', 'small:R3', 'mid:R2', 'mid:R3', 'large:R2', 'large:R3']
FAMILIES = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']
LABELS = dict(E1='calendar', E2='clock and elapsed', E3='numeric', E4='comparison',
              E5='entity binding counterfactual pairs', E6='exact copy',
              E7='explicit partial absence / not-provided handling')


def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(), *args], cwd=ROOT)


def check(condition, detail):
    if not condition:
        raise AssertionError(detail)


def semantic_signature(obj, schema):
    # This is a diagnostic repeat-comparison signature, never a scoring rule.
    if type(obj) is not dict or set(obj) != set(schema):
        return None
    result = []
    for k, s in sorted(schema.items()):
        if not typed(obj[k], s):
            return None
        v = str(Fraction(obj[k])) if s in ('number', 'integer') else obj[k]
        result.append([k, s, v])
    return canonical(result)


def inspect(member, completion, row):
    ev = completion['evaluation']
    obj, parsed, duplicate = parse_semantic(ev['normalization']['payload'])
    schema, gold = member['request']['input']['schema'], member['gold']
    issues = []
    if not parsed:
        issues.append('invalid_json')
    elif type(obj) is not dict:
        issues.append('non_object_root')
    else:
        if duplicate:
            issues.append('duplicate_keys')
        if set(schema) - set(obj):
            issues.append('missing_output_fields')
        if set(obj) - set(schema):
            issues.append('extra_output_fields')
        for k in sorted(set(obj) & set(schema)):
            if not typed(obj[k], schema[k]):
                issues.append('invalid_date_value' if schema[k] == 'YYYY-MM-DD' else
                              'invalid_time_value' if schema[k] == 'HH:MM' else 'wrong_output_type')
    issues = sorted(set(issues))
    facts = member['fixture']['source_fact_records']
    nodes = member['fixture']['operation_nodes']
    field_errors = []
    for k, s in schema.items():
        if type(obj) is not dict or k not in obj or equal(obj[k], gold[k], s):
            continue
        val = obj[k]
        matches = []
        for fact in facts:
            if fact['template_id'] != 'VALUE' or fact['schema_type'] != s:
                continue
            if equal(val, fact['value']['value'], s):
                matches.append(dict(field=fact['field_identifier'], entity=fact['entity_selector_value']))
        detail = dict(field=k, schema_type=s, observed_value=val,
                      observed_json_kind='number_token' if type(val) is NumericToken else type(val).__name__,
                      expected_value=gold[k], matches_source_facts=matches)
        category = 'exact_value_mismatch'
        if row['family'] == 'E1':
            category = 'calendar_date_mismatch'
            if 'invalid_date_value' in issues:
                category = 'calendar_invalid_date'
            elif typed(val, s):
                detail['days_from_expected'] = (date.fromisoformat(val) - date.fromisoformat(gold[k])).days
        elif row['family'] == 'E2':
            category = 'clock_offset_value_mismatch' if nodes[-1]['id'] == 'CLOCK_MINUTE_OFFSET' else 'elapsed_minutes_mismatch'
        elif row['family'] == 'E3':
            ids = [n['id'] for n in nodes]
            category = ('unit_conversion_or_derived_copy_mismatch' if 'UNIT_CONVERSION' in ids else
                        'division_or_derived_copy_mismatch' if 'DIVIDE' in ids else 'numeric_arithmetic_mismatch')
        elif row['family'] == 'E4':
            category = 'comparison_boolean_mismatch'
            detail['upstream_vs_comparison_cause_identified'] = False
        elif row['family'] == 'E5':
            args = nodes[-1]['arguments']
            selected = args['selector_value']['value']
            source_field = args['source_field']['value']
            if type(val) is str and val in [e['selector_value'] for e in member['fixture']['entities']]:
                category = 'entity_label_returned_instead_of_source_value'
            elif any(m['field'] == source_field and m['entity'] != selected for m in matches):
                category = 'nonselected_entity_source_value_returned'
            else:
                category = 'entity_bound_value_alteration'
            detail['selected_selector_value'] = selected
        elif row['family'] == 'E6':
            derived = any(n['id'] != 'EXACT_COPY' for n in nodes)
            category = ('untransformed_source_value_returned_for_derived_copy' if derived and matches else
                        'derived_copy_value_mismatch' if derived else 'exact_copy_value_alteration')
        elif row['family'] == 'E7':
            category = ev['outcome']
        detail['diagnostic_category'] = category
        field_errors.append(detail)
    if ev['semantic_correct']:
        category = 'correct'
    elif not ev['structural_valid']:
        category = 'schema_format_failure'
    elif field_errors:
        category = field_errors[0]['diagnostic_category']
    else:
        category = ev['outcome']
    present_exact = (parsed and type(obj) is dict and all(k in obj and equal(obj[k], v, schema[k])
                                                       for k, v in gold.items()))
    return dict(primary_diagnostic_category=category, format_issues=issues, field_errors=field_errors,
                expected_field_values_exact_despite_invalid_object=bool(present_exact and not ev['semantic_schema_valid']),
                parsed=parsed, parsed_object=obj, duplicate_keys=duplicate)


def main(write=False):
    p = Package(ROOT)
    run_dir = p.data / 'execution' / RUN_ID
    activation_path = p.data / 'preexecution/control_flow_closure/EXECUTION_FREEZE_ACTIVATION.json'
    candidate_path = activation_path.with_name('EXECUTION_FREEZE_CANDIDATE.json')
    historical = [ROOT / 'experiments/G-ROUTE4-candidate/closure' / name for name in
                  ['G_ROUTE4_CLOSURE.json', 'PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json']]
    source = source_pins()
    watched = sorted(set([ROOT / x for x in p.pins] + [ROOT / x for x in source] +
                         list(run_dir.rglob('*.json')) + [activation_path, candidate_path] + historical))
    before = {x.relative_to(ROOT).as_posix(): file_digest(x) for x in watched}
    check(len(p.pins) == 50 and len(source) == 8, 'protected/source inventories')
    activation, candidate = load(activation_path), load(candidate_path)
    check(file_digest(activation_path) == 'd4f647309ff85677714eeedf762577d49773c38dac74773958f05475ffc0a298', 'activation')
    check(file_digest(candidate_path) == '4819d754192df7c49055a825353b9387d2cf51efe9652ef9f64bda8736be62c1', 'candidate')
    manifest = load(run_dir / 'EVIDENCE_MANIFEST.json')
    check(len(manifest['files']) == 2893, 'evidence inventory')
    for rel, sha in manifest['files'].items():
        check(file_digest(run_dir / rel) == sha, 'evidence:' + rel)
    tracked = git('ls-tree', '-r', '-z', COMMIT, '--', run_dir.relative_to(ROOT).as_posix())
    committed_files = 0
    for entry in tracked.split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        raw = (ROOT / path.decode()).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        check(blob == meta.decode().split()[2], 'committed byte identity:' + path.decode())
        committed_files += 1
    check(committed_files == 2895 and len(list(run_dir.rglob('*.json'))) == 2895, 'execution package committed inventory')
    schedule = p.schedule('A')
    check(schedule == load(run_dir / 'PHASE_A_SCHEDULE.json') and len(schedule) == 480, 'A schedule')
    check(digest(canonical(schedule)) == '3c48390307dd683e7ba2f736318d42f4d9fbda6527bbb9d64ee03b4bf97bb4dd', 'schedule hash')
    auth = load(run_dir / 'PHASE_A_AUTHORIZATION.json')
    saved = load(run_dir / 'PHASE_A_RUN_REPORT.json')
    result = load(run_dir / 'PHASE_A_RESULT_PACKAGE.json')
    check(auth['status'] == 'EXPLICIT_OPERATOR_PHASE_AUTHORIZATION' and auth['phase'] == 'A' and
          auth['run_id'] == RUN_ID and auth['synthetic_evidence_allowed'] is False and
          auth['binding'] == saved['binding'], 'authorization binding')
    check(saved['binding']['protected_artifacts'] == p.pins and
          saved['binding']['implementation_sha256'] == source, 'frozen artifact bindings')
    check(load(run_dir / 'run/RUN.json') == dict(schema_version=saved['schema_version'], run_id=RUN_ID,
          mode='AUTHORIZED_EXPERIMENT', binding=saved['binding'], exercise_authorization=False,
          phase_a_schedule_sha256=digest(canonical(schedule))), 'run header binding and real mode')
    p.verify_receipts(result['provider_model_receipts'], contacted=True)
    check(result['activation_sha256'] == file_digest(activation_path) and
          result['authorization_sha256'] == file_digest(run_dir / 'PHASE_A_AUTHORIZATION.json'), 'result authorities')
    check(load(run_dir / 'CONDITIONAL_PHASE_B_SCHEDULE.json') == p.schedule('B', []) == [], 'B empty')

    # Allocate a read-only replay view, not a Run constructor/guarded operation:
    # no resume, integrity append, phase entry or transport path is invoked.
    run = object.__new__(Run)
    run.package, run.directory, run.run_id, run.mechanical = p, run_dir / 'run', RUN_ID, False
    run.binding = saved['binding']
    run.a, run.b, run.qualified = schedule, [], []
    run.events, run.event_scopes, run.evidence, run.attempted = [], [], {}, set()
    run.current_phase, run.checkpoint_lineage, run._last_checkpoint = 'A', None, None
    run.journal = object.__new__(Journal)
    run.journal.directory = run.directory / 'journal'
    run._replay()
    check(run.state() == saved['state'] and not run.events, 'state/scorer/checkpoint replay')
    check(not list((run.directory / 'integrity').glob('*.json')), 'no retained integrity incidents')
    records = run.journal.read()
    journal_counts = Counter(x['payload']['type'] for x in records)
    check(journal_counts == dict(CHECKPOINT_CREATED=481, START=480, COMPLETE=480), 'journal outcomes')
    check(saved['primary_verdict'] == result['phase_a_primary_verdict'] == VERDICT and
          saved['phase_a_calls'] == saved['provider_model_calls'] == 480 and saved['phase_b_calls'] == 0,
          'frozen result')
    facts = dict(events=[], provider_generation_calls=480, cell_states=list(run.state()['cell_states'].values()),
                 phase_a_terminal=True, phase_b_terminal=False, phase_b_entrant_count=0,
                 finally_qualified_count=0, b_failed_validation_count=0)
    check(primary_verdict(p.design, facts) == VERDICT, 'frozen verdict replay')
    check(result['phase_b_authorized'] is False and result['phase_a_qualified_cells'] == [], 'no B authority or eligibility')
    rows = {x['call_id']: x for x in schedule}
    completions = {x['payload']['call_id']: x['payload'] for x in records if x['payload']['type'] == 'COMPLETE'}
    observations = []
    for row in schedule:
        cid = row['call_id']
        item = completions[cid]
        member = p.variants[row['rendered_variant_id']]
        request = load(run_dir / 'provider' / f"{row['schedule_position']:06d}_REQUEST.json")
        response = load(run_dir / 'provider' / f"{row['schedule_position']:06d}_RESPONSE.json")
        wire, body = base64.b64decode(request['wire_body_b64'], validate=True), base64.b64decode(response['raw_body_b64'], validate=True)
        check(wire == p.wire(row) and digest(wire) == row['request_sha256'] == request['request_sha256'], 'wire:' + cid)
        for key in ('call_id', 'model', 'seed', 'request_sha256'):
            check(request[key] == response[key] == row[key], 'request/response binding:' + cid)
        response_obj = json.loads(body)
        check(digest(body) == response['raw_body_sha256'] == item['receipt']['raw_body_sha256'] and
              response['http_status'] == 200 and response_obj['done'] is True and response_obj['model'] == row['model'] and
              response_obj['response'] == item['raw_output'], 'response capture:' + cid)
        check(item['provider_truncated'] == (response_obj.get('done_reason') == 'length'), 'truncation:' + cid)
        check(evaluate(member, item['raw_output'], truncated=item['provider_truncated']) == item['evaluation'], 'frozen scoring:' + cid)
        diagnosis = inspect(member, item, row)
        observations.append(dict(schedule=row, raw_output=item['raw_output'], expected=member['gold'],
                                 source_text=member['request']['input']['text'], source_facts=member['fixture']['source_fact_records'],
                                 schema=member['request']['input']['schema'], operation_nodes=member['fixture']['operation_nodes'],
                                 frozen_evaluation=item['evaluation'], diagnosis=diagnosis,
                                 binding_status=dict(recorded_generic_binding_error=item['evaluation']['binding_error'],
                                     eligible_family_for_binding_gate=row['family'] in ('E5', 'E6'),
                                     counts_toward_binding_gate=row['family'] in ('E5','E6') and item['evaluation']['binding_error'])))
    check(len(observations) == len(run.evidence) == len(run.attempted) == 480, 'complete observation count')
    check(all(not x['frozen_evaluation']['infrastructure_missing'] for x in observations), 'no incomplete observations')
    reports = run.reports()['A']
    family_rows, subtype_rows, fixture_rows, repeat_pairs = [], [], [], []
    for cell in CELLS:
        obs = [x for x in observations if x['schedule']['cell_id'] == cell]
        bases = defaultdict(list)
        for x in obs:
            bases[x['schedule']['logical_base_id']].append(x)
        for base, values in sorted(bases.items()):
            first = values[0]['schedule']
            fixture_rows.append(dict(cell=cell, family=first['family'], subtype=first['subtype'], logical_base_id=base,
                semantic_all=all(x['frozen_evaluation']['semantic_correct'] for x in values),
                structural_all=all(x['frozen_evaluation']['structural_valid'] for x in values),
                useful_all=all(x['frozen_evaluation']['useful'] for x in values),
                false_clean_any=any(x['frozen_evaluation']['false_clean'] for x in values),
                malformed_any=any(x['frozen_evaluation']['malformed'] for x in values),
                binding_error_any=any(x['binding_status']['counts_toward_binding_gate'] for x in values),
                observation_count=len(values), call_ids=[x['schedule']['call_id'] for x in values]))
        rendered = defaultdict(list)
        for x in obs:
            rendered[x['schedule']['rendered_variant_id']].append(x)
        for variant, values in sorted(rendered.items()):
            check(len(values) == 2, 'repeat denominator')
            if all(x['frozen_evaluation']['false_clean'] for x in values):
                signatures = [semantic_signature(x['diagnosis']['parsed_object'], x['schema']) for x in values]
                repeat_pairs.append(dict(cell=cell, family=values[0]['schedule']['family'], subtype=values[0]['schedule']['subtype'],
                    rendered_variant_id=variant, call_ids=[x['schedule']['call_id'] for x in values],
                    outputs=[x['raw_output'] for x in values], expected=values[0]['expected'],
                    raw_byte_identical=values[0]['raw_output'] == values[1]['raw_output'],
                    parsed_exact_schema_semantically_equivalent=signatures[0] is not None and signatures[0] == signatures[1],
                    both_normalized_parsed_objects_identical=canonical(values[0]['diagnosis']['parsed_object']) == canonical(values[1]['diagnosis']['parsed_object']),
                    frozen_correlated_gate_affected=True))
        for family in FAMILIES:
            values = [x for x in obs if x['schedule']['family'] == family]
            fixtures = [x for x in fixture_rows if x['cell'] == cell and x['family'] == family]
            fam = dict(cell=cell, family=family, label=LABELS[family], fixture_count=len(fixtures),
                       rendered_variant_count=len({x['schedule']['rendered_variant_id'] for x in values}),
                       observation_count=len(values),
                       semantic_success_observations=sum(x['frozen_evaluation']['semantic_correct'] for x in values),
                       structural_success_observations=sum(x['frozen_evaluation']['structural_valid'] for x in values),
                       false_clean_observations=sum(x['frozen_evaluation']['false_clean'] for x in values),
                       malformed_observations=sum(x['frozen_evaluation']['malformed'] for x in values),
                       semantic_success_fixtures=sum(x['semantic_all'] for x in fixtures),
                       structural_success_fixtures=sum(x['structural_all'] for x in fixtures),
                       false_clean_fixtures=sum(x['false_clean_any'] for x in fixtures),
                       malformed_fixtures=sum(x['malformed_any'] for x in fixtures),
                       diagnostic_error_counts=dict(Counter(x['diagnosis']['primary_diagnostic_category'] for x in values
                                                            if not x['frozen_evaluation']['semantic_correct'])))
            check(fam['fixture_count'] == 5 and fam['observation_count'] == (20 if family == 'E5' else 10), 'family denominator')
            if family != 'E7':
                check(fam['semantic_success_fixtures'] == reports[cell]['statistics']['family_correct'][family], 'family score replay')
            family_rows.append(fam)
            for subtype in sorted({x['schedule']['subtype'] for x in values}):
                group = [x for x in values if x['schedule']['subtype'] == subtype]
                pos = p.positions[group[0]['schedule']['logical_base_id']]
                subtype_rows.append(dict(cell=cell, family=family, subtype=subtype, frozen_subtype_definition=pos['subtype'],
                    comparison_allocation=pos.get('comparison_allocation'), observation_count=len(group),
                    semantic_success_observations=sum(x['frozen_evaluation']['semantic_correct'] for x in group),
                    structural_success_observations=sum(x['frozen_evaluation']['structural_valid'] for x in group),
                    false_clean_observations=sum(x['frozen_evaluation']['false_clean'] for x in group),
                    malformed_observations=sum(x['frozen_evaluation']['malformed'] for x in group),
                    diagnostic_error_counts=dict(Counter(x['diagnosis']['primary_diagnostic_category'] for x in group
                                                         if not x['frozen_evaluation']['semantic_correct'])),
                    failed_call_ids=[x['schedule']['call_id'] for x in group if not x['frozen_evaluation']['semantic_correct']]))
        logical = [x for x in fixture_rows if x['cell'] == cell]
        check(sum(x['false_clean_any'] for x in logical) == reports[cell]['statistics']['false_clean_fixtures'], 'false-clean fixture reduction')
        check(sum(x['binding_error_any'] for x in logical) == reports[cell]['statistics']['binding_errors'], 'binding reduction')
        check(sum(x['cell'] == cell for x in repeat_pairs) == reports[cell]['statistics']['correlated_false_clean'], 'correlated reduction')

    false_clean = [x for x in observations if x['frozen_evaluation']['false_clean']]
    malformed = [x for x in observations if x['frozen_evaluation']['malformed']]
    failures = [x for x in observations if not x['frozen_evaluation']['semantic_correct']]
    check(len(false_clean) == 92 and len(repeat_pairs) == 42, 'false-clean recorded totals')
    check(sum(x['false_clean_any'] for x in fixture_rows) == 48, 'false-clean fixture total')
    near = [x for x in fixture_rows if x['cell'] == 'large:R2' and not x['semantic_all'] and x['family'] != 'E7']
    check([x['subtype'] for x in near] == ['E1-03','E1-04','E4-01','E4-04'], 'large:R2 exact failure set')
    after = {x.relative_to(ROOT).as_posix(): file_digest(x) for x in watched}
    check(after == before, 'read-only input preservation')
    verification = dict(verdict='PASS', execution_commit=COMMIT, committed_execution_files_verified=committed_files,
        manifest_members_verified=2893, evidence_manifest_sha256=file_digest(run_dir / 'EVIDENCE_MANIFEST.json'),
        post_execution_verification_sha256=file_digest(run_dir / 'POST_EXECUTION_VERIFICATION.json'),
        protected_artifacts_verified=50, implementation_hashes_verified=8, provider_capture_pairs_verified=480,
        scorer_observations_replayed=480, checkpoint_lineages_verified=481, checkpoints_resumed=0,
        journal_counts=dict(journal_counts), authorization_binding_verified=True, schedule_binding_verified=True,
        final_state_and_primary_verdict_replayed=True, incomplete_observations=0, failure_records=0, integrity_events=[],
        phase_b_calls=0, input_byte_preservation_verified=True, input_sha256_before=before, input_sha256_after=after,
        diagnostic_generator_sha256=file_digest(__file__), provider_model_calls_for_diagnosis=0)
    bindings = dict(execution_commit=COMMIT, accepted_science_closure_commit='6c85b10930cefe410a1965c0924e4fd9f47eb4ef',
        run_id=RUN_ID, activation_path=activation_path.relative_to(ROOT).as_posix(), activation_sha256=file_digest(activation_path),
        authorization_path=(run_dir / 'PHASE_A_AUTHORIZATION.json').relative_to(ROOT).as_posix(),
        authorization_sha256=file_digest(run_dir / 'PHASE_A_AUTHORIZATION.json'),
        phase_a_schedule_sha256=digest(canonical(schedule)), result_package_path=(run_dir / 'PHASE_A_RESULT_PACKAGE.json').relative_to(ROOT).as_posix(),
        result_package_sha256=file_digest(run_dir / 'PHASE_A_RESULT_PACKAGE.json'),
        final_report_sha256=file_digest(run_dir / 'PHASE_A_RUN_REPORT.json'), evidence_manifest_sha256=verification['evidence_manifest_sha256'])
    scaling = {}
    keys = ['semantic','structural','useful','false_clean_observations','false_clean_fixtures','malformed','binding_errors','e5_pairs','correlated_false_clean']
    for risk in ('R2','R3'):
        scaling[risk] = {key:[reports[tier + ':' + risk]['statistics'][key] for tier in ('small','mid','large')] for key in keys}
    round_changes = {tier:{key:reports[tier + ':R3']['statistics'][key] - reports[tier + ':R2']['statistics'][key]
                           for key in keys} for tier in ('small','mid','large')}
    family_totals = {}
    for family in FAMILIES:
        values = [x for x in family_rows if x['family'] == family]
        family_totals[family] = {key:sum(x[key] for x in values) for key in
            ['fixture_count','observation_count','semantic_success_observations','structural_success_observations',
             'false_clean_observations','malformed_observations','semantic_success_fixtures']}
    followup = dict(status='PROPOSAL_ONLY_NOT_AUTHORIZED', smallest_scope='large-model calendar-boundary false-clean diagnostic experiment',
        rationale='E1-04 is wrong in all 12 recorded observations (two fixtures across three models and two repeats, not 12 independent fixtures). Both large cells fail the E1 floor; year rollover and the 366-day edge are additional observed large-model errors.',
        focal_classes=['calendar leap boundary','calendar year boundary','366-day calendar edge'],
        candidate_hypotheses=['Calendar-boundary errors persist on fresh independently authored instances.',
            'Exact deterministic calendar checking may expose accepted wrong date outputs.'],
        minimal_prospective_contrasts=['Fresh E1 boundary cases with within-month controls.',
            'Record exact semantic and false-clean outcomes separately from structural acceptance.'],
        separate_followon_hypothesis='E4 composed-comparison failures warrant a separate matched upstream/comparison diagnostic if later authorized; final Boolean outputs do not distinguish the failed substep.',
        retest_strong_families_as_omnibus_gate=False, new_thresholds_defined=False, production_tooling_authorized=False,
        separate_design_and_execution_authorization_required=True)
    diagnostic = dict(schema_version='g-extract1.phase-a-offline-diagnostic.v1', bindings=bindings,
        primary_frozen_verdict=VERDICT, verification=verification,
        interpretation_boundary=['Descriptive benchmark counts only; no A/B or R2/R3 pooling for qualification.',
            'No new scoring rule: every stored evaluation, gate and verdict matches frozen replay.',
            'Diagnostic categories describe visible outputs and gold, not hidden reasoning or proven causes.',
            'Models differ beyond size; risk rounds contain different fixtures and value strata, not an isolated causal risk intervention.',
            'No fresh generalization validation took place because no A cell qualified and Phase B was not executed.',
            'Frozen binding_error is generic accepted-and-incorrect per observation; the binding gate counts only E5/E6 logical fixtures.',
            'Frozen correlated false-clean means both repeats accepted-and-wrong, not necessarily identical wrong values.'],
        per_cell_frozen_reports=reports, family_rows=family_rows, family_totals_descriptive_only=family_totals,
        subtype_rows=subtype_rows, fixture_reductions=fixture_rows, observations=observations,
        false_clean=dict(observation_count=len(false_clean), cell_fixture_instance_count=48,
                         call_ids=[x['schedule']['call_id'] for x in false_clean],
                         fixtures=[x for x in fixture_rows if x['false_clean_any']],
                         error_category_counts=dict(Counter(x['diagnosis']['primary_diagnostic_category'] for x in false_clean))),
        correlated_false_clean=dict(frozen_gate_pair_count=len(repeat_pairs), pairs=repeat_pairs,
            semantically_equivalent_exact_schema_wrong_pair_count=sum(x['parsed_exact_schema_semantically_equivalent'] for x in repeat_pairs),
            identical_normalized_parsed_wrong_pair_count=sum(x['both_normalized_parsed_objects_identical'] for x in repeat_pairs),
            raw_byte_identical_pair_count=sum(x['raw_byte_identical'] for x in repeat_pairs)),
        structural_diagnosis=dict(malformed_observation_count=len(malformed),
            malformed_call_ids=[x['schedule']['call_id'] for x in malformed],
            issue_counts_nonexclusive=dict(Counter(issue for x in malformed for issue in x['diagnosis']['format_issues'])),
            normalization_outcomes=dict(Counter(x['frozen_evaluation']['normalization']['outcome'] for x in observations)),
            wrappers_removed=dict(Counter(x['frozen_evaluation']['normalization'].get('wrapper_removed','') for x in observations)),
            provider_truncated_observations=sum(x['frozen_evaluation']['provider_truncated'] for x in observations),
            duplicate_observations=sum(x['frozen_evaluation']['duplicate_key_present'] for x in observations),
            semantically_invalid_but_operationally_accepted_call_ids=[x['schedule']['call_id'] for x in observations
                if x['frozen_evaluation']['operationally_accepted'] and not x['frozen_evaluation']['semantic_schema_valid']],
            note='Malformed is the frozen operational structural flag. Invalid Gregorian dates can be structurally accepted by the historical validator; no retrospective change.'),
        binding_diagnosis=dict(failure_observations=[x['schedule']['call_id'] for x in failures if x['schedule']['family'] in ('E5','E6')],
            binding_gate_affected_fixtures=[x for x in fixture_rows if x['binding_error_any']],
            exact_wrong_entity_source_match_call_ids=[x['schedule']['call_id'] for x in failures if any(
                e['diagnostic_category'] == 'nonselected_entity_source_value_returned' for e in x['diagnosis']['field_errors'])],
            note='Returning an entity label rather than its field is distinguishable from choosing a neighboring entity field value; do not conflate them.'),
        large_r2=dict(frozen_report=reports['large:R2'], failed_fixtures=near,
            observations=[x for x in observations if x['schedule']['cell_id'] == 'large:R2' and
                          x['schedule']['logical_base_id'] in {y['logical_base_id'] for y in near}],
            correlated_pairs=[x for x in repeat_pairs if x['cell'] == 'large:R2'],
            interpretation='26/30 remains below 29/30; useful 26/30 below 27/30; E1/E4 3/5 below 4/5; false-clean 7 observations/4 fixtures and correlated count 3 violate zero gates. Not qualified or essentially passed.'),
        scaling_descriptive=scaling, r3_minus_r2_descriptive=round_changes,
        supported_components=['large:R2 E2/E3/E5/E6 each 5/5 logical fixtures, structural 30/30 and binding errors 0.',
            'large:R3 E3/E6 each 5/5 logical fixtures; small:R3 E5 counterfactual pairs 5/5.',
            'All six cells E7 recognition/containment 10/10 observations. This is explicit partial absence, not broad ambiguity reasoning.'],
        g_route4_relationship=dict(historical_sha256={x.relative_to(ROOT).as_posix():file_digest(x) for x in historical},
            motivation='Preserved G-ROUTE4 diagnostic records 14/20 unsafe stops in structured extraction; G-EXTRACT1 prospectively tests requalification under the byte-bound baseline.',
            supported_interpretation='Structured extraction remains a qualification weakness under the current configuration. Larger models improve some tested dimensions, but false-clean errors remain and targeted requalification is not supported.',
            historical_result='CLOSED FAILED unchanged', historical_rescoring=False),
        smallest_prospective_followup=followup,
        routing_implications=['No tested cell qualifies for adaptive routing under these frozen extraction gates.',
            'Small-tier weaknesses support prospective exclusion/requalification investigation for the tested calendar/composed numeric/time classes, not a production exclusion policy.',
            'Mid improves R2 semantic count over small but is unchanged on R3 and structurally worse on both; no uniformly beneficial middle-tier fallback is demonstrated.',
            'Large is the best semantic tier in both rounds but insufficient for qualification; necessity for all extraction tasks is not established.',
            'Deterministic computation/checking for calendar and comparisons is a defensible prospective contrast, not runtime authority.'],
        governance=dict(provider_model_calls_this_task=0, provider_metadata_calls_this_task=0, phase_b_calls=0,
            phase_b_authorized=False, corpus_gold_design_blueprint_thresholds_unchanged=True,
            execution_evidence_unchanged=True, autonomy=False, belief_effects='none', g_route4='CLOSED FAILED unchanged'))
    markdown = render_markdown(diagnostic)
    diagnostic_bytes = canonical(diagnostic)
    closure = dict(schema_version='g-extract1.experiment-closure.v1', experiment='G-EXTRACT1',
        experiment_status='CLOSED', execution_status='VALID_COMPLETE', primary_verdict=VERDICT,
        result_interpretation='VALID EXPERIMENT; NEGATIVE QUALIFICATION RESULT; not infrastructure failure',
        bindings=bindings, phase_a_qualified_cells=[], phase_a_nonqualified_cells=CELLS,
        phase_b=dict(eligibility='NOT_ELIGIBLE', execution='NOT_EXECUTED', authorized=False, calls=0,
                     conditional_schedule_count=0, conditional_schedule_sha256=digest(canonical([]))),
        provider_generation_calls=480, completed_responses=480, provider_failures=0, incomplete_observations=0,
        integrity_events=[], checkpoint_resumes=0, verification_summary={k:v for k,v in verification.items()
            if k not in ('input_sha256_before','input_sha256_after')}, per_cell_frozen_reports=reports,
        diagnostic_artifacts_sha256={'PHASE_A_DIAGNOSTIC_REPORT.json':digest(diagnostic_bytes),
            'PHASE_A_DIAGNOSTIC_REPORT.md':digest(markdown), 'build_phase_a_diagnostic.py':file_digest(__file__)},
        future_work_authorized=False, provider_model_calls_for_closure=0, historical_results_changed=False,
        autonomy=False, belief_effects='none', g_route4='CLOSED FAILED unchanged')
    expected = {'PHASE_A_DIAGNOSTIC_REPORT.json':diagnostic_bytes,
                'PHASE_A_DIAGNOSTIC_REPORT.md':markdown, 'G_EXTRACT1_CLOSURE.json':canonical(closure)}
    if write:
        for name, raw in expected.items():
            if name.endswith('.json'):
                write_once(OUT / name, json.loads(raw))
            else:
                with (OUT / name).open('xb') as f:
                    f.write(raw)
    else:
        for name, raw in expected.items():
            check((OUT / name).read_bytes() == raw, 'diagnostic deterministic replay:' + name)
    check({x.relative_to(ROOT).as_posix():file_digest(x) for x in watched} == before, 'after-publication input bytes')
    print(json.dumps(dict(verification='PASS', execution_files=committed_files, protected=50, source=8,
        observations=480, wrong_observations=len(failures), false_clean_observations=len(false_clean),
        malformed_observations=len(malformed), correlated_pairs=len(repeat_pairs),
        identical_wrong_pairs=diagnostic['correlated_false_clean']['identical_normalized_parsed_wrong_pair_count'],
        typed_equivalent_wrong_pairs=diagnostic['correlated_false_clean']['semantically_equivalent_exact_schema_wrong_pair_count'],
        family_totals=family_totals, issue_counts=diagnostic['structural_diagnosis']['issue_counts_nonexclusive'],
        artifacts_sha256={name:file_digest(OUT/name) for name in expected}), indent=2))


def render_markdown(d):
    lines = ['# G-EXTRACT1 Closure and Phase A Diagnostic', '',
        '**CLOSED / VALID_COMPLETE / NO_PHASE_A_CELL_QUALIFIED**', '',
        'This is a valid experiment with a negative qualification result, not an infrastructure failure. '
        '480/480 Phase A observations completed; zero provider failures, incomplete observations, integrity events or Phase B calls. '
        'No cell qualified. Phase B remains unauthorized and was not executed.', '',
        '## Frozen Cell Results', '',
        'Semantic/structural/useful are distinct determinate fixture counts out of 30. '
        'Family counts require both repeats; E5 requires all four counterfactual-pair observations. '
        'FC means operationally accepted but not exactly correct.', '',
        '| Cell | Semantic | Structural | Useful | FC obs/fixtures | Malformed fixtures | Binding fixtures | E5 pairs | Correlated FC |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cell in CELLS:
        s = d['per_cell_frozen_reports'][cell]['statistics']
        lines.append(f"| {cell} | {s['semantic']}/30 | {s['structural']}/30 | {s['useful']}/30 | {s['false_clean_observations']}/{s['false_clean_fixtures']} | {s['malformed']} | {s['binding_errors']} | {s['e5_pairs']}/5 | {s['correlated_false_clean']} |")
    lines += ['', '| Cell | E1 | E2 | E3 | E4 | E5 | E6 | E7 observations |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for cell in CELLS:
        s = d['per_cell_frozen_reports'][cell]['statistics']
        lines.append('| ' + cell + ' | ' + ' | '.join(str(s['family_correct'][f])+'/5' for f in FAMILIES[:-1]) + ' | '+str(s['e7_correct'])+'/10 |')
    lines += ['', 'All cells pass denominator integrity, family/composed coverage and E7 recognition/containment. '
        'All fail semantic, useful, false-clean, family floor and correlated false-clean gates. '
        'Structural/malformed gates pass only small:R3 and both large cells. '
        'Binding gates pass only the large cells. E5 pair gate passes only small:R3 and large:R2. '
        'The JSON report retains every exact Boolean gate outcome.', '',
        '## Family and Subtype Concentrations', '',
        'Each family has 30 cell-fixture instances across six cells. E5 has 120 observations; each other family has 60. '
        'These descriptive totals are not pooled qualification denominators.', '',
        '| Family | Correct observations | Correct fixture instances | FC observations | Malformed observations |',
        '|---|---:|---:|---:|---:|']
    for family, s in d['family_totals_descriptive_only'].items():
        lines.append(f"| {family} {LABELS[family]} | {s['semantic_success_observations']}/{s['observation_count']} | {s['semantic_success_fixtures']}/{s['fixture_count']} | {s['false_clean_observations']} | {s['malformed_observations']} |")
    lines += ['', '| Subtype | Definition | Wrong observations | FC observations | Malformed observations |', '|---|---|---:|---:|---:|']
    for subtype in sorted({x['subtype'] for x in d['subtype_rows']}):
        rows = [x for x in d['subtype_rows'] if x['subtype'] == subtype]
        v = rows[0]['frozen_subtype_definition']
        lines.append(f"| {subtype} | {v['operation_shape']} / {v['coverage_class']} | {sum(x['observation_count']-x['semantic_success_observations'] for x in rows)} | {sum(x['false_clean_observations'] for x in rows)} | {sum(x['malformed_observations'] for x in rows)} |")
    lines += ['', '## Large:R2 Exact Failure Set', '',
        '- E1-03: 2041-12-27 + 12 calendar days = 2042-01-08; repeats returned 2052-01-08 and 2041-01-08.',
        '- E1-04: 2032-02-27 + 6 calendar days = 2032-03-04; both repeats returned 2032-03-05.',
        '- E4-01: (57 + 18) > 74 is true; both repeats returned false.',
        '- E4-04: 23:46 + 40 minutes = 00:26; 00:26 < 00:31 is true. Repeat 1 returned false; repeat 2 was correct.',
        '', 'These four fixtures explain 26/30 semantic, E1/E4 floors of 3/5 and all seven false-clean observations. '
        'E1-03, E1-04 and E4-01 account for three frozen correlated false-clean pairs. '
        'E1-03 is two different wrong results, not an identical-error repeat. '
        'Structural 30/30 and E2/E3/E5/E6 5/5 are component successes, not qualification. '
        'The cell also fails useful 26/30 against 27/30. It is not a partial or essentially passed cell.', '',
        '## False-Clean and Repeat Diagnosis', '',
        '92 accepted-wrong observations affect 48 cell-fixture instances. Every output, expected value, source, schema, '
        'frozen evaluation and diagnostic field mismatch is in the JSON observation ledger. '
        'Invalid Gregorian date values accepted by the historical operational validator remain false-clean; '
        'this diagnostic does not retrospectively tighten the validator.', '',
        f"Both repeats are false-clean in {d['correlated_false_clean']['frozen_gate_pair_count']} rendered-variant pairs. "
        f"{d['correlated_false_clean']['identical_normalized_parsed_wrong_pair_count']} have identical normalized parsed objects; "
        f"{d['correlated_false_clean']['semantically_equivalent_exact_schema_wrong_pair_count']} have the same wrong value under exact typed schema semantics. "
        'The latter excludes invalid calendar dates. The frozen gate counts all both-wrong pairs, including differing errors.', '',
        '## Structural, Format and Binding Findings', '',
        f"Malformed observations: {d['structural_diagnosis']['malformed_observation_count']}. Issues (nonexclusive): "
        + ', '.join(f'{k}={v}' for k,v in sorted(d['structural_diagnosis']['issue_counts_nonexclusive'].items())) + '.',
        '', 'The malformed outputs are valid JSON objects with schema problems, not an invalid-JSON or provider-truncation campaign. '
        'Mid-tier outputs repeatedly include unrequested intermediate/source keys and return entity labels where field values are required. '
        'Small-tier failures include empty objects and invalid minute values. Large:R3 has a leading-space field-name error. '
        'A format wrapper is not itself malformed when the frozen normalizer accepts it; wrapper outcomes are recorded separately. '
        'Prompt causation cannot be inferred because no controlled prompt contrast was run.', '',
        'E5 small:R2 alters 65.5 to 65 and omits one date output. Mid-tier E5 often returns the selected entity label '
        'rather than its requested source value; this is not proof of choosing the wrong entity. '
        'No failed response exactly substitutes a nonselected entity source value. '
        'E6 small-tier numeric copying loses the fraction, and derived-time copying returns incorrect or untransformed source values. '
        'Mid-tier E6 adds intermediate fields even where the expected terminal field is correct. '
        'No article/label-removal mechanism is implicated by an observed exact mismatch. '
        'E5 qualification remains the original two-selector counterfactual pair interpretation.', '',
        '## Scaling and Round Differences', '',
        'Small -> mid -> large semantic fixture counts: R2 15 -> 18 -> 26; R3 16 -> 16 -> 22. '
        'Structural counts are nonmonotonic: R2 28 -> 21 -> 30; R3 29 -> 22 -> 29. '
        'False-clean observations: R2 26 -> 9 -> 7; R3 24 -> 14 -> 12. '
        'Lower mid false-clean counts coexist with much more structural rejection, so they are not standalone proof of safer semantics. '
        'Binding errors decline to zero in both large cells, but large:R3 loses one E5 pair through schema naming.', '',
        'R3 versus R2: small semantic +1 and false-clean -2; mid semantic -2 and false-clean +5; '
        'large semantic -4 and false-clean +5. Large:R3 additionally loses E2 clock/elapsed and E4 comparison fixtures. '
        'Different independent fixture contents and frozen value strata prevent a causal claim from the risk-round label. '
        'Distinct model identities prevent a pure parameter-count scaling claim.', '',
        '## Supported Components and Historical Motivation', '',
        *['- '+x for x in d['supported_components']], '',
        d['g_route4_relationship']['motivation'],
        d['g_route4_relationship']['supported_interpretation'],
        'This does not reopen G-ROUTE4, establish production safety or demonstrate Phase B generalization.', '',
        '## Smallest Prospective Follow-Up', '',
        'Start with a calendar-boundary-only large-model diagnostic on fresh leap/year/366-day cases and within-month controls. '
        'The leap subtype failed in all 12 observations, representing two fixtures across three models and two repeats, '
        'not 12 independent instances. This is the smallest coherent scope supported by the recurring date pattern. '
        'Measure false-clean separately from format success; a deterministic calendar reference-check contrast is justified '
        'for investigation, not authorized implementation. E4 is a separate follow-on hypothesis: matched standalone upstream '
        'versus standalone comparison controls would distinguish subtask patterns that final Booleans alone cannot localize. '
        'Do not automatically retest all seven families or loosen the old gates. New design and execution require separate authorization.', '',
        'No production adaptive-routing policy follows from this run. Large improves several tested dimensions but is insufficient; '
        'mid is not uniformly beneficial; small is not qualified for the tested cells. '
        'Deterministic computation/checking is a prospective hypothesis, not runtime authority.', '',
        '## Verification and Governance', '',
        'Verified actual committed bytes for 2,895 execution files, 2,893 manifest members, 50 protected artifacts and 8 implementation files. '
        'Regenerated 480 requests, replayed all frozen scores and 481 checkpoint lineages, matched the final state/gates/verdict and authorization binding. '
        'All watched input hashes are identical before/after. The original evidence manifest and post-execution supplement remain separate and unchanged.', '',
        'Execution commit: `'+COMMIT+'`', 'Run: `'+RUN_ID+'`', '',
        'Provider/model/metadata calls in this task: 0. Phase B calls: 0; authorization: false. '
        'Corpus, gold, science, implementation, thresholds and historical execution evidence unchanged. '
        'G-ROUTE4 remains CLOSED FAILED. Autonomy false; belief effects none.', '']
    return '\n'.join(lines).encode('utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='exclusive creation of closure artifacts only')
    main(parser.parse_args().write)
