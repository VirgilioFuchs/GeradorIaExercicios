"""Deprecated short-lived bridge for legacy lab / flat-import muscle memory.

Prefer the installed package path::

    from exercise_ai.service import generate_batch

Removing this shim without a SemVer MAJOR is out of policy for v2.7.0 (D-03/D-04).
"""

from __future__ import annotations

import warnings

from exercise_ai.models import ExerciseBatch, GenerationRequest
from exercise_ai.service import (
    ConfigError,
    GenerationFailedError,
    InvalidRequestError,
    generate_batch,
)

warnings.warn(
    "exercise_ai.compat_shim is deprecated; import from exercise_ai.service "
    "(and exercise_ai.models) instead. Shim retained for SemVer MINOR through v2.7.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ConfigError",
    "ExerciseBatch",
    "GenerationFailedError",
    "GenerationRequest",
    "InvalidRequestError",
    "generate_batch",
]
