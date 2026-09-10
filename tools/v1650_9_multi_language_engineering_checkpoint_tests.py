from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from software_language_capabilities import *
checks=[]
def req(v,n):checks.append(n);assert v,n

def digest_tree(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def make_mixed(base):
 r=base/'mixed';(r/'src').mkdir(parents=True);(r/'web').mkdir();(r/'scripts').mkdir();(r/'config').mkdir()
 (r/'src/main.py').write_text('def f():\n    return 1\n',encoding='utf-8')
 (r/'src/app.js').write_text('export const x = 1;\n',encoding='utf-8')
 (r/'src/types.ts').write_text('export type X = {a:number};\n',encoding='utf-8')
 (r/'web/index.html').write_text('<!doctype html><html><body>ok</body></html>',encoding='utf-8')
 (r/'web/site.css').write_text('body { margin: 0; }',encoding='utf-8')
 (r/'config/app.json').write_text('{"enabled":true}',encoding='utf-8')
 (r/'config/app.yaml').write_text('enabled: true\n',encoding='utf-8')
 (r/'scripts/check.sh').write_text('echo "ok"\n',encoding='utf-8')
 (r/'package.json').write_text('{"name":"mixed"}',encoding='utf-8')
 (r/'package-lock.json').write_text('{"lockfileVersion":3}',encoding='utf-8')
 (r/'pyproject.toml').write_text('[project]\nname="mixed"\n',encoding='utf-8')
 return r

def make_java(base):
 r=base/'java';(r/'src/main/java').mkdir(parents=True)
 (r/'src/main/java/App.java').write_text('class App { public static void main(String[] a){} }',encoding='utf-8')
 (r/'pom.xml').write_text('<project></project>',encoding='utf-8')
 return r

with tempfile.TemporaryDirectory(prefix='eidolon-v1650-9-') as td:
 base=Path(td); repo=make_mixed(base); before=digest_tree(repo); rt=base/'rt'
 # Portable validators use actual parsers only where they can do so without project execution.
 for rel,lang in [('src/main.py','python'),('web/index.html','html'),('web/site.css','css'),('config/app.json','json'),('config/app.yaml','yaml'),('scripts/check.sh','shell')]:
  row=validate_portable_syntax(repo/rel,language=lang)
  req(row['status'] in {'validated','tokenized_not_executed','yaml_parser_unavailable'},f'{lang}_validation_status')
  req(not row['project_code_executed'] and not row['dependency_installed'],f'{lang}_no_execution')
 native=validate_portable_syntax(repo/'src/app.js',language='javascript')
 req(not native['validated'] and native['status']=='native_parser_deferred','js_native_deferred')
 req(not native['action_executed'] and not native['standing_authority_granted'],'js_authority')
 bad=repo/'config/bad.json';bad.write_text('{bad',encoding='utf-8')
 invalid=validate_portable_syntax(bad,language='json');req(not invalid['validated'] and invalid['status'].startswith('syntax_invalid:'),'json_invalid')
 bad.unlink()

 model_result=build_language_capability_model(repo,runtime_root=rt);model=model_result['language_model']
 req(model_result['ok'],'model_ok')
 req(model['contract_version']=='v1650.9','contract')
 req(model['language_count']>=8,'language_count')
 for lang in ('python','javascript','typescript','html','css','json','yaml','shell'):
  req(lang in model['languages'],f'detect_{lang}')
 req(model['manifest_count']>=3,'manifests')
 req(model['lockfile_count']>=1,'lockfile')
 req(model['execution_adapters_reused'],'reuse_execution_adapters')
 req(model['native_parser_execution_deferred'],'native_parser_truth')
 req(not model['dependency_installation_authorized'] and not model['runtime_download_authorized'],'install_denied')
 req(not model['project_code_executed'] and not model['provider_contacted'],'model_no_exec')
 req(not model['source_paths_exposed'] and not model['raw_source_content_exposed'],'model_privacy')
 req(not model['action_executed'] and not model['standing_authority_granted'],'model_authority')
 req(digest_tree(repo)==before,'model_source_immutable')
 again=build_language_capability_model(repo,runtime_root=rt);req(again['status']=='language_capability_model_current','model_idempotent')

 boundary=analyze_build_dependency_boundary(repo,runtime_root=rt,offline=True)['boundary']
 req(boundary['manager_count']>=2,'manager_detection')
 req(boundary['lockfile_present'],'boundary_lockfile')
 req(boundary['offline_requested'],'offline_request')
 req(boundary['native_toolchain_required_count']>=2,'native_toolchains')
 req(boundary['native_toolchain_evidence_deferred'],'native_toolchain_deferred')
 req(not boundary['dependency_resolution_performed'] and not boundary['dependency_installation_performed'],'no_dependency_change')
 req(not boundary['network_contacted'],'no_network')
 req(not boundary['offline_ready_proven'],'offline_honesty')
 req(boundary['installation_requires_separate_authority'],'separate_install_authority')
 req(not boundary['action_executed'] and not boundary['standing_authority_granted'],'boundary_authority')

 java=make_java(base); jbefore=digest_tree(java)
 bench=run_portable_cross_language_checkpoint([
  {'name':'mixed-heldout','root':repo,'expected_languages':['python','javascript','typescript','html','css','json','yaml','shell']},
  {'name':'java-heldout','root':java,'expected_languages':['java']},
 ],runtime_root=base/'bench_rt')
 cp=bench['checkpoint']
 req(bench['ok'],'checkpoint_ok')
 req(cp['project_count']==2,'checkpoint_projects')
 req(cp['aggregate_score']>=0.8,'checkpoint_score')
 req(cp['portable_only'] and not cp['native_builds_executed'],'checkpoint_portable')
 req(not cp['dependencies_installed'] and not cp['network_contacted'],'checkpoint_no_side_effects')
 req(not cp['native_windows_verified'],'windows_deferred')
 req(not cp['source_paths_exposed'] and not cp['raw_source_content_exposed'],'checkpoint_privacy')
 req(not cp['action_executed'] and not cp['standing_authority_granted'],'checkpoint_authority')
 req(digest_tree(repo)==before and digest_tree(java)==jbefore,'checkpoint_source_immutable')

print(json.dumps({'suite':'v1650.9-multi-language-engineering-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
