from pathlib import Path
REQ='Refactor the duplicated display-name normalization into a clear ownership boundary while preserving behavior and migration compatibility.'
def req(c,m):
 if not c:raise AssertionError(m)
def project(r:Path,duplicates=True,broken=False):
 p=r/'project';(p/'src').mkdir(parents=True);(p/'tests').mkdir();(p/'src'/'__init__.py').write_text('')
 expr='" ".join(value.strip().split())'
 if duplicates:
  source='''def normalize_display_name(value: str) -> str:\n    return %s\n\ndef create_profile(value: str) -> dict:\n    return {"display_name": %s}\n\ndef update_profile(profile: dict, value: str) -> dict:\n    updated = dict(profile)\n    updated["display_name"] = %s\n    return updated\n'''%(expr,expr,expr)
 else:source='def create_profile(value: str) -> dict:\n    return {"display_name": value}\n'
 (p/'src'/'profile_service.py').write_text(source);(p/'tests'/'test_profile_service.py').write_text('''import unittest\nfrom src.profile_service import create_profile, update_profile, normalize_display_name\nclass ProfileTests(unittest.TestCase):\n    def test_create(self): self.assertEqual(create_profile(" A   B ")["display_name"], %r)\n    def test_update(self): self.assertEqual(update_profile({}, " C  D ")["display_name"], "C D")\n    def test_compat_helper(self): self.assertEqual(normalize_display_name(" E  F "), "E F")\n'''%('WRONG' if broken else 'A B'));return p
