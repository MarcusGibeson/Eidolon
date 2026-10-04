"""Governed G-EXTRACT1 harness. This stage exposes only a no-provider pilot CLI.

The collection engine accepts an explicit byte transport, but live collection is
fail-closed unless a separately approved active freeze and phase authorization
are presented. No provider adapter is imported or initialized here.
"""
from __future__ import annotations

import copy
import importlib.util
from functools import wraps
from pathlib import Path

from g_extract1_contract import Package, canonical, digest, require, source_pins, verify_source, IntegrityError
from g_extract1_journal import Journal, write_once, seal_checkpoint, verify_checkpoint, checkpoint_payload
from g_extract1_scoring import evaluate, aggregate, transition, primary_verdict, event_category

VERSION = 'g-extract1.runner.v3'
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


def guarded(method):
    """One fail-closed path; catching a Python exception cannot untaint a run."""
    @wraps(method)
    def call(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except IntegrityError as exc:
            self._retain(exc)
            raise
        except Exception as exc:
            failure = IntegrityError('PROVENANCE_MISMATCH', method.__name__ + ':' + type(exc).__name__)
            self._retain(failure)
            raise failure from exc
    return call


def failure_event(row, kind, receipt):
    kinds = dict(timeout='PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', error='PROVIDER_ERROR_WITH_FAILURE_RECEIPT',
                 missing='MISSING_RESPONSE_WITH_FAILURE_RECEIPT')
    require(kind in {*kinds, 'unreceipted'}, 'PROVENANCE_MISMATCH', 'failure kind')
    if receipt is None:
        return 'PROVIDER_FAILURE_WITHOUT_RECEIPT'
    require(kind in kinds and type(receipt) is dict and receipt.get('call_id') == row['call_id'] and
            receipt.get('request_sha256') == row['request_sha256'] and receipt.get('failure_kind') == kind,
            'PROVENANCE_MISMATCH', 'failure receipt binding/kind')
    return kinds[kind]


def transport_outcome(row, result):
    """Only validated plain objects reach response/receipt field access."""
    unusable = dict(failure='unreceipted', receipt=None, unusable_reason='malformed_transport_outcome')
    try:
        if type(result) is not dict or not all(type(k) is str for k in result):
            return unusable
        if 'failure' in result:
            if type(result['failure']) is not str or not {'failure','receipt'} <= set(result) or \
                    {'raw_output','provider_truncated'} & set(result):
                return unusable
            receipt = result['receipt']
            if receipt is not None:
                canonical(receipt)
            failure_event(row, result['failure'], receipt)
            return dict(failure=result['failure'], receipt=receipt)
        if not {'raw_output','provider_truncated','receipt'} <= set(result) or \
                type(result['raw_output']) is not str or type(result['provider_truncated']) is not bool:
            return unusable
        receipt = result['receipt']
        if type(receipt) is not dict or receipt.get('call_id') != row['call_id'] or \
                receipt.get('request_sha256') != row['request_sha256']:
            return unusable
        success = dict(raw_output=result['raw_output'], provider_truncated=result['provider_truncated'], receipt=receipt)
        canonical(success)
        return success
    except Exception:
        # Never stringify or serialize arbitrary returned objects as evidence.
        return unusable


class Run:
    @guarded
    def __init__(self, package, directory, run_id, *, mechanical=True, authorization=None, resume=False,
                 exercise_authorization=False):
        self.package, self.directory, self.run_id = package, Path(directory), run_id
        self.mechanical = mechanical
        self.exercise_authorization = exercise_authorization
        self._owned = False
        self._checkpoint_verified = not resume
        self._resuming = resume
        self.events, self.event_scopes = [], []
        self._error_cell = None
        self.pins = source_pins()
        self.binding = dict(manifest_sha256=digest(package.manifest_path.read_bytes()),
                            package_commit=package.audit['republished_package_commit'],
                            closure_audit_sha256=digest((package.data / 'corpus/FINAL_READ_ONLY_CLOSURE_AUDIT.json').read_bytes()),
                            protected_artifacts=package.pins, implementation_sha256=self.pins)
        self.a = package.schedule('A')
        self.b = []
        self.qualified = []
        self.evidence = {}
        self.attempted = set()
        self.current_phase = 'A'
        self.authorization = authorization
        require(not exercise_authorization or mechanical, 'PROVENANCE_MISMATCH', 'authorization test must be mechanical')
        self.checkpoint_lineage = None
        self._last_checkpoint = None
        if not resume:
            if not mechanical or exercise_authorization:
                self._authorize('A')
            require(not self.directory.exists(), 'PRE_EXISTING_RUN_COLLISION', run_id)
            self.directory.mkdir(parents=True)
            write_once(self.directory / 'RUN.json', dict(schema_version=VERSION, run_id=run_id,
                mode=PILOT if mechanical else 'AUTHORIZED_EXPERIMENT', binding=self.binding,
                exercise_authorization=exercise_authorization,
                phase_a_schedule_sha256=digest(canonical(self.a))))
            self._owned = True
        self.journal = Journal(self.directory / 'journal')
        if resume:
            from g_extract1_contract import load
            header = load(self.directory / 'RUN.json')
            self._owned = header.get('run_id') == run_id
            require(header == dict(schema_version=VERSION, run_id=run_id,
                mode=PILOT if mechanical else 'AUTHORIZED_EXPERIMENT', binding=self.binding,
                exercise_authorization=exercise_authorization,
                phase_a_schedule_sha256=digest(canonical(self.a))), 'PROVENANCE_MISMATCH', 'run binding')
            self._replay()
            # Incident evidence is terminal for future operations, not a claim
            # that earlier valid START records occurred after the incident.
            self._load_incidents()
            # Read-only reconstruction establishes B before any phase grant check.
            if not mechanical or exercise_authorization:
                self._authorize(self.current_phase)

    def _remember(self, event, phase, cell=None):
        event_category(self.package.design,event)
        self.events.append(event)
        self.event_scopes.append(dict(event=event,phase=phase,cell=cell))

    def _retain(self, exc):
        if not hasattr(self, 'events') or exc.event in self.events:
            return
        phase = getattr(self,'current_phase','A')
        self._remember(exc.event,phase,getattr(self,'_error_cell',None))
        if self._owned:
            # Separate append-only incident evidence survives even a corrupt call
            # journal; it cannot be erased by catching an exception or restarting.
            Journal(self.directory / 'integrity').append(dict(type='INTEGRITY_EVENT',run_id=self.run_id,
                binding_sha256=digest(canonical(self.binding)),event=exc.event,detail=exc.detail,
                phase=phase,cell=self._error_cell))

    def _load_incidents(self):
        for record in Journal(self.directory / 'integrity').read():
            item = record['payload']
            require(item.get('type') == 'INTEGRITY_EVENT' and item.get('run_id') == self.run_id and
                    item.get('binding_sha256') == digest(canonical(self.binding)), 'PROVENANCE_MISMATCH', 'incident binding')
            self._remember(item['event'],item['phase'],item['cell'])

    def _operable(self, *, allow_interruption=False):
        for event in self.events:
            if allow_interruption and event == 'MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT':
                continue
            raise IntegrityError(event, 'terminal lifecycle event; continuation forbidden')
        require(self._checkpoint_verified, 'PROVENANCE_MISMATCH', 'CHECKPOINT_VERIFICATION_REQUIRED')

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
        reports['B'] = {cell:aggregate(self.package,self.b,self.evidence,'B',cell) for cell in self.qualified} if self.current_phase == 'B' else {}
        return reports

    def _cell_incomplete(self, phase, cell):
        return any(event_category(self.package.design,x['event']) == 'INCOMPLETE' and x['phase'] == phase and
                   (x['cell'] is None or x['cell'] == cell) for x in self.event_scopes)

    def _eligible(self, reports=None):
        reports = self.reports()['A'] if reports is None else reports
        return sorted(cell for cell,r in reports.items() if r['complete'] and r['passed'] and not self._cell_incomplete('A',cell))

    def _precontact_blocked(self):
        return not self.attempted and bool(set(self.events) &
            set(self.package.design['integrity_event_contract']['precontact_blocking_events']))

    def state(self):
        reports = self.reports()
        states = {}
        for phase, cells in reports.items():
            for cell, report in cells.items():
                origin = 'A_SCHEDULED' if phase == 'A' else 'B_SCHEDULED'
                if phase == 'A' and self._precontact_blocked():
                    states[phase + ':' + cell] = transition(self.package.design,origin,'A_BLOCKED',blocked=True)
                elif self._cell_incomplete(phase,cell):
                    states[phase + ':' + cell] = transition(self.package.design,origin,phase + '_INCOMPLETE',incomplete=True)
                elif report['complete']:
                    target = ('A_QUALIFIED_FOR_B' if report['passed'] else 'A_FAILED') if phase == 'A' else (
                        'FINALLY_QUALIFIED' if report['passed'] else 'B_FAILED_VALIDATION')
                    states[phase + ':' + cell] = transition(self.package.design,origin,target,complete=True,passed=report['passed'])
                else:
                    states[phase + ':' + cell] = origin
        for cell,report in reports['A'].items():
            if states['A:' + cell] == 'A_FAILED':
                states['B:' + cell] = transition(self.package.design,'A_FAILED','B_NOT_ELIGIBLE')
        return dict(current_phase=self.current_phase, qualified=self._eligible(reports['A']),
                    b_entered=self.current_phase == 'B', cell_states=states,
                    reports=reports, integrity_events=self.events,event_scopes=self.event_scopes)

    def _replay(self):
        pending = None
        records = self.journal.read()
        for offset,record in enumerate(records):
            item = record['payload']
            if item['type'] == 'START':
                require(all(x == 'MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT' for x in self.events),
                        'PROVENANCE_MISMATCH', 'call after terminal event')
                require(pending is None, 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT')
                row = item['call']
                require(row['call_id'] not in self.attempted, 'DUPLICATE_CALL')
                require(row['phase'] == self.current_phase, 'PROVENANCE_MISMATCH', 'phase not entered')
                schedule = self.active_schedule()
                index = len([x for x in self.attempted if x.startswith(row['phase'] + ':')])
                require(index < len(schedule), 'SCHEDULE_POSITION_MISMATCH')
                check_call(schedule[index], row)
                require(item['wire_sha256'] == digest(self.package.wire(row)), 'UNAUTHORIZED_PROMPT_MUTATION')
                require(item.get('checkpoint_lineage') == self.checkpoint_lineage,
                        'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'START lineage')
                require(item.get('mode') == (PILOT if self.mechanical else 'AUTHORIZED_EXPERIMENT'), 'PROVENANCE_MISMATCH', 'journal mode')
                self.attempted.add(row['call_id']); pending = row
            elif item['type'] == 'COMPLETE':
                require(pending is not None and pending['call_id'] == item['call_id'], 'PROVENANCE_MISMATCH', 'completion receipt')
                self._check_success_receipt(pending,item['receipt'])
                expected = evaluate(self.package.variants[pending['rendered_variant_id']], item['raw_output'], truncated=item['provider_truncated'])
                require(item['evaluation'] == expected, 'SCORER_DIGEST_MISMATCH', 'journal evaluation')
                self.evidence[pending['call_id']] = expected; pending = None
            elif item['type'] == 'FAILURE':
                require(pending is not None and pending['call_id'] == item['call_id'], 'PROVENANCE_MISMATCH', 'failure receipt')
                reconstructed = failure_event(pending,item['failure_kind'],item['receipt'])
                require(item['event'] == reconstructed and item['completion_state'] == event_category(self.package.design,reconstructed),
                        'PROVENANCE_MISMATCH', 'failure event not derived from receipt')
                self._remember(reconstructed,pending['phase'],pending['cell_id']); pending = None
            elif item['type'] == 'PHASE_B':
                require(pending is None and self.current_phase == 'A' and not self.events, 'PROVENANCE_MISMATCH', 'B transition replay')
                self._derive_b()
                require(item['qualified'] == self.qualified and item['schedule_sha256'] == digest(canonical(self.b)),
                        'PROVENANCE_MISMATCH', 'B eligibility journal')
            elif item['type'] == 'CHECKPOINT_CREATED':
                require(pending is None and type(item['label']) is str and item['label'].isalnum(),
                        'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'checkpoint marker')
                prefix = self.journal.prefix(records[:offset])
                expected_state = self.state()
                row = verify_checkpoint(self.directory / ('CHECKPOINT_' + item['label'] + '.json'),
                    run_id=self.run_id,binding=self.binding,schedule=self.active_schedule(),journal=self.journal,
                    reconstructed_state=expected_state,next_position=self._next_position(),prefix=prefix)
                require(item['checkpoint_sha256'] == row['sha256'], 'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'marker seal')
                self.checkpoint_lineage = row['sha256']
                self._last_checkpoint = dict(label=item['label'],row=row,record_count=offset+1,prefix=prefix)
            elif item['type'] == 'RESUME_VERIFIED':
                require(pending is None and self._last_checkpoint is not None and
                        offset == self._last_checkpoint['record_count'] and
                        item['checkpoint_sha256'] == self.checkpoint_lineage and
                        item['event'] == 'MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT' and item['phase'] == self.current_phase,
                        'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'resume lineage/event')
                self._remember(item['event'],item['phase'])
            else:
                raise IntegrityError('CORRUPTED_OR_UNPARSEABLE_JOURNAL', 'unrecognized record type')
        require(pending is None, 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT', 'unsealed in-flight call')

    @guarded
    def perform(self, row, transport, receipts):
        self._error_cell = row.get('cell_id')
        self._operable(allow_interruption=True)
        if not self.mechanical or self.exercise_authorization:
            self._authorize(row['phase'])
        if not self.mechanical:
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
        except Exception:
            # An exception is not a provider-issued failure receipt.
            result = dict(failure='unreceipted', receipt=None)
        result = transport_outcome(row, result)
        if result.get('failure'):
            self._close_failure(row,result['failure'],result['receipt'],result.get('unusable_reason'))
            return
        require(type(result.get('raw_output')) is str and type(result.get('provider_truncated')) is bool,
                'PROVENANCE_MISMATCH', 'response receipt shape')
        self._check_success_receipt(row,result.get('receipt'))
        try:
            evaluation = evaluate(self.package.variants[row['rendered_variant_id']], result['raw_output'], truncated=result['provider_truncated'])
        except Exception:
            self._close_failure(row,'unreceipted',None,'response_evaluation_failed')
            raise IntegrityError('PROVENANCE_MISMATCH', 'response evaluation failed after START')
        self.journal.append(dict(type='COMPLETE', call_id=row['call_id'], raw_output=result['raw_output'],
                                 provider_truncated=result['provider_truncated'], evaluation=evaluation,
                                 completion_state='RESPONSE_CAPTURED', receipt=result.get('receipt')))
        self.evidence[row['call_id']] = evaluation

    def _close_failure(self, row, kind, receipt, reason=None):
        event = failure_event(row,kind,receipt)
        self.journal.append(dict(type='FAILURE',call_id=row['call_id'],event=event,receipt=receipt,
            failure_kind=kind,unusable_reason=reason,completion_state=event_category(self.package.design,event)))
        self._remember(event,row['phase'],row['cell_id'])

    def _check_success_receipt(self, row, receipt):
        require(type(receipt) is dict and receipt.get('call_id') == row['call_id'] and
                receipt.get('request_sha256') == row['request_sha256'], 'PROVENANCE_MISMATCH', 'completion receipt binding')

    def _derive_b(self):
        reports = self.reports()['A']
        require(not self.events and all(x['complete'] for x in reports.values()), 'PROVENANCE_MISMATCH', 'A terminal required')
        self.qualified = self._eligible(reports)
        for cell in self.qualified:
            transition(self.package.design,'A_QUALIFIED_FOR_B','B_SCHEDULED',eligible=True)
        self.b = self.package.schedule('B', self.qualified)
        self.current_phase = 'B'

    @guarded
    def enter_b(self):
        self._error_cell = None
        self._operable()
        require(self.current_phase == 'A', 'PROVENANCE_MISMATCH', 'B already entered')
        if not self.mechanical or self.exercise_authorization:
            self._authorize('B')
        self._derive_b()
        self.journal.append(dict(type='PHASE_B', qualified=self.qualified, schedule_sha256=digest(canonical(self.b))))

    def _next_position(self):
        return 1 + len([x for x in self.attempted if x.startswith(self.current_phase + ':')])

    @guarded
    def checkpoint(self, label):
        self._operable(allow_interruption=True)
        self.package.verify(contacted=bool(self.attempted)); verify_source(self.pins,contacted=bool(self.attempted))
        require(label.isalnum(), 'PROVENANCE_MISMATCH', 'checkpoint label')
        next_position = self._next_position()
        payload = checkpoint_payload(self.run_id,self.binding,self.active_schedule(),self.journal,next_position,self.state())
        row = seal_checkpoint(self.directory / ('CHECKPOINT_' + label + '.json'),payload)
        self.journal.append(dict(type='CHECKPOINT_CREATED',label=label,checkpoint_sha256=row['sha256']))
        self.checkpoint_lineage = row['sha256']
        self._last_checkpoint = dict(label=label,row=row,record_count=self.journal.prefix()['record_count'],prefix=payload['journal_prefix'])
        return row

    @guarded
    def resume(self, checkpoint_path):
        require(self._resuming and not self._checkpoint_verified, 'PROVENANCE_MISMATCH', 'resume only once')
        for event in self.events:
            if event != 'MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT':
                raise IntegrityError(event, 'terminal resume')
        self.package.verify(contacted=bool(self.attempted)); verify_source(self.pins, contacted=bool(self.attempted))
        next_position = self._next_position()
        require(Path(checkpoint_path).is_file(), 'MISSING_CHECKPOINT_AFTER_INTERRUPTION')
        require(self._last_checkpoint is not None, 'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'no authoritative checkpoint marker')
        require(self.journal.prefix()['record_count'] == self._last_checkpoint['record_count'],
                'UNVERIFIABLE_JOURNAL_PREFIX', 'unsealed checkpoint tail')
        row = verify_checkpoint(checkpoint_path,run_id=self.run_id,binding=self.binding,schedule=self.active_schedule(),
                                journal=self.journal,reconstructed_state=self.state(),next_position=next_position,
                                prefix=self._last_checkpoint['prefix'])
        require(row['sha256'] == self.checkpoint_lineage, 'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'authoritative seal')
        if not self.mechanical or self.exercise_authorization:
            self._authorize(self.current_phase)
        self.journal.append(dict(type='RESUME_VERIFIED',checkpoint_sha256=row['sha256'],phase=self.current_phase,
                                 event='MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT'))
        self._remember('MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT',self.current_phase)
        self._checkpoint_verified = True
        return 'MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT'

    @guarded
    def final_report(self):
        require(self._checkpoint_verified, 'PROVENANCE_MISMATCH', 'CHECKPOINT_VERIFICATION_REQUIRED')
        self.package.verify(contacted=bool(self.attempted)); verify_source(self.pins,contacted=bool(self.attempted))
        reports = self.reports()
        eligible = self._eligible(reports['A'])
        state = self.state()
        facts = dict(events=self.events, provider_generation_calls=0 if self.mechanical else len(self.attempted),
            cell_states=list(state['cell_states'].values()),
            phase_a_terminal=all(x['complete'] for x in reports['A'].values()),
            phase_b_terminal=self.current_phase == 'B' and all(x['complete'] for x in reports['B'].values()),
            phase_b_entrant_count=len(eligible),
            finally_qualified_count=sum(state['cell_states'].get('B:' + cell) == 'FINALLY_QUALIFIED' for cell in reports['B']),
            b_failed_validation_count=sum(x['complete'] and not x['passed'] for x in reports['B'].values()))
        return dict(schema_version=VERSION, mode=PILOT if self.mechanical else 'AUTHORIZED_EXPERIMENT',
                    evidence_admissible_for_qualification=not self.mechanical,
                    synthetic_primary_verdict=primary_verdict(self.package.design,facts) if self.mechanical else None,
                    primary_verdict=None if self.mechanical else primary_verdict(self.package.design,facts),
                    phase_a_calls=0 if self.mechanical else sum(x.startswith('A:') for x in self.attempted),
                    phase_b_calls=0 if self.mechanical else sum(x.startswith('B:') for x in self.attempted),
                    synthetic_observations=len(self.evidence), provider_model_calls=0 if self.mechanical else len(self.attempted),
                    binding=self.binding, phase_a_schedule_sha256=digest(canonical(self.a)),
                    phase_b_schedule_sha256=digest(canonical(self.b)), state=state,
                    operational_stage='AWAITING_CONDITIONAL_PHASE_B' if facts['phase_a_terminal'] and eligible and self.current_phase == 'A' else self.current_phase,
                    autonomy=False, belief_effects='none')
