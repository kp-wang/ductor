from ductor_bot.tasks.policy import resolve_task_policy


def test_high_judgment_task_upgrades_codex_mini_low() -> None:
    decision = resolve_task_policy(
        prompt="Audit the source and review architecture race risks",
        provider="codex",
        model="gpt-5.4-mini",
        thinking="low",
    )

    assert decision.profile == "high_judgment"
    assert decision.review_required is True
    assert decision.model_override == "gpt-5.5"
    assert decision.thinking_override == "medium"


def test_lightweight_transcription_keeps_mini_low() -> None:
    decision = resolve_task_policy(
        prompt="Transcribe this voice note and summarize it",
        provider="codex",
        model="gpt-5.4-mini",
        thinking="low",
    )

    assert decision.profile == "lightweight"
    assert decision.review_required is False
    assert decision.model_override == "gpt-5.4-mini"
    assert decision.thinking_override == "low"


def test_explicit_lightweight_override_is_respected() -> None:
    decision = resolve_task_policy(
        prompt="Review architecture quickly with mini",
        provider="codex",
        model="gpt-5.4-mini",
        thinking="low",
        allow_lightweight_model=True,
    )

    assert decision.profile == "high_judgment"
    assert decision.review_required is True
    assert decision.model_override == "gpt-5.4-mini"
    assert decision.thinking_override == "low"
