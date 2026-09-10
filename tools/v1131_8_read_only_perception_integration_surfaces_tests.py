from pathlib import Path
import os, subprocess, sys, tempfile
from conscious_agent.api_server import handle_api_get
root=Path(__file__).resolve().parents[1]; code,payload=handle_api_get('/api/cognition/read-only-perception-integration-checkpoint',{}); cli=subprocess.run([sys.executable,str(root/'eidolon.py'),'read-only-perception-integration-checkpoint'],cwd=root,env={**os.environ,'EIDOLON_DATA_DIR':tempfile.mkdtemp()},capture_output=True,text=True); dash=(root/'conscious_agent/dashboard_first_use.py').read_text(); checks=[code==200,payload['ok'],payload['data']['contract_version']=='v1131.8',cli.returncode==0,'"contract_version": "v1131.8"' in cli.stdout,'read-only-perception-integration-checkpoint-panel' in dash,'/api/cognition/read-only-perception-integration-checkpoint' in dash]
print(f"v1131.8 read-only perception integration surfaces tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
