"""Bounded regeneration after retriable validation / invalid LLM response failures.

Phase 6 hook: math failures (MATH-02) reuse ``generate_validated_batch``
(raise a retriable ``ValueError`` from validation, or ``RuntimeError`` with
``retriable=True``) — do not invent a second retry path.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exercise_ai.models import ExerciseBatch, GenerationRequest, attach_bncc_echo, verify_plan_echo
from exercise_ai.generator import generate_exercises
from exercise_ai.validator import validate_exercise_batch
from exercise_ai.math_check import (
    clear_math_buffers,
    drain_inconsistency_records,
    drain_uninterpretable_records,
)
from exercise_ai.output_paths import DEFAULT_POSTMORTEM_PATH
from exercise_ai.token_usage import get_collector

_ALLOWED = frozenset({0, 1, 2, 3})
_DEFAULT = 1
POSTMORTEM_SCHEMA_VERSION = "1"

# Injectable for tests; default under exercicios-gerados/fail/postmortem/.
# Per-fail JSON siblings live in the same parent directory as this JSONL index.
POSTMORTEM_PATH: Path = DEFAULT_POSTMORTEM_PATH


def resolve_max_retries(cli_value: int | None) -> int:
    """Resolve regenerations after first try: CLI > RELY_MAX_RETRIES > 1 (D-01..D-04)."""
    from exercise_ai.service import ConfigError

    if cli_value is not None:
        n = cli_value
    else:
        raw = os.getenv("RELY_MAX_RETRIES", "").strip()
        if not raw:
            n = _DEFAULT
        else:
            try:
                n = int(raw)
            except ValueError as exc:
                raise ConfigError(
                    f"max-retries inválido '{raw}': use um inteiro 0, 1, 2 ou 3.",
                    kind="invalid_retries",
                ) from exc
    if n not in _ALLOWED:
        raise ConfigError(
            f"max-retries inválido '{n}': use um inteiro 0, 1, 2 ou 3.",
            kind="invalid_retries",
        )
    return n


def is_permanent_api_error(exc: BaseException) -> bool:
    """True when mappers marked the error non-retriable (auth/timeout/rate/conn)."""
    return getattr(exc, "retriable", None) is False


def is_retriable_invalid_response(exc: BaseException) -> bool:
    """True for invalid LLM response edges marked retriable=True (D-05, D-19)."""
    return getattr(exc, "retriable", None) is True


def _allowlisted_exercise_entry(rec: dict[str, Any]) -> dict[str, Any]:
    """Map a drain record to allowlisted exercise_index fields (D-02 — no prose)."""
    entry: dict[str, Any] = {
        "index": rec.get("index"),
        "error_kind": rec.get("reason") or rec.get("error_kind"),
        "rule_id": rec.get("rule_id"),
    }
    for key in ("tipo", "esperado", "obtido"):
        val = rec.get(key)
        if val is not None and val != "":
            entry[key] = val
    return entry


def build_postmortem_record(
    request: GenerationRequest | None = None,
    *,
    attempts: int | None = None,
    provider: str | None = None,
    error_kind: str | None = None,
    max_retries: int | None = None,
    reasoning_effort: str | None = None,
    total_ms: int | None = None,
    exercise_events: list[dict[str, Any]] | None = None,
    template_id: str | None = None,
    template_version: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build schema_version=1 allowlisted postmortem envelope (D-01..D-04)."""
    materia: str | None = None
    topico: str | None = None
    dificuldade: str | None = None
    plano: dict[str, Any] | None = None
    dificuldades: list[str] | None = None
    quantidade: int | None = None
    habilidades_bncc: list[str] | None = None

    if request is not None:
        materia = request.materia
        topico = request.topico
        quantidade = request.quantidade
        if request.dificuldade is not None:
            dificuldade = request.dificuldade.value
        if request.plano is not None:
            plano = request.plano.model_dump()
        if request.dificuldades is not None:
            dificuldades = [d.value for d in request.dificuldades]
        if request.habilidade_bncc is not None:
            habilidades_bncc = list(request.habilidade_bncc)

    return {
        "schema_version": POSTMORTEM_SCHEMA_VERSION,
        "materia": materia,
        "topico": topico,
        "dificuldade": dificuldade,
        "plano": plano,
        "dificuldades": dificuldades,
        "quantidade": quantidade,
        "attempts": attempts,
        "provider": provider,
        "error_kind": error_kind,
        "exercise_index": list(exercise_events) if exercise_events is not None else [],
        "habilidades_bncc": habilidades_bncc,
        "template_id": template_id,
        "template_version": template_version,
        "max_retries": max_retries,
        "reasoning_effort": reasoning_effort,
        "timestamp": timestamp,
        "total_ms": total_ms,
    }


