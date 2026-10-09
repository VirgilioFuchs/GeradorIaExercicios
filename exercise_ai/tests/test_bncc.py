"""Offline BNCC catalog + request validation (Phase 26)."""

from __future__ import annotations

import pytest

from exercise_ai.bncc_catalog import catalog_path, load_codigos, normalize_codigo, validate_codigos
from exercise_ai.models import DificuldadeEnum, ExerciseSpec, GenerationRequest


def test_catalog_lives_under_exercise_ai() -> None:
    path = catalog_path()
    assert path.is_file()
    assert "exercise_ai" in path.as_posix()
    assert ".planning" not in path.as_posix()
    codes = load_codigos()
    assert len(codes) == 290
    assert "EF06MA01" in codes


def test_normalize_and_validate_known_code() -> None:
    assert normalize_codigo(" ef06ma01 ") == "EF06MA01"
    assert validate_codigos([" ef06ma01 "]) == ["EF06MA01"]


def test_validate_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="desconhecido"):
        validate_codigos(["NOTREAL99"])


def test_validate_rejects_empty_entry() -> None:
    with pytest.raises(ValueError, match="vazio"):
        validate_codigos([""])


def test_validate_rejects_over_cap() -> None:
    codes = sorted(load_codigos())[:11]
    with pytest.raises(ValueError, match="limite"):
        validate_codigos(codes)


def test_request_accepts_known_bncc() -> None:
    req = GenerationRequest(
        topico="Frações",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
        habilidade_bncc=["EF06MA01"],
    )
    assert req.habilidade_bncc == ["EF06MA01"]


def test_request_rejects_empty_code_entry() -> None:
    with pytest.raises(ValueError):
        GenerationRequest(
            topico="Frações",
            dificuldade=DificuldadeEnum.FACIL,
            quantidade=1,
            habilidade_bncc=[""],
        )


def test_request_absent_bncc_is_non_curricular() -> None:
    req = GenerationRequest(
        topico="Frações",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
    )
    assert req.habilidade_bncc is None


def test_exercise_spec_optional_bncc() -> None:
    spec = ExerciseSpec(
        dificuldade=DificuldadeEnum.FACIL,
        habilidade_bncc=["EF06MA01"],
    )
    assert spec.habilidade_bncc == ["EF06MA01"]
    bare = ExerciseSpec(dificuldade=DificuldadeEnum.FACIL)
    assert bare.habilidade_bncc is None


def test_attach_bncc_echo_curricular_simple() -> None:
    """BNCC-03 / D-12: simple mode echo = normalized request list."""
    from exercise_ai.models import Exercise, ExerciseBatch, attach_bncc_echo

    req = GenerationRequest(
        topico="Frações",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
        habilidade_bncc=["EF06MA01"],
    )
    batch = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="e",
                resposta="r",
                explicacao="x",
                dificuldade=DificuldadeEnum.FACIL,
            )
        ],
        dificuldades=[DificuldadeEnum.FACIL],
        habilidades_bncc=["IGNORE_ME"],  # LLM invent — must be stripped
    )
    out = attach_bncc_echo(batch, req)
    assert out.habilidades_bncc == ["EF06MA01"]


def test_attach_bncc_echo_non_curricular_omits() -> None:
    from exercise_ai.models import Exercise, ExerciseBatch, attach_bncc_echo

    req = GenerationRequest(
        topico="Frações",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=1,
    )
    batch = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="e",
                resposta="r",
                explicacao="x",
                dificuldade=DificuldadeEnum.FACIL,
            )
        ],
        dificuldades=[DificuldadeEnum.FACIL],
    )
    out = attach_bncc_echo(batch, req)
    assert out.habilidades_bncc is None
    dumped = out.model_dump(exclude_none=True)
    assert "habilidades_bncc" not in dumped


def test_llm_parse_schema_excludes_bncc() -> None:
    """D-11: LlmExerciseBatch schema must not require BNCC fill."""
    from exercise_ai.models import LlmExerciseBatch

    schema = LlmExerciseBatch.model_json_schema()
    props = schema.get("properties", {})
    assert "habilidades_bncc" not in props
    assert "habilidade_bncc" not in props


