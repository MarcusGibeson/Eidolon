from __future__ import annotations
"""v1306 dependency-aware goal decomposition."""
from typing import Any,Mapping,Sequence
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1306.8'
def decompose_goal(goal:Mapping[str,Any],task_specs:Sequence[Mapping[str,Any]]):
 tasks=[];seen=set()
 for i,s in enumerate(list(task_specs)[:64]):
  code=str(s.get('code') or f't{i+1}');deps=tuple(str(x) for x in s.get('depends_on') or ());
  if code in seen:raise ValueError('duplicate_task_code')
  seen.add(code);tasks.append({'code':code,'depends_on':deps,'deliverable_digest':digest(str(s.get('deliverable') or code)),'test_digest':digest(str(s.get('test') or code)),'rollback_digest':digest(str(s.get('rollback') or code)),'completion_digest':digest(str(s.get('completion') or code))})
 codes={x['code'] for x in tasks}
 if any(d not in codes for x in tasks for d in x['depends_on']):raise ValueError('unknown_dependency')
 # cycle check
 def visit(c,stack,done):
  if c in stack:raise ValueError('dependency_cycle')
  if c in done:return
  stack.add(c);[visit(d,stack,done) for d in next(x for x in tasks if x['code']==c)['depends_on']];stack.remove(c);done.add(c)
 done=set();[visit(c,set(),done) for c in codes]
 row={'contract_version':CONTRACT_VERSION,'goal_id':goal.get('goal_id'),'goal_digest':goal.get('goal_digest'),'tasks':tasks,'task_count':len(tasks),'acyclic':True,'decomposition_grants_authority':False,**DENIED_AUTHORITY};row['decomposition_digest']=digest(row);return row
__all__=['CONTRACT_VERSION','decompose_goal']
