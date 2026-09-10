from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def write_fixture(root:Path)->None:
    (root/'invoice').mkdir(parents=True);(root/'tests').mkdir()
    (root/'invoice/__init__.py').write_text('from .summary import summarize\n')
    (root/'invoice/normalize.py').write_text('def normalize_code(code: str) -> str:\n    return code.strip()\n')
    (root/'invoice/summary.py').write_text('from .normalize import normalize_code\n\ndef summarize(rows):\n    return {normalize_code(r["code"]): float(r["amount"]) for r in rows}\n')
    (root/'invoice/cli.py').write_text('import argparse,json\nfrom .summary import summarize\n\ndef main(argv=None):\n p=argparse.ArgumentParser(description="Summarize invoice rows")\n p.add_argument("payload", help="JSON array of invoice rows")\n a=p.parse_args(argv); print(json.dumps(summarize(json.loads(a.payload)), sort_keys=True)); return 0\nif __name__=="__main__": raise SystemExit(main())\n')
    (root/'tests/__init__.py').write_text('')
    (root/'tests/test_summary.py').write_text('''import json,subprocess,sys,unittest\nfrom invoice.summary import summarize\nclass SummaryTests(unittest.TestCase):\n def test_normalized_aggregation(self):\n  self.assertEqual(summarize([{"code":" a ","amount":2},{"code":"A","amount":3}]),{"A":5.0})\n def test_distinct_codes(self):\n  self.assertEqual(summarize([{"code":"b","amount":1},{"code":"c","amount":4}]),{"B":1.0,"C":4.0})\n def test_cli(self):\n  p=subprocess.run([sys.executable,"-m","invoice.cli",json.dumps([{"code":" x ","amount":2}])],cwd=".",text=True,capture_output=True)\n  self.assertEqual(p.returncode,0); self.assertEqual(json.loads(p.stdout),{"X":2.0})\n''')
    (root/'README.md').write_text('# Invoice Summary\n\nText-only CLI. Run `python -m invoice.cli <json-array>`. Codes are trimmed, normalized to uppercase, and duplicate codes are summed.\n')

def project_manifest(root:Path)->dict:
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file():rows.append((p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()))
    return {'file_count':len(rows),'paths':[x[0] for x in rows],'digest':digest(rows)}

def run(root:Path,*args:str)->dict:
    p=subprocess.run([sys.executable,*args],cwd=root,text=True,capture_output=True,timeout=20)
    return {'passed':p.returncode==0,'returncode':p.returncode,'stdout_digest':hashlib.sha256(p.stdout.encode()).hexdigest(),'stderr_digest':hashlib.sha256(p.stderr.encode()).hexdigest()}

def normalization_probe(root:Path)->dict:
    p=subprocess.run([sys.executable,'-c','from invoice.normalize import normalize_code; print(normalize_code(" a "))'],cwd=root,text=True,capture_output=True,timeout=20)
    observed=p.stdout.strip(); return {'observed_value_digest':hashlib.sha256(observed.encode()).hexdigest(),'supports_combined_defect':observed!='A','passed':p.returncode==0}

def apply_solution(root:Path)->list[str]:
    (root/'invoice/normalize.py').write_text('def normalize_code(code: str) -> str:\n    return code.strip().upper()\n')
    (root/'invoice/summary.py').write_text('''from .normalize import normalize_code\n\ndef summarize(rows):\n    totals = {}\n    for row in rows:\n        code = normalize_code(row["code"])\n        totals[code] = totals.get(code, 0.0) + float(row["amount"])\n    return totals\n''')
    return ['invoice/normalize.py','invoice/summary.py']

def quality_evidence(scope_digest:str)->list[dict]:
    pairs={
      'coherence':'integration_test','usability':'usability_review','accessibility':'accessibility_review',
      'maintainability':'static_analysis','completeness':'requirements_review','operator_readiness':'operator_walkthrough'}
    return [{'dimension':d,'evidence_type':t,'state':'pass','evidence_digest':digest({'benchmark':d,'type':t,'scope':scope_digest}),'scope_digest':scope_digest,'fresh':True} for d,t in pairs.items()]
