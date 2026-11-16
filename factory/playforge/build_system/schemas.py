"""Contratos e excecoes do Build Manager multi-plataforma (Fase 10)."""
from __future__ import annotations

import re

from factory.playforge.models import FactoryError

BUILD_MANIFEST_SCHEMA_VERSION = 1

SUPPORTED_BUILD_TARGETS: tuple[str, ...] = ("windows", "linux", "android", "web", "macos", "ios")

BUILD_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

RELEASE_STATUS_UNAPPROVED = "UNAPPROVED"
RELEASE_STATUS_APPROVED = "RELEASE_APPROVED"

ARTIFACT_KIND_STRUCTURAL = "structural-source-bundle"

BUILD_EXCLUDED_DIRS: frozenset[str] = frozenset({"builds", ".godot", "__pycache__", ".git", ".import"})


class BuildError(FactoryError):
    """Erro base do subsistema de Build & Distribuicao."""


class BuildPrerequisiteError(BuildError):
    """Pre-requisito de build violado (spec invalida, segredo, auditoria de assets, versao)."""


class BuildTargetUnavailableError(BuildError):
    """Alvo de build indisponivel (toolchain ausente e bundle estrutural nao permitido)."""


class BuildIntegrityError(BuildError):
    """Hash ou conteudo do artefato diverge do manifesto de build."""


class ReleaseApprovalRequiredError(BuildError):
    """Operacao exige aprovacao humana de release valida."""
