"""Read-only bindings and request materialization for G-EXTRACT1.

No provider import, discovery, metadata request or transport lives in this module.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'experiments/G-EXTRACT1-candidate'
PACKAGE_COMMIT = '81dc9d05f49e9c1310bb38676bfd7cf6a8620cf7'
AUDIT_COMMIT = '6c85b10930cefe410a1965c0924e4fd9f47eb4ef'
MANIFEST_SHA = 'aad9f460edd373f5ce3a0b5469449e4b6df918081c956ca819c1b515f8ca1042'
AUDIT_SHA = 'dc75c2c40635a93babf0fb903521f54489f3fed4ff06128ae866801310df9c97'
CANDIDATE_SHA = 'f575c8d86ca82f2c5ea7727404d0c8bbb5a72f7b472abfd244471edb3180d068'
GOLD_PROJECTION_SHA = '803e8e4c57b63c7edb22f02194cbefdbf6be3fc964a0d77f65faa658f8904aec'
VERSION = 'g-extract1.execution-contract.v2'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_artifact_key:' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


class IntegrityError(RuntimeError):
    def __init__(self, event, detail=''):
        self.event, self.detail = event, detail
        super().__init__(event + ':' + detail)


def require(condition, event, detail=''):
    if not condition:
        raise IntegrityError(event, detail)


class Package:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.data = self.root / 'experiments/G-EXTRACT1-candidate'
        self.manifest_path = self.data / 'corpus/CORPUS_MANIFEST.json'
        require(digest(self.manifest_path.read_bytes()) == MANIFEST_SHA,
                'PRE_ARTIFACT_DIGEST_MISMATCH', 'manifest')
        self.manifest = load(self.manifest_path)
        self.pins, self.pin_categories = {}, {}
        prefix = 'experiments/G-EXTRACT1-candidate/corpus/'
        def pin(path, sha, category):
            require(path not in self.pins or self.pins[path] == sha,
                    'PRE_ARTIFACT_DIGEST_MISMATCH', 'contradictory manifest pin:' + path)
            self.pins[path] = sha
            self.pin_categories[path] = category
        for group, category in [('authority_artifacts_sha256','authority'), ('final_artifacts_sha256','final'),
                                ('checker_artifacts_sha256','checker'),
                                ('preserved_authoring_failure_and_repair_artifacts_sha256','preserved')]:
            for name, sha in self.manifest[group].items():
                pin(name if group == 'authority_artifacts_sha256' else prefix + name, sha, category)
        # These scalar pins are file bindings, not semantic projection digests.
        scalar_paths = dict(candidate_source_sha256='AUTHORING_CANDIDATES.json',
                            finalizer_sha256='validate_finalization.py',
                            checker_applicability_report_sha256='TUPLE_APPLICABILITY_CHECKER_REPORT.json',
                            independent_prepublication_audit_sha256='REVIEW_CLOSURE_PREPUBLICATION_AUDIT.json',
                            prior_external_review_history_sha256='CORPUS_GOLD_REREVIEW_HISTORY.json')
        for key, name in scalar_paths.items():
            pin(prefix + name, self.manifest[key], 'source_or_supplement')
        covered = set(scalar_paths) | {'gold_projection_sha256'}
        covered |= {'authority_artifacts_sha256', 'final_artifacts_sha256', 'checker_artifacts_sha256',
                    'preserved_authoring_failure_and_repair_artifacts_sha256'}
        require({x for x in self.manifest if x.endswith('_sha256')} == covered,
                'PRE_ARTIFACT_DIGEST_MISMATCH', 'unclassified manifest digest')
        self.pins['experiments/G-EXTRACT1-candidate/corpus/CORPUS_MANIFEST.json'] = MANIFEST_SHA
        self.pins['experiments/G-EXTRACT1-candidate/corpus/FINAL_READ_ONLY_CLOSURE_AUDIT.json'] = AUDIT_SHA
        self.verify()
        self.design = load(self.data / 'DESIGN_CANDIDATE.json')
        for row in self.design['baseline_binding']['existing_behavior_artifacts']:
            self.pins[row['path']] = row['sha256']
        self.verify()
        self.blueprint = load(self.data / 'blueprint/BLUEPRINT.json')
        self.audit = load(self.data / 'corpus/FINAL_READ_ONLY_CLOSURE_AUDIT.json')
        require(self.audit['verdict'] == 'PASS' and self.audit['republished_package_commit'] == PACKAGE_COMMIT,
                'PRE_ARTIFACT_DIGEST_MISMATCH', 'closure')
        require(self.manifest['candidate_source_sha256'] == CANDIDATE_SHA and
                self.manifest['gold_projection_sha256'] == GOLD_PROJECTION_SHA,
                'PRE_GOLD_DIGEST_MISMATCH', 'source bindings')
        require(load(self.data / 'corpus/CONTAMINATION_REPORT.json')['verdict'] == 'PASS_SUPPORTED_CONTROLS',
                'PRE_CONTAMINATION_AUDIT_FAILURE')
        # Git object provenance is checked independently of working-tree digests.
        for commit, relative in [(PACKAGE_COMMIT, self.manifest_path.relative_to(self.root).as_posix()),
                                 (AUDIT_COMMIT, 'experiments/G-EXTRACT1-candidate/corpus/FINAL_READ_ONLY_CLOSURE_AUDIT.json')]:
            result = subprocess.run(['git', '-c', 'safe.directory=' + self.root.as_posix(),
                                     'show', commit + ':' + relative], cwd=self.root, capture_output=True)
            require(result.returncode == 0 and digest(result.stdout) == self.pins[relative],
                    'PRE_ARTIFACT_DIGEST_MISMATCH', 'Git provenance:' + relative)
        self.positions = {x['logical_base_id']: x for x in self.blueprint['logical_positions']}
        self.variants = {}
        for name in ('SCORED_CORPUS.json', 'RESERVE_CORPUS.json'):
            for row in load(self.data / 'corpus' / name)['rendered_variants']:
                require(row['rendered_variant_id'] not in self.variants, 'PRE_ARTIFACT_DIGEST_MISMATCH', 'variant duplicate')
                self.variants[row['rendered_variant_id']] = row
        gold = {x['rendered_variant_id']: x['gold'] for x in load(self.data / 'corpus/GOLD.json')['rendered']}
        require(set(gold) == set(self.variants), 'PRE_GOLD_DIGEST_MISMATCH', 'variant keys')
        for key, row in self.variants.items():
            require(row['gold'] == gold[key] == row['fixture']['gold_values'], 'PRE_GOLD_DIGEST_MISMATCH', key)
        self.model_bindings = load(self.root / 'experiments/G-ROUTE4-candidate/model_bindings.json')
        candidates = load(self.data / 'corpus/AUTHORING_CANDIDATES.json')
        projection = [[row['logical_base_id'], row['fixture']['gold_values']] for row in candidates['accepted']]
        projection_bytes = json.dumps(projection, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('utf-8')
        require(digest(projection_bytes) == GOLD_PROJECTION_SHA,
                'PRE_GOLD_DIGEST_MISMATCH', 'semantic source projection')

    def verify(self, contacted=False):
        for relative, expected in self.pins.items():
            path = self.root / relative
            event = ('GOLD_DIGEST_MISMATCH' if contacted else 'PRE_GOLD_DIGEST_MISMATCH') if relative.endswith('/GOLD.json') else (
                'PROTECTED_ARTIFACT_DIGEST_MISMATCH' if contacted else 'PRE_ARTIFACT_DIGEST_MISMATCH')
            require(path.is_file() and file_digest(path) == expected, event, relative)

    def receipts(self):
        """Expected identities, not evidence of installed provider state."""
        return self.design['model_provider']

    def verify_receipts(self, receipts, contacted=False):
        expected = self.receipts()
        for key, pre, post in [
            ('models', 'PRE_MODEL_IDENTITY_MISMATCH', 'MODEL_IDENTITY_MISMATCH_AFTER_CONTACT'),
            ('provider', 'PRE_PROVIDER_VERSION_MISMATCH', 'PROVIDER_VERSION_MISMATCH_AFTER_CONTACT'),
            ('provider_version', 'PRE_PROVIDER_VERSION_MISMATCH', 'PROVIDER_VERSION_MISMATCH_AFTER_CONTACT'),
            ('generation_configuration', 'PRE_GENERATION_CONFIG_MISMATCH', 'GENERATION_CONFIGURATION_MISMATCH')]:
            require(receipts.get(key) == expected[key], post if contacted else pre, key)

    def skeleton(self, phase, replacements=None):
        require(phase in ('A', 'B'), 'PRE_SCHEDULE_DIGEST_MISMATCH', 'phase')
        replacements = replacements or {}
        active = [(p['logical_base_id'], self.positions[replacements.get(p['logical_base_id'], p['logical_base_id'])])
                  for p in self.positions.values() if p['phase'] == phase and p['primary_or_reserve'] == 'PRIMARY']
        active.sort(key=lambda x: x[1]['fixture_ordinal'])
        models = self.design['model_provider']['models']
        ranks = {'R2': 0, 'R3': 0}
        result = []
        for qualification_slot, p in active:
            risk = p['risk_round']
            start = (ranks[risk] + (0 if risk == 'R2' else 35)) % 3
            ranks[risk] += 1
            variants = sorted((x for x in self.variants.values() if x['logical_base_id'] == p['logical_base_id']),
                              key=lambda x: x['variant_id'])
            for model in models[start:] + models[:start]:
                for repeat in range(1, 3 if phase == 'A' else 2):
                    for variant in variants:
                        result.append(dict(template_schedule_position=len(result)+1,
                            call_id=f"{phase}:{model['tier']}:{risk}:{p['logical_base_id']}:{variant['variant_id']}:{repeat}",
                            cell_id=f"{model['tier']}:{risk}", model=model['model'], tier=model['tier'],
                            qualification_slot_id=qualification_slot, logical_base_id=p['logical_base_id'],
                            rendered_variant_id=variant['rendered_variant_id'], variant_id=variant['variant_id'],
                            repeat=repeat, seed=self.design['sampling']['candidate_phase_' + phase.lower() + '_seed_base'] +
                            (p['fixture_ordinal']-1)*10+repeat,
                            request_ref='DESIGN_CANDIDATE.json#/' + ('e5_counterfactual_selector_contract/request_contract'
                            if p['family'] == 'E5' else 'baseline_binding')))
        if not replacements:
            frozen = self.blueprint['schedule_plan']['phase_a' if phase == 'A' else 'phase_b_maximum_template']
            require(result == frozen, 'PRE_SCHEDULE_DIGEST_MISMATCH', 'frozen template')
        return result

    def wire(self, row):
        variant = self.variants[row['rendered_variant_id']]
        request = variant['request']
        options = dict(self.model_bindings['generation_configuration']['options'], seed=row['seed'])
        body = dict(model=row['model'], system=self.design['baseline_binding']['system_text'],
                    prompt=request['prompt'] + '\n\nINPUT:\n' + canonical(request['input']).decode('utf-8'),
                    stream=False, think=False, options=options)
        return canonical(body)

    def schedule(self, phase, qualified=None, replacements=None):
        rows = self.skeleton(phase, replacements)
        if phase == 'B':
            require(qualified is not None and qualified == sorted(set(qualified)) and
                    set(qualified) <= set(self.blueprint['schedule_plan']['phase_b_cell_order']),
                    'PROVENANCE_MISMATCH', 'B eligibility')
            rows = [x for x in rows if x['cell_id'] in qualified]
        for index, row in enumerate(rows, 1):
            row['schedule_position'] = index
            p = self.positions[row['logical_base_id']]
            row.update(phase=phase, risk_round=p['risk_round'], family=p['family'], subtype=p['subtype_slot'],
                       request_sha256=digest(self.wire(row)),
                       gold_sha256=digest(canonical(self.variants[row['rendered_variant_id']]['gold'])),
                       scorer_version='g-extract1.semantic-scorer.v1',
                       comparator_version='g-extract1.exact-value-comparator.v1',
                       provider=self.design['model_provider']['provider'],
                       provider_version=self.design['model_provider']['provider_version'],
                       generation_configuration=self.design['model_provider']['generation_configuration'])
        require(len({x['call_id'] for x in rows}) == len(rows), 'DUPLICATE_CALL')
        return rows

    def e5_wire_audit(self):
        audits = []
        for base in sorted({x['logical_base_id'] for x in self.variants.values() if ':E5-' in x['logical_base_id']}):
            members = sorted((x for x in self.variants.values() if x['logical_base_id'] == base), key=lambda x: x['variant_id'])
            for model in self.design['model_provider']['models']:
                for repeat in range(1, 3 if base.startswith('A:') else 2):
                    seed = self.design['sampling']['candidate_phase_' + base[0].lower() + '_seed_base'] + (self.positions[base]['fixture_ordinal']-1)*10 + repeat
                    masked, wires, spans = [], [], []
                    for member in members:
                        wire = self.wire(dict(rendered_variant_id=member['rendered_variant_id'], model=model['model'], seed=seed))
                        selector = member['fixture']['operation_nodes'][0]['arguments']['selector_value']['value']
                        # The catalog's selector placeholder is the final SUBJECT fragment.
                        quoted = json.dumps(selector, ensure_ascii=False)
                        prompt = member['request']['prompt']
                        marker = '. Copy names '
                        end_subject = prompt.index(marker)
                        require(prompt[:end_subject].endswith(quoted), 'UNAUTHORIZED_PROMPT_MUTATION', base)
                        prefix = prompt[:end_subject-len(quoted)]
                        start = wire.index(b'"prompt":') + len(b'"prompt":') + 1 + len(json.dumps(prefix, ensure_ascii=False)[1:-1].encode('utf-8'))
                        token = json.dumps(quoted, ensure_ascii=False)[1:-1].encode('utf-8')
                        end = start + len(token)
                        require(wire[start:end] == token, 'UNAUTHORIZED_PROMPT_MUTATION', 'selector span')
                        masked.append(wire[:start] + b'<SELECTOR_REQUEST>' + wire[end:])
                        wires.append(digest(wire)); spans.append([start, end])
                    require(len(masked) == 2 and masked[0] == masked[1] and wires[0] != wires[1],
                            'UNAUTHORIZED_PROMPT_MUTATION', base)
                    audits.append(dict(base=base, model=model['model'], repeat=repeat, wire_sha256=wires,
                                       spans=spans, masked_sha256=digest(masked[0])))
        require(len(audits) == 108, 'PROVENANCE_MISMATCH', 'E5 audit denominator')
        return audits


def source_pins():
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sorted((ROOT / 'tools').glob('g_extract1_*.py'))}


def verify_source(pins, contacted=False):
    for name, expected in pins.items():
        event = ('COMPARATOR_DIGEST_MISMATCH' if contacted else 'PRE_COMPARATOR_DIGEST_MISMATCH') if name.endswith('g_extract1_scoring.py') else (
            'SCORER_DIGEST_MISMATCH' if contacted else 'PRE_SCORER_DIGEST_MISMATCH')
        require((ROOT / name).is_file() and digest((ROOT / name).read_bytes()) == expected, event, name)