def test_attach_bncc_echo_advanced_slot_union() -> None:
    """D-13: advanced per-slot codes → deterministic union echo."""
    from exercise_ai.models import Exercise, ExerciseBatch, ExerciseSpec, attach_bncc_echo

    req = GenerationRequest(
        topico="Frações",
        quantidade=3,
        itens=[
            ExerciseSpec(
                dificuldade=DificuldadeEnum.FACIL,
                habilidade_bncc=["EF06MA01", "EF06MA02"],
            ),
            ExerciseSpec(
                dificuldade=DificuldadeEnum.FACIL,
                habilidade_bncc=["EF06MA02"],
            ),
            ExerciseSpec(
                dificuldade=DificuldadeEnum.FACIL,
                habilidade_bncc=["EF06MA01"],
            ),
        ],
    )
    batch = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado=f"e{i}",
                resposta="r",
                explicacao="x",
                dificuldade=DificuldadeEnum.FACIL,
            )
            for i in range(3)
        ],
        dificuldades=[DificuldadeEnum.FACIL],
    )
    out = attach_bncc_echo(batch, req)
    assert out.habilidades_bncc == ["EF06MA01", "EF06MA02"]


def test_cli_habilidade_bncc_wired(tmp_path, monkeypatch) -> None:
    import exercise_ai.main as main_mod
    from unittest.mock import patch

    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    captured: dict = {}

    def fake_run(request, out_path, max_retries=None):
        captured["request"] = request

    with patch.object(main_mod, "run", side_effect=fake_run):
        main_mod.main(
            [
                "--out",
                str(tmp_path / "o.json"),
                "--habilidade-bncc",
                "EF06MA01,EF06MA02",
            ]
        )
    assert captured["request"].habilidade_bncc == ["EF06MA01", "EF06MA02"]


def test_cli_unknown_bncc_exits() -> None:
    import exercise_ai.main as main_mod
    from unittest.mock import patch
    import io
    import contextlib

    err = io.StringIO()
    with patch.object(main_mod, "run") as run_mock:
        with contextlib.redirect_stderr(err):
            with pytest.raises(SystemExit) as se:
                main_mod.main(
                    ["--out", "x.json", "--habilidade-bncc", "NOTREAL99"]
                )
    assert se.value.code == 2
    assert run_mock.call_count == 0
    assert "desconhecido" in err.getvalue().lower() or "NOTREAL99" in err.getvalue()


def test_cli_itens_json_advanced_path(tmp_path, monkeypatch) -> None:
    import json
    import exercise_ai.main as main_mod
    from unittest.mock import patch

    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    captured: dict = {}

    def fake_run(request, out_path, max_retries=None):
        captured["request"] = request

    payload = json.dumps(
        [
            {
                "dificuldade": "facil",
                "habilidade_bncc": ["EF06MA01", "EF06MA02"],
            },
            {"dificuldade": "facil", "habilidade_bncc": ["EF06MA01"]},
            {"dificuldade": "facil"},
        ]
    )
    with patch.object(main_mod, "run", side_effect=fake_run):
        main_mod.main(
            ["--out", str(tmp_path / "o.json"), "--itens-json", payload]
        )
    req = captured["request"]
    assert req.quantidade == 3
    assert req.itens is not None
    assert req.itens[0].habilidade_bncc == ["EF06MA01", "EF06MA02"]
    from exercise_ai.models import attach_bncc_echo, Exercise, ExerciseBatch

    batch = ExerciseBatch(
        exercicios=[
            Exercise(
                enunciado="e",
                resposta="r",
                explicacao="x",
                dificuldade=DificuldadeEnum.FACIL,
            )
            for _ in range(3)
        ],
        dificuldades=[DificuldadeEnum.FACIL],
    )
    assert attach_bncc_echo(batch, req).habilidades_bncc == [
        "EF06MA01",
        "EF06MA02",
    ]
