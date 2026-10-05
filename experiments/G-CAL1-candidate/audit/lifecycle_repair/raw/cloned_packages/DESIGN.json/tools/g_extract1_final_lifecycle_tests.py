"""LR1-LR3 attacks through real runner paths; synthetic isolated evidence only."""
from __future__ import annotations

import copy
from pathlib import Path
import shutil

from g_extract1_contract import IntegrityError, canonical, file_digest
from g_extract1_journal import Journal, seal_checkpoint, write_once
from g_extract1_lifecycle_tests import reseal
from g_extract1_runner import Run
from g_extract1_scoring import evaluate, primary_verdict


class Probe:
    synthetic_only = True

    def __init__(self, delegate=None, value=None, raises=False):
        self.delegate, self.value, self.raises = delegate, value, raises
        self.calls = 0

    def __call__(self, wire, row):
        self.calls += 1
        if self.raises:
            raise RuntimeError('synthetic transport exception')
        return self.delegate(wire, row) if self.delegate else self.value


def final_lifecycle_tests(p, t, root, transport_class):
    root.mkdir(parents=True)
    good = transport_class(p)
    summary = {}
    seed = Run(p, root/'seed', 'lrseed')
    seed.perform(seed.a[0], good, p.receipts())
    checkpoint = seed.checkpoint('good')
    checkpoint_cases = [(name, value) for name, value in (
        ('list', []), ('null', None), ('zero', 0), ('one', 1),
        ('string', 'string'), ('boolean', True), ('empty_object', {}),
        ('prefix_only', {'journal_prefix':checkpoint['payload']['journal_prefix']}))]
    for name, mutate in (
        ('state_list', lambda x:x.update(state=[])),
        ('prefix_null', lambda x:x.update(journal_prefix=None)),
        ('position_string', lambda x:x.update(next_schedule_position='2')),
        ('position_bool', lambda x:x.update(next_schedule_position=True)),
        ('schedule_number', lambda x:x.update(schedule_sha256=0)),
        ('events_wrong_type', lambda x:x['state'].update(integrity_events=[0])),
        ('scope_wrong_type', lambda x:x['state'].update(event_scopes=[{'event':0,'phase':'A','cell':None}])),
        ('qualified_wrong_type', lambda x:x['state'].update(qualified=[True])),
        ('extra_payload_key', lambda x:x.update(extra=True))):
        payload = copy.deepcopy(checkpoint['payload']); mutate(payload)
        checkpoint_cases.append((name, payload))
    checkpoint_rows = []
    for name, payload in checkpoint_cases:
        folder = root/('checkpoint_' + name)
        shutil.copytree(seed.directory, folder)
        seal_checkpoint(folder/'ATTACK.json', payload)
        run = Run(p, folder, seed.run_id, resume=True)
        t.rejects('LR1', name + ':corruption retained', 'CORRUPTED_CHECKPOINT', lambda:run.resume(folder/'ATTACK.json'))
        probe = Probe(good)
        t.rejects('LR1', name + ':valid resume after catch rejected', 'CORRUPTED_CHECKPOINT', lambda:run.resume(folder/'CHECKPOINT_good.json'))
        t.rejects('LR1', name + ':collection after catch rejected', 'CORRUPTED_CHECKPOINT', lambda:run.perform(run.a[1],probe,p.receipts()))
        t.check('LR1', name + ':INVALID and incident persisted', primary_verdict(p.design,dict(events=run.events)) == 'INVALID' and
            Journal(folder/'integrity').read()[0]['payload']['event'] == 'CORRUPTED_CHECKPOINT')
        del run
        run = Run(p, folder, seed.run_id, resume=True)
        t.rejects('LR1', name + ':restart valid resume rejected', 'CORRUPTED_CHECKPOINT', lambda:run.resume(folder/'CHECKPOINT_good.json'))
        t.rejects('LR1', name + ':restart collection rejected', 'CORRUPTED_CHECKPOINT', lambda:run.perform(run.a[1],probe,p.receipts()))
        t.check('LR1', name + ':zero later transport and no verification', probe.calls == 0 and not run._checkpoint_verified and
            primary_verdict(p.design,dict(events=run.state()['integrity_events'])) == 'INVALID')
        checkpoint_rows.append(dict(case=name,event='CORRUPTED_CHECKPOINT',caught_continuation=False,restart_continuation=False,later_transport_calls=0))
    for name, envelope in (('list',[]), ('null',None), ('scalar',1), ('missing_payload',{'sha256':'0'*64}),
                           ('extra_key',dict(checkpoint,extra=True)), ('seal_number',dict(checkpoint,sha256=0))):
        folder = root/('envelope_' + name); shutil.copytree(seed.directory,folder)
        write_once(folder/'ATTACK.json',envelope)
        run = Run(p,folder,seed.run_id,resume=True)
        t.rejects('LR1', 'envelope:' + name,'CORRUPTED_CHECKPOINT',lambda:run.resume(folder/'ATTACK.json'))
        probe = Probe(good)
        t.rejects('LR1','envelope terminal:' + name,'CORRUPTED_CHECKPOINT',lambda:run.perform(run.a[1],probe,p.receipts()))
        t.check('LR1','envelope zero calls:' + name,probe.calls == 0)
    summary['LR1'] = dict(payload_cases=checkpoint_rows,envelope_cases=6,terminal_after_catch=True,restart_persistence=True)

    malformed = [('none',None),('list',[]),('string',''),('zero',0),('false',False),('object',object()),
        ('empty_dict',{}),('failure_null',{'failure':None}),('raw_null',{'raw_output':None}),
        ('missing_truncated',{'raw_output':'{}'}),('missing_raw',{'provider_truncated':False}),
        ('missing_receipt',{'raw_output':'{}','provider_truncated':False}),
        ('trunc_integer',{'raw_output':'{}','provider_truncated':0,'receipt':{}}),
        ('receipt_list',{'raw_output':'{}','provider_truncated':False,'receipt':[]}),
        ('unknown_failure',{'failure':'other','receipt':None}),
        ('non_string_key',{0:True}),('exception',None)]
    for name in ('other_receipt','receipt_unserializable','failure_receipt_scalar','failure_wrong_kind','hybrid','invalid_utf8'):
        malformed.append((name,None))
    transport_rows = []
    for name, value in malformed:
        run = Run(p,root/('transport_' + name),'transport_' + name)
        row = run.a[0]
        result = good(p.wire(row),row)
        if name == 'other_receipt':
            result['receipt']['call_id'] = run.a[1]['call_id']; value = result
        elif name == 'receipt_unserializable':
            result['receipt']['extra'] = object(); value = result
        elif name == 'failure_receipt_scalar':
            value = dict(failure='timeout',receipt=1)
        elif name == 'failure_wrong_kind':
            value = dict(failure='error',receipt=dict(call_id=row['call_id'],request_sha256=row['request_sha256'],failure_kind='timeout'))
        elif name == 'hybrid':
            value = dict(result,failure='timeout')
        elif name == 'invalid_utf8':
            result['raw_output'] = '\ud800'; value = result
        first = Probe(value=value,raises=name == 'exception')
        run.perform(row,first,p.receipts())
        records = run.journal.read()
        t.check('LR2',name + ':START governed closure',len(records) == 2 and
            [x['payload']['type'] for x in records] == ['START','FAILURE'] and
            records[-1]['payload']['event'] == 'PROVIDER_FAILURE_WITHOUT_RECEIPT' and
            records[-1]['payload']['call_id'] == row['call_id'])
        t.check('LR2',name + ':terminal INVALID',run.final_report()['synthetic_primary_verdict'] == 'INVALID')
        probe = Probe(good)
        t.rejects('LR2',name + ':next call rejected','PROVIDER_FAILURE_WITHOUT_RECEIPT',lambda:run.perform(run.a[1],probe,p.receipts()))
        folder, run_id = run.directory, run.run_id
        del run
        run = Run(p,folder,run_id,resume=True)
        t.check('LR2',name + ':replayed failure not open START',run.events == ['PROVIDER_FAILURE_WITHOUT_RECEIPT'] and len(run.attempted) == 1)
        t.rejects('LR2',name + ':restart next call rejected','PROVIDER_FAILURE_WITHOUT_RECEIPT',lambda:run.perform(run.a[1],probe,p.receipts()))
        t.check('LR2',name + ':zero later transport',first.calls == 1 and probe.calls == 0)
        transport_rows.append(dict(case=name,event='PROVIDER_FAILURE_WITHOUT_RECEIPT',start_closed=True,later_transport_calls=0,restart_retained=True))
    for kind,event in [('timeout','PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT'),('error','PROVIDER_ERROR_WITH_FAILURE_RECEIPT'),
                        ('missing','MISSING_RESPONSE_WITH_FAILURE_RECEIPT'),('unreceipted','PROVIDER_FAILURE_WITHOUT_RECEIPT'),(None,None)]:
        run = Run(p,root/('valid_' + str(kind)),'valid_' + str(kind))
        run.perform(run.a[0],transport_class(p,kind),p.receipts())
        recovered = Run(p,run.directory,run.run_id,resume=True)
        t.check('LR2','valid outcome replay:' + str(kind),recovered.events == ([] if event is None else [event]) and
            len(recovered.evidence) == int(event is None))
    summary['LR2'] = dict(malformed_transport_cases=transport_rows,valid_outcomes_replayed=5,raw_exception_escape=False,open_starts=0)

    precontact = p.design['integrity_event_contract']['precontact_blocking_events']
    pre_rows = []
    for event in precontact:
        run = Run(p,root/event,event)
        probe = Probe(good)
        receipts = copy.deepcopy(p.receipts())
        receipt_key = dict(PRE_MODEL_IDENTITY_MISMATCH='models',PRE_PROVIDER_VERSION_MISMATCH='provider_version',
                           PRE_GENERATION_CONFIG_MISMATCH='generation_configuration').get(event)
        if receipt_key:
            receipts[receipt_key] = 'mutated'
        else:
            isolated = copy.copy(p)
            def blocked(*args, _event=event, **kwargs):
                raise IntegrityError(_event,'synthetic frozen catalog blocker')
            isolated.verify = blocked
            run.package = isolated
        t.rejects('LR3',event + ':before first START',event,lambda:run.perform(run.a[0],probe,receipts))
        run.package = p
        report = run.final_report()
        t.check('LR3',event + ':all six A_BLOCKED',report['synthetic_primary_verdict'] == 'PRE_CONTACT_BLOCKED' and
            len(report['state']['cell_states']) == 6 and set(report['state']['cell_states'].values()) == {'A_BLOCKED'} and
            report['state']['qualified'] == [] and not report['state']['b_entered'] and probe.calls == 0 and not run.attempted)
        recovered = Run(p,run.directory,run.run_id,resume=True)
        t.check('LR3',event + ':restart all A_BLOCKED',set(recovered.state()['cell_states'].values()) == {'A_BLOCKED'})
        t.rejects('LR3',event + ':restart collection forbidden',event,lambda:recovered.perform(recovered.a[0],probe,p.receipts()))
        pre_rows.append(dict(event=event,verdict='PRE_CONTACT_BLOCKED',phase_a_cells=['A_BLOCKED']*6,transport_calls=0,
            trigger='actual receipt mutation' if receipt_key else 'synthetic frozen-event injection at integrated verification boundary'))
    for kind,event,expected in [('timeout','PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT','INCOMPLETE'),
                                ('unreceipted','PROVIDER_FAILURE_WITHOUT_RECEIPT','INVALID')]:
        run = Run(p,root/('contacted_' + kind),'contacted_' + kind)
        run.perform(run.a[0],transport_class(p,kind),p.receipts())
        report = run.final_report()
        t.check('LR3',kind + ':postcontact never A_BLOCKED',report['synthetic_primary_verdict'] == expected and
            'A_BLOCKED' not in report['state']['cell_states'].values() and event in run.events)
    summary['LR3'] = dict(precontact_event_matrix=pre_rows,postcontact_invalid_incomplete_not_blocked=True)

    # I2 real prompt corruption and representative I6 file-byte mutations retain
    # terminal evidence even after the healthy package is restored.
    run = Run(p,root/'prompt_mutation','prompt_mutation')
    run.perform(run.a[0],good,p.receipts())
    altered = copy.copy(p); altered.wire = lambda row:p.wire(row) + b' '
    run.package = altered
    t.rejects('I2','caught real prompt byte mutation','UNAUTHORIZED_PROMPT_MUTATION',lambda:run.perform(run.a[1],good,p.receipts()))
    run.package = p
    probe = Probe(good)
    t.rejects('I2','prompt catch continuation','UNAUTHORIZED_PROMPT_MUTATION',lambda:run.perform(run.a[1],probe,p.receipts()))
    recovered = Run(p,run.directory,run.run_id,resume=True)
    t.rejects('I2','prompt restart continuation','UNAUTHORIZED_PROMPT_MUTATION',lambda:recovered.perform(recovered.a[1],probe,p.receipts()))
    t.check('I2','prompt zero continuation transport',probe.calls == 0)
    mutations = []
    for file_name in ('AUTHORING_CANDIDATES.json','validate_corpus.py','independent_contamination.py','validate_finalization.py'):
        relative = next(x for x in p.pins if x.endswith('/' + file_name))
        for contacted in (False,True):
            label = file_name + ('_post' if contacted else '_pre')
            run = Run(p,root/label,label)
            if contacted:
                run.perform(run.a[0],good,p.receipts())
            isolated = copy.copy(p); isolated.root = root/('bytes_' + label)
            path = isolated.root/relative; path.parent.mkdir(parents=True)
            shutil.copyfile(p.root/relative,path)
            with path.open('r+b') as stream:
                value = stream.read(1); stream.seek(0); stream.write(bytes([value[0] ^ 1]))
            isolated.pins = {relative:p.pins[relative]}; run.package = isolated
            event = 'PROTECTED_ARTIFACT_DIGEST_MISMATCH' if contacted else 'PRE_ARTIFACT_DIGEST_MISMATCH'
            probe = Probe(good)
            next_row = run.a[int(contacted)]
            t.rejects('I6',label + ':real integrated mutation',event,lambda:run.perform(next_row,probe,p.receipts()))
            run.package = p
            t.rejects('I6',label + ':catch healthy package cannot continue',event,lambda:run.perform(next_row,probe,p.receipts()))
            recovered = Run(p,run.directory,run.run_id,resume=True)
            t.rejects('I6',label + ':restart healthy package cannot continue',event,lambda:recovered.perform(next_row,probe,p.receipts()))
            t.check('I6',label + ':zero calls original intact',probe.calls == 0 and file_digest(p.root/relative) == p.pins[relative])
            path.unlink()
            mutations.append(dict(path=relative,contacted=contacted,event=event,continuation_calls=0))
    summary['integrated_manifest_mutations'] = mutations
    for name in ('missing_marker','fabricated_seal'):
        folder = root/name; shutil.copytree(seed.directory,folder)
        payloads = [copy.deepcopy(x['payload']) for x in Journal(folder/'journal').read()]
        if name == 'missing_marker':
            (folder/'journal/000003.json').unlink()
        else:
            payloads[-1]['checkpoint_sha256'] = 'a'*64; reseal(folder/'journal',payloads)
        if name == 'missing_marker':
            run = Run(p,folder,seed.run_id,resume=True)
            t.rejects('I4',name,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT',lambda:run.resume(folder/'CHECKPOINT_good.json'))
        else:
            t.rejects('I4',name,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT',lambda:Run(p,folder,seed.run_id,resume=True))
    return summary


def completed_state_regressions(p,t,root,pilot_directory,transport_class):
    """Replayed full evidence tests actual B final states, not flag-only vectors."""
    payloads = [copy.deepcopy(x['payload']) for x in Journal(pilot_directory/'journal').read()]
    payloads = [x for x in payloads if x['type'] != 'CHECKPOINT_CREATED']
    cells = p.blueprint['schedule_plan']['phase_b_cell_order']
    results = []
    for name,failed in [('all_pass',set()),('mixed',{'small:R2'}),('all_fail',set(cells))]:
        run = Run(p,root/name,'mechanical-only')
        data = copy.deepcopy(payloads)
        pending = None
        for item in data:
            if item['type'] == 'START':
                pending = item['call']
            elif item['type'] == 'COMPLETE' and pending['phase'] == 'B' and pending['cell_id'] in failed:
                item['raw_output'] = '{'; item['evaluation'] = evaluate(p.variants[pending['rendered_variant_id']],'{')
        reseal(run.directory/'journal',data); run._replay()
        report = run.final_report()
        expected = 'TARGETED_REQUALIFICATION_SUPPORTED' if not failed else (
            'QUALIFICATION_METHOD_FAILED_VALIDATION' if len(failed) == 6 else 'MIXED_TARGETED_REQUALIFICATION_SUPPORTED')
        t.check('I3',name + ':full B integrated verdict',report['synthetic_primary_verdict'] == expected)
        t.check('I3',name + ':full B integrated states',all(report['state']['cell_states']['B:' + cell] ==
            ('B_FAILED_VALIDATION' if cell in failed else 'FINALLY_QUALIFIED') for cell in cells))
        write_once(run.directory/'FINAL_REPORT.json',report)
        results.append(dict(case=name,verdict=expected,states=report['state']['cell_states']))
    a_payloads = payloads[:next(i for i,x in enumerate(payloads) if x['type'] == 'PHASE_B')+1]
    for kind,expected in [('timeout','INCOMPLETE'),('unreceipted','INVALID')]:
        run = Run(p,root/('B_' + kind),'mechanical-only')
        reseal(run.directory/'journal',a_payloads); run._replay()
        run.perform(run.b[0],transport_class(p,kind),p.receipts())
        report = run.final_report()
        t.check('I3','B ' + kind + ':non-interruption state/verdict',report['synthetic_primary_verdict'] == expected and
            'A_BLOCKED' not in report['state']['cell_states'].values() and
            (kind != 'timeout' or report['state']['cell_states']['B:' + run.b[0]['cell_id']] == 'B_INCOMPLETE'))
        write_once(run.directory/'FINAL_REPORT.json',report)
    return results
