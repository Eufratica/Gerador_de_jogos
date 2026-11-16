"""Schemas, catalogo oficial WF-001..WF-020 e excecoes de automacao (Fase 9)."""
from __future__ import annotations

from dataclasses import dataclass

from factory.playforge.models import FactoryError

AUTOMATION_SCHEMA_VERSION = 1

ALLOWED_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

FORBIDDEN_COMMERCIAL_DOMAINS = (
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "api.elevenlabs.io",
    "api.stability.ai",
    "api.midjourney.com",
    "replicate.com",
    "api.cohere.ai",
    "api.mistral.ai",
)


class AutomationError(FactoryError):
    """Erro base da camada de automacao e integracao n8n."""


class WorkflowValidationError(AutomationError):
    """Workflow n8n ausente, malformado, com segredos ou violacao Zero-Cost/SEC."""


class HumanGateBlockedError(AutomationError):
    """Execucao bloqueada aguardando aprovacao humana explicita (WF-014/WF-016)."""


@dataclass(frozen=True)
class WorkflowDefinition:
    """Metadados contratuais de um workflow oficial WF-001..WF-020 (docs/AUTOMATION.md)."""

    workflow_id: str
    name: str
    filename: str
    trigger_type: str
    requires_human_gate: bool
    approval_stage: str | None
    cli_command: str
    description: str
    tags: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "filename": self.filename,
            "trigger_type": self.trigger_type,
            "requires_human_gate": self.requires_human_gate,
            "approval_stage": self.approval_stage,
            "cli_command": self.cli_command,
            "description": self.description,
            "tags": list(self.tags),
        }


