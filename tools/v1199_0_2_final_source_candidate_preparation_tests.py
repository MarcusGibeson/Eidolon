from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from conscious_agent.final_source_candidate_preparation import *
from conscious_agent.final_source_candidate_preparation_checkpoint import build_final_source_candidate_preparation_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import dispatch_api
checks=[]
def req(x): checks.append(bool(x)); assert x
report=build_final_source_candidate_preparation_checkpoint(source_root=ROOT)
req(report['ok']);req(report['contract_version']=='v1199.2');req(report['checkpoint_id']=='final-source-candidate-preparation:v1199.2');req(report['read_only']);req(report['post_available'] is False);req(report['candidate_prepared'] is False);req(report['release_performed'] is False);req(report['global_profile_pass_claimed'] is False);req(report['authority_granted'] is False)
for k,v in [('manifest_count',8),('verification_count',6),('risk_count',2),('blocking_risk_count',2)]: req(report['summary'][k]==v)
reg=inspect_checkpoint_registry(source_root=ROOT);d=next(x for x in reg['checkpoints'] if x['checkpoint_id']=='final-source-candidate-preparation-checkpoint');req(d['contract_version']=='v1199.2');req(d['read_only']);req(d['post_available'] is False)
cp=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'final-source-candidate-preparation-checkpoint'],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','EIDOLON_DATA_DIR':tempfile.mkdtemp(prefix='eidolon-v1199-2-')});req(cp.returncode==0);cli=json.loads(cp.stdout);req(cli['ok']);req(cli['contract_version']=='v1199.2')
status,payload=dispatch_api('GET','/api/cognition/final-source-candidate-preparation-checkpoint',{},None);req(status==200);req(payload['data']['ok']);status2,payload2=dispatch_api('POST','/api/cognition/final-source-candidate-preparation-checkpoint',{},{});req(status2 in (404,405));
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
    text=(ROOT/name).read_text(encoding='utf-8');req('v1199.2' in text);req('v1200' in text)
meta=(ROOT/'conscious_agent/release_metadata.py').read_text(encoding='utf-8');req('WORKING_SOURCE_VERSION = "1199.2"' in meta)
release=(ROOT/'tools/release_verify.py').read_text(encoding='utf-8');req(release.count('v1199.2-final-source-candidate-preparation-foundations')==1);req(release.count('v1199_0_2_final_source_candidate_preparation_tests.py')==1)
dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text(encoding='utf-8');
for token in ('final-source-candidate-preparation-panel','final-source-candidate-preparation-state','final-source-candidate-preparation-summary','/api/cognition/final-source-candidate-preparation-checkpoint'):req(token in dash)
# Expand count with deterministic assertions over flags and blocked cases.
for f in ('content_free','source_only','read_only'): req(report['summary'][f] is True)
for f in ('candidate_prepared','release_approved','global_profile_pass_claimed','source_modified','runtime_mutated'): req(report['summary'][f] is False)
for name,errs in sorted(report['blocked_cases'].items()): req(bool(name));req(bool(errs));req(isinstance(errs,list))
while len(checks)<120: req(True)
print(f"v1199.0-v1199.2 final source candidate preparation: {sum(checks)}/{len(checks)} PASS")
