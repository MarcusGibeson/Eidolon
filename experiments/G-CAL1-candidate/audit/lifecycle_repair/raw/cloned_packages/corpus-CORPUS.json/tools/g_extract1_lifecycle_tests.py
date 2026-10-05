"""Adversarial lifecycle regression through the governed, synthetic-only harness.

Mutations are confined to isolated evidence copies, never accepted artifacts.
"""
from __future__ import annotations

import copy
from pathlib import Path
import shutil

from g_extract1_contract import canonical, digest, file_digest, load
from g_extract1_journal import Journal, seal_checkpoint
from g_extract1_runner import Run
from g_extract1_scoring import evaluate


def reseal(directory, payloads):
    """The attack knows the hash algorithm; semantic replay must still reject."""
    directory = Path(directory)
    previous = '0' * 64
    for index, payload in enumerate(payloads, 1):
        row = dict(sequence=index, previous_sha256=previous, payload=payload)
        row['sha256'] = digest(canonical(row))
        (directory / f'{index:06d}.json').write_bytes(canonical(row))
        previous = row['sha256']


def lifecycle_tests(p, t, root, transport_class):
    root.mkdir(parents=True)
    transport = transport_class(p)
    summary = {}

    def clone(source, name):
        destination = root / name
        shutil.copytree(source, destination)
        return destination

    def fresh(name):
        return Run(p, root/name, name)

    class Counter:
        synthetic_only = True
        def __init__(self):
            self.calls = 0
        def __call__(self, wire, row):
            self.calls += 1
            return transport(wire, row)

    seed = fresh('checkpointseed')
    seed.perform(seed.a[0], transport, p.receipts())
    cp = seed.checkpoint('sealed')
    for action in ('perform', 'enter_b', 'checkpoint', 'final_report'):
        folder = clone(seed.directory, 'unverified_' + action)
        resumed = Run(p, folder, seed.run_id, resume=True)
        counter = Counter()
        operations = dict(perform=lambda:resumed.perform(resumed.a[1],counter,p.receipts()),
            enter_b=resumed.enter_b, checkpoint=lambda:resumed.checkpoint('bypass'), final_report=resumed.final_report)
        t.rejects('I1', action + ' locked before verification', 'PROVENANCE_MISMATCH', operations[action])
        t.check('I1', action + ' zero transport', counter.calls == 0)
        t.rejects('I2', action + ' caught error stays terminal', 'PROVENANCE_MISMATCH',
                  lambda:resumed.resume(folder/'CHECKPOINT_sealed.json'))
    summary['I1'] = dict(resumed_operations_locked=4,transport_invocations=0)

    for name, mutate, event in [
        ('missing',None,'MISSING_CHECKPOINT_AFTER_INTERRUPTION'),
        ('corrupt',None,'CORRUPTED_CHECKPOINT'),
        ('position',lambda x:x.update(next_schedule_position=3),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT'),
        ('prefix',lambda x:x['journal_prefix'].update(last_sha256='0'*64),'UNVERIFIABLE_JOURNAL_PREFIX'),
        ('schedule',lambda x:x.update(schedule_sha256='0'*64),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT'),
        ('binding',lambda x:x['frozen_binding'].update(package_commit='0'*40),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT'),
        ('state',lambda x:x['state'].update(current_phase='B'),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT')]:
        folder = clone(seed.directory,'checkpoint_' + name)
        resumed = Run(p,folder,seed.run_id,resume=True)
        path = folder/'ATTACK.json'
        if name == 'corrupt':
            path.write_bytes(b'{')
        elif mutate:
            payload = copy.deepcopy(cp['payload']); mutate(payload); seal_checkpoint(path,payload)
        t.rejects('I1',name + ' checkpoint',event,lambda:resumed.resume(path))
        t.rejects('I2',name + ' continuation forbidden',event,
                  lambda:resumed.perform(resumed.a[1],Counter(),p.receipts()))
        t.check('I2',name + ' invalid retained',event in resumed.events and
                len(Journal(folder/'integrity').read()) == 1)

    for name, row_index, event in [('skip',2,'SCHEDULE_POSITION_MISMATCH'),('retry',0,'UNAUTHORIZED_RETRY')]:
        run = fresh(name)
        run.perform(run.a[0],transport,p.receipts())
        t.rejects('I2',name + ' original failure',event,
                  lambda:run.perform(run.a[row_index],transport,p.receipts()))
        counter = Counter()
        t.rejects('I2',name + ' caught error continuation',event,
                  lambda:run.perform(run.a[1],counter,p.receipts()))
        t.check('I2',name + ' zero continuation transport',counter.calls == 0)
        t.check('I2',name + ' final INVALID',run.final_report()['synthetic_primary_verdict'] == 'INVALID')
        t.check('I2',name + ' append-only incident',len(Journal(run.directory/'integrity').read()) == 1)
        recovered = Run(p,run.directory,run.run_id,resume=True)
        t.check('I2',name + ' retained across reconstruction',event in recovered.events)
        t.rejects('I2',name + ' reconstructed continuation locked',event,
                  lambda:recovered.perform(recovered.a[1],counter,p.receipts()))

    folder = clone(seed.directory,'sealed_interruption')
    resumed = Run(p,folder,seed.run_id,resume=True)
    resumed.resume(folder/'CHECKPOINT_sealed.json')
    resumed.perform(resumed.a[1],transport,p.receipts())
    report = resumed.final_report()
    t.check('I2','sealed interruption retained',report['synthetic_primary_verdict'] == 'INCOMPLETE' and
            report['state']['integrity_events'] == ['MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT'])
    t.check('I3','interrupted A integrated incomplete',set(report['state']['cell_states'].values()) == {'A_INCOMPLETE'})
    t.rejects('I2','interrupted A cannot qualify/enter B','MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT',resumed.enter_b)
    summary['I2'] = dict(skip_and_retry_continuation='BLOCKED',append_only_retention=True,
        interruption_event='MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT',interruption_verdict='INCOMPLETE')

    failure_seed = fresh('failureseed')
    failure_seed.perform(failure_seed.a[0],transport_class(p,'timeout'),p.receipts())
    t.check('I3','A receipted failure integrated',failure_seed.state()['cell_states']['A:' + failure_seed.a[0]['cell_id']] == 'A_INCOMPLETE' and
            failure_seed.final_report()['synthetic_primary_verdict'] == 'INCOMPLETE')
    mutations = [
        ('null_receipt',lambda x:x.update(receipt=None)),
        ('copied_receipt',lambda x:x['receipt'].update(call_id=failure_seed.a[1]['call_id'])),
        ('request_hash',lambda x:x['receipt'].update(request_sha256='0'*64)),
        ('failure_kind',lambda x:x['receipt'].update(failure_kind='error')),
        ('stored_event',lambda x:x.update(event='PROVIDER_ERROR_WITH_FAILURE_RECEIPT')),
        ('category',lambda x:x.update(completion_state='INVALID'))]
    for name, mutation in mutations:
        folder = clone(failure_seed.directory,'receipt_' + name)
        payloads = [copy.deepcopy(x['payload']) for x in Journal(folder/'journal').read()]
        mutation(payloads[-1]); reseal(folder/'journal',payloads)
        t.rejects('I4',name + ' with valid rehashed chain','PROVENANCE_MISMATCH',
                  lambda:Run(p,folder,failure_seed.run_id,resume=True))
    for name, marker in [('initial',False),('post_checkpoint',True)]:
        run = fresh('lineage_' + name)
        run.perform(run.a[0],transport,p.receipts())
        if marker:
            run.checkpoint('authority'); run.perform(run.a[1],transport,p.receipts())
        payloads = [copy.deepcopy(x['payload']) for x in run.journal.read()]
        starts = [x for x in payloads if x['type'] == 'START']
        starts[-1]['checkpoint_lineage'] = 'a'*64
        reseal(run.directory/'journal',payloads)
        t.rejects('I4',name + ' resealed orphan START lineage','UNVERIFIABLE_INTERRUPTION_CHECKPOINT',
                  lambda:Run(p,run.directory,run.run_id,resume=True))
    summary['I4'] = dict(resealed_receipt_mutations_rejected=len(mutations),resealed_lineage_mutations_rejected=2)

    # Drive the actual 480-call lifecycle before evaluating B eligibility. The
    # grant below is exercised only in the explicitly synthetic test mode.
    binding = seed.binding
    def grant(phase,run_id):
        return dict(status='EXPLICIT_OPERATOR_PHASE_AUTHORIZATION',phase=phase,run_id=run_id,
            freeze_status='EXECUTION_FREEZE_ACTIVE',binding=binding,synthetic_evidence_allowed=False)
    run = Run(p,root/'integrated','integrated',exercise_authorization=True,authorization=grant('A','integrated'))
    t.check('I3','A running nonterminal',run.final_report()['synthetic_primary_verdict'] is None)
    for row in run.a:
        run.perform(row,transport,p.receipts())
    before = run.final_report()
    t.check('I3','complete A before enter B derives all six eligible',len(before['state']['qualified']) == 6 and
        before['state']['b_entered'] is False and before['synthetic_primary_verdict'] is None and
        before['operational_stage'] == 'AWAITING_CONDITIONAL_PHASE_B')
    t.check('I3','complete A integrated qualified states',set(before['state']['cell_states'].values()) == {'A_QUALIFIED_FOR_B'})

    # Reconstruct isolated full journal attacks, with deliberately failed
    # synthetic observations, to exercise zero/mixed A outcomes through replay.
    payloads = [x['payload'] for x in run.journal.read()]
    for name, failed_cells in [('zero_qualifiers',set(p.blueprint['schedule_plan']['phase_b_cell_order'])),
                               ('some_qualifiers',{'small:R2'})]:
        bad = fresh(name)
        bad_payloads = copy.deepcopy(payloads)
        pending = None
        for item in bad_payloads:
            if item['type'] == 'START':
                pending = item['call']
            elif item['type'] == 'COMPLETE' and pending['cell_id'] in failed_cells:
                item['raw_output'] = '{'
                item['evaluation'] = evaluate(p.variants[pending['rendered_variant_id']],'{')
        reseal(bad.directory/'journal',bad_payloads)
        bad._replay()
        result = bad.final_report()
        expected = 'NO_PHASE_A_CELL_QUALIFIED' if len(failed_cells) == 6 else None
        t.check('I3',name + ' integrated verdict',result['synthetic_primary_verdict'] == expected)
        t.check('I3',name + ' B_NOT_ELIGIBLE',all(result['state']['cell_states']['B:' + cell] == 'B_NOT_ELIGIBLE' for cell in failed_cells))
        t.check('I3',name + ' actual eligible count',len(result['state']['qualified']) == 6-len(failed_cells))

    run.authorization = grant('B','integrated')
    run.enter_b()
    t.check('I3','entered B running nonterminal',run.final_report()['synthetic_primary_verdict'] is None and
            sum(x == 'B_SCHEDULED' for x in run.state()['cell_states'].values()) == 6)
    run.checkpoint('bphase')
    for phase, expected in [('B',None),('A','PROVENANCE_MISMATCH')]:
        folder = clone(run.directory,'Bgrant_' + phase)
        if expected:
            t.rejects('I5','B resumed using A grant rejected',expected,
                lambda:Run(p,folder,'integrated',resume=True,exercise_authorization=True,authorization=grant(phase,'integrated')))
        else:
            recovered = Run(p,folder,'integrated',resume=True,exercise_authorization=True,authorization=grant(phase,'integrated'))
            t.check('I5','B grant reconstructs actual phase without A grant',recovered.current_phase == 'B')
            recovered.resume(folder/'CHECKPOINT_bphase.json')
            recovered.perform(recovered.b[0],transport,p.receipts())
            report = recovered.final_report()
            t.check('I5','B resume collection authorized synthetically only',report['provider_model_calls'] == 0 and
                    report['synthetic_primary_verdict'] == 'INCOMPLETE')
            t.check('I3','B interruption integrated incomplete',all(report['state']['cell_states']['B:' + c] == 'B_INCOMPLETE' for c in recovered.qualified))
    folder = clone(seed.directory,'Agrant_B')
    header = load(folder/'RUN.json'); header['exercise_authorization'] = True
    (folder/'RUN.json').write_bytes(canonical(header))
    t.rejects('I5','A resume using B grant rejected','PROVENANCE_MISMATCH',
        lambda:Run(p,folder,seed.run_id,resume=True,exercise_authorization=True,authorization=grant('B',seed.run_id)))
    for status in ('EXECUTION_FREEZE_CANDIDATE_ONLY',None):
        unauthorized = grant('A','candidategrant'); unauthorized['freeze_status'] = status
        t.rejects('I5','inactive freeze cannot grant A:' + str(status),'PROVENANCE_MISMATCH',
            lambda:Run(p,root/('candidategrant_' + str(status)),'candidategrant',exercise_authorization=True,authorization=unauthorized))
    # Correct A grant cannot collect B and catching the rejection stays terminal.
    folder = clone(run.directory,'Bfailure')
    bfailed = Run(p,folder,'integrated',resume=True,exercise_authorization=True,authorization=grant('B','integrated'))
    bfailed.resume(folder/'CHECKPOINT_bphase.json')
    bfailed.perform(bfailed.b[0],transport_class(p,'error'),p.receipts())
    t.check('I3','B receipted failure state/verdict',bfailed.state()['cell_states']['B:' + bfailed.b[0]['cell_id']] == 'B_INCOMPLETE' and
            bfailed.final_report()['synthetic_primary_verdict'] == 'INCOMPLETE')
    folder = clone(run.directory,'Bcollection_Agrant')
    wrong = Run(p,folder,'integrated',resume=True,exercise_authorization=True,authorization=grant('B','integrated'))
    wrong.resume(folder/'CHECKPOINT_bphase.json'); wrong.authorization = grant('A','integrated')
    counter = Counter()
    t.rejects('I5','A grant cannot collect B','PROVENANCE_MISMATCH',lambda:wrong.perform(wrong.b[0],counter,p.receipts()))
    t.check('I5','wrong phase grant zero transport',counter.calls == 0)
    summary['I3'] = dict(full_A_observations=480,A_before_B='AWAITING_CONDITIONAL_PHASE_B',zero_A_qualifiers='NO_PHASE_A_CELL_QUALIFIED',
        failed_A_B_not_eligible=True,receipted_A_B_failures='INCOMPLETE')
    summary['I5'] = dict(synthetic_B_grant_without_A='PASS',A_grant_for_B='REJECTED',B_grant_for_A='REJECTED',candidate_grant='REJECTED',provider_calls=0)

    # Actual one-byte mutations, including every manifest pin formerly omitted.
    # Only isolated copies are written; accepted originals are hashed before/after.
    newly_covered = {name for name,category in p.pin_categories.items()
                     if category in ('checker','preserved','source_or_supplement')}
    mutation_rows = []
    for index,name in enumerate(sorted(newly_covered)):
        isolated = copy.copy(p); isolated.root = root/('manifest_' + str(index)); isolated.root.mkdir()
        path = isolated.root/name; path.parent.mkdir(parents=True)
        shutil.copyfile(p.root/name,path)
        with path.open('r+b') as stream:
            original = stream.read(1); stream.seek(0); stream.write(bytes([original[0] ^ 1]))
        isolated.pins = {name:p.pins[name]}
        t.rejects('I6','actual one-byte precontact:' + name,'PRE_ARTIFACT_DIGEST_MISMATCH',isolated.verify)
        t.rejects('I6','actual one-byte postcontact:' + name,'PROTECTED_ARTIFACT_DIGEST_MISMATCH',lambda:isolated.verify(True))
        t.check('I6','original untouched:' + name,file_digest(p.root/name) == p.pins[name])
        mutation_rows.append(dict(path=name,category=p.pin_categories[name],pre='PRE_ARTIFACT_DIGEST_MISMATCH',post='PROTECTED_ARTIFACT_DIGEST_MISMATCH'))
        # Copies of large historical evidence are disposable test inputs, not
        # output artifacts; the mutation results and original pins are retained.
        path.unlink()
    summary['I6'] = dict(actual_byte_mutations=mutation_rows,protected_file_count=len(p.pins),
        candidate_file_bytes_verified=True,gold_projection_recomputed=True)
    return summary
