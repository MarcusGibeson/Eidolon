from pathlib import Path
import subprocess,sys,tempfile,os
from conscious_agent.api_server import handle_api_get
root=Path(__file__).resolve().parents[1]
code,payload=handle_api_get('/api/cognition/reflective-communication-intake-checkpoint',{})
cli=subprocess.run([sys.executable,str(root/'eidolon.py'),'reflective-communication-intake-checkpoint'],cwd=root,env={**os.environ,'EIDOLON_DATA_DIR':tempfile.mkdtemp()},capture_output=True,text=True)
dash=(root/'conscious_agent/dashboard_first_use.py').read_text()
checks=[code==200,payload['ok'],payload['data']['contract_version']=='v1129.2',cli.returncode==0,'"contract_version": "v1129.2"' in cli.stdout,'reflective-communication-intake-checkpoint-panel' in dash,"/api/cognition/reflective-communication-intake-checkpoint" in dash]
print(f"v1129.2 reflective communication surfaces tests: {sum(checks)}/{len(checks)} passed");raise SystemExit(0 if all(checks) else 1)
