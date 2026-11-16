"""Game Generator (MVP) da PlayForge Factory: geracao isolada, verificacao e empacotamento."""
from __future__ import annotations

from factory.playforge.generator.game_generator import GameGenerator
from factory.playforge.generator.schemas import (
    GENERATION_MANIFEST_SCHEMA_VERSION,
    GenerationConflictError,
    GenerationVerificationError,
    GeneratorError,
)

__all__ = [
    "GENERATION_MANIFEST_SCHEMA_VERSION",
    "GameGenerator",
    "GenerationConflictError",
    "GenerationVerificationError",
    "GeneratorError",
]
