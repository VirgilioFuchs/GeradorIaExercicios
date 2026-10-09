"""G1 offline locks for parametric AIG ax+b=c (Phase 28-01).

Judge is Phase 27 ``check_math_batch`` only — never the generator's
``_render_c``. Algebraic Fraction enum (3600) proves identity in the
Polar-Mat §6 domain; it does not prove pedagogical quality or cost savings.
"""

from __future__ import annotations

import importlib
import json
from fractions import Fraction
from pathlib import Path

import pytest
from unittest.mock import patch

from exercise_ai.aig_axb import (
    A_MAX,
    A_MIN,
    B_MAX,
    B_MIN,
    S_MAX,
    S_MIN,
    DomainError,
    ItemModelError,
    instantiate,
    instantiate_for_request,
    is_aig_covered,
    load_item_model,
    validate_params,
)
from exercise_ai.math_check import check_math_batch
from exercise_ai.models import Exercise, ExerciseBatch, DificuldadeEnum, GenerationRequest
import exercise_ai.service as service

_MODEL_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "item_models"
    / "ax_plus_b_eq_c.v1.json"
)

# Polar-Mat §6 table examples (a, b, s, c).
_TABLE_EXAMPLES = (
    (3, 4, 5, 19),
    (5, 6, 4, 26),
    (7, 3, 6, 45),
)


# ---------------------------------------------------------------------------
# Tracer / contract (28-01-01)
# ---------------------------------------------------------------------------


def test_contract_json_has_version_and_ef07ma18():
    payload = json.loads(_MODEL_PATH.read_text(encoding="utf-8"))
    assert "version" in payload
    assert payload["version"]
    assert "EF07MA18" in payload["habilidades_bncc"]
    assert payload["form"] == "a*x+b=c"
    assert payload["id"]
    assert payload["generator_id"]


def test_load_item_model_tracer():
    model = load_item_model()
    assert model["id"] == "ax_plus_b_eq_c"
    assert model["version"] == "1"


def test_contract_reject_missing_version(tmp_path: Path):
    bad = {
        "id": "ax_plus_b_eq_c",
        "params": {"a": {}, "b": {}, "s": {}},
        "habilidades_bncc": ["EF07MA18"],
        "generator_id": "aig_axb.v1",
        "form": "a*x+b=c",
    }
    path = tmp_path / "bad.v1.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ItemModelError, match="version"):
        load_item_model(path)


def test_instantiate_tracer_happy_path_judged_by_math_check():
    """a=3,b=4,s=5 → c=19; judge via check_math_batch (AIG-03)."""
    batch = instantiate(3, 4, 5)
    assert isinstance(batch, ExerciseBatch)
    assert len(batch.exercicios) == 1
    ex = batch.exercicios[0]
    assert ex.enunciado == "3x + 4 = 19"
    assert ex.resposta == "5"
    assert batch.habilidades_bncc == ["EF07MA18"]
    check_math_batch(batch)


def test_aig_module_import_graph_has_no_openai_or_httpx():
    """Happy-path AIG module must not pull LLM HTTP clients."""
    mod = importlib.import_module("exercise_ai.aig_axb")
    src = Path(mod.__file__).read_text(encoding="utf-8")
    for name in ("openai", "httpx"):
        assert f"import {name}" not in src
        assert f"from {name}" not in src
    assert "openai" not in src and "httpx" not in src


# ---------------------------------------------------------------------------
# G1: domain / unicity / correspondence / reproduction (28-01-02)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,s",
    [
        (1, 5, 5),  # a below min
        (11, 5, 5),  # a above max
        (3, 0, 5),  # b below
        (3, 21, 5),  # b above
        (3, 5, 0),  # s below
        (3, 5, 21),  # s above
        (0, 5, 5),  # a==0 unicity
    ],
)
def test_domain_reject_out_of_range(a: int, b: int, s: int):
    with pytest.raises(DomainError):
        validate_params(a, b, s)
    with pytest.raises(DomainError):
        instantiate(a, b, s)


def test_unique_coefficient_a_nonzero_guard():
    """Domain a∈[2,10] excludes zero; explicit guard if raw a offered."""
    with pytest.raises(DomainError, match="a=0|degenera|unicidade"):
        validate_params(0, 1, 1)