OFFICIAL_WORKFLOW_CATALOG: tuple[WorkflowDefinition, ...] = (
    WorkflowDefinition(
        workflow_id="WF-001",
        name="Project Initialization",
        filename="WF-001_project_initialization.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="create",
        description="Criar projeto isolado e registro inicial (auditado).",
        tags=("setup", "project"),
    ),
    WorkflowDefinition(
        workflow_id="WF-002",
        name="Market Research",
        filename="WF-002_market_research.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="automation-trigger WF-002",
        description="Consolidacao sanitizada anti-injection de referencias do genero.",
        tags=("research", "security"),
    ),
    WorkflowDefinition(
        workflow_id="WF-003",
        name="Game Design Document",
        filename="WF-003_game_design_document.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="gdd-generate",
        description="Geracao versionada do GDD de 25 secoes no workspace do projeto.",
        tags=("design", "gdd"),
    ),
    WorkflowDefinition(
        workflow_id="WF-004",
        name="Game Architecture",
        filename="WF-004_game_architecture.json",
        trigger_type="webhook",
        requires_human_gate=True,
        approval_stage="architecture",
        cli_command="automation-trigger WF-004",
        description="Validacao tecnica e gate arquitetural por projeto.",
        tags=("architecture", "human-gate"),
    ),
    WorkflowDefinition(
        workflow_id="WF-005",
        name="Game Specification",
        filename="WF-005_game_specification.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="spec-generate",
        description="Geracao e validacao fail-closed da GameSpecification JSON.",
        tags=("spec", "validation"),
    ),
    WorkflowDefinition(
        workflow_id="WF-006",
        name="Template Selection",
        filename="WF-006_template_selection.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="template-select",
        description="Selecao e checagem de compatibilidade no Template Registry.",
        tags=("templates",),
    ),
    WorkflowDefinition(
        workflow_id="WF-007",
        name="Project Generation",
        filename="WF-007_project_generation.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="game-generate",
        description="Instanciacao de workspace Godot isolado com guardas sandbox.",
        tags=("generator", "godot"),
    ),
    WorkflowDefinition(
        workflow_id="WF-008",
        name="Asset Generation",
        filename="WF-008_asset_generation.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="asset-generate-pack",
        description="Producao procedural zero-cost e auditoria de licenca/formato.",
        tags=("assets", "audio"),
    ),
    WorkflowDefinition(
        workflow_id="WF-009",
        name="Gameplay Development",
        filename="WF-009_gameplay_development.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="qa-static",
        description="Verificacao de scripts de gameplay e pureza de src/core/.",
        tags=("gameplay", "qa"),
    ),
    WorkflowDefinition(
        workflow_id="WF-010",
        name="UI/UX Generation",
        filename="WF-010_ui_ux_generation.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="qa-profile",
        description="Probe de instanciacao da MainScene/HUD no Godot headless.",
        tags=("ui-ux", "godot"),
    ),
    WorkflowDefinition(
        workflow_id="WF-011",
        name="Integration",
        filename="WF-011_integration.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="game-verify",
        description="Integracao e verificacao headless de cenas, sistemas e saves.",
        tags=("integration",),
    ),
    WorkflowDefinition(
        workflow_id="WF-012",
        name="Game QA",
        filename="WF-012_game_qa.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="qa-run",
        description="Execucao completa dos 4 pilares do QA Engine fail-closed.",
        tags=("qa",),
    ),
    WorkflowDefinition(
        workflow_id="WF-013",
        name="Balance Audit",
        filename="WF-013_balance_audit.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="qa-balance",
        description="Simulacao deterministica por genero e deteccao de soft-lock.",
        tags=("balance", "qa"),
    ),
    WorkflowDefinition(
        workflow_id="WF-014",
        name="Human Approval",
        filename="WF-014_human_approval.json",
        trigger_type="webhook",
        requires_human_gate=True,
        approval_stage="spec",
        cli_command="automation-approve",
        description="Pausa estado e aguarda decisao nominal explicita de humano.",
        tags=("human-gate", "governance"),
    ),
    WorkflowDefinition(
        workflow_id="WF-015",
        name="Build Generation",
        filename="WF-015_build_generation.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="game-package",
        description="Empacotamento reproduzivel com hashes apos QA+Balance.",
        tags=("build", "release"),
    ),
    WorkflowDefinition(
        workflow_id="WF-016",
        name="Publishing",
        filename="WF-016_publishing.json",
        trigger_type="webhook",
        requires_human_gate=True,
        approval_stage="release",
        cli_command="automation-trigger WF-016",
        description="Preparacao de manifesto de publicacao estritamente apos gate humano.",
        tags=("publishing", "human-gate"),
    ),
    WorkflowDefinition(
        workflow_id="WF-017",
        name="Analytics Collection",
        filename="WF-017_analytics_collection.json",
        trigger_type="schedule",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="automation-trigger WF-017",
        description="Agregacao local de metricas sem PII a partir de relatorios reais.",
        tags=("analytics", "privacy"),
    ),
    WorkflowDefinition(
        workflow_id="WF-018",
        name="Game Optimization",
        filename="WF-018_game_optimization.json",
        trigger_type="webhook",
        requires_human_gate=True,
        approval_stage=None,
        cli_command="automation-trigger WF-018",
        description="Geracao de proposta OpenSpec/JSON baseada em evidencias (nao auto-aplica).",
        tags=("optimization", "sdd"),
    ),
    WorkflowDefinition(
        workflow_id="WF-019",
        name="Error Recovery",
        filename="WF-019_error_recovery.json",
        trigger_type="webhook",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="workflow-resume",
        description="Recuperacao com checkpoint SQLite e limite estrito de retentativas.",
        tags=("recovery", "resilience"),
    ),
    WorkflowDefinition(
        workflow_id="WF-020",
        name="Factory Monitoring",
        filename="WF-020_factory_monitoring.json",
        trigger_type="schedule",
        requires_human_gate=False,
        approval_stage=None,
        cli_command="automation-trigger WF-020",
        description="Observabilidade continua: saude de IA, Godot, projetos e exports n8n.",
        tags=("monitoring", "observability"),
    ),
)

_WORKFLOW_BY_ID = {wf.workflow_id: wf for wf in OFFICIAL_WORKFLOW_CATALOG}


def get_workflow_definition(workflow_id: str) -> WorkflowDefinition:
    """Retorna metadados contratuais de um workflow WF-xxx ou falha fechado."""
    normalized = str(workflow_id).strip().upper()
    defn = _WORKFLOW_BY_ID.get(normalized)
    if defn is None:
        raise WorkflowValidationError(
            f"Workflow desconhecido '{workflow_id}'. Validos: WF-001..WF-020."
        )
    return defn
