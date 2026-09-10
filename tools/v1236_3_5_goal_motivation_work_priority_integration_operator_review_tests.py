from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / 'conscious_agent', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import goal_motivation_work_priority_integration as integration
import operator_governed_work_prioritization_scheduling as priority
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1236_priority_fixture import build_priority_integration_fixture, clone_runtime

checks=[]
def check(v): checks.append(bool(v))

fixture=build_priority_integration_fixture('v1236-review')
base=fixture['runtime']; qid=fixture['queue_item_id']; ranking=fixture['ranking']; lesson=fixture['lesson_review']

def prepare(rt):
    return integration.prepare_goal_motivation_work_priority_integration(
        qid, expected_prioritization_digest=ranking['prioritization_digest'],
        lesson_review_id=lesson['review_id'], expected_lesson_review_digest=lesson['review_digest'],
        runtime_root=rt,
    )

# Exact ordinary-chat preparation and acceptance.
rt=clone_runtime(base,'v1236-chat')
text=(f"Prepare goal motivation work priority integration for item {qid} prioritization "
      f"{ranking['prioritization_digest']} lesson review {lesson['review_id']} digest {lesson['review_digest']}.")
turn=process_ordinary_chat_development_turn(text,runtime_root=rt)
a=turn.get('goal_motivation_work_priority_integration') or {}
for v in (turn.get('active') is True,a.get('ok'),a.get('assessment_id','').startswith('goal_priority_assessment_'),
          'advisory' in turn.get('response','').lower(),'no goal' in turn.get('response','').lower()): check(v)
review_text=(f"Review goal motivation work priority integration accept_alignment for assessment "
             f"{a['assessment_id']} digest {a['assessment_digest']}.")
turn2=process_ordinary_chat_development_turn(review_text,runtime_root=rt)
r=turn2.get('goal_motivation_work_priority_integration') or {}
for v in (turn2.get('active') is True,r.get('ok'),r.get('disposition')=='accept_alignment',
          r.get('alignment_interpretation_accepted') is True,r.get('priority_changed') is False): check(v)
for k in ('goals_modified','motivations_modified','queue_modified','schedule_modified','project_modified','cognition_written','commands_executed','tests_executed','provider_contacted'):
    check(r.get(k) is False)

# Every exact decision remains non-mutating.
for disposition in ('accept_alignment','hold','reject','request_changes'):
    rt2=clone_runtime(base,f'v1236-review-{disposition}')
    a2=prepare(rt2)
    before_priority=priority.load_operator_governed_work_prioritization(runtime_root=rt2)
    row=integration.review_goal_motivation_work_priority_integration(
        a2['assessment_id'],expected_assessment_digest=a2['assessment_digest'],disposition=disposition,runtime_root=rt2)
    after_priority=priority.load_operator_governed_work_prioritization(runtime_root=rt2)
    check(row.get('ok')); check(row.get('disposition')==disposition); check(row.get('priority_changed') is False)
    check(before_priority.get('prioritization_digest')==after_priority.get('prioritization_digest'))
    check(row.get('operator_follow_up_required') is (disposition in {'hold','request_changes'}))

# A priority-change review creates only a proposal record.
rt3=clone_runtime(base,'v1236-propose')
a3=prepare(rt3)
before_priority=priority.load_operator_governed_work_prioritization(runtime_root=rt3)
proposal_text=(f"Review goal motivation work priority integration propose_priority_change for assessment "
               f"{a3['assessment_id']} digest {a3['assessment_digest']} to {a3['recommended_priority_level']}.")
proposal_turn=process_ordinary_chat_development_turn(proposal_text,runtime_root=rt3)
proposal=proposal_turn.get('goal_motivation_work_priority_integration') or {}
after_priority=priority.load_operator_governed_work_prioritization(runtime_root=rt3)
for v in (proposal_turn.get('active') is True,proposal.get('ok'),proposal.get('disposition')=='propose_priority_change',
          proposal.get('priority_change_proposal_recorded') is True,proposal.get('priority_changed') is False,
          before_priority.get('prioritization_digest')==after_priority.get('prioritization_digest')): check(v)

# Proposing the current level or an unsupported level fails closed.
rt4=clone_runtime(base,'v1236-propose-invalid'); a4=prepare(rt4)
current=integration.review_goal_motivation_work_priority_integration(
    a4['assessment_id'],expected_assessment_digest=a4['assessment_digest'],disposition='propose_priority_change',
    proposed_priority_level=a4['current_priority_level'],runtime_root=rt4)