def test_correspondence_enunciado_matches_params():
    a, b, s = 3, 4, 5
    batch = instantiate(a, b, s)
    ex = batch.exercicios[0]
    assert str(a) in ex.enunciado
    assert str(b) in ex.enunciado
    assert "19" in ex.enunciado  # c = a*s+b
    assert ex.resposta == str(s)


def test_correspondence_wrong_answer_fails_judge():
    """Tampered resposta must fail Phase 27 check_math_batch."""
    batch = instantiate(3, 4, 5)
    bad = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado=batch.exercicios[0].enunciado,
                resposta="99",
                explicacao=batch.exercicios[0].explicacao,
                dificuldade=DificuldadeEnum.FACIL,
            )
        ],
        dificuldades=batch.dificuldades,
        habilidades_bncc=list(batch.habilidades_bncc or []),
    )
    with pytest.raises(ValueError, match="inconsistência|matemática"):
        check_math_batch(bad)


def test_reproduce_same_params_same_item():
    b1 = instantiate(5, 6, 4)
    b2 = instantiate(5, 6, 4)
    assert b1.exercicios[0].enunciado == b2.exercicios[0].enunciado
    assert b1.exercicios[0].resposta == b2.exercicios[0].resposta
    assert b1.exercicios[0].explicacao == b2.exercicios[0].explicacao
    model = load_item_model()
    assert model["version"] == "1"
    check_math_batch(b1)


# ---------------------------------------------------------------------------
# Algebraic enum 3600 + sampled payloads (28-01-03)
# ---------------------------------------------------------------------------


def test_fraction_enum_3600_algebraic_identity():
    """Polar-Mat §6: enumerates domain; identity only — not pedagogy proof."""
    total = 0
    for a in range(A_MIN, A_MAX + 1):
        for b in range(B_MIN, B_MAX + 1):
            for s in range(S_MIN, S_MAX + 1):
                c = a * s + b
                resposta = Fraction(c - b, a)
                assert resposta == s
                assert a * resposta + b == c
                total += 1
    assert total == 3600


@pytest.mark.parametrize("a,b,s,c", _TABLE_EXAMPLES)
def test_sampled_table_examples_pass_math_check(a: int, b: int, s: int, c: int):
    batch = instantiate(a, b, s)
    assert batch.exercicios[0].enunciado == f"{a}x + {b} = {c}"
    assert batch.exercicios[0].resposta == str(s)
    check_math_batch(batch)


def test_sampled_extra_payloads_pass_judge():
    """Small fixed sample beyond the §6 table — full render, independent judge."""
    samples = (
        (2, 1, 1),
        (2, 20, 20),
        (10, 1, 20),
        (10, 20, 1),
        (4, 10, 10),
    )
    for a, b, s in samples:
        batch = instantiate(a, b, s)
        check_math_batch(batch)


# ---------------------------------------------------------------------------
# Coverage routing (28-02-01): covered = 0 LLM; uncovered → failover
# ---------------------------------------------------------------------------


def _covered_request(*, quantidade: int = 2) -> GenerationRequest:
    return GenerationRequest(
        materia="Matemática",
        topico="Equação do primeiro grau",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=quantidade,
        habilidade_bncc=["EF07MA18"],
    )


def _uncovered_request(*, quantidade: int = 2) -> GenerationRequest:
    """BNCC outside family set → explicit LLM path (AIG-05 / D-11)."""
    return GenerationRequest(
        materia="Matemática",
        topico="Equação do primeiro grau",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=quantidade,
        habilidade_bncc=["EF07MA13"],
    )


def test_coverage_predicate_ef07ma18_covered():
    assert is_aig_covered(_covered_request()) is True
    assert is_aig_covered(_uncovered_request()) is False
    bare = GenerationRequest(
        materia="Matemática",
        topico="soma",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
    )
    assert is_aig_covered(bare) is False


def test_coverage_generate_batch_covered_zero_failover():
    """Covered request instantiates locally; generate_with_failover never called."""
    with patch.object(service, "generate_with_failover") as failover:
        with patch.object(service, "begin_run"):
            with patch.object(service, "flush_token_usage") as flush:
                batch = service.generate_batch(_covered_request(quantidade=2))
    assert failover.call_count == 0
    flush.assert_called()
    assert len(batch.exercicios) == 2
    assert batch.habilidades_bncc == ["EF07MA18"]
    check_math_batch(batch)


