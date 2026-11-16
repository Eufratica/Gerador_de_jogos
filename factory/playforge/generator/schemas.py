"""Constantes e excecoes fail-closed do Game Generator (Fase 5)."""
from __future__ import annotations

from factory.playforge.models import FactoryError

GENERATION_MANIFEST_SCHEMA_VERSION: int = 1
PREVIEW_REPORT_SCHEMA_VERSION: int = 1


class GeneratorError(FactoryError):
    """Erro base do subsistema Game Generator."""


class GenerationConflictError(GeneratorError):
    """Conflito de workspace ou divergencia sem --force ao regenerar projeto."""


class GenerationVerificationError(GeneratorError):
    """Falha na verificacao de integridade ou testes Godot headless do jogo gerado."""
