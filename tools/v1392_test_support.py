from pathlib import Path
def req(c,m):
 if not c:raise AssertionError(m)
REQ='Add a slugify helper for URL-safe task titles while preserving the project conventions and tests.'
def project(r:Path,broken=False):
 p=r/'project';(p/'src').mkdir(parents=True);(p/'tests').mkdir();(p/'src'/'__init__.py').write_text('');(p/'src'/'text_utils.py').write_text('''def normalize_text(text: str) -> str:\n    return " ".join(text.strip().lower().split())\n''');(p/'tests'/'test_text_utils.py').write_text('''import unittest\nfrom src.text_utils import normalize_text\nclass ExistingTests(unittest.TestCase):\n    def test_normalize(self): self.assertEqual(normalize_text("  A   B "), %s)\n'''%(repr('wrong') if broken else repr('a b')));return p