def test_uncovered_generate_batch_calls_failover():
    """Uncovered request uses generate_with_failover explicitly (no silent AIG)."""
    stub = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="2x + 3 = 7",
                resposta="2",
                explicacao="ok",
                dificuldade=DificuldadeEnum.FACIL,
            ),
            Exercise(
                enunciado="3x + 1 = 10",
                resposta="3",
                explicacao="ok",
                dificuldade=DificuldadeEnum.FACIL,
            ),
        ],
        dificuldades=[DificuldadeEnum.FACIL],
        habilidades_bncc=["EF07MA13"],
    )
    with patch.object(service, "generate_with_failover", return_value=stub) as failover:
        with patch.object(service, "resolve_max_retries", return_value=0):
            with patch.object(service, "begin_run"):
                with patch.object(service, "flush_token_usage"):
                    with patch.object(service, "instantiate_for_request") as aig:
                        out = service.generate_batch(_uncovered_request())
    assert failover.call_count == 1
    assert aig.call_count == 0
    assert out is stub


def test_coverage_aig_math_fail_does_not_fallback_to_llm():
    """Covered AIG judge failure raises closed — no failover repair (T-28-06)."""
    with patch.object(service, "check_math_batch", side_effect=ValueError("inconsistência matemática")):
        with patch.object(service, "generate_with_failover") as failover:
            with patch.object(service, "begin_run"):
                with patch.object(service, "flush_token_usage"):
                    with pytest.raises(ValueError, match="inconsistência"):
                        service.generate_batch(_covered_request(quantidade=1))
    assert failover.call_count == 0


def test_instantiate_for_request_qty_and_deterministic():
    req = _covered_request(quantidade=3)
    b1 = instantiate_for_request(req)
    b2 = instantiate_for_request(req)
    assert len(b1.exercicios) == 3
    assert b1.exercicios[0].enunciado == b2.exercicios[0].enunciado
    # Index 0 → a=2,b=1,s=1 → c=3
    assert b1.exercicios[0].enunciado == "2x + 1 = 3"
    assert b1.exercicios[0].resposta == "1"
    check_math_batch(b1)


def test_aig_batch_exposes_template_id_and_version_meta():
    """Pipeline attaches template meta matching approved JSON (D-04)."""
    contract = load_item_model()
    with patch.object(service, "generate_with_failover") as failover:
        with patch.object(service, "begin_run"):
            with patch.object(service, "flush_token_usage"):
                batch = service.generate_batch(_covered_request(quantidade=1))
    assert failover.call_count == 0
    assert batch.template_id == contract["id"] == "ax_plus_b_eq_c"
    assert batch.version == contract["version"] == "1"
    # attach_bncc_echo must preserve meta
    assert batch.habilidades_bncc == ["EF07MA18"]


def test_llm_path_batch_leaves_template_meta_absent():
    """LLM Structured Outputs path does not invent template_id/version."""
    stub = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="2x + 3 = 7",
                resposta="2",
                explicacao="ok",
                dificuldade=DificuldadeEnum.FACIL,
            )
        ],
        dificuldades=[DificuldadeEnum.FACIL],
        habilidades_bncc=["EF07MA13"],
    )
    assert stub.template_id is None
    assert stub.version is None
    with patch.object(service, "generate_with_failover", return_value=stub):
        with patch.object(service, "resolve_max_retries", return_value=0):
            with patch.object(service, "begin_run"):
                with patch.object(service, "flush_token_usage"):
                    out = service.generate_batch(
                        GenerationRequest(
                            materia="Matemática",
                            topico="Equação",
                            dificuldade=DificuldadeEnum.FACIL,
                            quantidade=1,
                            habilidade_bncc=["EF07MA13"],
                        )
                    )
    assert out.template_id is None
    assert out.version is None


def test_llm_exercise_batch_schema_has_no_template_fields():
    """SO schema must not accept/require template meta (T-28-05)."""
    from exercise_ai.models import LlmExerciseBatch

    props = LlmExerciseBatch.model_json_schema().get("properties", {})
    assert "template_id" not in props
    assert "version" not in props
    assert "habilidades_bncc" not in props
    pub = ExerciseBatch.model_json_schema().get("properties", {})
    assert "template_id" in pub
    assert "version" in pub
