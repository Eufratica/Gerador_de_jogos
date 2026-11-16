"""Definições de schemas tipados e versionados da PlayForge Factory (Fase 3)."""
from __future__ import annotations

import re

SPEC_SCHEMA_VERSION = 1
SPEC_SCHEMA_VERSION_MULTIENGINE = 2
GDD_SCHEMA_VERSION = 1

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

SUPPORTED_ENGINES = ("godot",)
SUPPORTED_MULTIENGINE_ENGINES = ("godot", "unity", "unreal")
SPEC_V2_OPTIONAL_FIELDS = (
    "camera_spec",
    "physics_spec",
    "inventory_spec",
    "quests_spec",
    "tools_required",
    "engine_selection_report",
)
SUPPORTED_PLATFORMS = ("android", "windows", "linux", "web")
SUPPORTED_ORIENTATIONS = ("landscape", "portrait")
SUPPORTED_GENRES = (
    "action-rpg",
    "idle-rpg",
    "platformer-2d",
    "roguelike",
    "tower-defense",
    "puzzle",
    "arcade",
    "strategy",
    "adventure",
    "simulation",
    "ddtank-ballistics",
)

# 34 campos contratuais cobrindo as dimensões do Prompt Mestre v2.0 (Seção 27)
SPEC_REQUIRED_FIELDS = (
    "spec_id",
    "game_id",
    "name",
    "version",
    "spec_schema_version",
    "genre",
    "subgenre",
    "target_platforms",
    "engine",
    "engine_version",
    "target_audience",
    "product_goals",
    "value_proposition",
    "references",
    "core_gameplay",
    "core_loop",
    "controls",
    "mechanics",
    "characters",
    "enemies",
    "worlds_and_levels",
    "progression",
    "difficulty",
    "economy",
    "ui_ux",
    "accessibility",
    "narrative",
    "audio",
    "art_and_assets",
    "persistence",
    "technical_requirements",
    "security",
    "monetization",
    "acceptance_criteria",
)

# 25 seções obrigatórias no Game Design Document (Prompt Mestre v2.0, Seção 29)
GDD_SECTIONS = (
    "concept",
    "vision",
    "genre",
    "target_audience",
    "differentials",
    "references",
    "core_loop",
    "gameplay_loop",
    "mechanics",
    "controls",
    "characters",
    "enemies",
    "environments",
    "levels_and_worlds",
    "progression",
    "economy",
    "difficulty",
    "ui_ux",
    "audio",
    "visual_direction",
    "accessibility",
    "monetization",
    "technical_requirements",
    "mvp_scope",
    "acceptance_criteria",
)

GDD_REQUIRED_FIELDS = (
    "gdd_schema_version",
    "project_id",
    "title",
    "sections",
)

GDD_ALLOWED_FIELDS = GDD_REQUIRED_FIELDS + (
    "linked_spec_id",
    "linked_spec_version",
)
