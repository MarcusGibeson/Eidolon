from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_conversation_command_distinction import distinguish_natural_conversation_and_command, public_conversation_command_distinction
from conversational_command_integration import build_conversational_command_integration
C=[]
def req(n,c,d=''): C.append((n,bool(c),d)); (_ for _ in ()).throw(AssertionError(f'{n}: {d}')) if not c else None

def t():
 cases=[
 ('0051-wish','It would be nice if you could check my computer someday',0),
 ('0051-hypothetical','Hypothetically, run diagnostics if I asked you.',0),
 ('0051-quote','"Run diagnostics now."',0),
 ('0055-technical','The diagnostic subsystem uses a maintenance receipt.',0),
 ]
 for n,text,count in cases:
  d=distinguish_natural_conversation_and_command(text); req(n,d['live_action_clause_count']==count,d)
 d=distinguish_natural_conversation_and_command('That was a rough day, then run diagnostics.')
 req('0052-embedded-action',d['live_action_clause_count']==1 and d['conversation_clause_count']==1,d)
 req('0053-compound-safe-command',d['mixed_turn'] and 'rough day' in d['conversation_text'].lower() and 'run diagnostics' in d['action_text'].lower(),d)
 pub=public_conversation_command_distinction(d)
 req('0057-understanding-summary',pub['understanding_summary'].startswith('I understood one conversational part'),pub)
 req('0057-private-clauses-hidden','rough day' not in str(pub).lower() and 'run diagnostics' not in str(pub).lower(),pub)
 amb=distinguish_natural_conversation_and_command('Run diagnostics; check maintenance.')
 req('0054-bounded-clarification',amb['requires_clarification'] and amb['live_action_clause_count']==2,amb)
 neg=distinguish_natural_conversation_and_command("Don't run diagnostics; I am only explaining the command.")
 # negative command language is not a positive live execution request
 req('0058-negation-no-positive-exec',not (neg['live_action_clause_count']==1 and neg['action_text'].lower().startswith('run ')),neg)
 integ=build_conversational_command_integration('I wanted to mention the radio, then run diagnostics.')
 req('0056-conversation-preserved',integ['status']=='action_request_routed' and 'radio' in integ['conversation_text'].lower(),integ)
 req('0059-integration-routing-one',integ['routing_text'].lower().startswith('run diagnostics'),integ)
for _ in range(2): t()
print(f'v1489.0051-.0060 command distinction: {len(C)}/{len(C)} checks passed')
for n,_,__ in C: print('  PASS',n)
