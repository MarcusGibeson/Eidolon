from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import broader_project_language_adapters as a
checks=[]
def check(v): checks.append(bool(v))
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(ROOT).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),len(rows)
before=sig(); reg=a.adapter_registry(); contract=a.build_broader_project_language_adapter_contract()
for v in (reg.get('ok'),reg.get('adapter_count')==6,contract.get('ok'),contract.get('contract_version')=='v1238.8',contract.get('java_maven_and_gradle_supported'),contract.get('dotnet_rust_go_php_supported'),contract.get('existing_javascript_web_python_delegated'),contract.get('manifest_contents_not_read'),contract.get('v1237_compatible_orchestration_blueprint'),contract.get('adapter_acceptance_does_not_authorize_execution')): check(v)
for row in reg.get('adapters') or []:
    check(len(row.get('adapter_contract_digest',''))==64); check(row.get('executes_commands') is False); check(row.get('installs_dependencies') is False); check(row.get('downloads_runtimes') is False)
for k,e in a.AUTHORITY_FLAGS.items(): check(contract.get(k) is e)
cases=[
('java_maven',['pom.xml','src/main/java/App.java'],'java_maven'),
('java_gradle',['build.gradle.kts','gradlew','src/main/java/App.java'],'java_gradle'),
('dotnet',['App.sln','src/App/App.csproj','src/App/Program.cs'],'dotnet'),
('rust_cargo',['Cargo.toml','src/main.rs'],'rust_cargo'),
('go_module',['go.mod','cmd/app/main.go'],'go_module'),
('php_composer',['composer.json','src/App.php'],'php_composer'),
]
for label,paths,expected in cases:
    rt=tempfile.mkdtemp(prefix='eidolon-v1238-found-')
    r=a.prepare_broader_project_adapter_assessment('project_'+hashlib.sha256(label.encode()).hexdigest()[:16],relative_paths=paths,runtime_root=rt)
    check(r.get('ok')); check(r.get('detection_state')=='adapter_selected'); check(r.get('selected_adapter_id')==expected); check(r.get('project_contents_read') is False); check((r.get('inventory') or {}).get('raw_paths_stored') is False); check(len(r.get('assessment_digest',''))==64)
    replay=a.prepare_broader_project_adapter_assessment(r['project_reference'],relative_paths=paths,runtime_root=rt)
    check(replay.get('assessment_id')==r.get('assessment_id')); check(replay.get('assessment_digest')==r.get('assessment_digest'))
for paths,delegated in [(['package.json','src/index.js'],'node_javascript'),(['pyproject.toml','src/app.py'],'python'),(['index.html','app.js'],'browser_runtime')]:
    r=a.prepare_broader_project_adapter_assessment('project_'+hashlib.sha256(str(paths).encode()).hexdigest()[:16],relative_paths=paths,runtime_root=tempfile.mkdtemp())
    check(r.get('ok')); check(r.get('detection_state')=='adapter_delegated_existing'); check(delegated in (r.get('delegated_adapter_ids') or []))
amb=a.prepare_broader_project_adapter_assessment('project_'+'a'*16,relative_paths=['pom.xml','build.gradle','src/main/java/App.java'],runtime_root=tempfile.mkdtemp())
check(amb.get('ok')); check(amb.get('detection_state')=='adapter_ambiguous'); check(set(amb.get('candidate_adapter_ids') or [])=={'java_maven','java_gradle'})
explicit=a.prepare_broader_project_adapter_assessment('project_'+'b'*16,relative_paths=['pom.xml','build.gradle'],requested_adapter_id='java_maven',runtime_root=tempfile.mkdtemp())
check(explicit.get('ok')); check(explicit.get('selected_adapter_id')=='java_maven')
unsupported=a.prepare_broader_project_adapter_assessment('project_'+'c'*16,relative_paths=['README.md','src/data.txt'],runtime_root=tempfile.mkdtemp())
check(unsupported.get('ok')); check(unsupported.get('detection_state')=='adapter_unsupported')
check(before==sig())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
