"""Modelos, constantes e erros do Factory Core (stdlib apenas, offline e deterministico)."""
from __future__ import annotations

import re

SCHEMA_VERSION = 1

PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,39}$")

KIND_GAME = "game"
KIND_ANCHOR = "anchor"

DEFAULT_ENGINE = "godot"
DEFAULT_ENGINE_VERSION = "4.4-stable"

# Ciclo de vida padrao (docs/GAME_FACTORY.md, secao 2). As duas aprovacoes humanas
# recebem nomes distintos para que cada uma tenha seu proprio registro de aprovacao.
STAGES = (
    "IDEIA",
    "RESEARCH",
    "GDD",
    "GAME_SPECIFICATION",
    "ARQUITETURA",
    "APROVACAO_HUMANA_ARQUITETURA",
    "SELECAO_DE_TEMPLATE",
    "GERACAO_DO_PROJETO",
    "PRODUCAO_DE_ASSETS",
    "IMPLEMENTACAO",
    "INTEGRACAO",
    "TESTES",
    "BALANCEAMENTO",
    "AUDITORIA",
    "PREVIEW",
    "APROVACAO_HUMANA_PREVIEW",
    "BUILD",
    "DISTRIBUICAO",
    "MONITORAMENTO",
    "OTIMIZACAO",
)

APPROVAL_STAGES = ("APROVACAO_HUMANA_ARQUITETURA", "APROVACAO_HUMANA_PREVIEW")

ANCHOR_PROJECT_ID = "zaikor"
ANCHOR_NAME = "Zaikor: Zenkai Infinite"


class FactoryError(Exception):
    """Base de todos os erros da fabrica (todos sao fail-closed)."""


class InvalidProjectId(FactoryError):
    pass


class ProjectExists(FactoryError):
    pass


class ProjectNotFound(FactoryError):
    pass


class ApprovalRequired(FactoryError):
    pass


class InvalidTransition(FactoryError):
    pass


class EvidenceRequired(FactoryError):
    pass


class ProtectedProject(FactoryError):
    pass


class WorkspaceEscape(FactoryError):
    pass


class WorkspaceExists(FactoryError):
    pass


class RegistryCorrupt(FactoryError):
    pass
