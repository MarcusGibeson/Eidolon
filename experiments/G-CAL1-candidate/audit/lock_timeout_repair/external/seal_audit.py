"""Seal completed evidence from this SAME audit; no product tests or repo writes."""
import sys
sys.dont_write_bytecode = True
import json
from datetime import datetime, timezone
import audit as a

OUT = a.OUT
def load(name):
    return json.loads((OUT/name).read_bytes())
def digest_file(name):
    return a.sha((OUT/name).read_bytes())
def verify():
    manifest = load('FINAL_SHA256_MANIFEST.json')
    actual = a.tree(OUT)
    actual.pop('FINAL_SHA256_MANIFEST.json')
    assert actual==manifest['files'] and len(actual)==manifest['member_count']
    print(json.dumps({'verified':True,'member_count':len(actual),'manifest_sha256':digest_file('FINAL_SHA256_MANIFEST.json'),
                      'completion_sha256':digest_file('FINAL_AUDIT_COMPLETION.json'),'report_sha256':digest_file('FINAL_AUDIT_REPORT.md')}))

def recover_pending_completion():
    stop = load('FINAL_PENDING_LOG_WRITE_STOP.json')
    assert stop['required_checks_completed_before_failure'] is True
    preservation = load('raw/preservation_verification.json')
    sources = load('raw/source_bindings_verification.json')
    pilot_tree = load('raw/independent_pilot_tree.json')
    assert preservation['whole_checkout_unchanged'] is True and all(v['mismatches']==0 for v in preservation['groups'].values())
    assert len(sources)==22 and all(v['protected_checkout_hash_exact'] and (v['raw_equal'] or v['inherited_EOL_only']) for v in sources.values())
    assert len(pilot_tree)==327
    for name in ('independent_pilot_one','independent_pilot_two'):
        assert a.tree(OUT/'raw'/name)==pilot_tree
    data = a.REPO/'experiments/G-CAL1-candidate'
    directory = data/'preexecution/lock_timeout_repair'
    candidate = json.loads((directory/'EXECUTION_FREEZE_CANDIDATE.json').read_bytes())
    producer = json.loads((directory/'PILOT_REPORT.json').read_bytes())
    evidence = json.loads((directory/'EVIDENCE_MANIFEST.json').read_bytes())
    old_rows = load('completion_assertions.json')
    already = sum(r['passed'] and r['name'].startswith('source exact Git implementation bytes:') for r in old_rows)
    preserved = load('COMPLETION_INPUT_PRESERVATION.json')
    before = load('REPOSITORY_BEFORE.json')
    closure_prefix = 'experiments/G-EXTRACT1-candidate/closure/'
    closure_files = sum(k.startswith(closure_prefix) and '/' not in k[len(closure_prefix):] for k in before)
    fixed_checks = ['handoff','implementation ancestry','producer rows','producer categories','baseline scopes','manifest pin scope',
                    'manifest non-pin fields','candidate supersession','old timeout failure','old blocked audit','preparation stop',
                    'route4 closure','history metadata','seven untracked count','seven untracked bytes','whole checkout identity',
                    'Git status','network boundary','pilot equality']
    formula = {'source_lineage_new':len(sources)-already,'source_protected_hashes':len(sources),'producer_evidence_members':len(evidence['files']),
               'baseline_byte_checks':sum(v['files'] for v in preservation['groups'].values()),'accepted_closure_files':closure_files,
               'historical_external_input_hashes':len(preserved),'fixed_checks':len(fixed_checks)}
    count = sum(formula.values())
    assert already==16 and closure_files==4 and len(preserved)==18 and count==37781
    details = {'implementation':'c01706ca04f14e88819b26bdd148a3d61b5688ec','HEAD':load('initial_git.json')['head'],
               'branch':load('initial_git.json')['branch'],'candidate_sha256':a.sha((directory/'EXECUTION_FREEZE_CANDIDATE.json').read_bytes()),
               'protected_pins':len(candidate['protected_artifacts']),'producer_actual_assertions':len(producer['assertions']),
               'producer_actual_lock_assertions':sum(v for k,v in producer['categories'].items() if k.startswith('LOCK_TIMEOUT')),
               'producer_count_is_not_authority':True,'producer_manifest_members':len(evidence['files']),
               'preservation_groups':preservation['groups'],'whole_checkout_files':preservation['whole_checkout_files'],'untracked_preserved':len(preservation['untracked']),
               'pilot_files_each':len(pilot_tree),'pilot_tree_sha256':a.sha(a.canon(pilot_tree))}
    assert details['HEAD']=='ae7902c72384a65d65db53a56fc6afc5b119f8d9'
    record = {'schema':'g-cal1.same-audit.pending-completion.proof-recovery.v1','verdict':'PASS','assertions':count,'passed':count,'error':None,
              'details':details,'raw_per_assertion_ledger_available':False,'assertion_count_provenance':'Derived exactly from executed source call/loop structure and preserved inputs; not a recovered raw ledger.',
              'count_formula':formula,'fixed_check_names':fixed_checks,'proof_files_sha256':{x:digest_file(x) for x in stop['completion_proofs_written_before_failure']},
              'executed_source_sha256':digest_file('final_pending_checks.py'),'checks_rerun':False,'product_tests_rerun':False,
              'source_read_only_completion_proofs_written_after_final_assertion':True,'output_failure_record':'FINAL_PENDING_LOG_WRITE_STOP.json'}
    a.save('PENDING_CHECK_COMPLETION_RECOVERY.json',record)
    return record

