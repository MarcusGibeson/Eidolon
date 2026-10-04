import audit
import json
import subprocess
from g_extract1_contract import Package, canonical, digest, load, source_pins

ROOT, OUT = audit.ROOT, audit.OUT
summary = load(OUT/'FINAL_AUDIT.json')
assert summary['verdict'] == 'PASS' and not summary['product_assertion_failures']
baseline = load(OUT/'repository_before.json')
result = subprocess.run(['git','-c','safe.directory=C:/Users/marcu/Eidolon-g4adj','status','--porcelain=v1','--branch'],cwd=ROOT,capture_output=True)
if result.returncode or result.stdout.decode() != baseline['status']:
    raise RuntimeError('repository status changed at evidence sealing')
p = Package(ROOT)
if source_pins() != summary['source_sha256']:
    raise RuntimeError('audited source changed at sealing')
for name in p.pins:
    if digest((ROOT/name).read_bytes()) != baseline['files'][name]:
        raise RuntimeError('protected file changed at sealing:'+name)
for name in ('G_ROUTE4_CLOSURE.json','PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json'):
    relative = 'experiments/G-ROUTE4-candidate/closure/'+name
    if digest((ROOT/relative).read_bytes()) != baseline['files'][relative]:
        raise RuntimeError('historical closure changed at sealing')
files = {path.relative_to(OUT).as_posix():digest(path.read_bytes()) for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'EVIDENCE_MANIFEST.json'}
manifest = dict(schema='independent-audit-evidence.v1',evidence_root=str(OUT),verdict=summary['verdict'],file_count_excluding_manifest=len(files),files_sha256=files,
    final_candidate_sha256=summary['candidate_sha256'],repository_status_unchanged_at_sealing=True,
    protected_50_and_source_8_and_historical_closure_rechecked=True,socket_attempts=audit.network_attempts,
    packaging_checks_not_in_behavioral_assertion_counts=True)
(OUT/'EVIDENCE_MANIFEST.json').write_bytes(canonical(manifest))
print(json.dumps(dict(verdict=summary['verdict'],files=len(files),report_sha256=files['FINAL_AUDIT.json'],readable_report_sha256=files['AUDIT_REPORT.md'],evidence_manifest_sha256=digest((OUT/'EVIDENCE_MANIFEST.json').read_bytes()),socket_attempts=audit.network_attempts)),flush=True)
