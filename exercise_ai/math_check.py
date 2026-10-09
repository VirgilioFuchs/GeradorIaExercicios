"""Math consistency checks for exercise batches (Phase 6 + Phase 27 BNCC).

Stdlib-only heuristics for arithmetic and ax+b=c, dispatched by BNCC skill
codes from ``batch.habilidades_bncc``. Curricular empty/missing BNCC fails.
"""

from __future__ import annotations

import json
import re
import sys
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

from exercise_ai.models import Exercise, ExerciseBatch

_RULES_PATH = Path(__file__).resolve().parent / "data" / "math_check_bncc_rules.json"

_uninterpretable: list[dict[str, Any]] = []
_last_inconsistencies: list[dict[str, Any]] = []

_RAISE_MAX_LEN = 120

_ARITH_EXPR = re.compile(
    r"(?P<a>\d+(?:[.,]\d+)?)\s*"
    r"(?P<op>[+\-−*/÷×xX])\s*"
    r"(?P<b>\d+(?:[.,]\d+)?)"
    r"(?:\s*=\s*\??|\s*\?)?\s*$",
    re.IGNORECASE,
)

# ax + b = c  (integers; optional coeff defaults to 1; a ≠ 0)
_LINEAR_EQ = re.compile(
    r"^\s*(?P<a>-?\d*)\s*[xX]\s*"
    r"(?P<sign>[+\-−])\s*"
    r"(?P<b>\d+)\s*"
    r"=\s*(?P<c>-?\d+)\s*$",
)

_ANSWER_NUM = re.compile(r"^-?\d+(?:[.,]\d+)?$")

_OUT_OF_SCOPE = re.compile(
    r"(√|sqrt|sistema|inequa|≥|≤|≠|geometr|triâng|triang|área|area|ângulo|angulo"
    r"|frac[cç]|"
    r"\d+\s*/\s*\d+\s*[+\-−*/÷×]|"  # chained fraction ops
    r"[a-zA-Z]\s*/\s*[a-zA-Z])",
    re.IGNORECASE,
)

# Out-of-profile for mapped 1º-grau univariado pack (D-08).
_OUT_OF_PROFILE = re.compile(
    r"(√|sqrt|∛|sistema|inequa|≥|≤|≠|geometr|triâng|triang|área|area|ângulo|angulo"
    r"|cartes|coordenad|"
    r"[xX]\s*\^\s*2|[xX]²|[xX]\s*\*\s*[xX]|"
    r"[yY]\s*=|"
    r"\(\s*-?\d+\s*,\s*-?\d+\s*\))",
    re.IGNORECASE,
)

_VAR_UNKNOWN = re.compile(r"vari[aá]vel|inc[oó]gnita|[xX]\b", re.IGNORECASE)

_NUM_LITERAL = re.compile(r"-?\d+(?:[.,]\d+)?")


def drain_uninterpretable_records() -> list[dict[str, Any]]:
    """Return and clear accumulated uninterpretable records (D-02, D-08)."""
    records = list(_uninterpretable)
    _uninterpretable.clear()
    return records


def drain_inconsistency_records() -> list[dict[str, Any]]:
    """Return and clear last clear-inconsistency records (for postmortem)."""
    records = list(_last_inconsistencies)
    _last_inconsistencies.clear()
    return records


def clear_math_buffers() -> None:
    """Clear uninterpretable + inconsistency buffers (success path)."""
    _uninterpretable.clear()
    _last_inconsistencies.clear()


def _record_uninterpretable(index: int, ex: Exercise, reason: str = "uninterpretable") -> None:
    _uninterpretable.append(
        {
            "index": index,
            "enunciado": (ex.enunciado or "")[:80],
            "resposta": (ex.resposta or "")[:80],
            "reason": reason,
        }
    )


def _parse_number(raw: str) -> Decimal | None:
    text = raw.strip().replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _normalize_op(op: str) -> str | None:
    if op == "+":
        return "+"
    if op in ("-", "−"):
        return "-"
    if op in ("*", "×", "x", "X"):
        return "*"
    if op in ("/", "÷"):
        return "/"
    return None


def _compute(a: Decimal, op: str, b: Decimal) -> Decimal | None:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            return None
        return a / b
    return None


