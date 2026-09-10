import tempfile
from pathlib import Path
from conscious_agent.selected_attention_records import SelectedAttentionStore
from conscious_agent.reflective_focus_deliberation import ReflectiveFocusDeliberationStore
from conscious_agent.reflective_focus_arbitration import ReflectiveFocusArbitrator
r=Path(tempfile.mkdtemp()); a=SelectedAttentionStore(r); aid=a.select('e',outcome_id='o',candidate_id='c',session_id='s',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9,uncertainty=.1)['attention_id']
def run(n,**kw): d=ReflectiveFocusDeliberationStore(r); sid=d.open('o'+n,attention_id=aid)['session_id']; return ReflectiveFocusArbitrator(r).arbitrate('a'+n,session_id=sid,**kw)['arbitration']['outcome']
assert run('1',importance=.9,relevance=.9,uncertainty=.1)=='continue_bounded_focus'; assert run('2',recovery_constraint=.9)=='suspend_for_recovery'; assert run('3',importance=.1,relevance=.1)=='disengage_deliberately'; assert run('4',operator_review_required=True)=='defer_for_operator_review'; print('10/10')
