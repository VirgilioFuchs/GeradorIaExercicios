"""Unit tests for math_check (no live LLM). Named hybrid fixtures (D-05, D-17)."""
from __future__ import annotations

import contextlib
import inspect
import io

import pytest
from exercise_ai.math_check import (
    check_math_batch,
    clear_math_buffers,
    drain_inconsistency_records,
    drain_uninterpretable_records,
    resolve_bncc_rule_union,
)
from exercise_ai.models import DificuldadeEnum, Exercise, ExerciseBatch, GenerationRequest
from exercise_ai.validator import validate_exercise_batch


def _bncc_batch(
    enunciado: str,
    resposta: str,
    *,
    codes: list[str] | None = None,
    explicacao: str = "ok",
) -> ExerciseBatch:
    """ExerciseBatch with BNCC echo for curricular math path (D-15)."""
    return ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado=enunciado,
                resposta=resposta,
                explicacao=explicacao,
                dificuldade=DificuldadeEnum.FACIL,
            )
        ],
        dificuldades=[DificuldadeEnum.FACIL],
        habilidades_bncc=codes if codes is not None else ["EF07MA18"],
    )


def test_empty_bncc_curricular_fails():
    """D-15: missing/empty habilidades_bncc → ValueError on math path."""
    clear_math_buffers()
    batch = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="2x + 3 = 7",
                resposta="2",
                explicacao="ok",
                dificuldade=DificuldadeEnum.FACIL,
            )
        ],
        dificuldades=[DificuldadeEnum.FACIL],
        habilidades_bncc=None,
    )
    with pytest.raises(ValueError, match="BNCC|curricular|habilidades_bncc"):
        check_math_batch(batch)

    clear_math_buffers()
    batch_empty = ExerciseBatch(
        exercicios=batch.exercicios,
        dificuldades=batch.dificuldades,
        habilidades_bncc=[],
    )
    with pytest.raises(ValueError, match="BNCC|curricular|habilidades_bncc"):
        check_math_batch(batch_empty)


def test_echo_before_math_via_validate_bncc():
    """Validator attaches BNCC echo before math; correct ax+b=c passes (D-13)."""
    clear_math_buffers()
    req = GenerationRequest(
        topico="Equações do 1º grau",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
        habilidade_bncc=["EF07MA18"],
    )
    batch = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="2x + 3 = 7",
                resposta="2",
                explicacao="x=(7-3)/2",
                dificuldade=DificuldadeEnum.FACIL,
            )
        ],
        dificuldades=[DificuldadeEnum.FACIL],
        # LLM invent — must be stripped by attach_bncc_echo
        habilidades_bncc=["IGNORE_ME"],
    )
    out = validate_exercise_batch(batch, req)
    assert out.habilidades_bncc == ["EF07MA18"]
    sig = inspect.signature(check_math_batch)
    assert list(sig.parameters) == ["batch"]


def test_unmapped_bncc_dispatch_fails():
    """D-04/D-12: curricular code in catalog but absent from rule map → fail batch."""
    clear_math_buffers()
    batch = _bncc_batch("2x + 3 = 7", "2", codes=["EF06MA01"])
    with pytest.raises(ValueError, match="sem regra tipada|mapa"):
        check_math_batch(batch)


def test_union_dispatch_merges_rule_packs():
    """D-02/D-14: multi-code → union of rules (EF07MA13 adds variable_vs_unknown)."""
    rules, domain, codes = resolve_bncc_rule_union(["EF07MA18", "EF07MA13"])
    assert codes == ["EF07MA18", "EF07MA13"]
    assert "linear_univariate" in rules
    assert "variable_vs_unknown" in rules
    assert domain == "Z"


def test_EF07MA18_correct_linear_dispatch_passes():
    """MATH-01: single mapped EF07MA18 + correct ax+b=c passes."""
    clear_math_buffers()
    check_math_batch(_bncc_batch("2x + 3 = 7", "2", codes=["EF07MA18"]))
    assert drain_uninterpretable_records() == []


def test_domain_violation_naturals_fails():
    """D-05/D-07: EF06MA14 domain N rejects negative answer literal."""
    clear_math_buffers()
    # 2x + 3 = 1 → x = -1 (outside naturais)
    batch = _bncc_batch("2x + 3 = 1", "-1", codes=["EF06MA14"])
    with contextlib.redirect_stderr(io.StringIO()):
        with pytest.raises(ValueError):
            check_math_batch(batch)


def test_domain_union_most_restrictive():
    """Multi-code domain union: N ⊂ Z → enforce N."""
    rules, domain, _ = resolve_bncc_rule_union(["EF07MA18", "EF06MA14"])
    assert domain == "N"
    assert "linear_univariate" in rules


def test_in_domain_correct_linear_passes():
    """In-domain Z linear under EF07MA18 passes (incl. negative coeffs)."""
    clear_math_buffers()
    check_math_batch(_bncc_batch("-2x + 3 = 7", "-2", codes=["EF07MA18"]))


def test_out_of_profile_sistema_fails():
    """D-08: sistema/cartesian/radical under profile_1grau → fail not soft."""
    clear_math_buffers()
    batch = _bncc_batch(
        "Resolva o sistema: 2x + y = 1",
        "1",
        codes=["EF07MA18"],
    )
    with contextlib.redirect_stderr(io.StringIO()):
        with pytest.raises(ValueError):
            check_math_batch(batch)


