from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import adversarial_execution_cognitive_boundary as a
checks=[]
def check(v): checks.append(bool(v))
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(ROOT).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),len(rows)
before=sig(); registry=a.attack_registry(); contract=a.build_adversarial_execution_cognitive_boundary_contract(); upstream=a.upstream_boundary_contracts()
check(registry.get('ok')); check(registry.get('attack_case_count')==28)
check((registry.get('category_counts') or {}).get('execution_boundary')==12)
check((registry.get('category_counts') or {}).get('cognitive_boundary')==8)
check((registry.get('category_counts') or {}).get('compound_boundary')==8)
check(contract.get('ok')); check(contract.get('contract_version')=='v1239.8'); check(contract.get('roadmap_path')=='Balanced Mind-and-Action Path 3')
check(upstream.get('ok')); check(upstream.get('upstream_contract_count')==8); check(not upstream.get('dangerous_authority_violations'))
for row in upstream.get('upstream_contracts') or []:
    check(row.get('contract_ok')); check(not row.get('dangerous_authority_true')); check(len(row.get('contract_digest',''))==64)
for key,expected in a.AUTHORITY_FLAGS.items(): check(contract.get(key) is expected)
for case in registry.get('attack_cases') or []:
    check(case.get('category') in a.ATTACK_CATEGORIES); check(case.get('expected_fail_closed') is True); check(case.get('attack_executed') is False); check(len(case.get('attack_case_digest',''))==64)
rt=tempfile.mkdtemp(prefix='eidolon-v1239-found-')
for index,case in enumerate(registry.get('attack_cases') or []):
    project='project_'+hashlib.sha256(f'p{index}'.encode()).hexdigest()[:16]
    evidence=hashlib.sha256(f'e{index}'.encode()).hexdigest()
    lineage={'session':hashlib.sha256(f's{index}'.encode()).hexdigest(),'review':hashlib.sha256(f'r{index}'.encode()).hexdigest()}
    result=a.prepare_adversarial_boundary_assessment(project,attack_case_id=case['attack_case_id'],evidence_digest=evidence,lineage_digests=lineage,runtime_root=rt)
    check(result.get('ok')); check(result.get('assessment_state')=='attack_blocked'); check(result.get('boundary_decision')=='fail_closed'); check(result.get('authority_state')=='separate_not_granted'); check(result.get('attacks_executed') is False); check(result.get('private_state_fetched') is False); check(result.get('lineage_digests_stored') is False); check(result.get('raw_evidence_stored') is False)
    for key,expected in a.AUTHORITY_FLAGS.items(): check(result.get(key) is expected)
    replay=a.prepare_adversarial_boundary_assessment(project,attack_case_id=case['attack_case_id'],evidence_digest=evidence,lineage_digests=lineage,runtime_root=rt)
    check(replay.get('assessment_id')==result.get('assessment_id')); check(replay.get('assessment_record_digest')==result.get('assessment_record_digest'))
for kwargs,reason in [
    ({'project_reference':'bad','attack_case_id':'consumed_authorization_reuse','evidence_digest':'1'*64},'invalid_project_reference'),
    ({'project_reference':'project_'+'a'*16,'attack_case_id':'unknown','evidence_digest':'1'*64},'unknown_attack_case'),
    ({'project_reference':'project_'+'a'*16,'attack_case_id':'consumed_authorization_reuse','evidence_digest':'x'},'invalid_evidence_digest'),
    ({'project_reference':'project_'+'a'*16,'attack_case_id':'consumed_authorization_reuse','evidence_digest':'1'*64,'lineage_digests':{'secret_token':'2'*64}},'private_lineage_key_blocked'),
    ({'project_reference':'project_'+'a'*16,'attack_case_id':'consumed_authorization_reuse','evidence_digest':'1'*64,'lineage_digests':{'session':'bad'}},'invalid_lineage_digest'),
]:
    out=a.prepare_adversarial_boundary_assessment(runtime_root=tempfile.mkdtemp(),**kwargs); check(not out.get('ok')); check(out.get('reason')==reason)
check(before==sig())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
