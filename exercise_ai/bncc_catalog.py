"""Embedded BNCC Matemática (EF/EM) membership catalog (Phase 26).

Runtime loads codes from ``exercise_ai/data/`` only — never ``.planning/``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_MAX_CODIGOS = 10
_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "bncc_matematica_codigos.json"


def catalog_path() -> Path:
    """Absolute path to the shipped codes-only embed (for tests / diagnostics)."""
    return _CATALOG_PATH


@lru_cache(maxsize=1)
def load_codigos() -> frozenset[str]:
    """Load unique ``codigo_bncc`` membership set from the embedded catalog."""
    path = catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"catálogo BNCC embutido ausente: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    codes = payload.get("codigo_bncc")
    if not isinstance(codes, list) or not codes:
        raise ValueError(f"catálogo BNCC inválido (codigo_bncc vazio): {path}")
    return frozenset(str(c).strip().upper() for c in codes if str(c).strip())


def normalize_codigo(raw: str) -> str:
    """Trim + uppercase a BNCC code (D-03)."""
    if not isinstance(raw, str):
        raise ValueError("código BNCC deve ser string")
    return raw.strip().upper()


def validate_codigos(raw_codes: list[str]) -> list[str]:
    """Normalize and validate a list of BNCC codes (D-03, D-08).

    Rejects empty entries, unknown codes, and lists longer than 10.
    Returns normalized codes preserving order (first occurrence wins on dups).
    """
    if not isinstance(raw_codes, list):
        raise ValueError("habilidade_bncc deve ser uma lista de códigos")
    if len(raw_codes) > _MAX_CODIGOS:
        raise ValueError(
            f"habilidade_bncc excede o limite de {_MAX_CODIGOS} códigos "
            f"(recebido: {len(raw_codes)})"
        )

    catalog = load_codigos()
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_codes:
        if not isinstance(raw, str):
            raise ValueError("código BNCC deve ser string")
        code = normalize_codigo(raw)
        if not code:
            raise ValueError("código BNCC vazio não é permitido")
        if code not in catalog:
            raise ValueError(f"código BNCC desconhecido: {code}")
        if code in seen:
            continue
        seen.add(code)
        normalized.append(code)
    return normalized
