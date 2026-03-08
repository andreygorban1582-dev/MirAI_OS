"""
Tests for Okabe personality module.
"""


def test_apply_personality_adds_intro():
    from bot.personality.okabe import apply_personality
    # Short message should get an intro
    result = apply_personality("Hello world")
    assert len(result) > len("Hello world")
    # Should contain one of the known intros
    intros = ["Fuhahaha!", "Hououin Kyouma", "El Psy Kongroo"]
    assert any(intro in result for intro in intros)


def test_apply_personality_long_message_unchanged():
    from bot.personality.okabe import apply_personality
    long_msg = "a" * 200
    result = apply_personality(long_msg)
    # Long messages (>100 chars) should NOT be modified
    assert result == long_msg


def test_okabe_system_prompt_not_empty():
    from bot.personality.okabe import OKABE_SYSTEM_PROMPT
    assert len(OKABE_SYSTEM_PROMPT) > 50
    assert "Okabe" in OKABE_SYSTEM_PROMPT or "Hououin" in OKABE_SYSTEM_PROMPT
