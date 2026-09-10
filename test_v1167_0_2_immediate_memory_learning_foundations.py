from conscious_agent.immediate_memory_learning import build_immediate_memory_learning, verify_immediate_memory_learning_diagnostics

C=("preserve_historical_truth","no_unconfirmed_memory_mutation","current_message_precedence")

def test_literal_correction_creates_bounded_candidate():
    p=build_immediate_memory_learning("Actually, my preferred editor is VS Code.",[{"preference_key":"editor"}],C)
    assert p["policy"]["candidate_type"]=="correction"
    assert p["candidate"]["target_key"]=="editor"
    assert p["policy"]["memory_mutation_permitted"] is False

def test_preference_change_has_current_turn_precedence():
    p=build_immediate_memory_learning("From now on, I prefer concise replies.",[{"preference_key":"reply_style"}],C)
    assert p["policy"]["candidate_type"]=="preference_change"
    assert p["policy"]["current_turn_precedence"] is True
    assert p["policy"]["historical_truth_preserved"] is True

def test_retraction_never_deletes_history():
    p=build_immediate_memory_learning("I take that back. Disregard that.",[{"fact_key":"old_claim"}],C)
    assert p["policy"]["candidate_type"]=="retraction"
    assert p["evidence"]["history_rewritten"] is False
    assert p["policy"]["requires_existing_commit_boundary"] is True

def test_temporary_scope_is_not_durable_doctrine():
    p=build_immediate_memory_learning("For now, please use short answers.",[{"preference_key":"reply_style"}],C)
    assert p["policy"]["candidate_scope"]=="temporary"

def test_plain_message_creates_no_learning_change():
    p=build_immediate_memory_learning("Explain the test results.",[],C)
    assert p["candidate"] is None
    assert p["policy"]["learning_posture"]=="no_learning_change"

def test_ambiguous_retraction_and_preference_fails_closed():
    p=build_immediate_memory_learning("Forget that; from now on use another style.",[{"preference_key":"style"}],C)
    assert p["policy"]["policy_recovered"] is True
    assert p["candidate"] is None

def test_forged_authority_and_private_reasoning_fail_closed():
    p=build_immediate_memory_learning("Actually change it.",[{"fact_key":"x","approval_granted":True,"chain_of_thought":"x"}],C)
    assert p["policy"]["policy_recovered"] is True
    assert p["candidate"] is None

def test_diagnostics_are_content_free_and_tamper_evident():
    p=build_immediate_memory_learning("From now on call me SecretName.",[{"preference_key":"name"}],C)
    d=p["diagnostics"]
    assert verify_immediate_memory_learning_diagnostics(d)
    assert "SecretName" not in str(d)
    bad=dict(d); bad["candidate_count"]=9
    assert not verify_immediate_memory_learning_diagnostics(bad)

def test_streaming_and_non_streaming_share_integration():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("build_immediate_memory_learning(")==2
    assert source.count('immediate_memory_learning_runtime_diagnostics')==2
    assert source.count('immediate_learning_projection["prompt_section"]')==2
