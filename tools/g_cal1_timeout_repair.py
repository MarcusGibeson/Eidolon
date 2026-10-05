"""Offline lock repair certification; never regenerate scientific inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from g_cal1_contract import DATA, ROOT, Package
from g_cal1_pilot import Checks, adversarial, full_pilot, science_checks, tree
from g_cal1_repair_tests import attacks, deny_network, science_replay
from g_cal1_stage import preservation_snapshot
from g_extract1_contract import canonical, digest, file_digest, load
from g_extract1_journal import SCHEMA, write_once

OUT = DATA/'preexecution/lock_timeout_repair'
SOURCES = ('tools/g_cal1_lab.py','tools/g_cal1_timeout_tests.py','tools/g_cal1_timeout_repair.py')


def prepare():
    OUT.mkdir(parents=True,exist_ok=False)
    old = load(DATA/'LAB_MANIFEST.json')
    prior = {p.relative_to(ROOT).as_posix():file_digest(p) for p in sorted(DATA.rglob('*'))
             if p.is_file() and not p.is_relative_to(OUT) and p.name not in ('LAB_MANIFEST.json','STAGE_STATUS.json','README.md')}
    science = {p:h for p,h in old['protected_artifacts'].items() if not p.startswith('tools/g_cal1_')}
    write_once(OUT/'PRIOR_LAB_MANIFEST.json',old)
    write_once(OUT/'PRESERVATION_BEFORE.json',{'science':science,'prior_evidence':prior,
                                              'closed_history':preservation_snapshot()})
    print(json.dumps({'prepared':True,'science':len(science),'prior_evidence':len(prior)}))


def rebind():
    old = load(OUT/'PRIOR_LAB_MANIFEST.json')
    rebound = dict(old,protected_artifacts=dict(old['protected_artifacts']))
    for name in SOURCES:
        rebound['protected_artifacts'][name] = file_digest(ROOT/name)
    # This is mutable package metadata for the new implementation, not science.
    path = DATA/'LAB_MANIFEST.json'
    expected = load(DATA/'preexecution/lifecycle_repair/EXECUTION_FREEZE_CANDIDATE.json')['binding']['manifest_sha256']
    if file_digest(path)!=expected or load(path)!=old:
        raise RuntimeError('manifest is not the preserved predecessor')
    path.write_bytes(canonical(rebound))
    write_once(OUT/'MANIFEST_REBIND_REPORT.json',{
        'prior_sha256':expected,'new_sha256':file_digest(path),'source_hashes':{p:rebound['protected_artifacts'][p] for p in SOURCES},
        'prior_semantic_snapshot_sha256':file_digest(OUT/'PRIOR_LAB_MANIFEST.json'),
        'scientific_pins_unchanged':all(rebound['protected_artifacts'][p]==h for p,h in old['protected_artifacts'].items() if p not in SOURCES),
        'scope':'implementation-only rebind; no science/corpus/gold/request/schedule edits'})
    print(json.dumps({'rebound':True,'pins':len(rebound['protected_artifacts'])}))


def certify():
    from g_cal1_timeout_tests import timeout_tests
    sys.addaudithook(deny_network)
    package, checks = Package(), Checks()
    baseline = load(OUT/'PRESERVATION_BEFORE.json')
    try:
        timeout_tests(package,checks,OUT/'timeout_attacks',actual=True)
        science_checks(package,checks)
        adversarial(package,checks,OUT/'established_regression')
        attacks(package,checks,OUT/'former_four_regression')
        # The disk-drift regression's shadow package is not pilot authority.
        shadow = OUT/'former_four_regression/shadow'
        external = ROOT.parent/'G-CAL1-lock-repair-external-shadow'
        if shadow.exists():
            if not shadow.resolve().is_relative_to(OUT.resolve()) or external.resolve().parent!=ROOT.resolve().parent:
                raise RuntimeError('shadow preservation path outside intended directories')
            if external.exists():
                raise RuntimeError('shadow preservation destination exists')
            shutil.move(str(shadow),str(external))
            write_once(OUT/'SHADOW_PRESERVATION.json',{'path':str(external),'authority':False})
        science_replay(package,checks)
        first, second = OUT/'pilot_one', OUT/'pilot_two'
        full_pilot(package,first,checks)
        full_pilot(package,second,checks)
        one,two = tree(first),tree(second)
        checks.check(one==two,'determinism','two complete 80-observation result trees identical')
        groups = {}
        for name, rows in baseline.items():
            mismatches = [p for p,h in rows.items() if not (ROOT/p).is_file() or file_digest(ROOT/p)!=h]
            checks.check(not mismatches,'preservation',name+' byte-identical')
            groups[name] = {'files':len(rows),'mismatches':mismatches}
        write_once(OUT/'PRESERVATION_REPORT.json',{'byte_identical':True,'groups':groups,'provider_model_calls':0})
        categories = {c:sum(r['category']==c for r in checks.rows) for c in sorted({r['category'] for r in checks.rows})}
        write_once(OUT/'PILOT_REPORT.json',{'schema_version':'g-cal1.lock-repair-pilot.v1','verdict':'PASS',
            'checks':len(checks.rows),'categories':categories,'assertions':checks.rows,
            'two_pilot_trees_identical':True,'authority_evidence_files_each_tree':len(one),'pilot_tree':one,
            'synthetic_observations_each_pilot':80,'provider_model_calls':0,'real_observations':0,
            'freeze_active':False,'execution_authorized':False})
        previous = load(DATA/'preexecution/lifecycle_repair/EXECUTION_FREEZE_CANDIDATE.json')
        candidate = dict(previous,binding=package.binding,protected_artifacts=package.pins,
            pilot_report_sha256=file_digest(OUT/'PILOT_REPORT.json'),
            preservation_report_sha256=file_digest(OUT/'PRESERVATION_REPORT.json'),
            supersedes_blocked_lock_timeout_candidate_sha256=file_digest(DATA/'preexecution/lifecycle_repair/EXECUTION_FREEZE_CANDIDATE.json'),
            failed_lock_timeout_review_sha256=file_digest(DATA/'audit/lifecycle_repair/LOCK_TIMEOUT_REVIEW_COMPLETION.json'),
            lock_boundary_incident_schema='g-cal1.lock-boundary-incident.v1',
            lock_boundary_incident_storage='exclusive pending-file create, flush/fsync, atomic no-replace hard-link publication; immutable sealed INVALID records, independent of lifecycle lock',
            timeout_targeted_report_sha256=file_digest(OUT/'timeout_attacks/ACTUAL_TIMEOUT_REPORT.json'),
            audit_pending=True)
        write_once(OUT/'EXECUTION_FREEZE_CANDIDATE.json',candidate)
        write_once(OUT/'EVIDENCE_MANIFEST.json',{'files':tree(OUT),'self_excluded':True})
        print(json.dumps({'verdict':'PASS','checks':len(checks.rows),'categories':categories,
                          'files_each':len(one),'candidate_sha256':file_digest(OUT/'EXECUTION_FREEZE_CANDIDATE.json')}))
    except BaseException as exc:
        write_once(OUT/'PRODUCER_STOP.json',{'exception_type':type(exc).__name__,'detail':str(exc),
            'checks_completed':len(checks.rows),'assertions':checks.rows,'provider_model_calls':0,'candidate_created':False})
        raise


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=('prepare','rebind','certify'))
    args = parser.parse_args()
    {'prepare':prepare,'rebind':rebind,'certify':certify}[args.mode]()
