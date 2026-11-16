"""Contratos e constantes do Game Template Registry (Fase 4)."""
from __future__ import annotations

import re

TEMPLATE_MANIFEST_SCHEMA_VERSION: int = 1

TEMPLATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")

TEMPLATE_STATUS_ACTIVE: str = "ACTIVE"
TEMPLATE_STATUS_DEPRECATED: str = "DEPRECATED"
TEMPLATE_STATUSES: tuple[str, ...] = (
    TEMPLATE_STATUS_ACTIVE,
    TEMPLATE_STATUS_DEPRECATED,
)

ALLOWED_TEST_RUNNERS: tuple[str, ...] = ("godot-headless",)

APPROVED_OPEN_SOURCE_LICENSES: tuple[str, ...] = (
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "CC0-1.0",
)

TEMPLATE_REQUIRED_FIELDS: tuple[str, ...] = (
    "template_manifest_schema_version",
    "template_id",
    "name",
    "template_version",
    "engine",
    "engine_version",
    "supported_genres",
    "supported_platforms",
    "status",
    "spec_schema_version",
    "license",
    "description",
    "documentation",
    "available_systems",
    "reusable_components",
    "asset_slots",
    "dependencies",
    "allowed_extensions",
    "file_structure",
    "tests",
    "demo_project_path",
)

TEMPLATE_OPTIONAL_FIELDS: tuple[str, ...] = ("deprecation",)

TEMPLATE_ALL_ALLOWED_FIELDS: frozenset[str] = frozenset(
    TEMPLATE_REQUIRED_FIELDS + TEMPLATE_OPTIONAL_FIELDS
)
