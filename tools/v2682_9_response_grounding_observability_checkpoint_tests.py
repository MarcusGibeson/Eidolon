from pathlib import Path
from conscious_agent.dashboard import render_cognitive_observability_dashboard
from conscious_agent.response_grounding_learning_observability_v2680 import build_response_grounding_learning_observability
import tempfile
checks={}
with tempfile.TemporaryDirectory() as td:
 o=build_response_grounding_learning_observability(td); checks['read_only']=not o['automatic_policy_change_permitted']; checks['no_authority']=not o['authority_granted']
html=render_cognitive_observability_dashboard();checks['dashboard_card']='Response grounding' in html;checks['state_element']='mind-grounding-learning-state' in html;checks['no_hidden_claim']='not hidden chain-of-thought' in html.lower();checks['no_auto_policy']='auto policy change' in html.lower()
print({'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)});raise SystemExit(0 if all(checks.values()) else 1)
