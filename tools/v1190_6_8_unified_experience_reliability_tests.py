from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1'); os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1190-8-data-'))
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.unified_experience_reliability_checkpoint import build_unified_experience_reliability_checkpoint
checks=[]; req=lambda x:checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 r=build_unified_experience_reliability_checkpoint(source_root=ROOT,runtime_root=Path(td))
 for k,v in [('ok',True),('contract_version','v1190.8'),('checkpoint_id','unified-experience-reliability:v1190.8'),('read_only',True),('post_available',False),('content_free',True),('source_modified',False),('runtime_mutated',False),('recovery_executed',False),('authority_granted',False),('authority_preserved',True)]: req(r.get(k)==v)
 req(r.get('passed')==r.get('total')); req(r.get('source_signature_before')==r.get('source_signature_after')); req(len(r.get('limitations',[]))==5); req(len(r.get('structural_digest',''))==64)
 s=r.get('summary',{}); req(s.get('approved_reliability_count')==1); req(s.get('rejected_reliability_count')==1); req(s.get('deferred_reliability_count')==1); req(s.get('blocked_boundary_case_count')==7)
reg=inspect_checkpoint_registry(source_root=ROOT); row=next((x for x in reg['checkpoints'] if x['checkpoint_id']=='unified-experience-reliability-checkpoint'),None); req(row is not None); req((row or {}).get('contract_version')=='v1190.8'); req(not reg['duplicate_checkpoint_ids']); req(not reg['duplicate_builder_targets'])
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'unified-experience-reliability-checkpoint'],cwd=ROOT,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','EIDOLON_DATA_DIR':tempfile.mkdtemp()}); req(proc.returncode==0)
try: j=json.loads(proc.stdout.strip().splitlines()[-1]); req(j.get('ok') is True); req(j.get('contract_version')=='v1190.8')
except Exception: req(False); req(False)
status,payload=dispatch_api('GET','/api/cognition/unified-experience-reliability-checkpoint'); req(status==200); req(payload.get('ok') is True); req((payload.get('data') or {}).get('contract_version')=='v1190.8')
status,_=dispatch_api('POST','/api/cognition/unified-experience-reliability-checkpoint'); req(status in {404,405})
release=(ROOT/'tools/release_verify.py').read_text(encoding="utf-8"); req(release.count('v1190.8-unified-experience-reliability')==1); req(release.count('v1190_6_8_unified_experience_reliability_tests.py')==1)
meta=(ROOT/'conscious_agent/release_metadata.py').read_text(encoding="utf-8"); req('WORKING_SOURCE_VERSION = "1190.8"' in meta); req('PREVIOUS_WORKING_SOURCE_VERSION = "1190.5"' in meta); req('v1190.9 Unified Experience checkpoint' in meta)
for n in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/n).read_text(encoding="utf-8"); req('v1190.8' in t); req('v1190.6-v1190.8 Unified Experience Reliability and Privacy Hardening' in t); req('v1190.9 Unified Experience checkpoint' in t); req('v1200' in t)
print(json.dumps({'suite':'v1190.6-8-unified-experience-reliability','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
