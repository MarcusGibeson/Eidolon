from __future__ import annotations
import hashlib, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS, active_grant, precondition

MODULE='''from __future__ import annotations\n\n\ndef add(a: int, b: int) -> int:\n    return a + b\n\n\nasync def scale(value: int) -> int:\n    return value * 2\n'''
INIT='''from .calc import add, scale\n\n__all__ = ["add", "scale"]\n'''
TEST='''from __future__ import annotations\nimport unittest\nfrom app.calc import add\n\nclass CalcTests(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\nif __name__ == "__main__":\n    unittest.main()\n'''

def init_repo(src:Path)->str:
    git='git'
    subprocess.run([git,'init'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    subprocess.run([git,'config','user.email','fixture@example.invalid'],cwd=src,check=True)
    subprocess.run([git,'config','user.name','Fixture'],cwd=src,check=True)
    subprocess.run([git,'add','-A'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    subprocess.run([git,'commit','-m','python fixture'],cwd=src,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return git

def source_fixture(base:Path):
    src=base/'source';(src/'app').mkdir(parents=True);(src/'tests').mkdir()
    (src/'app'/'__init__.py').write_text(INIT,encoding='utf-8')
    (src/'app'/'calc.py').write_text(MODULE,encoding='utf-8')
    (src/'tests'/'test_calc.py').write_text(TEST,encoding='utf-8')
    (src/'pyproject.toml').write_text('[project]\nname="fixture"\nversion="0.0.0"\nrequires-python=">=3.11"\n',encoding='utf-8')
    (src/'README.md').write_text('# v1341 fixture\n',encoding='utf-8')
    git=init_repo(src);runtime=base/'runtime';grant=active_grant(commands=('git','git_worktree','shell'))
    pres={k:precondition(runtime,k) for k in ('git','file_read','file_patch','shell')}
    return src,runtime,grant,pres,git

def implementation_args(src:Path,runtime:Path,grant,pres,git,*,patches=None,relative_path='app/calc.py',test_argv=None,**extra):
    target=src.joinpath(*relative_path.split('/'))
    expected=hashlib.sha256(target.read_bytes()).hexdigest()
    if patches is None:
        patches=[{'type':'replace_text','old':'    return a + b','new':'    total = a + b\n    return total','expected_occurrences':1}]
    if test_argv is None:
        test_argv=[sys.executable,'-m','unittest','discover','-s','tests','-q']
    out=dict(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_ids=pres,relative_path=relative_path,expected_content_digest=expected,patches=patches,test_argv=test_argv,commit_message='Refine Python implementation',runtime_root=runtime,now_unix=101,git_executable=git,python_executable=sys.executable,cleanup_on_complete=True)
    out.update(extra);return out

def content_manifest(src:Path):
    return sorted((p.relative_to(src).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()) for p in src.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts)
