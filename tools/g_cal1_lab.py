"""Isolated G-CAL1 laboratory; explicit transport injection, no provider API."""
from __future__ import annotations

from pathlib import Path

from g_cal1_contract import DATA, ROOT, diagnosis, summarize
from g_extract1_contract import canonical, digest, file_digest, load, require, IntegrityError
from g_extract1_journal import Journal, checkpoint_payload, seal_checkpoint, verify_checkpoint, write_once
from g_extract1_runner import check_call, failure_event, guarded, transport_outcome
from g_extract1_scoring import evaluate, event_category

VERSION = 'g-cal1.lab.v1'


def transport_boundary(transport, mechanical):
    require(type(mechanical) is bool,'PROVENANCE_MISMATCH','mode must be Boolean')
    if not mechanical:
        require(getattr(transport,'synthetic_only',True) is False,
                'PROVENANCE_MISMATCH','synthetic or unmarked transport forbidden in live mode')


def authority(package, run_id, activation, authorization, receipts):
    """No G-EXTRACT1 grant or candidate-only status can authorize G-CAL1."""
    pointer_path = DATA/'execution/ACTIVE_FREEZE.json'
    require(pointer_path.is_file(),'PROVENANCE_MISMATCH','no separately active G-CAL1 freeze')
    pointer = load(pointer_path)
    require(type(pointer) is dict and set(pointer)=={'activation_path','activation_sha256'},'PROVENANCE_MISMATCH','active pointer')
    path = DATA/'execution/EXECUTION_FREEZE_ACTIVATION.json'
    require(pointer['activation_path']=='execution/EXECUTION_FREEZE_ACTIVATION.json' and path.is_file() and
            file_digest(path)==pointer['activation_sha256'],'PROVENANCE_MISMATCH','activation binding')
    record = load(path)
    require(record==activation and record.get('experiment')=='G-CAL1' and record.get('status')=='EXECUTION_FREEZE_ACTIVE' and
            record.get('binding')==package.binding and record.get('phase_authorized') is False,
            'PROVENANCE_MISMATCH','active freeze only, no implicit phase authority')
    candidate_path = DATA/'preexecution/final/EXECUTION_FREEZE_CANDIDATE.json'
    candidate = load(candidate_path)
    require(file_digest(candidate_path)==record.get('candidate_sha256') and candidate.get('binding')==package.binding and
            candidate.get('status')=='EXECUTION_FREEZE_CANDIDATE_ONLY' and candidate.get('activated') is False,
            'PROVENANCE_MISMATCH','reviewed candidate identity')
    require(type(authorization) is dict and authorization.get('status')=='EXPLICIT_OPERATOR_PHASE_AUTHORIZATION' and
            authorization.get('experiment')=='G-CAL1' and authorization.get('phase')=='CAL' and
            authorization.get('run_id')==run_id and authorization.get('freeze_status')=='EXECUTION_FREEZE_ACTIVE' and
            authorization.get('binding')==package.binding and authorization.get('synthetic_evidence_allowed') is False,
            'PROVENANCE_MISMATCH','separate CAL grant')
    expected = candidate['provider_binding']
    require(type(receipts) is dict and receipts.get('provider')==expected['provider'] and
            receipts.get('provider_version')==expected['provider_version'],'PRE_PROVIDER_VERSION_MISMATCH')
    require(receipts.get('models')==expected['models'],'PRE_MODEL_IDENTITY_MISMATCH')
    require(receipts.get('generation_configuration')==package.design['generation_configuration'],'PRE_GENERATION_CONFIG_MISMATCH')
    return {'activation_sha256':file_digest(path),'authorization_sha256':digest(canonical(authorization)),
            'provider_receipts_sha256':digest(canonical(receipts))}


