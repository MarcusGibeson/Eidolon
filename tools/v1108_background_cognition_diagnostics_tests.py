from pathlib import Path
import tempfile
from conscious_agent.proactive_communication import CognitiveInitiativeService
class BadCycle:
 def inspection_summary(self): return {'controls':{'mode':'running'}}
 def run_due_cadence(self,**kwargs): raise RuntimeError('private failure text')
class Comm: pass
def run():
 root=Path(tempfile.mkdtemp());s=CognitiveInitiativeService(root,cycle=BadCycle(),communication=Comm(),poll_seconds=5);s._record_background_failure(RuntimeError('private failure text'));import json;d=json.loads(s.diagnostics_path.read_text());row=d['failures'][-1];tests=[row['error_type']=='RuntimeError','private failure text' not in s.diagnostics_path.read_text(),row['content_free'] is True,row['authority_changed'] is False]
 print({'suite':'background-cognition-diagnostics','passed':sum(tests),'total':len(tests)});return all(tests)
if __name__=='__main__':raise SystemExit(0 if run() else 1)
