"""Camada de automacao n8n Community e Ponte Local da PlayForge Factory (Fase 9)."""

from .exporter import build_workflow_export, generate_official_exports
from .runner import AutomationEngine, AutomationWebhookServer
from .schemas import (
    AUTOMATION_SCHEMA_VERSION,
    OFFICIAL_WORKFLOW_CATALOG,
    AutomationError,
    HumanGateBlockedError,
    WorkflowDefinition,
    WorkflowValidationError,
    get_workflow_definition,
)
from .validator import validate_exports_directory, validate_workflow_export

__all__ = [
    "AUTOMATION_SCHEMA_VERSION",
    "OFFICIAL_WORKFLOW_CATALOG",
    "AutomationEngine",
    "AutomationError",
    "AutomationWebhookServer",
    "HumanGateBlockedError",
    "WorkflowDefinition",
    "WorkflowValidationError",
    "build_workflow_export",
    "generate_official_exports",
    "get_workflow_definition",
    "validate_exports_directory",
    "validate_workflow_export",
]
