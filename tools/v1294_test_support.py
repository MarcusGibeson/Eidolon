from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,shutil,subprocess,sys,tempfile

def d(value)->str:return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def tree_digest(root:Path)->str:
 rows=[]
 for p in sorted(root.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'):
   b=p.read_bytes();rows.append((p.relative_to(root).as_posix(),sha256(b).hexdigest()))
 return d(rows)
def write_fixture(root:Path)->None:
 (root/'invoice').mkdir(parents=True);(root/'tests').mkdir()
 (root/'invoice/__init__.py').write_text('')
 (root/'invoice/parse.py').write_text("def money(text):\n    return float(text.strip().replace('$',''))\n")
 (root/'invoice/report.py').write_text("def summary(values):\n    return f'total=${sum(values)}'\n")
 (root/'tests/__init__.py').write_text('')
 (root/'tests/test_focused.py').write_text("import unittest\nfrom invoice.parse import money\nclass T(unittest.TestCase):\n def test_currency(self): self.assertEqual(money('$12.50'),12.5)\n")
 (root/'tests/test_regression.py').write_text("import unittest\nfrom invoice.parse import money\nfrom invoice.report import summary\nclass T(unittest.TestCase):\n def test_separator(self): self.assertEqual(money('$1,200.50'),1200.5)\n def test_summary(self): self.assertEqual(summary([money('$1,200.50'),money('$12.50')]),'Total: $1,213.00')\n")
def run(cwd:Path,args:list[str])->dict:
 cp=subprocess.run([sys.executable,*args],cwd=cwd,text=True,capture_output=True,timeout=20)
 return {'passed':cp.returncode==0,'returncode':cp.returncode,'run_digest':d({'cwd_tag':cwd.name,'args':args,'rc':cp.returncode,'stdout':sha256(cp.stdout.encode()).hexdigest(),'stderr':sha256(cp.stderr.encode()).hexdigest()})}
def build_two_candidates()->dict:
 base=Path(tempfile.mkdtemp(prefix='eidolon-v1294-base-'));write_fixture(base);base_digest=tree_digest(base)
 parent=Path(tempfile.mkdtemp(prefix='eidolon-v1294-candidates-'));a=parent/'candidate-a';b=parent/'candidate-b';shutil.copytree(base,a);shutil.copytree(base,b)
 # A addresses only the obvious parser token and intentionally misses separator + report regression.
 (a/'invoice/parse.py').write_text("def money(text):\n    return float(text.strip().lstrip('$'))\n")
 # B repairs both parsing normalization and report formatting.
 (b/'invoice/parse.py').write_text("from decimal import Decimal\ndef money(text):\n    return float(Decimal(text.strip().replace('$','').replace(',','')))\n")
 (b/'invoice/report.py').write_text("def summary(values):\n    return f'Total: ${sum(values):,.2f}'\n")
 out={'base':base,'parent':parent,'baseline_digest':base_digest,'a':a,'b':b}
 for key in ('a','b'):
  root=out[key];out[key+'_focused']=run(root,['-m','unittest','tests.test_focused']);out[key+'_regression']=run(root,['-m','unittest','discover','-s','tests']);out[key+'_tree']=tree_digest(root)
 return out
