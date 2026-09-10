import tempfile
from pathlib import Path
from conscious_agent.selected_attention_records import SelectedAttentionStore
from conscious_agent.reflective_focus_deliberation import ReflectiveFocusDeliberationStore
r=Path(tempfile.mkdtemp()); a=SelectedAttentionStore(r); x=a.select('e',outcome_id='o',candidate_id='c',session_id='s',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9,uncertainty=.1); aid=x['attention_id']; d=ReflectiveFocusDeliberationStore(r); y=d.open('f',attention_id=aid,focus_budget=2); assert y['status']=='reflective_focus_session_opened'; z=d.open('f',attention_id=aid); assert z['idempotent']; q=d.record_outcome('g',session_id=y['session_id'],outcome='continue_bounded_focus',reason_code='test'); assert q['outcome']=='continue_bounded_focus'; print('10/10')