def seal():
    pending = recover_pending_completion()
    assert pending['verdict']=='PASS' and pending['passed']==pending['assertions'] and not pending['error']
    first = load('timeout_result.json')
    middle = load('remaining_result.json')
    assert first['verdict']=='PASS'
    definitions = [
        ('timeout',None,None),
        ('full','boundary:seal/binding tamper event:event','HARNESS_EXPECTATION_ADJUDICATION.json'),
        ('remaining','candidate:targeted timeout report resolves uniquely','HARNESS_REPORT_LOCATION_ADJUDICATION.json'),
        ('completion','source exact Git implementation bytes:tools/g_route1_operational.py','HARNESS_INHERITED_EOL_ADJUDICATION.json')]
    phase_counts, exclusions, assertion_files = {}, [], {}
    for phase, excluded_name, adjudication in definitions:
        name = phase+'_assertions.json'
        rows = load(name)
        failures = [r for r in rows if not r['passed']]
        if excluded_name:
            assert len(failures)==1 and failures[0]['name']==excluded_name
            assert load(adjudication)['classification'].endswith('NOT_PRODUCT_FINDING')
            exclusions.append({'phase':phase,'assertion':excluded_name,'adjudication':adjudication,'raw_false_row_preserved':True,'counted_as_pass':False})
        else:
            assert not failures
        phase_counts[phase] = {'raw_rows':len(rows),'valid_passed':sum(r['passed'] for r in rows),
                               'harness_only_false_expectations':len(failures),'sha256':digest_file(name)}
        assertion_files[name] = digest_file(name)
    valid_passes = sum(x['valid_passed'] for x in phase_counts.values())
    raw_rows = sum(x['raw_rows'] for x in phase_counts.values())
    recorded_passes = valid_passes
    phase_counts['final_pending'] = {'raw_rows':None,'source_derived_executed_checks':pending['assertions'],
                                   'source_derived_passed':pending['passed'],'proof_recovery':'PENDING_CHECK_COMPLETION_RECOVERY.json',
                                   'raw_per_assertion_ledger_available':False}
    valid_passes += pending['passed']
    details = pending['details']
    preservation = load('raw/preservation_verification.json')
    science = middle['details']['science']
    attacks = middle['details']['former_blockers']
    timeout = first['details']['actual_timeout']
    versions = {name:digest_file(name) for name in ['FIRST_TIMEOUT_EXECUTED_SOURCE.py','FULL_EXECUTED_SOURCE.py',
                'REMAINING_EXECUTED_SOURCE.py','completion_checks.py','final_pending_checks.py','seal_audit.py']}
    findings = []
    limitations = [
        'Offline provider/model/blob/config binding only; no metadata contact, option-honoring attestation or new scientific observations.',
        'No machine power-loss or kernel/filesystem fault-injection claim. Atomic native hardlink publication, no-replace collision, seals and process/object behavior were exercised.',
        'Whole-checkout content-file byte snapshot excludes Git administrative files; Git optional locks were disabled in expanded/final harnesses. No commit, push, activation, grant or repository-content write performed.',
        'First-case source was reconstructed from the exact recorded initial patch after the preservation note arrived after extension; it was not hashed before its original execution. The LF source and reconstruction provenance are preserved.',
        'Initial unmodified production lock used the default external temporary OS-lock namespace; synchronization bytes are not scientific/evidence journals. Subsequent lock housekeeping and all authored audit/evidence artifacts are within this one external directory.',
        'Three unsupported harness assumptions interrupted phases. Raw stops, false rows and executed sources remain unchanged; only pending coverage continued, with no timeout, former-blocker or pilot reruns.'
        ,'The final pending helper completed and wrote all three completion proofs, then refused to overwrite its historical ledger due an output-name bug. Its 37,781 check count is reconstructed exactly from preserved source/inputs; no per-check raw list was fabricated. Proof recovery and the writer stop are explicit artifacts.'
    ]
    report = f'''# G-CAL1 Independent Audit Completion

Verdict: PASS. Exactly one NEW independent audit, continued in the same external directory after interruptions. No product P1/P2 findings. Previous repository BLOCKED reviews remain historical failures.

## Identity and Authority

- Worktree: C:/Users/marcu/Eidolon-g4adj; branch: {details['branch']}.
- Implementation: {details['implementation']}.
- Pilot/candidate HEAD: {details['HEAD']}.
- Candidate SHA-256: {details['candidate_sha256']}.
- Protected pins: {details['protected_pins']}, actual checkout bytes verified.
- Candidate only; activated=false; execution unauthorized; audit evidence is not an activation or grant.
- Provider/model/network metadata/contact: 0. Explicit Python socket deny hooks installed in external scripts and child processes. No agents or new reviewer, product repairs, repository writes, commits or push.

## First Attack: Real Default Timeout

A/B/C shared one unique external synthetic run directory; C predated the timeout. A held the real OS-backed lifecycle lock inside public perform at a paused pre-START readiness point. B attempted public perform. The production deadline and exception signal were not patched or replaced.

- Observed elapsed time: {timeout['elapsed_seconds']} seconds (unmodified 120-second path).
- Event/category: PROVENANCE_MISMATCH / INVALID through frozen inherited catalog.
- Published sealed incident: {timeout['incident_file']}.
- Incident SHA-256: {timeout['incident_sha256']}.
- Exact run ID, binding, phase CAL, correct cell and lock-unavailable detail checked.
- Persistence completed while A still held the real lifecycle lock.
- Original exception object/type/args propagated after persistence, observed around the actual contextmanager without replacing its signal.
- B.state verdict INVALID. Same B, stale C and fresh constructor/resume rejected promptly while lock held and again after release.
- Timeout-case transport=0; START=0; open START=false; fake receipts=0. A released with exact pre-START cleanup; published incident bytes remained unchanged.
- Ordinary integrity Journal alone was not used as authority; the independently published lock_boundary_incidents namespace was inspected directly.

Repair boundary reviewed: lock-entry errors are caught outside the acquisition attempt, retained through independently sealed/no-replace publication, then the original error is re-raised. Published terminal incidents are observed before attempting a contended lock. Publication flushes/fsyncs an exclusively created pending file, then exposes complete bytes through atomic no-replace hardlink.

## Former Blockers and Storage

- P1-A: stale perform/checkpoint/verify_resume/final_report, stale duplicate, coordinated cross-object thread and separate-process serialization passed.
- P1-B: four signals at transport, normalization, receipt traversal, scoring, before COMPLETE and after durable COMPLETE: 24 vectors. Exact propagation; preclosure INVALID omission and terminal rejection without forged receipts; safe durable-completion replay and next-observation behavior.
- P1-C: 12 authoritative cache mutations, detached callback row/config aliases, and actual external cloned corpus/design/schedule disk mutations passed.
- P1-D: only explicit synthetic_only is True accepted. Unmarked, false, integer 1, other markers, provider-like and unmarked-wrapper cases rejected with no START/contact; inactive live authority rejected before any live directory creation.
- Independent boundary publication: two separate processes published while governed lifecycle lock was held; distinct incidents retained, hardlink collision did not overwrite bytes, canonical seal/run/binding/phase/cell/event/detail tampering rejected. Ordinary uncontended calls created no spurious incidents.
- Storage: three unverified-resume public methods, eight malformed checkpoint shapes, six resealed checkpoint lineage mutations, four failure kinds, seven malformed outcomes, six schedule mutations, journal corruption, no retry, exact valid checkpoint/restart and receipt replay passed.

## Science and Pilots

- Frozen fixtures: 40; C1/C2/C3/C4: 10 each. Integer Gregorian cycle conversion independently agreed with all 40 gold values and library arithmetic; allocation/source/answer uniqueness also verified.
- Independently reconstructed 80 frozen wire bodies, seeds, order and schedule SHA: {science['schedule_sha256']}.
- Historical controls: 12,720 exact records recomputed using independently authored decisions over frozen dual encodings. NEW/NEW: 780 exact records recomputed.
- Unavailable legacy tuples: 5,040 N/A, zero pass credit; typed history: 7,680 applicable comparisons. Symbolic scaffold recomputed; ordinary/shape/content/residual comparisons retained.
- Model/config binding checked entirely offline against frozen local receipts. Descriptive-only science preserved; no qualification threshold, routing authority, phase B or scientific observations.
- Two fresh independently executed full pilots completed 80 observations each, with complete 327-file trees. Exact checkpoint/resume, receipt/scorer and independent journal-chain replay verified.
- Both fresh trees equal each other and BOTH candidate-bound producer trees byte-for-byte. Pilot tree SHA-256 (canonical relative-path-to-file-hash map): {details['pilot_tree_sha256']}.
- Producer report checked independently: {details['producer_actual_assertions']} actual passing assertion rows, {details['producer_actual_lock_assertions']} lock-related; counts were not audit authority.

## Preservation and Bindings

- Actual baseline bytes checked: science 91 files; prior G-CAL1 evidence 33,513 files; closed history 2,961 files; zero mismatches.
- Whole checkout: {details['whole_checkout_files']} content files; exact initial/final file-byte identity. Seven unrelated untracked G-EXTRACT1 corpus artifacts unchanged; Git status and requested HEAD unchanged.
- Producer evidence manifest: {details['producer_manifest_members']} actual bound members checked.
- LAB_MANIFEST rebind limited to repaired lab hash and two added implementation/test source hashes; non-pin scientific/governance fields unchanged. Science/old evidence not rewritten; only expected existing metadata revisions were accepted.
- Repaired G-CAL1 source bytes match the exact implementation Git blobs. Inherited Windows CRLF checkout conversions were explicitly recorded and verified against unchanged Git content AND exact protected checkout hashes.
- G-EXTRACT1 accepted closure 1757155387af122d126f6db9fd03477e2823c2bb preserved, CLOSED VALID NEGATIVE with no qualified Phase A cell. G-ROUTE4 actual closure remains CLOSED FAILED.
- Old f45825a0165f23b78da13fb0fec8dcade010b37fadbe7cdc8c2020a05b0f0336 candidate remains BLOCKED/unactivated/superseded. Prior BLOCKED audits, failed timeout supplement/completion record and initial zero-test PREPARATION_STOP_01 preserved unchanged.

## Harness Stops, Not Product Findings

1. FULL_EXECUTED_SOURCE.py:491 expected corrupted-journal for unknown event; frozen g_extract1_scoring.py:237 correctly raises INVALID PROVENANCE_MISMATCH. Raw full_result/full_assertions preserved.
2. REMAINING_EXECUTED_SOURCE.py:819 incorrectly required a unique hash-search match. Producer source tools/g_cal1_timeout_repair.py:98 explicitly binds ACTUAL_TIMEOUT_REPORT.json; its intentional per-run copy has identical bytes. Raw remaining_result/remaining_assertions preserved.
3. completion_checks.py:62 required raw Git equality on inherited g_route1_operational.py despite Git-recorded i/lf w/crlf. Only 211 CRLF conversions differed; exact protected checkout digest and Git content were verified. Raw completion_result/completion_assertions preserved.

These three false harness expectations are NOT converted into passes and are NOT product P1 findings. Their adjudication records and executed sources remain immutable. No product repair or attack/pilot rerun followed them. The earlier report writer's exclusive-create collision with its historical report did not overwrite that report.

## Exact Assertion Accounting

- Serialized raw assertion rows across preserved phases: {raw_rows}.
- Serialized valid passing assertion rows: {recorded_passes}.
- Additional completed pending checks: {pending['assertions']}, exact source-derived count supported by post-final-assertion proof files; raw per-check ledger unavailable after the exclusive-create writer failure.
- Total valid executed checks: {valid_passes}, combining recorded rows and explicitly reconstructed final count.
- Preserved unsupported harness false expectations excluded from pass count: {len(exclusions)}.
- Final pending read-only checks: {pending['assertions']}/{pending['passed']} passing.
- Counts include preservation/lineage checks and N/A-label verification, not scientific observations or N/A contamination pass credit.

Phase counts, reconstruction arithmetic, and every AVAILABLE assertion-file hash are in FINAL_AUDIT_COMPLETION.json and PENDING_CHECK_COMPLETION_RECOVERY.json. First executed source SHA: {versions['FIRST_TIMEOUT_EXECUTED_SOURCE.py']}. All executed-source hashes and raw evidence are in the final SHA manifest.

## Reproduction

Use these preserved source versions in ONE empty external reproduction directory with this exact repository HEAD, in order. Commands intentionally reproduce and preserve the three documented harness stops before finishing remaining checks; they never run an old repository review.

```powershell
python -B FIRST_TIMEOUT_EXECUTED_SOURCE.py timeout
python -B FULL_EXECUTED_SOURCE.py full
python -B REMAINING_EXECUTED_SOURCE.py remaining
python -B completion_checks.py
python -B final_pending_checks.py
```

Keep the adjudication JSON files with the scripts; sibling audit.py supplies shared helpers without auto-executing product tests. The final helper intentionally reproduces the preserved exclusive-create output-name error after saving all required proof files. seal_audit.py performs explicitly labelled proof/count recovery without re-executing required checks, generates final artifacts, then --verify checks every final manifest member.

## Limitations and Completion

''' + '\n'.join('- '+x for x in limitations) + '''

Required authorized coverage is complete; remaining required gaps: none. No remote HEAD check or push performed. Parent archival/status changes are outside reviewer scope. PASS permits freeze REVIEW only, never activation or live execution. Autonomy=false; belief effects=none.

READY_FOR_G_CAL1_EXECUTION_FREEZE_REVIEW
'''
    path = OUT/'FINAL_AUDIT_REPORT.md'
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(report)
    completion = {'schema':'g-cal1.same-new-independent-audit.completion.v1','verdict':'PASS','completed':True,
                  'new_independent_audits':1,'same_external_directory':str(OUT),'prior_failed_audit_resumed':False,
                  'attacks_or_pilots_restarted_on_resume':False,'product_findings':findings,'required_remaining_gaps':[],
                  'HEAD':details['HEAD'],'branch':details['branch'],'implementation':details['implementation'],
                  'candidate_sha256':details['candidate_sha256'],'candidate_status':'EXECUTION_FREEZE_CANDIDATE_ONLY',
                  'activated':False,'execution_authorized':False,'provider_model_calls':0,'network_attempts':0,
                  'repository_writes':0,'push_performed':False,'autonomy':False,'belief_effects':'none',
                  'first_timeout':timeout,'former_blockers':attacks,'science':science,
                  'pilots':{'completed_each':80,'files_each':327,'tree_sha256':details['pilot_tree_sha256'],'byte_identical':True,'supplied_trees_equal':True},
                  'binding_preservation_completion':details,'whole_checkout_preservation':preservation,
                  'phase_assertion_counts':phase_counts,'raw_assertion_rows':raw_rows,'valid_passing_assertions':valid_passes,
                  'serialized_passing_assertions':recorded_passes,'source_derived_pending_passes':pending['passed'],
                  'final_pending_raw_ledger_available':False,'pending_proof_recovery':'PENDING_CHECK_COMPLETION_RECOVERY.json',
                  'harness_only_exclusions':exclusions,'assertion_file_sha256':assertion_files,'executed_source_sha256':versions,
                  'limitations':limitations,'report_path':str(path),'report_sha256':digest_file('FINAL_AUDIT_REPORT.md'),
                  'final_manifest':'FINAL_SHA256_MANIFEST.json','manifest_self_excluded':True,
                  'completed_utc':datetime.now(timezone.utc).isoformat(),'readiness':'READY_FOR_G_CAL1_EXECUTION_FREEZE_REVIEW'}
    a.save('FINAL_AUDIT_COMPLETION.json',completion)
    files = a.tree(OUT)
    a.save('FINAL_SHA256_MANIFEST.json',{'schema':'g-cal1.independent-audit.final-sha256-manifest.v1','files':files,
                                      'member_count':len(files),'self_excluded':True,'canonical_tree_sha256':a.sha(a.canon(files))})
    verify()
    print(json.dumps({'verdict':'PASS','valid_passing_assertions':valid_passes,'raw_rows':raw_rows,'harness_only_exclusions':len(exclusions),
                      'phase_counts':phase_counts,'details':details}))

if __name__=='__main__':
    if sys.argv[1:]==['--verify']:
        verify()
    else:
        seal()
