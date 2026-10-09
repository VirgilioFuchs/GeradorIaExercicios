"""Offline tracer: editable install imports generate_batch + package data resolve.

No network / no live LLM (D-06).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import exercise_ai.aig_axb as aig_axb
from exercise_ai.bncc_catalog import catalog_path, load_codigos
from exercise_ai.models import ExerciseBatch, GenerationRequest
from exercise_ai.service import generate_batch


def test_generate_batch_importable_from_package() -> None:
    assert callable(generate_batch)


def test_generate_batch_signature_unchanged() -> None:
    sig = inspect.signature(generate_batch)
    params = list(sig.parameters)
    assert params == ["request"]
    assert sig.return_annotation is ExerciseBatch or sig.return_annotation == "ExerciseBatch"


def test_bncc_catalog_resolves_after_install() -> None:
    path = catalog_path()
    assert path.is_file(), f"BNCC catalog missing: {path}"
    codes = load_codigos()
    assert len(codes) > 0
    assert "EF06MA01" in codes or any(c.startswith("EF") for c in codes)


def test_aig_item_model_json_resolves() -> None:
    path = (
        Path(aig_axb.__file__).resolve().parent
        / "data"
        / "item_models"
        / "ax_plus_b_eq_c.v1.json"
    )
    assert path.is_file(), f"AIG item-model JSON missing: {path}"


def test_generation_request_type_available() -> None:
    assert GenerationRequest is not None
