"""Study qualifiers are bounded, transient and never proof of freshness."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'conscious_agent'))
from governed_public_web_research_adapter import _VisibleTextParser, _study_context

p = _VisibleTextParser()
p.feed('<meta property="article:published_time" content="2022-05-01"><footer><meta name="date" content="2026-01-01"></footer><p>Results.</p>')
assert p.publication_dates == ['2022-05-01']
text = 'Marketing slogan. The survey was conducted in May 2022 among 750 participants. The subgroup contained 447 participants. Buy now.'
context = _study_context(text)
assert 'May 2022' in context and '447' in context
assert 'Buy now' not in context and 'Marketing slogan' not in context
assert _study_context(text, 30) == ''
assert len(_study_context(text * 100)) <= 600
assert _study_context('No methodological qualifiers here.') == 'No methodological qualifiers here.'
print('study context checks passed')
