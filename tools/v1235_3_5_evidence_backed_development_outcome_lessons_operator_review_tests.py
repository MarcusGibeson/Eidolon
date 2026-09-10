from __future__ import annotations

import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1235-review-api-'))

import evidence_backed_development_outcome_lessons as lessons
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1235_lesson_fixture import build_lesson_fixture,clone_runtime

checks=[]
def check(v): checks.append(bool(v))
fixture=build_lesson_fixture('v1235-review'); base=fixture['runtime']; a=fixture['quality_assessment']; qr=fixture['quality_review']

def prepare(rt):
    return lessons.prepare_evidence_backed_development_lesson(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],quality_review_id=qr['review_id'],expected_quality_review_digest=qr['review_digest'],runtime_root=rt)

rt=clone_runtime(base,'v1235-chat')
text=f"Prepare evidence-backed development lesson for quality assessment {a['assessment_id']} digest {a['assessment_digest']} review {qr['review_id']} digest {qr['review_digest']}."
turn=process_ordinary_chat_development_turn(text,runtime_root=rt)
c=turn.get('evidence_backed_development_lesson') or {}
for v in (turn.get('active') is True,c.get('ok'),c.get('candidate_id','').startswith('development_lesson_'),'grants no cognition' in turn.get('response','')): check(v)
review_text=f"Review evidence-backed development lesson accept for candidate {c['candidate_id']} digest {c['candidate_digest']}."
turn2=process_ordinary_chat_development_turn(review_text,runtime_root=rt)
r=turn2.get('evidence_backed_development_lesson') or {}
for v in (turn2.get('active') is True,r.get('ok'),r.get('disposition')=='accept',r.get('durable_project_scoped_learning_recorded') is True,r.get('lesson_active') is True): check(v)
for k in ('cognition_written','project_modified','tests_executed','commands_executed','provider_contacted'):
    check(r.get(k) is False)

for disp in ('accept','reject','defer','suspend'):
    rt2=clone_runtime(base,f'v1235-review-{disp}')
    c2=prepare(rt2)
    row=lessons.review_evidence_backed_development_lesson(c2['candidate_id'],expected_candidate_digest=c2['candidate_digest'],disposition=disp,runtime_root=rt2)
    check(row.get('ok')); check(row.get('disposition')==disp)
    check(row.get('durable_project_scoped_learning_recorded') is (disp=='accept'))

rt3=clone_runtime(base,'v1235-revise')
c3=prepare(rt3)
revise=process_ordinary_chat_development_turn(
    f"Review evidence-backed development lesson revise for candidate {c3['candidate_id']} digest {c3['candidate_digest']} with lessons retain_verified_approach;preserve_goal_alignment.",runtime_root=rt3)
rv=revise.get('evidence_backed_development_lesson') or {}
check(rv.get('ok')); check(rv.get('disposition')=='revise'); check(rv.get('lesson_codes')==['retain_verified_approach','preserve_goal_alignment']); check(rv.get('lesson_active') is True)

# Inspection/listing surfaces remain content-free.
show=process_ordinary_chat_development_turn(f"Show evidence-backed development lesson {c['candidate_id']}.",runtime_root=rt)
check(show.get('active') is True); check((show.get('evidence_backed_development_lesson') or {}).get('candidate_id')==c['candidate_id'])
listed=process_ordinary_chat_development_turn('Show evidence-backed development lessons.',runtime_root=rt).get('evidence_backed_development_lesson') or {}
reviews=process_ordinary_chat_development_turn('Show evidence-backed development lesson reviews.',runtime_root=rt).get('evidence_backed_development_lesson') or {}
recons=process_ordinary_chat_development_turn('Show evidence-backed development lesson reconsiderations.',runtime_root=rt).get('evidence_backed_development_lesson') or {}
check(listed.get('candidate_count')==1); check(reviews.get('review_count')==1); check(recons.get('reconsideration_count')==0)
check(all('requirements' not in row and 'evidence' not in row for row in listed.get('candidates') or []))

# Replay is exact; conflicting decisions are blocked.
replay=lessons.review_evidence_backed_development_lesson(c['candidate_id'],expected_candidate_digest=c['candidate_digest'],disposition='accept',runtime_root=rt)
check(replay.get('ok')); check(replay.get('operation_status')=='replayed')
conflict=lessons.review_evidence_backed_development_lesson(c['candidate_id'],expected_candidate_digest=c['candidate_digest'],disposition='reject',runtime_root=rt)
check(conflict.get('ok') is False); check(conflict.get('status')=='evidence_backed_lesson_conflicting_review')

# Casual, quoted, and incomplete language remains inert.
for text in (
    'It would be nice to prepare an evidence-backed development lesson.',
    'The guide says "prepare evidence-backed development lesson".',
    'Review evidence-backed development lesson accept.',
    'Could you maybe show evidence-backed development lessons someday?',
):
    check(process_ordinary_chat_development_turn(text,runtime_root=rt).get('evidence_backed_development_lesson') is None)

# CLI public list.
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'evidence-backed-development-lessons','--runtime-root',str(rt)],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
check(proc.returncode==0)
try:
    data=json.loads(proc.stdout.strip().splitlines()[-1]); check(data.get('ok')); check(data.get('candidate_count')==1)
except Exception:
    check(False); check(False)

print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