def _unique_postmortem_json_path(directory: Path, stamp: str) -> Path:
    """UTC stamp filename; same-second collision → -a/-b or 4-hex (D-07)."""
    candidate = directory / f"math_postmortem-{stamp}.json"
    if not candidate.exists():
        return candidate
    for suffix in "abcdefghijklmnopqrstuvwxyz":
        alt = directory / f"math_postmortem-{stamp}-{suffix}.json"
        if not alt.exists():
            return alt
    return directory / f"math_postmortem-{stamp}-{secrets.token_hex(2)}.json"


def _write_postmortem(
    path: Path,
    *,
    request: GenerationRequest | None = None,
    attempts: int | None = None,
    provider: str | None = None,
    error_kind: str | None = None,
    max_retries: int | None = None,
    reasoning_effort: str | None = None,
    total_ms: int | None = None,
    template_id: str | None = None,
    template_version: str | None = None,
) -> Path:
    """Write indented JSON + append JSONL pointer (D-05..D-08; LOG-02).

    ``path`` is the injectable JSONL index (``POSTMORTEM_PATH``). Per-fail JSON
    files are siblings in the same directory. Pointer ``path`` is the JSON
    filename relative to that directory. Returns the JSON path written.
    """
    raw = drain_inconsistency_records() + drain_uninterpretable_records()
    exercise_index = [_allowlisted_exercise_entry(r) for r in raw]

    now = datetime.now(timezone.utc)
    ts_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    record = build_postmortem_record(
        request,
        attempts=attempts,
        provider=provider,
        error_kind=error_kind,
        max_retries=max_retries,
        reasoning_effort=reasoning_effort,
        total_ms=total_ms,
        exercise_events=exercise_index,
        template_id=template_id,
        template_version=template_version,
        timestamp=ts_iso,
    )

    postmortem_dir = path.parent
    postmortem_dir.mkdir(parents=True, exist_ok=True)
    json_path = _unique_postmortem_json_path(postmortem_dir, stamp)
    json_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    pointer: dict[str, Any] = {
        "timestamp": ts_iso,
        "schema_version": POSTMORTEM_SCHEMA_VERSION,
        "path": json_path.name,
    }
    if error_kind is not None:
        pointer["error_kind"] = error_kind

    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(pointer, ensure_ascii=False) + "\n")

    return json_path


def generate_validated_batch(
    request: GenerationRequest,
    max_retries: int,
) -> ExerciseBatch:
    """Generate → validate with bounded regenerations (Phase 5 + Phase 6 hook).

    Same ``request`` (hence same prompt) on every attempt. Only validator
    ``ValueError`` and ``RuntimeError`` with ``retriable=True`` regenerate.
    Permanent API errors and unmarked RuntimeError fail through immediately.
    Config ``ValueError`` from generate (missing keys) is never retried.
    """
    t0 = time.perf_counter()
    calls = 0
    last_err: BaseException | None = None

    try:
        for attempt in range(0, max_retries + 1):
            if attempt == 0:
                print("Gerando…", file=sys.stderr)
            else:
                print(f"{attempt}ª Regeneração", file=sys.stderr)
                print("Gerando…", file=sys.stderr)

            try:
                calls += 1
                batch = generate_exercises(request)
            except RuntimeError as exc:
                last_err = exc
                if is_permanent_api_error(exc):
                    raise
                if is_retriable_invalid_response(exc) and attempt < max_retries:
                    get_collector().retag_last(
                        "attempt",
                        error_kind=type(exc).__name__,
                    )
                    continue
                raise

            print("Validando…", file=sys.stderr)
            try:
                validated = validate_exercise_batch(batch, request)
                verify_plan_echo(validated, request)
                validated = attach_bncc_echo(validated, request)
                clear_math_buffers()
                return validated
            except ValueError as exc:
                last_err = exc
                if attempt < max_retries:
                    get_collector().retag_last(
                        "attempt",
                        error_kind="validation",
                    )
                    continue
                # Final failure: postmortem + optional exhaustion prefix (D-08, D-13)
                get_collector().retag_last(
                    "error",
                    error_kind="validation",
                )
                reason = str(exc)
                from exercise_ai.service import InvalidRequestError

                if max_retries > 0:
                    raise InvalidRequestError(
                        f"após {max_retries} regenerações: {reason}",
                        kind="validation_exhausted",
                    ) from exc
                raise InvalidRequestError(
                    reason, kind="validation_exhausted"
                ) from exc

        assert last_err is not None
        raise last_err
    finally:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        print(
            f"duração total_ms={elapsed_ms} chamadas={calls}",
            file=sys.stderr,
        )
