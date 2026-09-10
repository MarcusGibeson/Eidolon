from __future__ import annotations
import json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.adversarial_campaign_hardening_long_session_checkpoint import build_adversarial_campaign_hardening_long_session_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[];req=lambda v:checks.append(bool(v))
with tempfile.TemporaryDirectory() as d:
 r=build_adversarial_campaign_hardening_long_session_checkpoint(source_root=ROOT,runtime_root=Path(d)/'runtime');req(r['ok']);req(r['passed']==r['total']);req(r['contract_version']=='v1189.5');req(r['read_only']);req(r['post_available'] is False);req(r['content_free']);req(r['source_modified'] is False);req(r['authority_preserved']);req(len(r['limitations'])==3);req(len(r['structural_digest'])==64)
reg=inspect_checkpoint_registry(source_root=ROOT);row=next((x for x in reg['checkpoints'] if x['checkpoint_id']=='adversarial-campaign-hardening-long-session-checkpoint'),None);req(row is not None);req((row or {}).get('contract_version')=='v1189.5');req(not reg['duplicate_checkpoint_ids'])
text=(ROOT/'tools/release_verify.py').read_text();req(text.count('v1189.5-adversarial-campaign-hardening-long-session')==1);req(text.count('tools/v1189_3_5_adversarial_campaign_hardening_long_session_tests.py')==1)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/name).read_text();req('Current source: v1189.5' in t);req('v1189.3-v1189.5' in t);req('v1200' in t)
print(json.dumps({'suite':'v1189.3-5-adversarial-hardening-long-session','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
