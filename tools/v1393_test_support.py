import hashlib
from pathlib import Path
V=hashlib.sha256(b'visual-screenshot-evidence').hexdigest();REPORT='The screenshot shows a negative refund as $12.50, but it should keep the minus sign and display -$12.50.'
def req(c,m):
 if not c:raise AssertionError(m)
def project(r:Path,bug=True,broken_test=False):
 p=r/'project';(p/'tests').mkdir(parents=True);body='return f"${abs(amount):.2f}"' if bug else 'return f"-${abs(amount):.2f}" if amount < 0 else f"${amount:.2f}"';(p/'money.py').write_text('def format_currency(amount: float) -> str:\n    '+body+'\n');(p/'tests'/'test_money.py').write_text('''import unittest\nfrom money import format_currency\nclass MoneyTests(unittest.TestCase):\n    def test_positive(self): self.assertEqual(format_currency(5), %r)\n'''%('$6.00' if broken_test else '$5.00'));return p