def _numbers_equal(expected: Decimal, obtained: Decimal) -> bool:
    return abs(expected - obtained) <= Decimal("0.0001")


def _parse_answer(resposta: str) -> Decimal | None:
    ans_clean = resposta.strip().replace(" ", "")
    if not _ANSWER_NUM.match(ans_clean):
        return None
    return _parse_number(ans_clean)


def _is_out_of_scope(enunciado: str) -> bool:
    en = enunciado.strip()
    if _OUT_OF_SCOPE.search(en):
        return True
    # Radical symbol alone
    if "√" in en or "∛" in en:
        return True
    # Inequality operators
    if any(ch in en for ch in (">", "<", "≥", "≤", "≠")):
        return True
    return False


def _try_linear(enunciado: str, resposta: str) -> tuple[str, Decimal | None, Decimal | None]:
    """Return (status, expected_x, obtained) for ax+b=c."""
    m = _LINEAR_EQ.match(enunciado.strip())
    if m is None:
        return "skip", None, None

    a_raw = m.group("a")
    if a_raw in ("", "+"):
        a = 1
    elif a_raw == "-":
        a = -1
    else:
        a = int(a_raw)
    if a == 0:
        return "uninterpretable", None, None

    sign = m.group("sign")
    b = int(m.group("b"))
    if sign in ("-", "−"):
        b = -b
    c = int(m.group("c"))

    # ax + b = c  →  x = (c - b) / a
    if c - b != (c - b) // a * a:
        # Non-integer exact division still OK if answer matches Decimal
        pass
    expected = Decimal(c - b) / Decimal(a)
    obtained = _parse_answer(resposta)
    if obtained is None:
        return "uninterpretable", None, None
    if _numbers_equal(expected, obtained):
        return "ok", expected, obtained
    return "inconsistent", expected, obtained


def _try_arithmetic(enunciado: str, resposta: str) -> tuple[str, Decimal | None, Decimal | None]:
    """Return (status, expected, obtained) for binary arithmetic."""
    en = enunciado.strip()
    m = _ARITH_EXPR.search(en)
    if m is None:
        return "skip", None, None

    # Require the match to cover essentially the whole enunciado (known template).
    matched = m.group(0).strip()
    en_compact = re.sub(r"\s+", " ", en).strip()
    matched_compact = re.sub(r"\s+", " ", matched).strip()
    if en_compact != matched_compact and not en_compact.startswith(matched_compact):
        # Allow leading filler only if remaining is empty after match at end
        if not en_compact.endswith(matched_compact):
            return "skip", None, None
        # Reject if substantial non-math prefix (e.g. "Simplifique √16 / 2")
        prefix = en_compact[: -len(matched_compact)].strip()
        if prefix and not re.fullmatch(r"[=?]*", prefix):
            if re.search(r"[A-Za-zÀ-ÿ√]", prefix):
                return "skip", None, None

    a = _parse_number(m.group("a"))
    b = _parse_number(m.group("b"))
    op = _normalize_op(m.group("op"))
    if a is None or b is None or op is None:
        return "uninterpretable", None, None

    # Bare "x" as multiply only when not part of equation variable (handled by linear first)
    expected = _compute(a, op, b)
    if expected is None:
        return "uninterpretable", None, None

    obtained = _parse_answer(resposta)
    if obtained is None:
        return "uninterpretable", None, None

    if _numbers_equal(expected, obtained):
        return "ok", expected, obtained
    return "inconsistent", expected, obtained


def _classify(ex: Exercise) -> tuple[str, str, Decimal | None, Decimal | None]:
    """Return (status, tipo, expected, obtained)."""
    en = (ex.enunciado or "").strip()
    ans = (ex.resposta or "").strip()
    if not en or not ans:
        return "uninterpretable", "", None, None

    if _is_out_of_scope(en):
        return "uninterpretable", "", None, None

    status, expected, obtained = _try_linear(en, ans)
    if status != "skip":
        return status, "ax+b=c", expected, obtained

    status, expected, obtained = _try_arithmetic(en, ans)
    if status != "skip":
        return status, "aritmetica", expected, obtained

    return "uninterpretable", "", None, None


