"""Governed G-EXTRACT1 harness. This stage exposes only a no-provider pilot CLI.

The collection engine accepts an explicit byte transport, but live collection is
fail-closed unless a separately approved active freeze and phase authorization
are presented. No provider adapter is imported or initialized here.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

from g_extract1_contract import Package, canonical, digest, require, source_pins, verify_source, IntegrityError
from g_extract1_journal import Journal, write_once, seal_checkpoint, verify_checkpoint, checkpoint_payload
from g_extract1_scoring import evaluate, aggregate, transition, primary_verdict, event_category

VERSION = 'g-extract1.runner.v1'
PILOT = 'NO_PROVIDER_MECHANICAL_PILOT'


def actual_reserve_profile(package, base):
    # Use the pinned, accepted authoring validator only for pre-contact reserve
    # revalidation. It is never a response scorer or a source of new gold.
    path = package.data / 'validate_design.py'
    spec = importlib.util.spec_from_file_location('g_extract1_frozen_design_checks', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    p = package.positions[base]
    members = sorted((x for x in package.variants.values() if x['logical_base_id'] == base), key=lambda x:x['variant_id'])
    slot = dict(p['subtype'], phase=p['phase'], risk_round=p['risk_round'])
    if p['family'] == 'E5':
        return module.counterfactual_reserve_profile(members[0]['fixture'],slot,package.design)
    return module.reserve_profile_bytes(members[0]['fixture'],slot,package.design,True)


def reserve_replacements(package, claims, *, contacted=False, consumed=(), approved_refreeze=None):
    require(not contacted, 'POST_CONTACT_FIXTURE_MUTATION', 'reserve after contact')
    mappings = {row['covered_primary_base_id']: row for row in package.blueprint['reserve_map']}
    slots = {}
    replacements = {}
    for claim in claims:
        base = claim['primary_base_id']
        p = package.positions.get(base)
        require(p is not None and p['primary_or_reserve'] == 'PRIMARY', 'PROVENANCE_MISMATCH', 'reserve primary')
        slot = (p['phase'],p['risk_round'],p['family'])
        require(slot not in slots, 'PROVENANCE_MISMATCH', 'multiple reserve claims')
        slots[slot] = base
        require(base in mappings and claim['reason'] in package.design['reserve_activation_contract']['eligible_reasons'],
                'PROVENANCE_MISMATCH', 'uncovered/ineligible reserve claim')
        mapping = mappings[base]
        reserve = claim['reserve_base_id']
        require(reserve == mapping['reserve_base_id'] and reserve not in consumed, 'PROVENANCE_MISMATCH', 'reserve mapping/consumption')
        actual = sorted(x['rendered_variant_id'] for x in package.variants.values() if x['logical_base_id'] == reserve)
        require(claim['rendered_variant_ids'] == actual, 'PROVENANCE_MISMATCH', 'whole logical reserve/pair required')
        # Profiles are from the accepted final semantic validation, not author declarations.
        primary_position, reserve_position = package.positions[base], package.positions[reserve]
        for dimension in ('phase','risk_round','family','subtype_slot','composed_quota_row','secondary_features'):
            require(primary_position[dimension] == reserve_position[dimension], 'PROVENANCE_MISMATCH', dimension)
        require(actual_reserve_profile(package,base) == actual_reserve_profile(package,reserve),
                'PROVENANCE_MISMATCH', 'profile mismatch')
        replacements[base] = reserve
    if claims:
        # Actual activation requires a separately approved complete revalidation/refreeze.
        require(approved_refreeze is not None and approved_refreeze['synthetic_only'] is True and
                all(approved_refreeze[k] is True for k in ('contamination','gold_review','balance','profiles')),
                'PROVENANCE_MISMATCH', 'no real reserve activation authorized')
    return replacements


def check_call(expected, actual):
    for key, event in [('schedule_position','SCHEDULE_POSITION_MISMATCH'), ('seed','SEED_MISMATCH'),
                       ('model','MODEL_IDENTITY_MISMATCH_AFTER_CONTACT'),
                       ('provider_version','PROVIDER_VERSION_MISMATCH_AFTER_CONTACT'),
                       ('generation_configuration','GENERATION_CONFIGURATION_MISMATCH'),
                       ('request_sha256','UNAUTHORIZED_PROMPT_MUTATION')]:
        require(actual.get(key) == expected.get(key), event, key)
    require(actual == expected, 'PROVENANCE_MISMATCH', 'schedule record')


class Run:
    def __init__(self, package, directory, run_id, *, mechanical=True, authorization=None, resume=False):
        self.package, self.directory, self.run_id = package, Path(directory), run_id
        self.mechanical = mechanical
        self.pins = source_pins()
        self.binding = dict(manifest_sha256=digest(package.manifest_path.read_bytes()),
                            package_commit=package.audit['republished_package_commit'],
                            closure_audit_sha256=digest((package.data / 'corpus/FINAL_READ_ONLY_CLOSURE_AUDIT.json').read_bytes()),
                            protected_artifacts=package.pins, implementation_sha256=self.pins)
        self.a = package.schedule('A')
        self.b = []
        self.qualified = []
        self.evidence = {}
        self.events = []
        self.attempted = set()
        self.current_phase = 'A'
        self.authorization = authorization
        if not mechanical:
            self._authorize('A')
        if not resume:
            require(not self.directory.exists(), 'PRE_EXISTING_RUN_COLLISION', run_id)
            self.directory.mkdir(parents=True)
            write_once(self.directory / 'RUN.json', dict(schema_version=VERSION, run_id=run_id,
                mode=PILOT if mechanical else 'AUTHORIZED_EXPERIMENT', binding=self.binding,
                phase_a_schedule_sha256=digest(canonical(self.a))))
        self.journal = Journal(self.directory / 'journal')
        self.checkpoint_lineage = None
        if resume:
            from g_extract1_contract import load
            header = load(self.directory / 'RUN.json')
            require(header == dict(schema_version=VERSION, run_id=run_id,
                mode=PILOT if mechanical else 'AUTHORIZED_EXPERIMENT', binding=self.binding,
                phase_a_schedule_sha256=digest(canonical(self.a))), 'PROVENANCE_MISMATCH', 'run binding')
            self._replay()

    def _authorize(self, phase):
        # Candidate artifacts cannot be used as an activation or phase grant.
        grant = self.authorization
        require(isinstance(grant, dict) and grant.get('status') == 'EXPLICIT_OPERATOR_PHASE_AUTHORIZATION' and
                grant.get('phase') == phase and grant.get('run_id') == self.run_id and
                grant.get('freeze_status') == 'EXECUTION_FREEZE_ACTIVE' and
                grant.get('binding') == self.binding and grant.get('synthetic_evidence_allowed') is False,
                'PROVENANCE_MISMATCH', 'separate active freeze and phase authorization required')

    def active_schedule(self):
        return self.a if self.current_phase == 'A' else self.b

    def reports(self):
        reports = {'A': {cell:aggregate(self.package,self.a,self.evidence,'A',cell)
                         for cell in self.package.blueprint['schedule_plan']['phase_b_cell_order']}}
        reports['B'] = {cell:aggregate(self.package,self.b,self.evidence,'B',cell) for cell in self.qualified}
        return reports

    def state(self):
        reports = self.reports()
        states = {}
        for phase, cells in reports.items():
            for cell, report in cells.items():
                origin = 'A_SCHEDULED' if phase == 'A' else 'B_SCHEDULED'
                if report['complete']:
                    target = ('A_QUALIFIED_FOR_B' if report['passed'] else 'A_FAILED') if phase == 'A' else (
                        'FINALLY_QUALIFIED' if report['passed'] else 'B_FAILED_VALIDATION')
                    states[phase + ':' + cell] = transition(self.package.design,origin,target,complete=True,passed=report['passed'])
                else:
                    states[phase + ':' + cell] = origin
        return dict(current_phase=self.current_phase, qualified=self.qualified, cell_states=states,
                    reports=reports, integrity_events=self.events)

    def _replay(self):
        pending = None
        for record in self.journal.read():
            item = record['payload']
            if item['type'] == 'START':
                require(pending is None, 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT')
                row = item['call']
                require(row['call_id'] not in self.attempted, 'DUPLICATE_CALL')
                if row['phase'] == 'B' and self.current_phase == 'A':
                    self.enter_b(record=False)
                schedule = self.active_schedule()
                index = len([x for x in self.attempted if x.startswith(row['phase'] + ':')])
                require(index < len(schedule), 'SCHEDULE_POSITION_MISMATCH')
                check_call(schedule[index], row)
                require(item['wire_sha256'] == digest(self.package.wire(row)), 'UNAUTHORIZED_PROMPT_MUTATION')
                self.attempted.add(row['call_id']); pending = row
            elif item['type'] == 'COMPLETE':
                require(pending is not None and pending['call_id'] == item['call_id'], 'PROVENANCE_MISMATCH', 'completion receipt')
                expected = evaluate(self.package.variants[pending['rendered_variant_id']], item['raw_output'], truncated=item['provider_truncated'])
                require(item['evaluation'] == expected, 'SCORER_DIGEST_MISMATCH', 'journal evaluation')
                self.evidence[pending['call_id']] = expected; pending = None
            elif item['type'] == 'FAILURE':
                require(pending is not None and pending['call_id'] == item['call_id'], 'PROVENANCE_MISMATCH', 'failure receipt')
                event_category(self.package.design,item['event'])
                self.events.append(item['event']); pending = None
            elif item['type'] == 'PHASE_B':
                self.enter_b(record=False)
                require(item['qualified'] == self.qualified and item['schedule_sha256'] == digest(canonical(self.b)),
                        'PROVENANCE_MISMATCH', 'B eligibility journal')
            else:
                raise IntegrityError('CORRUPTED_OR_UNPARSEABLE_JOURNAL', 'unrecognized record type')
        require(pending is None, 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT', 'unsealed in-flight call')

    def perform(self, row, transport, receipts):
        require(not self.events, 'PROVENANCE_MISMATCH', 'terminated receipt cannot retry')
        if not self.mechanical:
            self._authorize(row['phase'])
            require(getattr(transport, 'synthetic_only', True) is False, 'PROVENANCE_MISMATCH', 'synthetic transport in real mode')
        else:
            require(getattr(transport, 'synthetic_only', False) is True, 'PROVENANCE_MISMATCH', 'pilot transport boundary')
        self.package.verify(contacted=bool(self.attempted))
        verify_source(self.pins, contacted=bool(self.attempted))
        self.package.verify_receipts(receipts, contacted=bool(self.attempted))
        require(row['call_id'] not in self.attempted, 'UNAUTHORIZED_RETRY', row['call_id'])
        schedule = self.active_schedule()
        index = len([x for x in self.attempted if x.startswith(self.current_phase + ':')])
        require(index < len(schedule), 'SCHEDULE_POSITION_MISMATCH')
        check_call(schedule[index], row)
        wire = self.package.wire(row)
        require(digest(wire) == row['request_sha256'], 'UNAUTHORIZED_PROMPT_MUTATION')
        self.journal.append(dict(type='START', call=row, wire_sha256=digest(wire),
                                 start_state=self.current_phase + '_SCHEDULED',
                                 checkpoint_lineage=self.checkpoint_lineage,
                                 mode=PILOT if self.mechanical else 'AUTHORIZED_EXPERIMENT'))
        self.attempted.add(row['call_id'])
        try:
            result = transport(wire, row)
        except Exception as exc:
            # An exception is not a provider-issued failure receipt.
            result = dict(failure='unreceipted', receipt=None, exception_type=type(exc).__name__)
        if result.get('failure'):
            receipt = result.get('receipt')
            valid = isinstance(receipt,dict) and receipt.get('call_id') == row['call_id'] and receipt.get('request_sha256') == row['request_sha256']
            kinds = dict(timeout='PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', error='PROVIDER_ERROR_WITH_FAILURE_RECEIPT',
                         missing='MISSING_RESPONSE_WITH_FAILURE_RECEIPT')
            event = kinds.get(result['failure']) if valid else None
            event = event or 'PROVIDER_FAILURE_WITHOUT_RECEIPT'
            self.journal.append(dict(type='FAILURE', call_id=row['call_id'], event=event, receipt=receipt,
                                     completion_state=event_category(self.package.design,event)))
            self.events.append(event)
            return
        require(type(result.get('raw_output')) is str and type(result.get('provider_truncated')) is bool,
                'PROVENANCE_MISMATCH', 'response receipt shape')
        evaluation = evaluate(self.package.variants[row['rendered_variant_id']], result['raw_output'], truncated=result['provider_truncated'])
        self.journal.append(dict(type='COMPLETE', call_id=row['call_id'], raw_output=result['raw_output'],
                                 provider_truncated=result['provider_truncated'], evaluation=evaluation,
                                 completion_state='RESPONSE_CAPTURED', receipt=result.get('receipt')))
        self.evidence[row['call_id']] = evaluation

    def enter_b(self, *, record=True):
        reports = self.reports()['A']
        require(not self.events and all(x['complete'] for x in reports.values()), 'PROVENANCE_MISMATCH', 'A terminal required')
        self.qualified = sorted(cell for cell, report in reports.items() if report['passed'])
        for cell in self.qualified:
            transition(self.package.design,'A_QUALIFIED_FOR_B','B_SCHEDULED',eligible=True)
        self.b = self.package.schedule('B', self.qualified)
        self.current_phase = 'B'
        if record:
            self.journal.append(dict(type='PHASE_B', qualified=self.qualified, schedule_sha256=digest(canonical(self.b))))

    def checkpoint(self, label):
        require(label.isalnum(), 'PROVENANCE_MISMATCH', 'checkpoint label')
        next_position = 1 + len([x for x in self.attempted if x.startswith(self.current_phase + ':')])
        payload = checkpoint_payload(self.run_id,self.binding,self.active_schedule(),self.journal,next_position,self.state())
        row = seal_checkpoint(self.directory / ('CHECKPOINT_' + label + '.json'),payload)
        self.checkpoint_lineage = row['sha256']
        return row

    def resume(self, checkpoint_path):
        self.package.verify(contacted=bool(self.attempted)); verify_source(self.pins, contacted=bool(self.attempted))
        next_position = 1 + len([x for x in self.attempted if x.startswith(self.current_phase + ':')])
        row = verify_checkpoint(checkpoint_path,run_id=self.run_id,binding=self.binding,schedule=self.active_schedule(),
                                journal=self.journal,reconstructed_state=self.state(),next_position=next_position)
        self.checkpoint_lineage = row['sha256']
        return 'MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT'

    def final_report(self):
        reports = self.reports()
        facts = dict(events=self.events, provider_generation_calls=0 if self.mechanical else len(self.attempted),
            phase_a_terminal=all(x['complete'] for x in reports['A'].values()),
            phase_b_terminal=all(x['complete'] for x in reports['B'].values()),
            phase_b_entrant_count=len(self.qualified),
            finally_qualified_count=sum(x['passed'] for x in reports['B'].values()),
            b_failed_validation_count=sum(x['complete'] and not x['passed'] for x in reports['B'].values()))
        return dict(schema_version=VERSION, mode=PILOT if self.mechanical else 'AUTHORIZED_EXPERIMENT',
                    evidence_admissible_for_qualification=not self.mechanical,
                    synthetic_primary_verdict=primary_verdict(self.package.design,facts) if self.mechanical else None,
                    primary_verdict=None if self.mechanical else primary_verdict(self.package.design,facts),
                    phase_a_calls=0 if self.mechanical else len(self.a), phase_b_calls=0 if self.mechanical else len(self.b),
                    synthetic_observations=len(self.evidence), provider_model_calls=0 if self.mechanical else len(self.attempted),
                    binding=self.binding, phase_a_schedule_sha256=digest(canonical(self.a)),
                    phase_b_schedule_sha256=digest(canonical(self.b)), state=self.state(),
                    autonomy=False, belief_effects='none')
