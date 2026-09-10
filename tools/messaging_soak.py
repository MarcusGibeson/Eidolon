from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))
from messaging_soak import run_messaging_soak

def main() -> int:
    p=argparse.ArgumentParser(description='Run a bounded content-free Eidolon messaging soak.')
    p.add_argument('--iterations',type=int,default=60)
    p.add_argument('--json',action='store_true')
    a=p.parse_args(); report=run_messaging_soak(iterations=a.iterations)
    print(json.dumps(report,indent=2) if a.json else f"Messaging soak: {report['status']} ({report['accepted_operations']}/{report['iterations']})")
    return 0 if report['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
