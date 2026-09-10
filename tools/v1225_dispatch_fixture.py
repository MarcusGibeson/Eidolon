from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for v in (ROOT/"conscious_agent",ROOT/"tools"):
 if str(v) not in sys.path: sys.path.insert(0,str(v))
import operator_governed_work_prioritization_scheduling as priority
from v1224_prioritization_fixture import build_prioritization_fixture
def build_dispatch_fixture(seed="v1225"):
 f=build_prioritization_fixture(seed); rt=f["runtime"]; ranking=priority.build_operator_governed_work_prioritization(runtime_root=rt); assert ranking.get("ok"),ranking
 accepted=priority.record_work_prioritization_review("accept",expected_prioritization_digest=ranking["prioritization_digest"],runtime_root=rt); assert accepted.get("ok"),accepted
 schedule=priority.prepare_operator_governed_work_schedule(expected_prioritization_digest=ranking["prioritization_digest"],runtime_root=rt); assert schedule.get("ok") and schedule.get("slots"),schedule
 review=priority.record_operator_governed_work_schedule_review("accept",expected_schedule_digest=schedule["schedule_digest"],runtime_root=rt); assert review.get("ok"),review
 return {**f,"ranking":ranking,"schedule":schedule,"schedule_review":review}