check(current.get('ok') is False); check('proposed_priority_must_change' in current.get('reason',''))
invalid=integration.review_goal_motivation_work_priority_integration(
    a4['assessment_id'],expected_assessment_digest=a4['assessment_digest'],disposition='propose_priority_change',
    proposed_priority_level='urgent',runtime_root=rt4)
check(invalid.get('ok') is False); check(invalid.get('status')=='goal_motivation_work_priority_review_invalid')

# Inspection and listing are content-free.
show=process_ordinary_chat_development_turn(f"Show goal motivation work priority integration {a['assessment_id']}.",runtime_root=rt)
check(show.get('active') is True); check((show.get('goal_motivation_work_priority_integration') or {}).get('assessment_id')==a['assessment_id'])
listed=process_ordinary_chat_development_turn('Show goal motivation work priority integrations.',runtime_root=rt).get('goal_motivation_work_priority_integration') or {}
reviews=process_ordinary_chat_development_turn('Show goal motivation work priority integration reviews.',runtime_root=rt).get('goal_motivation_work_priority_integration') or {}
check(listed.get('assessment_count')==1); check(reviews.get('review_count')==1)
for row in (listed.get('assessments') or [])+(reviews.get('reviews') or []):
    check('summary' not in row); check('goal_rows' not in row); check('motivation_rows' not in row); check('origin_ref' not in row)
check(listed.get('private_content_exposed') is False); check(reviews.get('private_content_exposed') is False)

# Exact replay works; conflicting decisions are blocked.
replay=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='accept_alignment',runtime_root=rt)
check(replay.get('ok')); check(replay.get('operation_status')=='replayed')
conflict=integration.review_goal_motivation_work_priority_integration(a['assessment_id'],expected_assessment_digest=a['assessment_digest'],disposition='reject',runtime_root=rt)
check(conflict.get('ok') is False); check('conflicting_assessment_review' in conflict.get('reason',''))

# Casual, hypothetical, quoted, and incomplete language remains inert.
for casual in (
    'It would be nice if goals influenced priorities.',
    'The guide says "prepare goal motivation work priority integration".',
    'Review goal motivation work priority integration accept_alignment.',
    'Could you maybe show goal motivation work priority integrations later?',
):
    check(process_ordinary_chat_development_turn(casual,runtime_root=rt).get('goal_motivation_work_priority_integration') is None)

# CLI list and review surfaces.
for command, count_key, expected in (
    ('goal-motivation-work-priority-integrations','assessment_count',1),
    ('goal-motivation-work-priority-integration-reviews','review_count',1),
):
    proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),command,'--runtime-root',str(rt)],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    check(proc.returncode==0)
    try:
        data=json.loads(proc.stdout.strip().splitlines()[-1]); check(data.get('ok')); check(data.get(count_key)==expected)
    except Exception:
        check(False); check(False)

# GET-only API surfaces work in a clean process and expose no mutation route.
api_code='''\nimport json\nfrom conscious_agent.api_server import handle_api_get, dispatch_api\nstatus,payload=handle_api_get("/api/cognition/goal-motivation-work-priority-integrations")\nstatus2,payload2=handle_api_get("/api/cognition/goal-motivation-work-priority-integration-reviews")\npost_status,post_payload=dispatch_api("POST","/api/cognition/goal-motivation-work-priority-integrations",body={})\nprint(json.dumps({"status":status,"payload":payload,"status2":status2,"payload2":payload2,"post_status":post_status,"post_payload":post_payload},sort_keys=True))\n'''
proc=subprocess.run([sys.executable,'-c',api_code],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'EIDOLON_DATA_DIR':str(rt),'PYTHONPATH':f"{ROOT}:{ROOT/'conscious_agent'}:{ROOT/'tools'}",'PYTHONDONTWRITEBYTECODE':'1'})
check(proc.returncode==0)
try:
    data=json.loads(proc.stdout.strip().splitlines()[-1])
    check(data.get('status')==200); check((data.get('payload') or {}).get('data',{}).get('assessment_count')==1)
    check(data.get('status2')==200); check((data.get('payload2') or {}).get('data',{}).get('review_count')==1)
    check(data.get('post_status') in {404,405})
except Exception:
    for _ in range(5): check(False)

print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
