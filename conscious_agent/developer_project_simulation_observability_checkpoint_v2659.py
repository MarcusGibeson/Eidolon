from __future__ import annotations
"""v2659 project rehearsal observability checkpoint."""
from pathlib import Path
from developer_project_simulation_observability_v2656 import build_project_simulation_observability

def build_checkpoint(source_root=None)->dict:
 root=Path(source_root or Path(__file__).resolve().parents[1]);api=(root/'conscious_agent'/'api_server.py').read_text(encoding='utf-8');dash=(root/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8');obs=build_project_simulation_observability(root/'data'/'development')
 checks={'read_model':obs.get('ok') is True,'api_route':'["cognition", "observability", "project-simulation"]' in api,'mind_card':'mind-project-simulation-state' in dash,'synthetic_label':'Synthetic lifecycle rehearsal only' in dash,'real_verification_label':'real verification still required' in dash,'no_auto_start':not obs.get('automatic_project_start_permitted'),'no_authority':not obs.get('authority_granted')}
 return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
