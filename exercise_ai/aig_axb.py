"""Parametric AIG for family a*x+b=c (Phase 28) — generator, not the judge.

Loads the approved item-model JSON, instantiates Polar-Mat narrow-domain
params, and renders Exercise/ExerciseBatch with 0 LLM calls. Mathematical
authority remains Phase 27 ``check_math_batch`` (separate module).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exercise_ai.models import (
    DificuldadeEnum,
    Exercise,
    ExerciseBatch,
    GenerationRequest,
    resolve_bncc_codes,
)

_MODEL_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "item_models"
    / "ax_plus_b_eq_c.v1.json"
)

# Polar-Mat §6 narrow domain (D-05); mirrored in the approved model file.
A_MIN, A_MAX = 2, 10
B_MIN, B_MAX = 1, 20
S_MIN, S_MAX = 1, 20

_A_SPAN = A_MAX - A_MIN + 1
_B_SPAN = B_MAX - B_MIN + 1
_S_SPAN = S_MAX - S_MIN + 1
_DOMAIN_SIZE = _A_SPAN * _B_SPAN * _S_SPAN  # 3600

_REQUIRED_KEYS = (
    "id",
    "version",
    "params",
    "habilidades_bncc",
    "generator_id",
    "form",
)


class ItemModelError(ValueError):
    """Invalid or incomplete approved item-model contract."""


class DomainError(ValueError):
    """Parameters outside the approved Polar-Mat narrow domain."""


def _validate_contract(payload: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in _REQUIRED_KEYS if k not in payload]
    if missing:
        raise ItemModelError(
            f"item-model contrato incompleto: faltam {', '.join(missing)}"
        )
    if not payload.get("version"):
        raise ItemModelError("item-model exige version imutável não-vazia")
    if not payload.get("id"):
        raise ItemModelError("item-model exige id não-vazio")
    form = payload.get("form")
    if form != "a*x+b=c":
        raise ItemModelError(f"form não suportado neste gerador: {form!r}")
    bncc = payload.get("habilidades_bncc")
    if not isinstance(bncc, list) or not bncc:
        raise ItemModelError("habilidades_bncc deve ser lista não-vazia")
    if "EF07MA18" not in bncc:
        raise ItemModelError("família exige EF07MA18 no conjunto BNCC aprovado")
    params = payload.get("params")
    if not isinstance(params, dict):
        raise ItemModelError("params deve ser objeto")
    for name in ("a", "b", "s"):
        if name not in params:
            raise ItemModelError(f"params faltando intervalo para {name}")
    return payload


def load_item_model(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the approved ax+b=c item-model JSON (stdlib only)."""
    model_path = path if path is not None else _MODEL_PATH
    if not model_path.is_file():
        raise ItemModelError(f"item-model ausente: {model_path}")
    try:
        payload = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ItemModelError(f"item-model JSON inválido: {exc}") from exc
    if not isinstance(payload, dict):
        raise ItemModelError("item-model raiz deve ser objeto JSON")
    return _validate_contract(payload)


def family_bncc_codes(model: dict[str, Any] | None = None) -> frozenset[str]:
    """Approved BNCC set for the pilot family (coverage intersection)."""
    contract = model if model is not None else load_item_model()
    return frozenset(str(c) for c in contract["habilidades_bncc"])


def is_aig_covered(
    request: GenerationRequest,
    *,
    model: dict[str, Any] | None = None,
) -> bool:
    """D-10: covered when request BNCC ∩ family codes is non-empty.

    Pilot form/profile = curricular intersection with the single algebraic
    family (no topic NLP classifier). Prefer fail-open to LLM when no
    curricular codes resolve.
    """
    codes = resolve_bncc_codes(request)
    if not codes:
        return False
    return not family_bncc_codes(model).isdisjoint(codes)


def _nth_domain_params(n: int) -> tuple[int, int, int]:
    """Deterministic (a,b,s) from domain index (lex a→b→s, wraps at 3600)."""
    idx = n % _DOMAIN_SIZE
    a_i = idx // (_B_SPAN * _S_SPAN)
    rem = idx % (_B_SPAN * _S_SPAN)
    b_i = rem // _S_SPAN
    s_i = rem % _S_SPAN
    return A_MIN + a_i, B_MIN + b_i, S_MIN + s_i


