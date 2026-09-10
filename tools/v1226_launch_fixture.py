from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for v in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(v) not in sys.path: sys.path.insert(0,str(v))
import supervised_work_dispatch_execution_session_preparation as dispatch
from v1225_dispatch_fixture import build_dispatch_fixture

def build_launch_fixture(seed='v1226'):
    f=build_dispatch_fixture(seed)
    rt=f['runtime']
    slot=f['schedule']['slots'][0]
    session=dispatch.prepare_development_execution_session(
        slot['queue_item_id'],
        expected_schedule_digest=f['schedule']['schedule_digest'],
        runtime_root=rt,
    )
    assert session.get('ok'),session
    review=dispatch.record_prepared_execution_session_review(
        'accept',
        session_id=session['session_id'],
        expected_session_digest=session['session_digest'],
        runtime_root=rt,
    )
    assert review.get('ok'),review
    return {**f,'prepared_session':session,'prepared_session_review':review}
