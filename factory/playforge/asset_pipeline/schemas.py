"""Schemas, licencas permitidas e excecoes do Pipeline de Assets e Audio (Fase 7)."""
from __future__ import annotations

import re

from factory.playforge.models import FactoryError

ASSET_REGISTRY_SCHEMA_VERSION = 1

ASSET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}[a-z0-9]$")

IMAGE_ASSET_TYPES: tuple[str, ...] = ("sprite_2d", "tileset", "ui_icon", "background")
AUDIO_ASSET_TYPES: tuple[str, ...] = ("sfx", "bgm")
MODEL_3D_ASSET_TYPES: tuple[str, ...] = ("model_3d", "animation_3d", "environment_mesh")
PBR_ASSET_TYPES: tuple[str, ...] = (
    "texture_albedo",
    "texture_normal",
    "texture_roughness",
    "texture_metallic",
    "texture_ao",
)
OTHER_ASSET_TYPES: tuple[str, ...] = ("font", "shader_data", "texture") + MODEL_3D_ASSET_TYPES + PBR_ASSET_TYPES
ASSET_TYPES: tuple[str, ...] = IMAGE_ASSET_TYPES + AUDIO_ASSET_TYPES + OTHER_ASSET_TYPES

SUPPORTED_ASSET_FORMATS: tuple[str, ...] = ("png", "jpg", "jpeg", "wav", "ogg", "mp3", "gltf", "glb", "fbx", "obj")
ASSET_OPTIONAL_EXTENDED_FIELDS: tuple[str, ...] = (
    "compatible_engines",
    "lod_level",
    "pbr_maps",
    "has_rig",
    "has_materials",
)

ORIGIN_TYPES: tuple[str, ...] = (
    "procedural_local",
    "created_in_house",
    "open_source_verified",
    "local_ai_verified",
)

APPROVED_ASSET_LICENSES: tuple[str, ...] = (
    "OWN_ORIGINAL_PROCEDURAL",
    "CC0-1.0",
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "CC-BY-4.0",
    "OFL-1.1",
)

LICENSES_REQUIRING_ATTRIBUTION: frozenset[str] = frozenset({"CC-BY-4.0", "OFL-1.1"})

DISALLOWED_LICENSE_TOKENS: tuple[str, ...] = (
    "NC",
    "NONCOMMERCIAL",
    "NON-COMMERCIAL",
    "ND",
    "ALL_RIGHTS_RESERVED",
    "UNKNOWN",
    "UNVERIFIED",
    "PROPRIETARY",
    "AI_UNVERIFIED",
)

TEMP_OR_FORBIDDEN_SUFFIXES: tuple[str, ...] = (".tmp", ".bak", ".swp", ".part", ".crdownload")

ASSET_REGISTRY_REQUIRED_FIELDS: tuple[str, ...] = (
    "asset_id",
    "name",
    "asset_type",
    "project_id",
    "game_id",
    "version",
    "file_path",
    "format",
    "dimensions",
    "resolution",
    "byte_size",
    "origin",
    "author_or_provider",
    "tool_used",
    "model_used",
    "prompt_or_seed",
    "license",
    "restrictions",
    "sha256_hash",
    "validation_status",
)


class AssetError(FactoryError):
    """Erro base do Pipeline de Assets e Audio."""


class AssetValidationError(AssetError):
    """Asset corrompido, com formato invalido, clipping, orfao ou fora de confinamento."""


class AssetLicenseError(AssetError):
    """Asset bloqueado por licenca nao comercial/nao verificada ou proveniencia ausente."""


class AssetNotFoundError(AssetError):
    """Asset nao encontrado no workspace ou no AssetRegistry do projeto."""
