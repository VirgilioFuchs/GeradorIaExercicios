"""Pytest fixtures for exercise_ai package tests (editable install; no sys.path)."""

from __future__ import annotations

import pytest

from exercise_ai.models import (
    DificuldadeEnum,
    Exercise,
    ExerciseBatch,
    GenerationRequest,
)


# Default mapped BNCC for curricular math_check (Phase 27 / D-15).
_DEFAULT_BNCC = ["EF07MA18"]

# Correct ax+b=c fixtures (index → (enunciado, resposta)).
_LINEAR_OK = (
    ("x + 1 = 2", "1"),
    ("2x + 3 = 7", "2"),
    ("3x + 1 = 10", "3"),
    ("4x + 2 = 14", "3"),
    ("5x + 5 = 20", "3"),
)


@pytest.fixture
def make_request():
    """Factory for GenerationRequest with sensible defaults (curricular BNCC)."""

    def _make(
        *,
        materia: str = "Matemática",
        topico: str = "Equações do 1º grau",
        dificuldade: DificuldadeEnum = DificuldadeEnum.FACIL,
        quantidade: int = 2,
        habilidade_bncc: list[str] | None = None,
    ) -> GenerationRequest:
        return GenerationRequest(
            materia=materia,
            topico=topico,
            dificuldade=dificuldade,
            quantidade=quantidade,
            habilidade_bncc=(
                list(habilidade_bncc)
                if habilidade_bncc is not None
                else list(_DEFAULT_BNCC)
            ),
        )

    return _make


@pytest.fixture
def make_exercise():
    """Factory for a single Exercise (supplies required dificuldade echo)."""

    def _make(
        *,
        enunciado: str = "x + 1 = 2",
        resposta: str = "1",
        explicacao: str = "explicacao",
        dificuldade: DificuldadeEnum = DificuldadeEnum.FACIL,
    ) -> Exercise:
        return Exercise(
            enunciado=enunciado,
            resposta=resposta,
            explicacao=explicacao,
            dificuldade=dificuldade,
        )

    return _make


@pytest.fixture
def make_batch(make_exercise):
    """Factory for ExerciseBatch with N filled linear exercises + dificuldades echo."""

    def _make(
        n: int = 2,
        *,
        dificuldades: list[DificuldadeEnum] | None = None,
        **field_overrides,
    ) -> ExerciseBatch:
        exercises = []
        for i in range(n):
            en, ans = _LINEAR_OK[i % len(_LINEAR_OK)]
            kwargs = {
                "enunciado": en,
                "resposta": ans,
                "explicacao": f"explicacao-{i}",
            }
            kwargs.update(field_overrides)
            exercises.append(make_exercise(**kwargs))
        if dificuldades is None:
            bands = {ex.dificuldade for ex in exercises}
            order = (
                DificuldadeEnum.FACIL,
                DificuldadeEnum.MEDIO,
                DificuldadeEnum.DIFICIL,
            )
            dificuldades = [b for b in order if b in bands] or [DificuldadeEnum.FACIL]
        return ExerciseBatch(exercicios=exercises, dificuldades=dificuldades)

    return _make
