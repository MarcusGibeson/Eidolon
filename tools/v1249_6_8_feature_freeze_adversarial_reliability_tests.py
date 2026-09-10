from __future__ import annotations
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from feature_freeze_final_hardening import *
from feature_freeze_final_hardening import _REQUIRED_SURFACES
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();checks=[];ck=lambda v:checks.append(bool(v))
# Invalid, unknown, and authority-expanding requests fail closed.
for change_class,evidence,rationale,surfaces in (
    ('unknown',h('e'),h('r'),[h('s')]),
    ('authority_expansion',h('e'),h('r'),[h('s')]),
    ('new_feature',h('e'),h('r'),[h('s')]),
    ('defect_correction','bad',h('r'),[h('s')]),
    ('defect_correction',h('e'),'bad',[h('s')]),
    ('defect_correction',h('e'),h('r'),['bad']),
):
    row=classify_freeze_change(change_class=change_class,affected_surface_digests=surfaces,evidence_digest=evidence,rationale_digest=rationale)
    ck(not row['separate_work_eligible']);ck(not row['mutation_performed']);ck(not row['release_authorized'])
# Deterministic duplicate convergence.
a=classify_freeze_change(change_class='security_correction',affected_surface_digests=[h('z'),h('a'),h('z')],evidence_digest=h('e'),rationale_digest=h('r'))
b=classify_freeze_change(change_class='security_correction',affected_surface_digests=[h('a'),h('z')],evidence_digest=h('e'),rationale_digest=h('r'))
for v in (a['change_request_digest']==b['change_request_digest'],a['affected_surface_count']==2,a['affected_surface_digests']==sorted(a['affected_surface_digests'])):ck(v)
# Replay and tamper remain bounded.
first=review_freeze_change(change_request=a,decision='accept_for_separate_work',expected_change_request_digest=a['change_request_digest'])
second=review_freeze_change(change_request=a,decision='accept_for_separate_work',expected_change_request_digest=a['change_request_digest'])
tampered=dict(a);tampered['change_class']='authority_expansion'
third=review_freeze_change(change_request=tampered,decision='accept_for_separate_work',expected_change_request_digest=a['change_request_digest'])
for v in (first['review_digest']==second['review_digest'],first['accepted_for_separate_work'],not third['accepted_for_separate_work'],not third['source_change_performed']):ck(v)
# Missing and modified frozen surfaces block a copied tree without exposing contents.
with tempfile.TemporaryDirectory() as td:
    dst=Path(td)/'Eidolon';dst.mkdir()
    for rel in _REQUIRED_SURFACES:
        src=R/rel;target=dst/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if src.is_file():shutil.copy2(src,target)
    (dst/'conscious_agent/release_metadata.py').write_text('WORKING_SOURCE_VERSION = "0.0"\n')
    manifest=build_feature_freeze_manifest(source_root=dst)
    ck(not manifest['ok']);ck(manifest['stable_surface_count']<manifest['surface_count']);ck(not manifest['public_interfaces_frozen']);ck('WORKING_SOURCE_VERSION = \"1249.9\"' not in json.dumps(manifest))
# Runtime and archive debris are detected but only as digests.
with tempfile.TemporaryDirectory() as td:
    dst=Path(td)/'Eidolon';shutil.copytree(R,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    runtime=dst/'data'/'secret.json';runtime.parent.mkdir(exist_ok=True);runtime.write_text('synthetic')
    report=build_final_hardening_report(source_root=dst)
    ck(not report['ok']);ck(report['forbidden_source_entry_count']>=1);ck(report['forbidden_source_entry_digests']);ck('secret.json' not in json.dumps(report))
reg=feature_freeze_registry();manifest=build_feature_freeze_manifest(source_root=R);report=build_final_hardening_report(source_root=R)
for obj in (reg,manifest,report,first,third):
    for key,expected in AUTHORITY_FLAGS.items():ck(obj.get(key) is expected)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
