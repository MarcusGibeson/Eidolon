from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.persistent_supervised_developer_hardening_checkpoint import build_persistent_supervised_developer_hardening_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[];req=lambda v:checks.append(bool(v))
with tempfile.TemporaryDirectory() as d:
 r=build_persistent_supervised_developer_hardening_checkpoint(source_root=ROOT,runtime_root=Path(d)/'runtime')
 req(r['ok']);req(r['passed']==r['total']);req(r['contract_version']=='v1189.2');req(r['read_only']);req(r['post_available'] is False);req(r['content_free']);req(r['source_modified'] is False);req(r['runtime_mutated'] is False);req(r['authority_preserved']);req(r['desktop_verification_deferred_until_v1200']);req(len(r['structural_digest'])==64);req(len(r['limitations'])==3)
reg=inspect_checkpoint_registry(source_root=ROOT);row=next((x for x in reg['checkpoints'] if x['checkpoint_id']=='persistent-supervised-developer-hardening-checkpoint'),None);req(row is not None);req((row or {}).get('builder')=='build_persistent_supervised_developer_hardening_checkpoint');req((row or {}).get('contract_version')=='v1189.2');req(not reg['duplicate_checkpoint_ids'])
text=(ROOT/'tools/release_verify.py').read_text();req(text.count('v1189.2-persistent-supervised-developer-hardening-foundations')==1);req(text.count('tools/v1189_0_2_persistent_supervised_developer_hardening_tests.py')==1)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/name).read_text();req('Current source: v1189.2' in t);req('v1189.0-v1189.2' in t);req('v1200' in t)
print(json.dumps({'suite':'v1189.0-2-hardening','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
