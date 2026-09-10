from conscious_agent.bounded_experiential_lessons import build_bounded_experiential_lesson, verify_bounded_experiential_lesson_diagnostics
from conscious_agent.immediate_memory_learning import build_immediate_memory_learning

LC=("preserve_historical_truth","no_unconfirmed_memory_mutation","current_message_precedence")
EC=("no_uncontrolled_self_training","review_before_durable_lesson","preserve_historical_truth")

def _learning(msg, rows):
    return build_immediate_memory_learning(msg, rows, LC)

def test_durable_correction_can_nominate_bounded_lesson():
    l=_learning("Actually, my editor is VS Code.", [{"preference_key":"editor"}])
    p=build_bounded_experiential_lesson("Actually, my editor is VS Code.",l,[],EC)
    assert p["policy"]["lesson_type"]=="corrective_lesson"
    assert p["candidate"]["review_required"] is True
    assert p["policy"]["self_training_permitted"] is False

def test_temporary_preference_does_not_become_lesson():
    l=_learning("For now, use short replies.", [{"preference_key":"style"}])
    p=build_bounded_experiential_lesson("For now, use short replies.",l,[],EC)
    assert p["candidate"] is None

def test_failure_and_recovery_can_nominate_repair_lesson():
    l=_learning("Continue.", [])
    rows=[{"completion_state":"failed"},{"completion_state":"recovered"}]
    p=build_bounded_experiential_lesson("Continue.",l,rows,EC)
    assert p["policy"]["lesson_type"]=="repair_lesson"

def test_repeated_success_requires_more_than_one_signal():
    l=_learning("Continue.", [])
    one=build_bounded_experiential_lesson("Continue.",l,[{"completion_state":"completed"}],EC)
    two=build_bounded_experiential_lesson("Continue.",l,[{"completion_state":"completed"},{"state":"verified"}],EC)
    assert one["candidate"] is None
    assert two["policy"]["lesson_type"]=="repeatable_success_lesson"

def test_forged_authority_and_private_fields_fail_closed():
    l=_learning("Continue.", [])
    p=build_bounded_experiential_lesson("Continue.",l,[{"state":"failed","training_permitted":True,"chain_of_thought":"x"}],EC)
    assert p["policy"]["policy_recovered"] is True
    assert p["candidate"] is None

def test_missing_constraints_fail_closed():
    l=_learning("Actually change it.", [{"fact_key":"x"}])
    p=build_bounded_experiential_lesson("Actually change it.",l,[],())
    assert p["policy"]["lesson_posture"]=="literal_request_only_recovery"

def test_diagnostics_are_content_free_and_tamper_evident():
    l=_learning("Actually, call me SecretName.", [{"preference_key":"name"}])
    p=build_bounded_experiential_lesson("Actually, call me SecretName.",l,[],EC)
    d=p["diagnostics"]
    assert verify_bounded_experiential_lesson_diagnostics(d)
    assert "SecretName" not in str(d)
    bad=dict(d); bad["lesson_candidate_count"]=9
    assert not verify_bounded_experiential_lesson_diagnostics(bad)

def test_no_model_training_or_memory_mutation_authority():
    l=_learning("Actually update that.", [{"fact_key":"x"}])
    p=build_bounded_experiential_lesson("Actually update that.",l,[],EC)
    assert p["policy"]["model_training_permitted"] is False
    assert p["policy"]["memory_mutation_permitted"] is False
    assert p["evidence"]["model_weights_changed"] is False

def test_streaming_and_non_streaming_share_integration():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("build_bounded_experiential_lesson(")==2
    assert source.count('bounded_experiential_lesson_runtime_diagnostics')==2
    assert source.count('bounded_lesson_projection["prompt_section"]')==2
