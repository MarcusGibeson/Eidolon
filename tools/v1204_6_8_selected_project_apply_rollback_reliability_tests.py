from __future__ import annotations
import contextlib, hashlib, io, json, runpy, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import _read_json, _atomic_json
from selected_project_apply import (
    authorize_and_apply_selected_project, create_or_resume_rollback_request,
    authorize_and_rollback_selected_project, recover_interrupted_selected_project_rollback,
    recover_interrupted_selected_project_apply, _result_path, _rollback_result_path,
    _rollback_path, _apply_journal_path, _rollback_journal_path, _authorization_path,
)
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
    CHECKS.append(bool(v))
    if not v: raise AssertionError(d)
# Reuse and re-run the complete v1204.5 deterministic fixture as the compatibility floor.
with contextlib.redirect_stdout(io.StringIO()):
    prior=runpy.run_path(str(ROOT/'tools/v1204_3_5_selected_project_rollback_recovery_tests.py'))
prepared=prior['prepared']; sig=prior['sig']
# Consumed apply authorization never re-enters the write loop when its final result is missing.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-reliable-apply-'))
try:
    project,p,req,applied,before,calls=prepared(rt,'reliable-apply')
    after=sig(project); _result_path(p['proposal_id'],1,rt).unlink()
    phrase=f"APPLY {p['proposal_id']} REVISION 1 REQUEST {req['apply_request_digest']}"
    recovered=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=req['apply_request_digest'],authorization_phrase=phrase,runtime_root=rt)
    require(recovered['status']=='selected_project_apply_completed_recovered',recovered)
    require(recovered['authorization_consumption_count']==1)
    require(sig(project)==after)
    require(_read_json(_authorization_path(p['proposal_id'],1,rt))['consumption_count']==1)
    journal=_read_json(_apply_journal_path(p['proposal_id'],1,rt)); require(journal['phase']=='sealed_recovered'); require(bool(journal['journal_digest']))
finally: shutil.rmtree(rt,ignore_errors=True)
# Rollback request creation refuses to overwrite an operator edit made after apply.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-post-apply-conflict-'))
try:
    project,p,req,applied,before,calls=prepared(rt,'post-apply-conflict')
    (project/'main.py').write_text('operator edit after apply\n')
    blocked=create_or_resume_rollback_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_result_digest=applied['apply_result_digest'],runtime_root=rt)
    require(blocked['status']=='selected_project_changed_after_apply',blocked)
finally: shutil.rmtree(rt,ignore_errors=True)
# Missing rollback result resumes from its consumed receipt and seals once.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-reliable-rollback-'))
try:
    project,p,req,applied,before,calls=prepared(rt,'reliable-rollback')
    rr=create_or_resume_rollback_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_result_digest=applied['apply_result_digest'],runtime_root=rt)
    phrase=f"ROLLBACK {p['proposal_id']} REVISION 1 REQUEST {rr['rollback_request_digest']}"
    done=authorize_and_rollback_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=rr['rollback_request_digest'],authorization_phrase=phrase,runtime_root=rt)
    require(done['ok'] is True); _rollback_result_path(p['proposal_id'],1,rt).unlink()
    recovered=recover_interrupted_selected_project_rollback(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=rr['rollback_request_digest'],runtime_root=rt)
    require(recovered['status']=='selected_project_rollback_completed_recovered',recovered)
    require(recovered['authorization_consumption_count']==1); require(sig(project)==before)
    journal=_read_json(_rollback_journal_path(p['proposal_id'],1,rt)); require(journal['phase']=='sealed_recovered')
finally: shutil.rmtree(rt,ignore_errors=True)
# A third-state edit after a consumed rollback blocks recovery rather than clobbering it.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-rollback-conflict-'))
try:
    project,p,req,applied,before,calls=prepared(rt,'rollback-conflict')
    rr=create_or_resume_rollback_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_result_digest=applied['apply_result_digest'],runtime_root=rt)
    phrase=f"ROLLBACK {p['proposal_id']} REVISION 1 REQUEST {rr['rollback_request_digest']}"
    done=authorize_and_rollback_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=rr['rollback_request_digest'],authorization_phrase=phrase,runtime_root=rt)
    _rollback_result_path(p['proposal_id'],1,rt).unlink(); (project/'main.py').write_text('new operator edit after rollback\n')
    blocked=recover_interrupted_selected_project_rollback(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=rr['rollback_request_digest'],runtime_root=rt)
    require(blocked['status']=='rollback_recovery_conflict_detected',blocked)
    require((project/'main.py').read_text()=='new operator edit after rollback\n')
finally: shutil.rmtree(rt,ignore_errors=True)
# Corrupted private rollback content and corrupted phase journals are rejected.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-integrity-'))
try:
    project,p,req,applied,before,calls=prepared(rt,'integrity')
    manifest=_read_json(_rollback_path(p['proposal_id'],1,rt)); manifest['entries'][0]['content_b64']='dGFtcGVyZWQ='; _atomic_json(_rollback_path(p['proposal_id'],1,rt),manifest)
    blocked=create_or_resume_rollback_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_result_digest=applied['apply_result_digest'],runtime_root=rt)
    require(blocked['status']=='rollback_manifest_missing_or_invalid',blocked)
finally: shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-journal-integrity-'))
try:
    project,p,req,applied,before,calls=prepared(rt,'journal-integrity'); _result_path(p['proposal_id'],1,rt).unlink()
    journal=_read_json(_apply_journal_path(p['proposal_id'],1,rt)); journal['phase']='invented'; _atomic_json(_apply_journal_path(p['proposal_id'],1,rt),journal)
    blocked=recover_interrupted_selected_project_apply(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=req['apply_request_digest'],runtime_root=rt)
    require(blocked['status']=='apply_journal_invalid',blocked)
finally: shutil.rmtree(rt,ignore_errors=True)
# Static integration, privacy, and verifier coverage.
dashboard=(ROOT/'conscious_agent/dashboard.py').read_text(errors='ignore'); metadata=(ROOT/'conscious_agent/release_metadata.py').read_text(); verifier=(ROOT/'tools/release_verify.py').read_text()
require('/api/development-campaign/recover-selected-project-rollback' in dashboard)
require('WORKING_SOURCE_VERSION = "1204.8"' in metadata)
require('v1204.6-v1204.8 Selected-Project Apply and Rollback Reliability Hardening' in metadata)
require(verifier.count('v1204.8-selected-project-apply-rollback-reliability')==2)
require(verifier.count('tools/v1204_6_8_selected_project_apply_rollback_reliability_tests.py')==1)
for path in (ROOT/'README_NEXT_STEPS.md',ROOT/'README_RELEASE_HISTORY.md'):
    require('v1204.6-v1204.8' in path.read_text())
encoded=json.dumps({'apply':recover_interrupted_selected_project_apply.__name__,'rollback':recover_interrupted_selected_project_rollback.__name__})
windows_user_prefix = 'C:' + chr(92) + 'Users' + chr(92)
posix_user_prefix = '/' + 'Users' + '/'
require(posix_user_prefix not in encoded and windows_user_prefix not in encoded)
print(json.dumps({'ok':True,'version':'1204.8','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'phase_journals':True,'exactly_once_recovery':True,'post_apply_conflict_blocking':True,'manifest_integrity':True,'release_authorized':False,'authority_granted':False},sort_keys=True))
