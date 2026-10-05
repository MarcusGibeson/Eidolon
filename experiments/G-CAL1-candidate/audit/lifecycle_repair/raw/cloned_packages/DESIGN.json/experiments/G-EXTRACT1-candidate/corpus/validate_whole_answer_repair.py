"""Offline encoding differential only. Never author, rescore or finalize corpus."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import types
from datetime import date, time
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
ROOT = DESIGN.parent.parent
REPORT = HERE / 'WHOLE_ANSWER_CHECKER_REPAIR_REPORT.json'
DESIGN_COMMIT = 'd1b9e2aa5dbe0aeebb74f8226ca8033182f7b3c1'
BLUEPRINT_COMMIT = 'd8396179204411da15c2dfc330666a490a2287e8'
CHECKER_BASE = '6fb3f2af5806760c034006a8561ce08e938c210a'
CHECKERS = ('validate_corpus.py', 'independent_contamination.py')
HISTORICAL_GOLD_WORKTREE_HASHES = {
    'gold_a.json': '86e1821061cf45e6678b300185aaa05065a289813b7462f3e14cabfa00f4faf9',
    'gold_b.json': '8ab13330c31fb7b5d38c98e9e7e858387e9cd54cc50b1188df2fdc46dad1b078',
    'reserve_gold_a.json': 'a9d81bf7a441d1e3a4bff8597c62f7d9b4b2eb8f4c2d0ea2170c7afb5d9f8079',
    'reserve_gold_b.json': 'c6aa157a3d08f33bc698b6fd4e78c0f7ecb391b34b9c944c1db5228aa9f9bbf6',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit, path):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(),
                                   'show', commit + ':' + path.relative_to(ROOT).as_posix()], cwd=ROOT)


def load(name, path, baseline=False):
    if baseline:
        module = types.ModuleType(name)
        module.__file__ = str(path)
        exec(compile(git_bytes(CHECKER_BASE, path), str(path), 'exec'), module.__dict__)
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot():
    authority = json.loads(git_bytes(DESIGN_COMMIT, DESIGN / 'DESIGN_VALIDATION_REPORT.json'))
    pinned = authority['whole_answer_canonicalization_amendment']
    files = {}
    for relative, item in pinned['preserved_corpus_files'].items():
        name = Path(relative).name
        files[name] = sha((HERE / name).read_bytes())
        if name not in CHECKERS and files[name] != item['after_sha256']:
            raise ValueError('immutable_artifact_changed:' + name)
    original_files = {Path(k).name: v['after_sha256'] for k, v in pinned['preserved_corpus_files'].items()}
    for name in CHECKERS:
        if sha(git_bytes(CHECKER_BASE, HERE / name)) != original_files[name]:
            raise ValueError('checker_base_not_original_snapshot')
    candidates = json.loads((HERE / 'AUTHORING_CANDIDATES.json').read_bytes())
    gold = [[r['logical_base_id'], r['fixture']['gold_values']] for r in candidates['accepted']]
    gold_sha = sha(json.dumps(gold, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('utf-8'))
    if gold_sha != pinned['preserved_gold_projection']['after_sha256']:
        raise ValueError('candidate_gold_changed')
    bound = {}
    for folder, commit, names in (
        (DESIGN, DESIGN_COMMIT, ('DESIGN_CANDIDATE.md', 'DESIGN_CANDIDATE.json',
                                'DESIGN_REVISION_CHANGELOG.md', 'HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md',
                                'validate_design.py', 'DESIGN_VALIDATION_REPORT.json')),
        (DESIGN / 'blueprint', BLUEPRINT_COMMIT, ('BLUEPRINT.json', 'BLUEPRINT.md',
                                                'validate_blueprint.py', 'BLUEPRINT_VALIDATION_REPORT.json', '.gitattributes')),
    ):
        for name in names:
            path = folder / name
            if path.read_bytes() != git_bytes(commit, path): raise ValueError('accepted_artifact_changed:' + name)
            bound[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    historical = {}
    for name, item in pinned['preserved_historical_files'].items():
        path = ROOT / 'experiments/G-ROUTE4-candidate/closure' / name
        historical[name] = sha(path.read_bytes())
        if historical[name] != item['after_sha256']: raise ValueError('historical_closure_changed')
    c = json.loads((DESIGN / 'DESIGN_CANDIDATE.json').read_bytes())
    for binding in c['historical_fingerprint_adapter_contract']['artifact_bindings']:
        path = ROOT / binding['path']
        if sha(path.read_bytes()) != binding['sha256'].lower(): raise ValueError('historical_corpus_changed')
        historical[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
        gold_path = path.with_name(path.name.replace('corpus', 'gold'))
        gold_raw = gold_path.read_bytes()
        if sha(gold_raw) != HISTORICAL_GOLD_WORKTREE_HASHES[gold_path.name]:
            raise ValueError('historical_gold_worktree_changed')
        if gold_raw.replace(b'\r\n', b'\n') != git_bytes(BLUEPRINT_COMMIT, gold_path):
            raise ValueError('historical_gold_committed_content_changed')
        historical[gold_path.relative_to(ROOT).as_posix()] = sha(gold_path.read_bytes())
    return dict(files=files, original_before_files=original_files, gold_projection_sha256=gold_sha,
                accepted_artifacts_sha256=bound, historical_sha256=historical)


def scope_audit():
    """Restore only the answer expression, then require complete AST equality."""
    result = {}
    for name in CHECKERS:
        path = HERE / name
        original_text = git_bytes(CHECKER_BASE, path).decode('utf-8-sig')
        current_text = path.read_text(encoding='utf-8-sig')
        original = ast.parse(original_text)
        current = ast.parse(current_text)
        old_functions = {n.name: n for n in original.body if isinstance(n, ast.FunctionDef)}
        new_functions = {n.name: n for n in current.body if isinstance(n, ast.FunctionDef)}
        additions = set(new_functions) - set(old_functions)
        expected = {'whole_answer_text', 'whole_answer_bytes', 'require_whole_answer_bytes'} if name == CHECKERS[0] else {
            'whole_answer_value', 'whole_answer_render', 'whole_answer_bytes', 'require_whole_answer_bytes'}
        if additions != expected: raise ValueError('unexpected_checker_functions:' + name)
        normalized = copy.deepcopy(current)
        normalized.body = [n for n in normalized.body if not (isinstance(n, ast.FunctionDef) and n.name in additions)]
        integration = 'cache' if name == CHECKERS[0] else 'evidence'
        node = next(n for n in normalized.body if isinstance(n, ast.FunctionDef) and n.name == integration)
        old_node = old_functions[integration]
        if integration == 'cache':
            new_answer = next(n for n in node.body if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == 'answer' for t in n.targets))
            old_answer = next(n for n in old_node.body if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == 'answer' for t in n.targets))
            new_answer.value = copy.deepcopy(old_answer.value)
        else:
            ret = next(n for n in node.body if isinstance(n, ast.Return))
            old_ret = next(n for n in old_node.body if isinstance(n, ast.Return))
            next(k for k in ret.value.keywords if k.arg == 'answer').value = copy.deepcopy(
                next(k for k in old_ret.value.keywords if k.arg == 'answer').value)
        if ast.dump(normalized, include_attributes=False) != ast.dump(original, include_attributes=False):
            raise ValueError('unrelated_checker_AST_change:' + name)
        # Also compare exact source text of every unaffected function.
        untouched = []
        for function, old_node in old_functions.items():
            if function == integration: continue
            new_node = new_functions[function]
            old_span = '\n'.join(original_text.splitlines()[old_node.lineno-1:old_node.end_lineno])
            new_span = '\n'.join(current_text.splitlines()[new_node.lineno-1:new_node.end_lineno])
            if old_span != new_span: raise ValueError('unrelated_function_text_change:' + name + ':' + function)
            untouched.append(function)
        for function in additions:
            for n in ast.walk(new_functions[function]):
                if isinstance(n, ast.Name) and n.id in {'D', 'B', 'primary', 'independent', 'helper'}:
                    raise ValueError('shared_whole_answer_helper:' + name)
        imports_old = [ast.dump(n, include_attributes=False) for n in original.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        imports_new = [ast.dump(n, include_attributes=False) for n in current.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        if imports_old != imports_new: raise ValueError('checker_import_change')
        result[name] = dict(whole_only_integration=integration, whole_answer_functions=sorted(additions),
                            unchanged_existing_functions=untouched, imports_unchanged=True,
                            restored_answer_expression_full_AST_equal=True, unaffected_function_text_equal=True)
    return result


def mutations():
    packed = lambda rows: json.dumps(rows, ensure_ascii=True, separators=(',', ':')).encode('utf-8')
    cases = []
    for name, schema, value, tag, bad in (
        ('boolean_scalar_true', 'boolean', True, 'BOOLEAN', True), ('boolean_scalar_false', 'boolean', False, 'BOOLEAN', False),
        ('integer_numeric_scalar', 'integer', '0', 'INTEGER', 0), ('number_numeric_scalar', 'number', '5', 'NUMBER', 5),
        ('number_exponent', 'number', '5e0', 'NUMBER', '5e0'), ('number_trailing_zeroes', 'number', '5.00', 'NUMBER', '5.00'),
        ('number_negative_zero', 'number', '-0.0', 'NUMBER', '-0'), ('integer_negative_zero', 'integer', '-0', 'INTEGER', '-0'),
        ('date_reformatted', 'YYYY-MM-DD', '2039-10-05', 'DATE', '10/05/2039'),
        ('time_reformatted', 'HH:MM', '23:45', 'TIME', '11:45 PM'),
        ('string_trimmed', 'string', ' label_001_01 ', 'STRING', 'label_001_01'),
        ('enum_ordinal', 'option_a|option_b', 'option_b', 'ENUM', 1),
        ('not_provided_null', 'provided|not_provided', 'not_provided', 'ENUM', None),
        ('null_value', 'integer', '0', 'INTEGER', None), ('array_value', 'integer', '0', 'INTEGER', []),
        ('object_value', 'integer', '0', 'INTEGER', {}),
    ): cases.append((name, [['field', schema, value]], packed([['field', schema, [tag, bad]]])))
    base = [['field', 'integer', '0']]
    for name, bad in (
        ('tag_lowercase', [['field', 'integer', ['integer', '0']]]),
        ('tag_replaced_by_schema', [['field', 'integer', ['integer', '0']]]),
        ('schema_replaced_by_tag', [['field', 'INTEGER', ['INTEGER', '0']]]),
        ('typed_numeric_collapse', [['field', 'integer', ['NUMBER', '0']]]),
        ('inner_missing_element', [['field', 'integer', ['INTEGER']]]),
        ('inner_extra_element', [['field', 'integer', ['INTEGER', '0', 'extra']]]),
        ('outer_missing_element', [['field', ['INTEGER', '0']]]),
        ('outer_extra_element', [['field', 'integer', ['INTEGER', '0'], 'extra']]),
    ): cases.append((name, base, packed(bad)))
    good = [['field', 'integer', ['INTEGER', '0']]]
    cases.extend([
        ('ensure_ascii_false', [['field', 'string', '\u00e9']], json.dumps([['field', 'string', ['STRING', '\u00e9']]], ensure_ascii=False, separators=(',', ':')).encode('utf-8')),
        ('pretty_JSON', base, json.dumps(good, indent=2).encode('utf-8')),
        ('terminal_newline', base, packed(good) + b'\n'),
        ('wrong_field_sorting', [['z', 'integer', '0'], ['a', 'integer', '1']], packed([['z', 'integer', ['INTEGER', '0']], ['a', 'integer', ['INTEGER', '1']]])),
    ])
    return cases


def validate():
    before = snapshot()
    scope = scope_audit()
    primary = load('whole_primary', HERE / CHECKERS[0])
    independent = load('whole_independent', HERE / CHECKERS[1])
    old_primary = load('old_whole_primary', HERE / CHECKERS[0], True)
    old_independent = load('old_whole_independent', HERE / CHECKERS[1], True)
    c, b = primary.C, primary.B
    accepted = c['whole_answer_canonicalization_contract']
    if b['whole_answer_serialization_plan']['materialized_contract'] != accepted: raise ValueError('whole_answer_blueprint_binding')
    encoders = (primary.whole_answer_bytes, lambda rows: independent.whole_answer_bytes(rows, c))
    guards = (primary.require_whole_answer_bytes, lambda raw, rows: independent.require_whole_answer_bytes(raw, rows, c))
    checks = []
    def require(ok, label):
        if not ok: raise ValueError(label)
        checks.append(label)
    vectors = []
    tags = set()
    for vector in accepted['validation_vectors']:
        left, right = [encode(vector['semantic_rows']) for encode in encoders]
        require(left == right == vector['expected_utf8'].encode('utf-8'), 'semantic_vector:' + vector['id'])
        require(json.loads(left) == vector['expected_rows'], 'semantic_rows:' + vector['id'])
        require(all(type(x) is str for row in json.loads(left) for x in (row[0], row[1], *row[2])), 'all_string_leaves:' + vector['id'])
        require(all(encode(list(reversed(vector['semantic_rows']))) == left for encode in encoders), 'field_order:' + vector['id'])
        tags.update(row[2][0] for row in json.loads(left))
        vectors.append(dict(id=vector['id'], primary_sha256=sha(left), independent_sha256=sha(right), agreement=True))
    require(tags == set(accepted['semantic_tags']), 'seven_tags')
    for group in accepted['equivalence_groups']:
        require({encode([['field', group['schema_type'], v]]) for encode in encoders for v in group['values']}
                == {group['expected_utf8'].encode('utf-8')}, 'numeric_equivalence:' + group['id'])
    for schema in ('integer', 'number'):
        for v in (0, 1, -1, 42, 10**100 + 1):
            require(len({encode([['field', schema, x]]) for encode in encoders for x in (v, str(v), Decimal(str(v)), Fraction(v))}) == 1,
                    'host_types:' + schema + ':' + str(v))
    for value, text in ((Fraction(1, 8), '0.125'), (Fraction(-617, 50), '-12.34'),
                        (Decimal('123456789012345678901234567890.125000'), '123456789012345678901234567890.125')):
        with localcontext() as context:
            context.prec = 2
            expected = json.dumps([['field', 'number', ['NUMBER', text]]], separators=(',', ':')).encode()
            require(all(encode([['field', 'number', value]]) == expected for encode in encoders), 'exact_no_context_rounding:' + text)
    for schema, value, text in (('YYYY-MM-DD', date(2039, 10, 5), '2039-10-05'), ('HH:MM', time(23, 45), '23:45')):
        require(all(encode([['field', schema, value]]) == encode([['field', schema, text]]) for encode in encoders), 'temporal_host:' + schema)
    for i, (left, right) in enumerate([
        ([['field', 'integer', '5']], [['field', 'number', '5']]),
        ([['field', 'number', '5']], [['field', 'number', '5.0001']]),
        ([['field', 'number', '0.5']], [['field', 'number', '0.05']]),
        ([['field', 'boolean', True]], [['field', 'string', 'true']]),
        ([['field', 'string', '\u00e9']], [['field', 'string', 'e\u0301']]),
    ]): require(all(encode(left) != encode(right) for encode in encoders), 'distinctness:' + str(i))
    mutation_results = []
    for name, rows, altered in mutations():
        for label, guard in zip(('primary', 'independent'), guards):
            try: guard(altered, rows)
            except ValueError: checks.append('mutation_rejected:' + label + ':' + name)
            else: raise ValueError('mutation_accepted:' + label + ':' + name)
        mutation_results.append(dict(id=name, primary_rejected=True, independent_rejected=True))
    require({r['id'] for r in mutation_results} == set(accepted['mutation_catalog']), 'exact_accepted_mutation_catalog')
    class DisplayOnly:
        def __str__(self): return '5'
    bad = [
        [['field', 'integer', True]], [['field', 'integer', 5.0]], [['field', 'integer', '5e0']],
        [['field', 'integer', '05']], [['field', 'integer', '+5']], [['field', 'integer', Fraction(1, 2)]],
        [['field', 'number', 0.5]], [['field', 'number', True]], [['field', 'number', 'NaN']],
        [['field', 'number', Fraction(1, 3)]], [['field', 'number', object()]],
        [['field', 'number', DisplayOnly()]], [['field', 'integer', DisplayOnly()]],
        [['field', 'boolean', 'true']], [['field', 'boolean', 1]], [['field', 'YYYY-MM-DD', '2039-02-29']],
        [['field', 'YYYY-MM-DD', '2039-1-05']], [['field', 'HH:MM', '24:00']], [['field', 'HH:MM', '3:45']],
        [['field', 'option_a|option_b', 0]], [['field', 'option_a|option_b', 'option_c']],
        [['field', 'DATE', '2039-10-05']], [['field', 'date', '2039-10-05']],
        [['field', 'TIME', '23:45']], [['field', 'time', '23:45']], [['field', 'ENUM', 'not_provided']],
        [['field', 'string', None]], [['field', 'string', '\ud800']], [['\ud800', 'string', 'value']],
        [['field', 'integer', '0'], ['field', 'integer', '1']], [['field', 'integer']],
        [['field', 'integer', '0', 'extra']], [[1, 'integer', '0']], [['field', 'integer', {'display': '0'}]],
    ]
    for i, rows in enumerate(bad):
        for label, encode in zip(('primary', 'independent'), encoders):
            try: encode(rows)
            except (ValueError, TypeError, UnicodeError): checks.append('invalid_semantics:' + label + ':' + str(i))
            else: raise ValueError('invalid_semantics_accepted:' + label + ':' + str(i))
    candidates = json.loads((HERE / 'AUTHORING_CANDIDATES.json').read_bytes())
    bases = {r['logical_base_id']: r['fixture'] for r in candidates['accepted']}
    require(len(bases) == 168, '168_immutable_bases')
    variants, base_results = [], []
    failure = None
    for p in b['logical_positions']:
        fixture = bases[p['logical_base_id']]
        require(primary.independent_gold(fixture)[0] == fixture['gold_values'], 'gold_unchanged:' + p['logical_base_id'])
        rows = [[f['name'], f['schema_type'], fixture['gold_values'][f['name']]] for f in fixture['output_fields']]
        left, right = [encode(rows) for encode in encoders]
        require(left == right, 'base_answer:' + p['logical_base_id'])
        base_results.append(dict(logical_base_id=p['logical_base_id'], primary_sha256=sha(left), independent_sha256=sha(right), agreement=True))
        members = primary.D.counterfactual_members(fixture, dict(p['subtype'], phase=p['phase'], risk_round=p['risk_round']), c) if p['family'] == 'E5' else [fixture]
        for index, member in enumerate(members):
            variant = 'CF' + str(index+1) if p['family'] == 'E5' else 'SINGLE'
            first = primary.cache(member, p, variant)
            second = independent.evidence(member, first['request'], c)
            require(first['answer'] == second['answer'], 'variant_answer:' + p['logical_base_id'] + ':' + variant)
            rows = [[f['name'], f['schema_type'], member['gold_values'][f['name']]] for f in member['output_fields']]
            require(first['answer'] == encoders[0](rows) == encoders[1](rows), 'answer_integration:' + p['logical_base_id'] + ':' + variant)
            old_first = old_primary.cache(member, p, variant)
            old_second = old_independent.evidence(member, first['request'], c)
            require({k:v for k,v in first.items() if k != 'answer'} == {k:v for k,v in old_first.items() if k != 'answer'},
                    'primary_nonanswer_evidence_exact:' + p['logical_base_id'] + ':' + variant)
            require({k:v for k,v in second.items() if k != 'answer'} == {k:v for k,v in old_second.items() if k != 'answer'},
                    'independent_nonanswer_evidence_exact:' + p['logical_base_id'] + ':' + variant)
            require(all(first[k] == second[k] for k in second if k != 'answer'), 'nonanswer_differential:' + p['logical_base_id'] + ':' + variant)
            variants.append(dict(logical_base_id=p['logical_base_id'], rendered_variant_id=p['logical_base_id']+':'+variant,
                                 variant_id=variant, primary_sha256=sha(first['answer']), independent_sha256=sha(second['answer']), agreement=True))
            if p['logical_base_id'] == 'A:R2:E4-01:PRIMARY':
                require(first['answer'] == b'[["d016_02","boolean",["BOOLEAN","true"]]]', 'original_failure_exact_new_bytes')
                stop = json.loads((HERE / 'FINALIZATION_CONTAMINATION_DISAGREEMENT_REPORT.json').read_bytes())['disagreement']
                require(old_first['answer'].decode() == stop['primary_bytes_utf8'] and old_second['answer'].decode() == stop['independent_bytes_utf8'], 'original_failure_old_path_reconstructed')
                failure = dict(logical_base_id=p['logical_base_id'], before_primary_utf8=old_first['answer'].decode(),
                               before_independent_utf8=old_second['answer'].decode(), after_primary_utf8=first['answer'].decode(),
                               after_independent_utf8=second['answer'].decode(), agreement=True)
    require({r['rendered_variant_id'] for r in variants} == {r['rendered_variant_id'] for r in b['rendered_variants']}
            and len(variants) == 192, 'exact_192_variants')
    require(failure is not None, 'original_failure_present')
    historical = []
    for binding in c['historical_fingerprint_adapter_contract']['artifact_bindings']:
        path = ROOT / binding['path']
        gold_path = path.with_name(path.name.replace('corpus', 'gold'))
        items = json.loads(gold_path.read_bytes(), parse_float=Decimal)['items']
        gold_map = {r['fixture_id']: r['expected'] for r in items}
        for fixture in json.loads(path.read_bytes())['fixtures']:
            if fixture['task_class'] != 'structured_extraction': continue
            schema = fixture['input']['schema']
            gold = gold_map[fixture['fixture_id']]
            require(set(schema) == set(gold), 'historical_gold_schema:' + fixture['fixture_id'])
            rows = [[field, s, gold[field]] for field, s in schema.items()]
            left, right = [encode(rows) for encode in encoders]
            require(left == right, 'historical_encoding:' + fixture['fixture_id'])
            historical.append(dict(path=binding['path'], fixture_id=fixture['fixture_id'], primary_sha256=sha(left), independent_sha256=sha(right), agreement=True))
    require(len(historical) == 106, '106_historical_answers_encoded_without_artifact_edits')
    # Replay the preserved freshness test body. Only obsolete metadata wrappers
    # are rebound in memory after the stronger whole-only scope audit above.
    fresh = load('preserved_freshness_suite', HERE / 'validate_freshness_repair.py')
    fresh.preservation_snapshot = snapshot
    fresh.scope_audit = scope_audit
    fresh.SPECIFICATION_COMMITS = dict(fresh.SPECIFICATION_COMMITS, blueprint=BLUEPRINT_COMMIT,
                                      whole_answer_amendment=DESIGN_COMMIT)
    freshness = fresh.validate()
    previous = json.loads((HERE / 'FRESHNESS_CHECKER_REPAIR_REPORT.json').read_bytes())
    require(freshness['checks'] == previous['checks'] and freshness['check_count'] == 811,
            '811_original_freshness_behavioral_checks_exactly_replayed')
    require(freshness['variant_results'] == previous['variant_results'] and freshness['rendered_variant_count'] == 192
            and freshness['disagreement_count'] == 0, '192_freshness_results_exactly_preserved')
    for key in ('schema_vector_results', 'numeric_equivalence_results', 'host_type_results', 'invalid_semantic_inputs', 'mutation_results', 'existing_gold_replay'):
        require(freshness[key] == previous[key], 'freshness_prior_result_exact:' + key)
    after = snapshot()
    require(before == after, 'all_current_artifacts_unchanged_during_validation')
    return dict(
        schema_version='g-extract1.whole-answer-checker-repair.v1', verdict='PASS',
        status='READY_TO_RESUME_G_EXTRACT1_CORPUS_FINALIZATION',
        accepted_design_commit=DESIGN_COMMIT, accepted_blueprint_commit=BLUEPRINT_COMMIT,
        accepted_freshness_amendment='e12484224cd11cf9c84026eb7deadf8c4eb9bab8', checker_base_commit=CHECKER_BASE,
        canonicalization_contract_id=accepted['contract_id'], normative_path='DESIGN_CANDIDATE.json#/whole_answer_canonicalization_contract',
        root_cause='Primary used legacy imported canonical_answer_bytes; independent reused canon/dump with native BOOLEAN values. Display/gold/tuple representations were not completed whole-answer storage.',
        primary_implementation='Local validated-schema conversion; unchanged local fixed() exact rational power-of-ten scaler; separate whole-answer rows/ASCII serialization.',
        independent_implementation='Local typed parse into exact Fraction/Boolean/text; separate long-division renderer; independent field-index assembly and ASCII serialization.',
        shared_whole_answer_helper=False, scope_audit=scope,
        primary_checker_sha256=after['files'][CHECKERS[0]], independent_checker_sha256=after['files'][CHECKERS[1]],
        test_script_sha256=sha(Path(__file__).read_bytes()),
        original_before=before['original_before_files'], replay_before=before, after=after,
        original_failure_replay=failure, semantic_vector_count=len(vectors), semantic_vector_results=vectors,
        semantic_tags=sorted(tags), numeric_equivalence_groups=len(accepted['equivalence_groups']),
        mutation_count=len(mutation_results), mutation_results=mutation_results,
        invalid_semantic_input_count=len(bad), logical_base_count=len(base_results), base_results=base_results,
        rendered_variant_count=len(variants), variant_results=variants, disagreement_count=0,
        historical_encoding_count=len(historical), historical_encoding_results=historical,
        historical_encoding_scope='106 historical and 192 NEW answers encoded independently; no pairwise final contamination decisions',
        freshness_certification=dict(verdict='PASS', check_count=811, rendered_variant_count=192, disagreement_count=0,
            prior_checks_and_vector_results_exact=True, preserved_test_script_and_report_unchanged=True,
            method='Unchanged original validate() behavioral body; obsolete snapshot/scope wrappers rebound in memory to accepted lineage and independently verified whole-only AST audit; no source/report edits.'),
        check_count=len(checks), checks=checks, final_contamination_campaign_run=False, corpus_accepted=False,
        corpus_finalized=False, manifest_frozen=False,
        governance=dict(provider_model_calls=0, corpus_regeneration=0, gold_modifications=0, design_changes=0,
            blueprint_changes=0, runtime_implementation=False, experiment_execution=False,
            G_ROUTE4='CLOSED FAILED unchanged', belief_effects='none'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-report', action='store_true', help='Write narrow repair report only after all checks pass.')
    args = parser.parse_args()
    report = validate()
    if args.write_report:
        REPORT.write_bytes((json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    elif json.loads(REPORT.read_bytes()) != report: raise ValueError('whole_answer_repair_report_stale')
    print(json.dumps({k: report[k] for k in ('verdict', 'check_count', 'semantic_vector_count', 'mutation_count',
                                            'logical_base_count', 'rendered_variant_count', 'historical_encoding_count',
                                            'disagreement_count', 'freshness_certification', 'corpus_finalized')}, indent=2))


if __name__ == '__main__':
    main()
