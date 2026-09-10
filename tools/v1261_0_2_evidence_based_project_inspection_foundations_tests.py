from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from evidence_based_project_inspection_foundations import CLAIM_CLASSES,DENIED_AUTHORITY,EVIDENCE_KINDS,inspect_project_evidence,public_project_evidence_inspection
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            r=p.relative_to(ROOT).as_posix()
            if r.startswith('data/') or '__pycache__' in r or r.endswith(('.pyc','.pyo')): continue
            rows.append((r,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig()
with tempfile.TemporaryDirectory(prefix='eidolon-v1261-foundation-') as td:
    project=Path(td)/'project';(project/'src').mkdir(parents=True);(project/'tests').mkdir();(project/'docs').mkdir();(project/'data').mkdir()
    (project/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8')
    (project/'README.md').write_text('# Demo\nKnown limitation: example only.\n',encoding='utf-8')
    (project/'src'/'app.py').write_text('# TODO improve validation\nVALUES = [\n' + ('1,\n' * 30000) + ']\ndef add(a,b):\n    return a+b\n',encoding='utf-8')
    (project/'tests'/'test_app.py').write_text('from src.app import add\ndef test_add(): assert add(1,2)==3\n',encoding='utf-8')
    (project/'docs'/'architecture.md').write_text('# Architecture\n',encoding='utf-8')
    (project/'data'/'private.txt').write_text('DO_NOT_SCAN_PRIVATE_PAYLOAD',encoding='utf-8')
    report=inspect_project_evidence(project); public=public_project_evidence_inspection(report)
    req(report['ok'] and report['status']=='evidence_based_project_inspection_ready','inspection_ready')
    req(report['project_type']=='python_project' and report['adapter_id']=='python','python_project_detected')
    req(report['file_count']==5,'private_data_excluded_from_file_count')
    req(report['private_or_excluded_count']>=1,'private_exclusion_recorded')
    req(report['test_file_count']==1,'test_surface_counted')
    req(report['documentation_file_count']>=2,'documentation_surface_counted')
    req(report['configuration_file_count']==1,'configuration_surface_counted')
    req(report['maintenance_marker_count']>=1,'maintenance_markers_minimized')
    req(report['limitation_marker_count']>=1,'limitation_markers_minimized')
    req(report['python_parse_failure_count']==0,'python_parse_clean');req(report['python_parse_skipped_count']==0,'large_valid_python_parsed_without_prefix_false_positive')
    req(len(report['source_manifest_digest'])==64 and len(report['inspection_digest'])==64,'sealed_digests_present')
    req(set(report['claim_class_counts'])==set(CLAIM_CLASSES),'all_claim_classes_present')
    req(all(report['claim_class_counts'][k]>=1 for k in CLAIM_CLASSES),'each_epistemic_class_used')
    req(all(e['kind'] in EVIDENCE_KINDS for e in report['evidence']),'evidence_kinds_bounded')
    req(all(e['content_minimized'] for e in report['evidence']),'evidence_content_minimized')
    req(not report['raw_source_content_stored'] and not report['raw_operator_feedback_stored'] and not report['raw_runtime_payload_stored'],'raw_content_not_stored')
    req(not report['private_runtime_discovery_performed'],'private_runtime_not_discovered')
    req(not report['development_proposal_created'] and not report['backlog_item_created'],'inspection_creates_no_work')
    req(public['content_minimized'] and not public['raw_paths_exposed'] and not public['raw_source_content_exposed'],'public_projection_minimized')
    req(public['file_count']==5 and public['test_file_count']==1,'public_counts_match')
    req('DO_NOT_SCAN_PRIVATE_PAYLOAD' not in json.dumps(report),'private_payload_absent')
    for k,v in DENIED_AUTHORITY.items(): req(report[k] is v,f'{k}_denied')
    second=inspect_project_evidence(project)
    req(second['inspection_digest']==report['inspection_digest'],'deterministic_duplicate_inspection')
    req(second['source_manifest_digest']==report['source_manifest_digest'],'deterministic_manifest')
    bad=project/'src'/'broken.py';bad.write_text('def broken(:\n',encoding='utf-8')
    broken=inspect_project_evidence(project)
    req(broken['python_parse_failure_count']==1,'syntax_signal_observed')
    req(any(c['claim_code']=='python_parse_failure_observed' and c['claim_class']=='observed' for c in broken['claims']),'syntax_claim_observed_not_inferred')
req(sig()==before,'foundation_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1261.0-v1261.2-evidence-based-project-inspection-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'project_modified':False,'backlog_created':False,'release_authorized':False},indent=2,sort_keys=True))
