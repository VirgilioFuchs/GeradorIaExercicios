"""Smoke: skill de geração importável (CONTRACT-01 / Phase 16)."""

from __future__ import annotations

from exercise_ai.skills.generation import get_persona_system


def test_get_persona_system_returns_nonempty_str() -> None:
    text = get_persona_system()
    assert isinstance(text, str)
    assert text.strip()
    assert "PLACEHOLDER" not in text
    assert "professor" in text.lower()
