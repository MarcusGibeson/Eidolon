from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from self_development_alpha_foundations import prepare_self_development_alpha_campaign
from isolated_self_modification_foundations import source_only_manifest


def fixture(base: Path) -> Path:
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir()
    files={
        'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n',
        'conscious_agent/package_integrity.py':'POLICY=True\n',
        'README_NEXT_STEPS.md':'next\n',
        'pyproject.toml':'[project]\nname="alpha-fixture"\n',
        'conscious_agent/app.py':'def value():\n    return 0\n',
        'tools/test_app.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"conscious_agent"))\nfrom app import value\nassert value()==1\n',
    }
    for rel,text in files.items():
        q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    return p


def evidence():
    return [{'kind':'tests','status':'failing','claim_code':'alpha_value_contract','polarity':'supports','confidence':'high','evidence_digest':'a'*64}]


def priority_context():
    return [{'objective_code':'investigate_test_signal:alpha_value_contract','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'b'*64}]


def prepared_chain(base: Path):
    source=fixture(base);runtime=base/'runtime';before=source_only_manifest(source)['source_manifest_digest']
    campaign=prepare_self_development_alpha_campaign(source,external_evidence=evidence(),priority_context=priority_context(),runtime_root=runtime)
    return {'source':source,'runtime':runtime,'campaign':campaign,'before':before}


def initial_provider(calls: list[dict]):
    def provider(req):
        calls.append(dict(req))
        return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]}
    return provider


def repair_provider(calls: list[dict]):
    def provider(req):
        calls.append(dict(req))
        return {'strategy_code':'restore_alpha_value_contract','changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 1\n# v1270 repaired candidate\n'}]}
    return provider
