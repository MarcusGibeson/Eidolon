from __future__ import annotations
import argparse, json, shutil, tempfile, zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'conscious_agent'))

from release_metadata import WORKING_SOURCE_VERSION
from release_handoff_inspection import inspect_selected_candidate_archive
from release_installation_preview import create_installation_impact_preview, installation_impact_preview_status
from release_candidate_identity import freeze_release_candidate
from release_archive_coherence import build_candidate_archive


def check(name, ok, detail=''):
    return {'name': name, 'ok': bool(ok), 'detail': detail}


def make_candidate(source: Path, runtime: Path, out: Path) -> Path:
    frozen = freeze_release_candidate(source, runtime_root=runtime, expected_version=WORKING_SOURCE_VERSION)
    if not frozen.get('ok'):
        raise RuntimeError(frozen)
    pkg = build_candidate_archive(source, runtime_root=runtime, destination_dir=out)
    name = pkg.get('package_filename') or ''
    path = out / name
    if not path.is_file():
        hits=list(out.glob('*.zip')); path=hits[0]
    return path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json', action='store_true'); args=ap.parse_args()
    rows=[]
    with tempfile.TemporaryDirectory(prefix='eidolon-v1096-2-') as td:
        base=Path(td); source=base/'source'; shutil.copytree(ROOT, source)
        runtime=base/'runtime'; out=base/'out'; out.mkdir()
        target=base/'target'; shutil.copytree(source, target)
        archive=make_candidate(source, runtime/'candidate', out)
        handoff_runtime=runtime/'handoff'
        inspected=inspect_selected_candidate_archive(archive, runtime_root=handoff_runtime)
        rows.append(check('exact-handoff-coherent', inspected.get('ok'), str(inspected.get('status'))))
        registry=base/'projects.json'
        registry.write_text(json.dumps({'projects':[{'id':'eidolon-target','name':'Target','source_root':str(target),'source_identity_markers':['conscious_agent/release_metadata.py','README_NEXT_STEPS.md']}]}), encoding='utf-8')
        preview=create_installation_impact_preview('eidolon-target', runtime_root=handoff_runtime, project_registry_path=registry)
        rows.append(check('explicit-target-preview', preview.get('ok') and preview.get('explicit_target_selected')))
        rows.append(check('read-only-no-apply', preview.get('read_only_preview') and not preview.get('installation_apply_available') and not preview.get('installation_changed')))
        rows.append(check('path-private', str(target) not in json.dumps(preview) and str(archive) not in json.dumps(preview)))
        rows.append(check('protected-runtime-data', preview.get('effect_counts',{}).get('protected',0) >= 3))
        rows.append(check('no-directory-scan', preview.get('directory_scan_performed') is False))
        missing=create_installation_impact_preview('missing', runtime_root=handoff_runtime, project_registry_path=registry)
        rows.append(check('exact-project-id-required', not missing.get('ok') and missing.get('contradiction_count',0)>0))
        before=(target/'README.md').read_bytes(); status=installation_impact_preview_status(runtime_root=handoff_runtime)
        rows.append(check('status-coherent', status.get('ok') and status.get('target_revalidated')))
        rows.append(check('target-unmodified', (target/'README.md').read_bytes()==before))
        (target/'README.md').write_text('drift', encoding='utf-8')
        stale=installation_impact_preview_status(runtime_root=handoff_runtime)
        rows.append(check('target-drift-detected', not stale.get('ok') and stale.get('status')=='stale_preview'))
        (target/'README.md').write_bytes(before)
        # Changed archive is detected through active handoff revalidation.
        with archive.open('ab') as h: h.write(b'changed')
        changed=installation_impact_preview_status(runtime_root=handoff_runtime)
        rows.append(check('changed-archive-detected', not changed.get('ok')))
        rows.append(check('ordinary-authority-unchanged', not preview.get('installed') and not preview.get('approved') and not preview.get('promoted') and not preview.get('certified')))
        rows.append(check('records-external-content-free', preview.get('records_external') and preview.get('content_free')))
    passed=sum(1 for r in rows if r['ok']); report={'suite':'v1096.2-operator-controlled-installation-preview-foundation','passed':passed,'failed':len(rows)-passed,'checks':rows,'ok':passed==len(rows)}
    print(json.dumps(report, indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
