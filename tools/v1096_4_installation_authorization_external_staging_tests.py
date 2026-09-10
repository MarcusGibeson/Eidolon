from __future__ import annotations
import argparse, json, shutil, tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from release_metadata import WORKING_SOURCE_VERSION
from release_candidate_identity import freeze_release_candidate, read_json
from release_archive_coherence import build_candidate_archive
from release_handoff_inspection import inspect_selected_candidate_archive
from release_installation_preview import create_installation_impact_preview
from release_installation_plan import create_installation_plan
from release_installation_staging import preview_installation_staging_authorization, stage_authorized_installation, installation_staging_status, staging_directory, STAGING_CONFIRMATION

def c(n,o,d=''): return {'name':n,'ok':bool(o),'detail':d}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); ap.parse_args(); rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1096-4-') as td:
  b=Path(td); source=b/'source'; target=b/'target'; shutil.copytree(ROOT,source); shutil.copytree(ROOT,target)
  original=(target/'README.md').read_bytes(); (target/'README.md').write_text('target drift for replace'); (target/'tools'/'obsolete_install_fixture.py').write_text('old=True\n')
  target_snapshot={p.relative_to(target).as_posix():p.read_bytes() for p in target.rglob('*') if p.is_file()}
  runtime=b/'runtime'; out=b/'out'; out.mkdir(); cand=runtime/'candidate'
  freeze_release_candidate(source,runtime_root=cand,expected_version=WORKING_SOURCE_VERSION); pkg=build_candidate_archive(source,runtime_root=cand,destination_dir=out); archive=out/pkg['package_filename']
  hand=runtime/'handoff'; rows.append(c('handoff',inspect_selected_candidate_archive(archive,runtime_root=hand).get('ok')))
  registry=b/'projects.json'; registry.write_text(json.dumps({'projects':[{'id':'target','name':'Target','source_root':str(target),'source_identity_markers':['conscious_agent/release_metadata.py']}]}))
  rows.append(c('preview',create_installation_impact_preview('target',runtime_root=hand,project_registry_path=registry).get('ok')))
  rows.append(c('plan',create_installation_plan(runtime_root=hand).get('ok')))
  auth=preview_installation_staging_authorization(runtime_root=hand); token=auth.get('authorization_token','')
  rows.append(c('authorization-bound',auth.get('ok') and token and auth.get('literal_confirmation')==STAGING_CONFIRMATION))
  bad=stage_authorized_installation(token,confirm='true',runtime_root=hand); rows.append(c('literal-confirmation',not bad.get('ok')))
  stage=stage_authorized_installation(token,confirm=STAGING_CONFIRMATION,runtime_root=hand)
  rows.append(c('externally-staged',stage.get('ok') and stage.get('status')=='externally_staged'))
  rows.append(c('candidate-mirror-exact',stage.get('candidate_mirror_verified') and stage.get('staged_manifest_sha256')==stage.get('source_manifest_sha256')))
  rows.append(c('backup-rollback-planned',stage.get('backup_entry_count',0)>=2 and stage.get('rollback_entry_count',0)>=2))
  rows.append(c('path-private',str(target) not in json.dumps(stage) and str(archive) not in json.dumps(stage)))
  rows.append(c('target-unmodified',all((target/k).read_bytes()==v for k,v in target_snapshot.items()) and len([p for p in target.rglob('*') if p.is_file()])==len(target_snapshot)))
  reused=stage_authorized_installation(token,confirm=STAGING_CONFIRMATION,runtime_root=hand); rows.append(c('token-reuse-rejected',not reused.get('ok')))
  rows.append(c('status-coherent',installation_staging_status(runtime_root=hand).get('ok')))
  # Stage tamper.
  ptr=read_json(staging_directory(hand)/'active_stage.json'); rec=read_json(staging_directory(hand)/'records'/f"{ptr['stage_id']}.json"); staged=Path(rec['candidate_stage_root_path']); (staged/'README.md').write_text('tamper')
  rows.append(c('staged-tamper-detected',not installation_staging_status(runtime_root=hand).get('ok')))
  # Cross-plan/stale token: create token, drift target, old token must fail and active stage pointer remains.
  create_installation_impact_preview('target',runtime_root=hand,project_registry_path=registry); create_installation_plan(runtime_root=hand); auth2=preview_installation_staging_authorization(runtime_root=hand); token2=auth2['authorization_token']
  (target/'README.md').write_text('new drift')
  fail=stage_authorized_installation(token2,confirm=STAGING_CONFIRMATION,runtime_root=hand); rows.append(c('stale-plan-token-rejected',not fail.get('ok')))
  ptr2=read_json(staging_directory(hand)/'active_stage.json'); rows.append(c('failed-stage-preserves-active',ptr2.get('stage_id')==ptr.get('stage_id')))
  rows.append(c('no-target-installation',not stage.get('target_modified') and not stage.get('installation_changed') and not stage.get('installation_apply_available')))
  rows.append(c('authority-separate',not stage.get('installed') and not stage.get('approved') and not stage.get('promoted') and not stage.get('certified')))
 report={'suite':'v1096.4-installation-authorization-external-staging-foundation','passed':sum(r['ok'] for r in rows),'failed':sum(not r['ok'] for r in rows),'checks':rows}; report['ok']=report['failed']==0; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
