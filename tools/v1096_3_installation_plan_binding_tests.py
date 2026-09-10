from __future__ import annotations
import argparse, json, shutil, tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from release_metadata import WORKING_SOURCE_VERSION
from release_candidate_identity import freeze_release_candidate, read_json, atomic_json
from release_archive_coherence import build_candidate_archive
from release_handoff_inspection import inspect_selected_candidate_archive, handoff_directory
from release_installation_preview import create_installation_impact_preview, preview_directory
from release_installation_plan import create_installation_plan, installation_plan_status, plan_directory, protected_policy_sha256

def c(n,o,d=''): return {'name':n,'ok':bool(o),'detail':d}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); ap.parse_args(); rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1096-3-') as td:
  b=Path(td); source=b/'source'; target=b/'target'; shutil.copytree(ROOT,source); shutil.copytree(ROOT,target)
  runtime=b/'runtime'; out=b/'out'; out.mkdir(); cand=runtime/'candidate'
  frozen=freeze_release_candidate(source,runtime_root=cand,expected_version=WORKING_SOURCE_VERSION); pkg=build_candidate_archive(source,runtime_root=cand,destination_dir=out); archive=out/pkg['package_filename']
  hand=runtime/'handoff'; rows.append(c('handoff',inspect_selected_candidate_archive(archive,runtime_root=hand).get('ok')))
  registry=b/'projects.json'; registry.write_text(json.dumps({'projects':[{'id':'target','name':'Target','source_root':str(target),'source_identity_markers':['conscious_agent/release_metadata.py']}]}))
  rows.append(c('preview',create_installation_impact_preview('target',runtime_root=hand,project_registry_path=registry).get('ok')))
  plan=create_installation_plan(runtime_root=hand); rows.append(c('plan-bound',plan.get('ok') and plan.get('status')=='bound_plan'))
  rows.append(c('immutable-identities',all(plan.get(k) for k in ['plan_id','plan_binding_sha256','preview_binding_sha256','candidate_id','archive_sha256','target_inventory_sha256','effects_sha256','protected_policy_sha256'])))
  rows.append(c('no-token-stage-apply',not plan.get('confirmation_token_available') and not plan.get('staging_available') and not plan.get('installation_apply_available')))
  rows.append(c('path-private',str(target) not in json.dumps(plan) and str(archive) not in json.dumps(plan)))
  rows.append(c('status-coherent',installation_plan_status(runtime_root=hand).get('ok')))
  rows.append(c('policy-bound',plan.get('protected_policy_sha256')==protected_policy_sha256()))
  before=(target/'README.md').read_bytes(); (target/'README.md').write_text('drift')
  rows.append(c('target-drift',not installation_plan_status(runtime_root=hand).get('ok'))); (target/'README.md').write_bytes(before)
  # Tamper private preview effect digest and verify stale.
  pp=read_json(preview_directory(hand)/'active_preview.json'); pr=preview_directory(hand)/'records'/f"{pp['preview_id']}.json"; pv=read_json(pr); pv['effects_sha256']='0'*64; atomic_json(pr,pv)
  rows.append(c('preview-drift',not installation_plan_status(runtime_root=hand).get('ok')))
  # Restore preview and tamper plan binding.
  create_installation_impact_preview('target',runtime_root=hand,project_registry_path=registry); plan=create_installation_plan(runtime_root=hand)
  ptr=read_json(plan_directory(hand)/'active_plan.json'); rp=plan_directory(hand)/'records'/f"{ptr['plan_id']}.json"; rec=read_json(rp); rec['archive_sha256']='f'*64; atomic_json(rp,rec)
  rows.append(c('plan-tamper',not installation_plan_status(runtime_root=hand).get('ok')))
  rows.append(c('target-unmodified-by-plan',(target/'README.md').read_bytes()==before))
  rows.append(c('authority-separate',not plan.get('installed') and not plan.get('approved') and not plan.get('promoted') and not plan.get('certified')))
 report={'suite':'v1096.3-installation-plan-binding-drift-protection','passed':sum(r['ok'] for r in rows),'failed':sum(not r['ok'] for r in rows),'checks':rows}; report['ok']=report['failed']==0; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
