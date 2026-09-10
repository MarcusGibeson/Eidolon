from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from conversation_context import build_conversation_prompt
from natural_conversation_quality_runtime import build_natural_conversation_quality_runtime_profile

C=[]
def req(n,c,d=''):
 C.append((n,bool(c),d))
 if not c: raise AssertionError(f'{n}: {d}')

def packet(msg,h=(),follow=None):
 return build_conversation_prompt(user_message=msg,self_model={'name':'Eidolon'},desires={},memories=[],project_context='',goal_context='',task_context='',conversation_history=list(h),context_size=8192,max_tokens=512,natural_follow_up_policy=follow)

def test_profiles():
 hist=[{'user_message':'Hi','assistant_response':'Hello, Marcus.'},{'user_message':'Long day.','assistant_response':'Hello again. What project should we work on?'}]
 p=build_natural_conversation_quality_runtime_profile('Still thinking about that radio.',hist,short_follow_up=True,maximum_follow_up_questions=0)
 req('0031-repeated-greeting-suppressed',p.repeated_greeting_suppressed,p.public_summary())
 req('0032-project-redirect-suppressed',p.unsolicited_project_redirect_suppressed,p.public_summary())
 req('0034-active-topic',p.active_topic_continuation_required,p.public_summary())
 req('0036-closing-question-suppressed',p.optional_closing_question_suppressed,p.public_summary())
 direct=build_natural_conversation_quality_runtime_profile('What do you think about jazz?',[])
 req('0033-direct-opinion',direct.direct_answer_required,direct.public_summary())
 emotional=build_natural_conversation_quality_runtime_profile('Honestly, that rough day still hurt, but finishing it felt good.',[{'assistant_response':'Thanks for sharing that.'}],emotional=True)
 req('0035-emotional-subtext',emotional.emotional_subtext_acknowledgment_required and emotional.therapy_script_suppressed,emotional.public_summary())
 present=build_natural_conversation_quality_runtime_profile('Why does that matter to me right now?',[{'assistant_response':'You sound proud and worn out.'}])
 present_guidance=' '.join(present.prompt_lines()).lower()
 req('0035a-present-stakes-detected',present.present_stakes_grounding_required,present.public_summary())
 req('0035b-present-stakes-requires-current-evidence','attributable current circumstance' in present_guidance,present_guidance)
 req('0035c-present-stakes-suppresses-generic-advice','do not substitute generic advice' in present_guidance,present_guidance)
 general=build_natural_conversation_quality_runtime_profile('Why does taking breaks matter?',[{'assistant_response':'Rest can help.'}])
 req('0035d-general-why-question-unaffected',not general.present_stakes_grounding_required,general.public_summary())
 req('0038-canned-suppression',emotional.canned_phrase_suppressed,emotional.public_summary())
 short=build_natural_conversation_quality_runtime_profile('Nice.',[]); long=build_natural_conversation_quality_runtime_profile('I had a long reflective day and there were several things I wanted to tell you about because it mattered to me.',[],emotional=True)
 req('0037-proportional-length',short.acknowledgement_target_max_words < long.acknowledgement_target_max_words,(short,long))

def test_provider_prompt_contracts():
 hist=[{'user_message':'Hey','assistant_response':'Hey there.'},{'user_message':'I fixed the dial.','assistant_response':'Thanks for sharing. What would you like to work on next?'}]
 follow={'maximum_follow_up_questions':0,'question_permission':'none','avoid_generic_closing_offer':True}
 p=packet('It felt good to finally get it turning smoothly.',hist,follow)
 prompt=p.prompt
 req('0031-prompt-no-greeting-again','Do not greet again' in prompt,prompt)
 req('0032-prompt-no-work-redirect','Do not redirect to work' in prompt,prompt)
 req('0035-prompt-no-therapy','generic therapeutic script' in prompt,prompt)
 req('0036-prompt-no-question','QUESTION BOUNDARY: Ask no question' in prompt,prompt)
 req('0038-prompt-vary-canned','Avoid the recent canned acknowledgment opener' in prompt,prompt)
 req('0037-prompt-budget',p.metrics.fast_path_bound_passed and p.metrics.estimated_prompt_tokens<=900,p.metrics.estimated_prompt_tokens)
 direct=packet('What is your favorite kind of conversation?',[],follow)
 req('0033-prompt-direct','Give the direct identity, preference, or opinion answer first' in direct.prompt,direct.prompt)
 present=packet('Why does that matter to me right now?',hist,follow)
 req('0035a-prompt-present-stakes','attributable current circumstance' in present.prompt,present.prompt)
 req('0035b-prompt-rejects-generic-advice','Do not substitute generic advice' in present.prompt,present.prompt)
 req('0035c-present-stakes-receipt',present.metrics.natural_quality_present_stakes_grounding_required,present.metrics.to_dict())

def test_multiturn_naturalness_fixture():
 turns=[]
 prompts=[]
 sequence=[
  'I finally repaired the old radio.',
  'The tuning knob was the annoying part.',
  'Still, it felt good when it worked.',
  'Honestly, I just wanted to share that.',
 ]
 assistant=['That must have been satisfying.','That knob sounds stubborn.','I can see why that landed well.','I like hearing the little victories too.']
 follow={'maximum_follow_up_questions':0,'question_permission':'none','avoid_generic_closing_offer':True}
 for i,msg in enumerate(sequence):
  p=packet(msg,turns,follow); prompts.append(p)
  req(f'0039-turn-{i}-bounded',p.metrics.estimated_prompt_tokens<=900,p.metrics.estimated_prompt_tokens)
  req(f'0039-turn-{i}-casual',p.metrics.prompt_lane=='casual_fast',p.metrics.prompt_lane)
  req(f'0039-turn-{i}-no-project','PROJECT CONTEXT' not in p.prompt and 'DEVELOPMENT CAMPAIGN' not in p.prompt,p.prompt)
  turns.append({'user_message':msg,'assistant_response':assistant[i]})
 req('0039-short-followup-continuity',prompts[1].metrics.natural_quality_active_topic_required,prompts[1].metrics.to_dict())
 req('0039-final-no-question-pressure',prompts[-1].metrics.natural_quality_optional_question_suppressed,prompts[-1].metrics.to_dict())

def main():
 for f in (test_profiles,test_provider_prompt_contracts,test_multiturn_naturalness_fixture): f()
 print(f'v1489.0031-.0040 natural conversation quality: {len(C)}/{len(C)} checks passed')
 for n,o,_ in C: print(f"  {'PASS' if o else 'FAIL'} {n}")
if __name__=='__main__': main()
