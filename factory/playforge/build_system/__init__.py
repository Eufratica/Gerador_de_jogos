"""Pacote de Build & Distribuicao (Fase 10)."""

from .builder import BuildManager
from .schemas import (
    BUILD_MANIFEST_SCHEMA_VERSION,
    SUPPORTED_BUILD_TARGETS,
    BuildError,
    BuildIntegrityError,
    BuildPrerequisiteError,
    BuildTargetUnavailableError,
    ReleaseApprovalRequiredError,
)

__all__ = [
    "BUILD_MANIFEST_SCHEMA_VERSION",
    "BuildError",
    "BuildIntegrityError",
    "BuildManager",
    "BuildPrerequisiteError",
    "BuildTargetUnavailableError",
    "ReleaseApprovalRequiredError",
    "SUPPORTED_BUILD_TARGETS",
]