def test_tipado_uninterpretable_fails_closed():
    """D-09: tipado unreadable → ValueError (not legacy soft-pass)."""
    clear_math_buffers()
    batch = _bncc_batch("Explique o conceito de igualdade", "ok", codes=["EF07MA18"])
    with contextlib.redirect_stderr(io.StringIO()):
        with pytest.raises(ValueError):
            check_math_batch(batch)


def test_wrong_linear_raises_math_dual_channel():
    """Clear wrong ax+b=c → ValueError; [MATH] on stderr only (legacy arithmetic→linear)."""
    clear_math_buffers()
    batch = _bncc_batch("2x + 3 = 7", "5", explicacao="errado")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        with pytest.raises(ValueError) as exc_info:
            check_math_batch(batch)
    msg = str(exc_info.value)
    assert "[MATH]" not in msg
    assert "matemática" in msg.lower() or "inconsist" in msg.lower()
    assert "[MATH]" in buf.getvalue()
    assert "índice=0" in buf.getvalue() or "indice=0" in buf.getvalue().lower()


def test_correct_linear_bncc_passes():
    """Correct ax+b=c with BNCC echo passes (converted from arithmetic legacy)."""
    clear_math_buffers()
    check_math_batch(_bncc_batch("2x + 3 = 7", "2", explicacao="dois"))
    assert drain_uninterpretable_records() == []


def test_correct_axb_equals_c_passes():
    """Correct ax+b=c solution passes and is interpreted."""
    clear_math_buffers()
    check_math_batch(_bncc_batch("2x + 3 = 7", "2", explicacao="x = (7-3)/2"))
    assert drain_uninterpretable_records() == []


def test_wrong_axb_equals_c_raises():
    """Wrong ax+b=c solution raises with [MATH] stderr."""
    clear_math_buffers()
    batch = _bncc_batch("2x + 3 = 7", "5", explicacao="errado")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        with pytest.raises(ValueError) as exc_info:
            check_math_batch(batch)
    msg = str(exc_info.value)
    assert "[MATH]" not in msg
    assert "0" in msg
    assert "[MATH]" in buf.getvalue()


def test_uninterpretable_tipado_raises_not_soft():
    """D-09: radical/out-of-profile under tipado BNCC → ValueError (not soft)."""
    clear_math_buffers()
    batch = _bncc_batch(
        "Simplifique √16 / 2",
        "2",
        codes=["EF07MA18"],
        explicacao="radical",
    )
    with contextlib.redirect_stderr(io.StringIO()):
        with pytest.raises(ValueError):
            check_math_batch(batch)
    records = drain_inconsistency_records()
    assert len(records) >= 1
    assert records[0]["reason"] in ("out_of_profile", "tipado_unreadable")
    assert records[0]["index"] == 0
    assert "rule_id" in records[0]
    assert "codigo_bncc" in records[0]


def test_typed_fail_evidence_has_bncc_rule_index():
    """D-11: drainable inconsistency records include index, codigo_bncc, rule_id."""
    clear_math_buffers()
    batch = _bncc_batch("2x + 3 = 7", "5", codes=["EF07MA18"], explicacao="errado")
    with contextlib.redirect_stderr(io.StringIO()):
        with pytest.raises(ValueError):
            check_math_batch(batch)
    records = drain_inconsistency_records()
    assert len(records) == 1
    rec = records[0]
    assert rec["index"] == 0
    assert rec["codigo_bncc"] == ["EF07MA18"]
    assert rec["rule_id"] == "linear_univariate"
    assert drain_inconsistency_records() == []


def test_multi_index_lists_all_inconsistencies():
    """Two clear inconsistencies → one ValueError listing both indices."""
    clear_math_buffers()
    batch = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="2x + 3 = 7",
                resposta="5",
                explicacao="errado",
                dificuldade=DificuldadeEnum.FACIL,
            ),
            Exercise(
                enunciado="3x + 1 = 10",
                resposta="1",
                explicacao="errado",
                dificuldade=DificuldadeEnum.FACIL,
            ),
            Exercise(
                enunciado="x + 1 = 2",
                resposta="1",
                explicacao="ok",
                dificuldade=DificuldadeEnum.FACIL,
            ),
        ],
        dificuldades=[DificuldadeEnum.FACIL],
        habilidades_bncc=["EF07MA18"],
    )
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        with pytest.raises(ValueError) as exc_info:
            check_math_batch(batch)
    msg = str(exc_info.value)
    assert "0" in msg and "1" in msg
    assert "[MATH]" not in msg
    stderr = buf.getvalue()
    assert stderr.count("[MATH]") >= 2


def test_wrong_linear_checked_like_legacy_percent():
    """Converted legacy percent/arithmetic check → wrong linear under BNCC fails."""
    clear_math_buffers()
    batch_wrong = _bncc_batch("10x + 10 = 30", "5", explicacao="errado")
    with contextlib.redirect_stderr(io.StringIO()):
        with pytest.raises(ValueError):
            check_math_batch(batch_wrong)
