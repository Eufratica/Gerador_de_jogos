"""Registry, validador e seletor de templates de jogos da PlayForge Factory."""
from __future__ import annotations

from factory.playforge.template_registry.registry import TemplateRegistry
from factory.playforge.template_registry.schemas import (
    APPROVED_OPEN_SOURCE_LICENSES,
    TEMPLATE_ID_RE,
    TEMPLATE_MANIFEST_SCHEMA_VERSION,
    TEMPLATE_REQUIRED_FIELDS,
    TEMPLATE_STATUSES,
    TEMPLATE_STATUS_ACTIVE,
    TEMPLATE_STATUS_DEPRECATED,
)
from factory.playforge.template_registry.validator import (
    TemplateCompatibilityError,
    TemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateValidator,
)

__all__ = [
    "APPROVED_OPEN_SOURCE_LICENSES",
    "TEMPLATE_ID_RE",
    "TEMPLATE_MANIFEST_SCHEMA_VERSION",
    "TEMPLATE_REQUIRED_FIELDS",
    "TEMPLATE_STATUSES",
    "TEMPLATE_STATUS_ACTIVE",
    "TEMPLATE_STATUS_DEPRECATED",
    "TemplateCompatibilityError",
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateRegistry",
    "TemplateValidationError",
    "TemplateValidator",
]
