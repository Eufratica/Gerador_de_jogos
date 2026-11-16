"""Game Specification Engine da PlayForge Factory (Fase 3)."""
from .generator import SpecificationGenerator
from .schemas import GDD_SCHEMA_VERSION, SPEC_SCHEMA_VERSION
from .validator import (
    SchemaCompatibilityError,
    SpecificationValidator,
    ValidationError,
    compute_spec_digest,
)

__all__ = [
    "SPEC_SCHEMA_VERSION",
    "GDD_SCHEMA_VERSION",
    "SpecificationValidator",
    "SpecificationGenerator",
    "ValidationError",
    "SchemaCompatibilityError",
    "compute_spec_digest",
]