# Domain restrictiveness: N ⊂ Z ⊂ Q ⊂ IRR ⊂ R (most restrictive wins on union).
_DOMAIN_RANK = {"N": 0, "Z": 1, "Q": 2, "IRR": 3, "R": 4}


@lru_cache(maxsize=1)
def load_bncc_rules() -> dict[str, Any]:
    """Load versioned exact-code → rules map from package data (stdlib json)."""
    path = _RULES_PATH
    if not path.is_file():
        raise FileNotFoundError(f"mapa de regras BNCC ausente: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    codes = payload.get("codes")
    if not isinstance(codes, dict) or not codes:
        raise ValueError(f"mapa de regras BNCC inválido (codes vazio): {path}")
    return payload


def _batch_bncc_codes(batch: ExerciseBatch) -> list[str]:
    """Return non-empty BNCC echo codes or raise (D-15)."""
    codes = batch.habilidades_bncc
    if not codes:
        raise ValueError(
            "BNCC curricular obrigatório: habilidades_bncc ausente ou vazio"
        )
    return list(codes)


def resolve_bncc_rule_union(codes: list[str]) -> tuple[list[str], str, list[str]]:
    """Exact-code dispatch: union of rules; most restrictive domain (D-01..D-04, D-12).

    Returns (ordered unique rule_ids, domain, codes).
    Raises ValueError if any code lacks a typed map entry.
    Domain union uses most restrictive: N ⊂ Z ⊂ Q ⊂ IRR ⊂ R.
    """
    payload = load_bncc_rules()
    code_map: dict[str, Any] = payload["codes"]
    missing = [c for c in codes if c not in code_map]
    if missing:
        raise ValueError(
            f"código BNCC sem regra tipada no mapa: {', '.join(missing)}"
        )

    rule_ids: list[str] = []
    seen_rules: set[str] = set()
    domain = "R"
    best_rank = _DOMAIN_RANK["R"]
    for code in codes:
        entry = code_map[code]
        for rid in entry.get("rules") or []:
            rid_s = str(rid)
            if rid_s not in seen_rules:
                seen_rules.add(rid_s)
                rule_ids.append(rid_s)
        d = str(entry.get("domain") or "R")
        rank = _DOMAIN_RANK.get(d, _DOMAIN_RANK["R"])
        if rank < best_rank:
            best_rank = rank
            domain = d
    return rule_ids, domain, list(codes)


def _is_out_of_profile(enunciado: str) -> bool:
    en = enunciado.strip()
    if _OUT_OF_PROFILE.search(en):
        return True
    if any(ch in en for ch in (">", "<", "≥", "≤", "≠")):
        return True
    return False


def _is_integer(n: Decimal) -> bool:
    return n == n.to_integral_value()


def _number_in_domain(n: Decimal, domain: str) -> bool:
    """Year-aware domain ladder (D-05): N ⊂ Z ⊂ Q ⊂ IRR ⊂ R."""
    if domain == "N":
        return _is_integer(n) and n >= 0
    if domain == "Z":
        return _is_integer(n)
    if domain == "Q":
        return True  # Decimal literals are rational
    if domain in ("IRR", "R"):
        return True
    return True


def _extract_literals(enunciado: str, resposta: str) -> list[Decimal]:
    values: list[Decimal] = []
    for raw in _NUM_LITERAL.findall(enunciado or ""):
        parsed = _parse_number(raw)
        if parsed is not None:
            values.append(parsed)
    ans = _parse_answer(resposta or "")
    if ans is not None:
        values.append(ans)
    return values


def _literals_in_domain(enunciado: str, resposta: str, domain: str) -> bool:
    literals = _extract_literals(enunciado, resposta)
    if not literals:
        return True
    return all(_number_in_domain(n, domain) for n in literals)


def _evidence(
    index: int,
    ex: Exercise,
    *,
    reason: str,
    codes: list[str],
    rule_ids: list[str],
    rule_id: str | None = None,
    tipo: str = "",
    expected: Decimal | None = None,
    obtained: Decimal | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "index": index,
        "enunciado": (ex.enunciado or "")[:80],
        "resposta": (ex.resposta or "")[:80],
        "reason": reason,
        "codigo_bncc": list(codes),
        "rule_id": rule_id if rule_id is not None else list(rule_ids),
    }
    if tipo:
        detail["tipo"] = tipo
    if expected is not None:
        detail["esperado"] = str(expected)
    if obtained is not None:
        detail["obtido"] = str(obtained)
    return detail


def _check_tipado_exercise(
    ex: Exercise,
    *,
    rule_ids: list[str],
    domain: str,
) -> tuple[str, str, Decimal | None, Decimal | None, str | None]:
    """Return (status, tipo, expected, obtained, rule_id_for_fail).

    status: ok | inconsistent | out_of_profile | tipado_unreadable | domain
    """
    en = (ex.enunciado or "").strip()
    ans = (ex.resposta or "").strip()
    if not en or not ans:
        return "tipado_unreadable", "", None, None, "linear_univariate"

    if "profile_1grau" in rule_ids and _is_out_of_profile(en):
        return "out_of_profile", "", None, None, "profile_1grau"

    if "linear_univariate" in rule_ids:
        status, expected, obtained = _try_linear(en, ans)
        if status == "ok":
            if "variable_vs_unknown" in rule_ids and not _VAR_UNKNOWN.search(en):
                return "tipado_unreadable", "ax+b=c", None, None, "variable_vs_unknown"
            if "domain_literals" in rule_ids and not _literals_in_domain(en, ans, domain):
                return "domain", "ax+b=c", expected, obtained, "domain_literals"
            return "ok", "ax+b=c", expected, obtained, None
        if status == "inconsistent":
            return "inconsistent", "ax+b=c", expected, obtained, "linear_univariate"
        # skip or uninterpretable under linear pack → tipado fail (D-09)
        return "tipado_unreadable", "", None, None, "linear_univariate"

    # Tipado pack without linear: fall back to legacy classify, but fail closed.
    status, tipo, expected, obtained = _classify(ex)
    if status == "ok":
        if "domain_literals" in rule_ids and not _literals_in_domain(en, ans, domain):
            return "domain", tipo, expected, obtained, "domain_literals"
        return "ok", tipo, expected, obtained, None
    if status == "inconsistent":
        return "inconsistent", tipo, expected, obtained, rule_ids[0] if rule_ids else None
    return "tipado_unreadable", "", None, None, rule_ids[0] if rule_ids else None


def check_math_batch(batch: ExerciseBatch) -> None:
    """Raise ValueError on curricular math / profile / domain failures.

    Requires non-empty ``batch.habilidades_bncc`` (D-15). Unmapped curricular
    codes fail the entire batch (D-04, D-12). Union of rule packs applies to
    each exercise (D-02, D-14). Tipado unreadable and out-of-profile fail (D-08, D-09).
    """
    global _last_inconsistencies
    clear_math_buffers()
    codes = _batch_bncc_codes(batch)
    rule_ids, domain, codes = resolve_bncc_rule_union(codes)
    inconsistencies: list[dict[str, Any]] = []

    for i, ex in enumerate(batch.exercicios):
        status, tipo, expected, obtained, fail_rule = _check_tipado_exercise(
            ex, rule_ids=rule_ids, domain=domain
        )
        if status == "ok":
            continue

        reason = status if status != "inconsistent" else "inconsistent"
        detail = _evidence(
            i,
            ex,
            reason=reason,
            codes=codes,
            rule_ids=rule_ids,
            rule_id=fail_rule,
            tipo=tipo,
            expected=expected,
            obtained=obtained,
        )
        inconsistencies.append(detail)
        print(
            f"[MATH] índice={i} reason={reason} rule_id={fail_rule} "
            f"tipo={tipo} esperado={expected} obtido={obtained}",
            file=sys.stderr,
        )

    _last_inconsistencies = list(inconsistencies)

    if not inconsistencies:
        return

    indices = ", ".join(str(d["index"]) for d in inconsistencies)
    user_message = f"inconsistência matemática nos exercícios: {indices}"
    if len(user_message) > _RAISE_MAX_LEN:
        user_message = user_message[: _RAISE_MAX_LEN - 1] + "…"
    raise ValueError(user_message)
