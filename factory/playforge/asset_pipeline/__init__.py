"""Pipeline de Assets e Audio Zero Cost, Registro de Proveniencia e Validacao Godot (Fase 7)."""

from .registry import AssetRegistry
from .schemas import (
    APPROVED_ASSET_LICENSES,
    ASSET_REGISTRY_REQUIRED_FIELDS,
    ASSET_REGISTRY_SCHEMA_VERSION,
    ASSET_TYPES,
    AUDIO_ASSET_TYPES,
    AssetError,
    AssetLicenseError,
    AssetNotFoundError,
    AssetValidationError,
    IMAGE_ASSET_TYPES,
    ORIGIN_TYPES,
)
from .synthesizer import inspect_media_toolchain, synthesize_png_sprite, synthesize_wav_audio
from .validator import inspect_ogg, inspect_png, inspect_wav, validate_asset_record, validate_license_and_provenance

__all__ = [
    "APPROVED_ASSET_LICENSES",
    "ASSET_REGISTRY_REQUIRED_FIELDS",
    "ASSET_REGISTRY_SCHEMA_VERSION",
    "ASSET_TYPES",
    "AUDIO_ASSET_TYPES",
    "AssetError",
    "AssetLicenseError",
    "AssetNotFoundError",
    "AssetRegistry",
    "AssetValidationError",
    "IMAGE_ASSET_TYPES",
    "ORIGIN_TYPES",
    "inspect_media_toolchain",
    "inspect_ogg",
    "inspect_png",
    "inspect_wav",
    "synthesize_png_sprite",
    "synthesize_wav_audio",
    "validate_asset_record",
    "validate_license_and_provenance",
]