def validate_params(a: int, b: int, s: int) -> None:
    """Reject out-of-domain or degenerate coefficients (G1 domínio / unicidade)."""
    if not isinstance(a, int) or isinstance(a, bool):
        raise DomainError(f"a deve ser int; obtido {type(a).__name__}")
    if not isinstance(b, int) or isinstance(b, bool):
        raise DomainError(f"b deve ser int; obtido {type(b).__name__}")
    if not isinstance(s, int) or isinstance(s, bool):
        raise DomainError(f"s deve ser int; obtido {type(s).__name__}")
    if a == 0:
        raise DomainError("coeficiente a=0 degenera a família (unicidade)")
    if not (A_MIN <= a <= A_MAX):
        raise DomainError(f"a fora do domínio [{A_MIN},{A_MAX}]: {a}")
    if not (B_MIN <= b <= B_MAX):
        raise DomainError(f"b fora do domínio [{B_MIN},{B_MAX}]: {b}")
    if not (S_MIN <= s <= S_MAX):
        raise DomainError(f"s fora do domínio [{S_MIN},{S_MAX}]: {s}")


def _render_c(a: int, b: int, s: int) -> int:
    """Compute c for rendering only — not the mathematical judge (AIG-03)."""
    return a * s + b


def render_exercise(
    a: int,
    b: int,
    s: int,
    *,
    dificuldade: DificuldadeEnum = DificuldadeEnum.FACIL,
) -> Exercise:
    """Render one algebraic item; caller must have validated domain."""
    c = _render_c(a, b, s)
    enunciado = f"{a}x + {b} = {c}"
    resposta = str(s)
    rhs = c - b
    explicacao = (
        f"Subtraia {b} dos dois lados: {a}x = {rhs}. "
        f"Divida por {a}: x = {s}."
    )
    return Exercise(
        enunciado=enunciado,
        resposta=resposta,
        explicacao=explicacao,
        dificuldade=dificuldade,
    )


def instantiate(
    a: int,
    b: int,
    s: int,
    *,
    model: dict[str, Any] | None = None,
    dificuldade: DificuldadeEnum = DificuldadeEnum.FACIL,
) -> ExerciseBatch:
    """Build ExerciseBatch from narrow-domain params (0 LLM).

    Sets ``habilidades_bncc`` from the approved family codes so Phase 27
    ``check_math_batch`` can judge the emitted payload independently.
    """
    validate_params(a, b, s)
    contract = model if model is not None else load_item_model()
    exercise = render_exercise(a, b, s, dificuldade=dificuldade)
    return ExerciseBatch(
        exercicios=[exercise],
        dificuldades=[dificuldade],
        habilidades_bncc=list(contract["habilidades_bncc"]),
    )


def instantiate_for_request(
    request: GenerationRequest,
    *,
    model: dict[str, Any] | None = None,
) -> ExerciseBatch:
    """Instantiate ``quantidade`` exercises deterministically (0 LLM).

    Params walk the Polar-Mat domain in lex order a→b→s starting at index 0.
    Difficulties follow ``request.itens_ordenados``. Does not call the judge.
    Attaches approved ``template_id`` / ``version`` (pipeline authority, D-04).
    """
    contract = model if model is not None else load_item_model()
    specs = request.itens_ordenados
    exercises: list[Exercise] = []
    for i, spec in enumerate(specs):
        a, b, s = _nth_domain_params(i)
        validate_params(a, b, s)
        exercises.append(
            render_exercise(a, b, s, dificuldade=spec.dificuldade)
        )
    dificuldades = list(request.dificuldades or [specs[0].dificuldade])
    return ExerciseBatch(
        exercicios=exercises,
        dificuldades=dificuldades,
        habilidades_bncc=list(contract["habilidades_bncc"]),
        template_id=str(contract["id"]),
        version=str(contract["version"]),
    )