class Run:
    @guarded
    def __init__(self,package,directory,run_id,*,mechanical=True,resume=False,
                 activation=None,authorization=None,provider_receipts=None):
        self.package,self.directory,self.run_id = package,Path(directory),run_id
        self.mechanical,self._owned = mechanical,False
        self.events,self.event_scopes = [],[]
        self._error_cell = None
        self._checkpoint_verified = not resume
        self.evidence,self.attempted,self.last_checkpoint = {},set(),None
        self.binding = dict(package.binding,lab_version=VERSION)
        self.activation,self.authorization,self.provider_receipts = activation,authorization,provider_receipts
        require(type(mechanical) is bool,'PROVENANCE_MISMATCH','mode must be Boolean')
        package.verify()
        self.authority_evidence = None if mechanical else authority(package,run_id,activation,authorization,provider_receipts)
        if resume:
            require(self.directory.is_dir(),'MISSING_CHECKPOINT_AFTER_INTERRUPTION','run directory')
            self._owned = True
        else:
            require(not self.directory.exists(),'PRE_EXISTING_RUN_COLLISION',str(self.directory))
            self.directory.mkdir(parents=True)
            self._owned = True
        self.journal = Journal(self.directory/'journal')
        self.incidents = Journal(self.directory/'integrity')
        if resume:
            for row in self.incidents.read():
                p = row['payload']
                require(type(p) is dict and p.get('binding')==self.binding and p.get('run_id')==run_id,
                        'CORRUPTED_OR_UNPARSEABLE_JOURNAL','incident binding')
                self.events.append(p['event'])
                self.event_scopes.append({'event':p['event'],'phase':'CAL','cell':p['cell']})
            require(not self.events,self.events[0] if self.events else 'PROVENANCE_MISMATCH','retained terminal incident')
            self._replay()
        else:
            self.journal.append({'kind':'RUN_CREATED','run_id':run_id,'binding':self.binding,
                                 'mode':'SYNTHETIC_ONLY' if mechanical else 'LIVE','authority':self.authority_evidence})

    def _retain(self,error):
        if not hasattr(self,'events'): return
        scope = {'event':error.event,'phase':'CAL','cell':self._error_cell}
        if scope not in self.event_scopes:
            self.events.append(error.event);self.event_scopes.append(scope)
            if self._owned:
                journal = self.incidents if hasattr(self,'incidents') else Journal(self.directory/'integrity')
                journal.append({'event':error.event,'detail':error.detail,'phase':'CAL','cell':self._error_cell,
                                'run_id':self.run_id,'binding':self.binding})

    def state(self):
        invalid = any(event_category(self.package.historical.design,e)=='INVALID' for e in self.events)
        pre = any(event_category(self.package.historical.design,e)=='PRE_CONTACT_BLOCKED' for e in self.events)
        if invalid: verdict='INVALID'
        elif pre and not self.attempted: verdict='PRE_CONTACT_BLOCKED'
        elif self.events: verdict='INCOMPLETE'
        elif len(self.evidence)==80: verdict='VALID_COMPLETE'
        else: verdict='RUNNING'
        return {'qualified':[],'integrity_events':list(self.events),'event_scopes':list(self.event_scopes),
                'verdict':verdict,'completed_observations':len(self.evidence),'attempted_calls':len(self.attempted)}

    def _ready(self):
        require(self._checkpoint_verified,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT','verify before collection/report/checkpoint')
        require(not self.events,self.events[0] if self.events else 'PROVENANCE_MISMATCH','terminal retained incident')
        self.package.verify(contacted=bool(self.attempted))
        if not self.mechanical:
            require(authority(self.package,self.run_id,self.activation,self.authorization,self.provider_receipts)==self.authority_evidence,
                    'PROVENANCE_MISMATCH','authority drift')

    @guarded
    def perform(self,row,transport):
        self._error_cell = row.get('cell_id') if type(row) is dict else None
        self._ready()
        position = len(self.attempted)
        require(position<len(self.package.schedule),'UNAUTHORIZED_RETRY','schedule exhausted')
        expected = self.package.schedule[position]
        require(type(row) is dict,'PROVENANCE_MISMATCH','schedule object')
        check_call(expected,row)
        require(row['call_id'] not in self.attempted,'UNAUTHORIZED_RETRY')
        request = self.package.wire(row)
        require(digest(request)==row['request_sha256'],'UNAUTHORIZED_PROMPT_MUTATION')
        transport_boundary(transport,self.mechanical)
        self.journal.append({'kind':'START','row':row,'request_sha256':digest(request),'binding':self.binding,
                             'run_id':self.run_id,'mode':'SYNTHETIC_ONLY' if self.mechanical else 'LIVE'})
        self.attempted.add(row['call_id'])
        try:
            result = transport(request,row)
        except Exception:
            result = {'failure':'unreceipted','receipt':None}
        except BaseException:
            self._retain(IntegrityError('SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT','transport control-flow exception'))
            raise
        result = transport_outcome(row,result)
        if 'failure' in result:
            event = failure_event(row,result['failure'],result['receipt'])
            self.journal.append({'kind':'FAILURE','call_id':row['call_id'],'failure':result['failure'],
                                 'receipt':result['receipt'],'event':event})
            self._retain(IntegrityError(event,'transport failure'))
            raise IntegrityError(event)
        require(self.mechanical or result['receipt'].get('synthetic_only') is not True,
                'PROVENANCE_MISMATCH','synthetic response in live mode')
        # Re-check immutable inputs before interpreting returned bytes.
        self.package.verify(contacted=True)
        member = self.package.members[row['fixture_id']]
        score = evaluate(member,result['raw_output'],truncated=result['provider_truncated'])
        diagnostic = diagnosis(member,result['raw_output'],score)
        self.journal.append({'kind':'COMPLETE','call_id':row['call_id'],'result':result,'score':score,'diagnostic':diagnostic})
        self.evidence[row['call_id']] = score
        self._error_cell = None
        return score

    @guarded
    def checkpoint(self):
        self._ready()
        path = self.directory/'checkpoints'/f'{len(self.journal.read()):06d}.json'
        payload = checkpoint_payload(self.run_id,self.binding,self.package.schedule,self.journal,len(self.attempted)+1,self.state())
        seal_checkpoint(path,payload)
        marker = {'kind':'CHECKPOINT_CREATED','path':path.relative_to(self.directory).as_posix(),
                  'file_sha256':file_digest(path),'payload':payload}
        self.journal.append(marker)
        self.last_checkpoint = marker
        return path

    def _replay(self):
        records = self.journal.read()
        require(records and records[0]['payload']=={'kind':'RUN_CREATED','run_id':self.run_id,'binding':self.binding,
                'mode':'SYNTHETIC_ONLY' if self.mechanical else 'LIVE','authority':self.authority_evidence},
                'CORRUPTED_OR_UNPARSEABLE_JOURNAL','run creation')
        pending = None
        for index,record in enumerate(records[1:],1):
            p = record['payload']
            require(type(p) is dict and type(p.get('kind')) is str,'CORRUPTED_OR_UNPARSEABLE_JOURNAL','payload')
            if p['kind']=='START':
                require(pending is None and len(self.attempted)<80,'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT')
                row = self.package.schedule[len(self.attempted)]
                check_call(row,p['row'])
                require(p['run_id']==self.run_id and p['binding']==self.binding and
                        p['mode']==('SYNTHETIC_ONLY' if self.mechanical else 'LIVE') and
                        p['request_sha256']==digest(self.package.wire(row)), 'PROVENANCE_MISMATCH','START lineage')
                pending = row;self.attempted.add(row['call_id'])
            elif p['kind']=='COMPLETE':
                require(pending is not None and p['call_id']==pending['call_id'],'CORRUPTED_OR_UNPARSEABLE_JOURNAL','completion lineage')
                result = transport_outcome(pending,p['result'])
                require('failure' not in result and result==p['result'],'PROVENANCE_MISMATCH','success receipt')
                member = self.package.members[pending['fixture_id']]
                score = evaluate(member,result['raw_output'],truncated=result['provider_truncated'])
                require(score==p['score'] and diagnosis(member,result['raw_output'],score)==p['diagnostic'],
                        'PROVENANCE_MISMATCH','scorer replay')
                self.evidence[pending['call_id']]=score;pending=None
            elif p['kind']=='FAILURE':
                require(pending is not None and p['call_id']==pending['call_id'],'CORRUPTED_OR_UNPARSEABLE_JOURNAL','failure lineage')
                require(p['event']==failure_event(pending,p['failure'],p['receipt']),'PROVENANCE_MISMATCH','failure event')
                raise IntegrityError(p['event'],'failure history terminal')
            elif p['kind']=='CHECKPOINT_CREATED':
                require(pending is None,'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT')
                path = self.directory/p['path']
                require(path.parent==self.directory/'checkpoints' and path.is_file() and file_digest(path)==p['file_sha256'],
                        'CORRUPTED_CHECKPOINT','marker/file binding')
                prefix = self.journal.prefix(records[:index])
                row = verify_checkpoint(path,run_id=self.run_id,binding=self.binding,schedule=self.package.schedule,
                    journal=self.journal,reconstructed_state=self.state(),next_position=len(self.attempted)+1,prefix=prefix)
                require(row['payload']==p['payload'],'UNVERIFIABLE_INTERRUPTION_CHECKPOINT','marker payload')
                self.last_checkpoint = p
            elif p['kind']=='RESUME_VERIFIED':
                require(pending is None and self.last_checkpoint is not None and
                        p=={'kind':'RESUME_VERIFIED','checkpoint':self.last_checkpoint},'UNVERIFIABLE_INTERRUPTION_CHECKPOINT')
            else:
                raise IntegrityError('CORRUPTED_OR_UNPARSEABLE_JOURNAL','unknown record type')
        require(pending is None,'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT','open START')

    @guarded
    def verify_resume(self,path):
        require(self.last_checkpoint is not None,'MISSING_CHECKPOINT_AFTER_INTERRUPTION')
        # Validate supplied structure before comparing it to the checkpoint marker.
        verify_checkpoint(path,run_id=self.run_id,binding=self.binding,schedule=self.package.schedule,
                          journal=self.journal,reconstructed_state=self.state(),next_position=len(self.attempted)+1,
                          prefix=self.last_checkpoint['payload']['journal_prefix'])
        require(Path(path)==self.directory/self.last_checkpoint['path'] and file_digest(path)==self.last_checkpoint['file_sha256'],
                'UNVERIFIABLE_INTERRUPTION_CHECKPOINT','must resume latest original checkpoint')
        require(not self.events,'PROVENANCE_MISMATCH','terminal incident')
        self._checkpoint_verified=True
        self._ready()
        self.journal.append({'kind':'RESUME_VERIFIED','checkpoint':self.last_checkpoint})

    @guarded
    def final_report(self):
        self._ready()
        return {'experiment':'G-CAL1','run_id':self.run_id,'binding':self.binding,'state':self.state(),
                'mode':'SYNTHETIC_ONLY' if self.mechanical else 'LIVE','summary':summarize(self.package,self.evidence),
                'provider_model_calls':0 if self.mechanical else len(self.attempted),
                'autonomy':False,'belief_effects':'none','phase_b':False}
