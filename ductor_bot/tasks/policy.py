"""Purpose-aware policy helpers for background tasks.

The task system is often used for cheap reports and for high-stakes source or
architecture review. Keep those execution classes separate so lightweight
models do not accidentally inherit into work that needs stronger judgment.
"""

from __future__ import annotations

from dataclasses import dataclass

LIGHTWEIGHT_CODEX_MODELS = ("mini", "spark")
LOW_EFFORTS = {"", "low"}
HIGH_JUDGMENT_TERMS = (
    "architecture",
    "audit",
    "code review",
    "critical review",
    "diagnose",
    "implement",
    "investment process",
    "janitor",
    "race",
    "refactor",
    "review",
    "source",
    "stateful",
    "system",
    "wip",
)
LIGHTWEIGHT_TERMS = (
    "digest",
    "report",
    "summarize",
    "summary",
    "transcribe",
    "transcription",
)
DEFAULT_STRONG_CODEX_MODEL = "gpt-5.5"
DEFAULT_STRONG_EFFORT = "medium"


@dataclass(frozen=True)
class TaskPolicyDecision:
    """Resolved execution policy metadata for a background task."""

    profile: str
    review_required: bool
    model_override: str
    thinking_override: str
    note: str = ""


def classify_task(prompt: str, name: str = "") -> str:
    """Return a coarse task profile from prompt/name text."""
    text = f"{name}\n{prompt}".lower()
    if any(term in text for term in HIGH_JUDGMENT_TERMS):
        return "high_judgment"
    if any(term in text for term in LIGHTWEIGHT_TERMS):
        return "lightweight"
    return "standard"


def is_lightweight_model(model: str) -> bool:
    lowered = (model or "").lower()
    return any(term in lowered for term in LIGHTWEIGHT_CODEX_MODELS)


def resolve_task_policy(
    *,
    prompt: str,
    name: str = "",
    provider: str = "",
    model: str = "",
    thinking: str = "",
    allow_lightweight_model: bool = False,
) -> TaskPolicyDecision:
    """Resolve model/thinking guardrails and review requirement.

    High-judgment tasks may still run on a lightweight model when explicitly
    allowed, but the default path upgrades Codex mini/spark + low effort to a
    stronger model/effort.
    """
    profile = classify_task(prompt, name)
    review_required = profile == "high_judgment"
    resolved_model = model
    resolved_thinking = thinking
    note = ""

    if profile == "high_judgment" and not allow_lightweight_model:
        if (provider == "codex" or not provider) and is_lightweight_model(model):
            resolved_model = DEFAULT_STRONG_CODEX_MODEL
            note = f"upgraded lightweight model {model!r} to {resolved_model!r}"
        if (provider == "codex" or not provider) and resolved_thinking in LOW_EFFORTS:
            resolved_thinking = DEFAULT_STRONG_EFFORT
            note = (note + "; " if note else "") + "upgraded low reasoning to medium"

    return TaskPolicyDecision(
        profile=profile,
        review_required=review_required,
        model_override=resolved_model,
        thinking_override=resolved_thinking,
        note=note,
    )
