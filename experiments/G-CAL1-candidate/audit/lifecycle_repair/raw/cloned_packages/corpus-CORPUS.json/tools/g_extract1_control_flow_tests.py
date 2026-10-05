"""Scoped control-flow closure through actual synthetic runner methods."""
from __future__ import annotations

import copy

from g_extract1_contract import canonical
from g_extract1_journal import Journal, write_once
from g_extract1_lifecycle_tests import reseal
from g_extract1_runner import Run
from g_extract1_scoring import event_category

OMISSION = 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT'


class ControlSignal(BaseException):
    pass


class RaisingTransport:
    synthetic_only = True

    def __init__(self, signal):
        self.signal, self.calls = signal, 0

    def __call__(self, wire, row):
        self.calls += 1
        raise self.signal


class CountingTransport:
    synthetic_only = True

    def __init__(self, delegate):
        self.delegate, self.calls = delegate, 0

    def __call__(self, wire, row):
        self.calls += 1
        return self.delegate(wire, row)


def exercise_signal(p,t,run,signal,good,label,*,boundary='invocation'):
    schedule = run.active_schedule()
    first, second = schedule[:2]
    if boundary == 'result_validation':
        class SignalValue:
            def __eq__(self, other):
                raise signal
        class ReturnedControl:
            synthetic_only = True
            calls = 0
            def __call__(self, wire, row):
                self.calls += 1
                result = good(wire,row)
                result['receipt']['call_id'] = SignalValue()
                return result
        transport = ReturnedControl()
    else:
        transport = RaisingTransport(signal)
    caught = None
    try:
        run.perform(first,transport,p.receipts())
    except BaseException as exc:
        caught = exc
    t.check('CF',label + ':original signal identity and payload',caught is signal and
        type(caught) is type(signal) and caught.args == signal.args)
    t.check('CF',label + ':retained before propagation',run.events == [OMISSION] and
        event_category(p.design,OMISSION) == 'INVALID' and
        run.event_scopes == [dict(event=OMISSION,phase=first['phase'],cell=first['cell_id'])])
    incidents = Journal(run.directory/'integrity').read()
    t.check('CF',label + ':owned incident persisted',len(incidents) == 1 and
        incidents[0]['payload']['event'] == OMISSION and incidents[0]['payload']['phase'] == first['phase'] and
        incidents[0]['payload']['cell'] == first['cell_id'])
    records = run.journal.read()
    t.check('CF',label + ':no fabricated response or failure receipt',records[-1]['payload']['type'] == 'START' and
        records[-1]['payload']['call'] == first and first['call_id'] not in run.evidence)
    t.check('CF',label + ':immediate INVALID report',run.final_report()['synthetic_primary_verdict'] == 'INVALID')
    later = CountingTransport(good)
    t.rejects('CF',label + ':external catch cannot collect',OMISSION,lambda:run.perform(second,later,p.receipts()))
    t.check('CF',label + ':no second START',later.calls == 0 and transport.calls == 1 and
        canonical(records) == canonical(run.journal.read()))
    folder,run_id = run.directory,run.run_id
    del run
    t.rejects('CF',label + ':restart rejects open call under frozen omission',OMISSION,
        lambda:Run(p,folder,run_id,resume=True))
    t.check('CF',label + ':restart cannot invoke transport',later.calls == 0 and
        Journal(folder/'integrity').read()[0]['payload']['event'] == OMISSION)
    row = dict(case=label,phase=first['phase'],cell=first['cell_id'],exception=type(signal).__name__,
        original_object_propagated=True,event=OMISSION,category='INVALID',persisted_before_propagation=True,
        fabricated_receipts=0,later_transport_calls=0,second_start=False,restart='REJECTED_OMISSION',boundary=boundary)
    write_once(folder/'CONTROL_FLOW_RESULT.json',row)
    return row


def control_flow_tests(p,t,root,transport_class):
    root.mkdir(parents=True)
    good = transport_class(p)
    cases = []
    for signal in (KeyboardInterrupt('keyboard signal'),SystemExit(17),GeneratorExit('generator signal'),ControlSignal('custom signal')):
        label = type(signal).__name__
        run = Run(p,root/label,label)
        cases.append(exercise_signal(p,t,run,signal,good,label))
    # Malformed host values must not smuggle the same escape through receipt
    # comparison after the transport callable has returned.
    for signal in (KeyboardInterrupt('receipt keyboard'),ControlSignal('receipt custom')):
        label = 'result_' + type(signal).__name__
        run = Run(p,root/label,label)
        cases.append(exercise_signal(p,t,run,signal,good,label,boundary='result_validation'))
    ordinary = []
    for signal in (RuntimeError('ordinary'),ValueError('ordinary'),OSError('ordinary')):
        label = 'ordinary_' + type(signal).__name__
        run = Run(p,root/label,label)
        transport = RaisingTransport(signal)
        run.perform(run.a[0],transport,p.receipts())
        records = run.journal.read()
        t.check('CF',label + ':governed unreceipted behavior unchanged',run.events == ['PROVIDER_FAILURE_WITHOUT_RECEIPT'] and
            [x['payload']['type'] for x in records] == ['START','FAILURE'] and records[-1]['payload']['receipt'] is None)
        later = CountingTransport(good)
        t.rejects('CF',label + ':caught path terminal','PROVIDER_FAILURE_WITHOUT_RECEIPT',lambda:run.perform(run.a[1],later,p.receipts()))
        recovered = Run(p,run.directory,run.run_id,resume=True)
        t.rejects('CF',label + ':restart terminal','PROVIDER_FAILURE_WITHOUT_RECEIPT',lambda:recovered.perform(recovered.a[1],later,p.receipts()))
        t.check('CF',label + ':zero later transport',later.calls == 0)
        ordinary.append(dict(exception=type(signal).__name__,event='PROVIDER_FAILURE_WITHOUT_RECEIPT',restart='TERMINAL',later_calls=0))
    return dict(control_flow_cases=cases,ordinary_exception_regression=ordinary,
        generic_guard_unchanged=True,new_journal_record_types=0,provider_model_calls=0)


def control_flow_b_regressions(p,t,root,pilot_directory,transport_class):
    payloads = [copy.deepcopy(x['payload']) for x in Journal(pilot_directory/'journal').read()]
    payloads = payloads[:next(i for i,x in enumerate(payloads) if x['type'] == 'PHASE_B')+1]
    cases = []
    for signal in (KeyboardInterrupt('B keyboard'),SystemExit(23),GeneratorExit('B generator'),ControlSignal('B custom')):
        label = 'B_' + type(signal).__name__
        run = Run(p,root/label,'mechanical-only')
        reseal(run.directory/'journal',payloads); run._replay()
        cases.append(exercise_signal(p,t,run,signal,transport_class(p),label))
    return cases
