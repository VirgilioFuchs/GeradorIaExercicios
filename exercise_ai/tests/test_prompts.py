"""Prompt slot enumeration (Phase 14 / PROMPT-01; Phase 25 TEST-02 home)."""

from __future__ import annotations

import pytest

from exercise_ai.models import DificuldadeEnum, GenerationRequest, PlanoDificuldade
from exercise_ai.prompts import _format_slot_list, build_prompts, hygiene_prompt_field
from exercise_ai.skills.generation import get_persona_system


def test_system_prompt_comes_from_get_persona_system():
    """PROMPT-02: SYSTEM is wired to domain persona (single source)."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Soma",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
    )
    system, _ = build_prompts(req)
    assert system == get_persona_system()
    assert "PLACEHOLDER" not in system
    assert "professor" in system.lower()


def test_system_prompt_has_no_schema_field_contract_cue():
    """PROMPT-03: anti-self-check without schema word; pedagogy kept."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Soma",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
    )
    system, user = build_prompts(req)
    assert "schema" not in system.lower()
    assert "validação determinística" in system
    assert "auto-checagem" in system
    assert "clareza no enunciado" in system
    assert "enunciado:" not in user
    assert "resposta:" not in user
    assert "explicacao:" not in user
    assert "ExerciseBatch" not in system
    assert "ExerciseBatch" not in user


def test_prompts_have_no_schema_or_field_contract_dumps():
    """TEST-01: built SYSTEM/USER must not contain schema/field-contract dumps (uniform + mixed)."""
    markers = (
        "enunciado:",
        "resposta:",
        "explicacao:",
        "ExerciseBatch",
        "```json",
        '"properties"',
        "$schema",
        "$defs",
    )
    fixtures = [
        GenerationRequest(
            materia="Matemática",
            topico="Soma",
            dificuldade=DificuldadeEnum.FACIL,
            quantidade=2,
        ),
        GenerationRequest(
            materia="Matemática",
            topico="Frações",
            quantidade=3,
            plano=PlanoDificuldade(facil=1, medio=1, dificil=1),
        ),
    ]
    for req in fixtures:
        system, user = build_prompts(req)
        blob = system + "\n" + user
        assert "schema" not in system.lower()
        for marker in markers:
            assert marker not in blob, marker


def test_mixed_prompt_enumerates_hybrid_slots():
    """PROMPT-04 / TEST-02: Mixed plano → numbered hybrid labels per slot (D-01, D-04)."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Frações",
        quantidade=3,
        plano=PlanoDificuldade(facil=1, medio=1, dificil=1),
    )
    _, user = build_prompts(req)
    assert "1. fácil (facil)" in user
    assert "2. médio (medio)" in user
    assert "3. difícil (dificil)" in user
    assert "enunciado:" not in user
    assert "resposta:" not in user
    assert "explicacao:" not in user


def test_uniform_prompt_enumerates_n_slots_same_band():
    """PROMPT-04 / TEST-02: Uniform scalar dificuldade still enumerates N hybrid lines (D-02)."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Equação do primeiro grau",
        dificuldade=DificuldadeEnum.MEDIO,
        quantidade=3,
    )
    _, user = build_prompts(req)
    assert "1. médio (medio)" in user
    assert "2. médio (medio)" in user
    assert "3. médio (medio)" in user
    assert user.count("médio (medio)") == 3
    assert "Matemática" in user
    assert "Equação do primeiro grau" in user
    assert "enunciado:" not in user
    assert "resposta:" not in user
    assert "explicacao:" not in user


def test_uniform_facil_prompt_uses_hybrid_facil_label():
    """PROMPT-04 / TEST-02: Uniform fácil path uses accented hybrid label (D-02, D-04)."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Soma",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=2,
    )
    _, user = build_prompts(req)
    assert "1. fácil (facil)" in user
    assert "2. fácil (facil)" in user
    assert user.count("fácil (facil)") == 2

def test_slot_list_line_count_matches_itens_ordenados_test02():
    """PROMPT-04 / TEST-02: line count == len(itens_ordenados) and block embedded in USER (Phase 25 D-03)."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Frações",
        quantidade=3,
        plano=PlanoDificuldade(facil=1, medio=1, dificil=1),
    )
    slot_block = _format_slot_list(req)
    assert len(slot_block.splitlines()) == len(req.itens_ordenados)
    _, user = build_prompts(req)
    assert slot_block in user


def test_prompt_includes_dificuldades_summary_shape_cue():
    """G-14-4 / SEED-008: one-line unique-band resumo cue; no field-schema dump."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Frações",
        dificuldade=DificuldadeEnum.MEDIO,
        quantidade=2,
    )
    _, user = build_prompts(req)
    assert "resumo das faixas distintas" in user
    assert "enunciado:" not in user
    assert "resposta:" not in user
    assert "explicacao:" not in user


# --- VAL-04 / Phase 23: request-field hygiene (materia / topico) ---


def test_hygiene_strips_controls_and_whitespace():
    """D-01: ASCII controls + surrounding whitespace stripped."""
    assert hygiene_prompt_field("Mat\x00emática", "materia") == "Matemática"
    assert hygiene_prompt_field("  Soma\x07  ", "topico") == "Soma"
    assert hygiene_prompt_field("x" * 200, "materia") == ("x" * 200)


def test_hygiene_rejects_empty_after_strip():
    """D-01/D-05: whitespace-only or control-only → ValueError."""
    with pytest.raises(ValueError, match="materia"):
        hygiene_prompt_field("   ", "materia")
    with pytest.raises(ValueError, match="topico"):
        hygiene_prompt_field("\x00\x1f\x7f", "topico")


def test_hygiene_bound_rejects_overlong_no_truncate():
    """D-02/D-03: length 200 OK; 201 → ValueError (no silent truncate)."""
    assert hygiene_prompt_field("a" * 200, "materia") == ("a" * 200)
    with pytest.raises(ValueError, match="200"):
        hygiene_prompt_field("b" * 201, "materia")
    with pytest.raises(ValueError, match="topico"):
        hygiene_prompt_field("c" * 201, "topico")


def test_hygiene_build_prompts_uses_cleaned_materia_topico():
    """D-04: cleaned materia/topico appear in USER; controls absent."""
    req = GenerationRequest(
        materia="Mat\x00emática",
        topico="Fra\x1fções",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
    )
    _, user = build_prompts(req)
    assert "Matemática" in user
    assert "Frações" in user
    assert "\x00" not in user
    assert "\x1f" not in user


def test_bncc_curricular_user_includes_codes_only():
    """BNCC-02 / D-05: curricular USER lists codes; no schema dump."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Frações",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
        habilidade_bncc=["EF06MA01"],
    )
    _, user = build_prompts(req)
    assert "EF06MA01" in user
    assert "Habilidades BNCC" in user
    assert "ExerciseBatch" not in user
    assert '"properties"' not in user
    assert "$schema" not in user


def test_bncc_non_curricular_omits_bncc_section():
    """BNCC-02: non-curricular USER has no BNCC heading/codes noise."""
    req = GenerationRequest(
        materia="Matemática",
        topico="Frações",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
    )
    _, user = build_prompts(req)
    assert "Habilidades BNCC" not in user
    assert "EF06MA01" not in user
