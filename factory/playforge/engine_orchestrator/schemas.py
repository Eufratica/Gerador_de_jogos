"""Schemas, criterios oficiais de selecao (14 dimensoes) e excecoes multi-engine (P1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from factory.playforge.models import FactoryError

ENGINE_SELECTION_SCHEMA_VERSION = 1

SUPPORTED_MULTIENGINE_ENGINES: tuple[str, ...] = ("godot", "unity", "unreal")

WORLD_DIMENSIONS: tuple[str, ...] = ("2d", "2.5d", "3d-indie", "3d-aaa-large")
CAMERA_TYPES: tuple[str, ...] = (
    "side-scroller",
    "top-down",
    "isometric",
    "first-person",
    "third-person-cinematic",
)
ANIMATION_COMPLEXITIES: tuple[str, ...] = (
    "basic-2d",
    "skeletal-2d",
    "standard-3d",
    "advanced-mocap-cinematic",
)
PHYSICS_MODES: tuple[str, ...] = (
    "none",
    "arcade-2d",
    "deterministic-2d",
    "rigidbody-3d",
    "advanced-destruction-cloth",
)
GRAPHIC_QUALITIES: tuple[str, ...] = (
    "pixel-vector-2d",
    "stylized-3d",
    "pbr-standard",
    "photorealistic-lumen-nanite",
)
PERFORMANCE_TARGETS: tuple[str, ...] = (
    "mobile-60fps-low-spec",
    "desktop-60fps",
    "high-end-gpu-60fps",
)
DEVELOPMENT_COMPLEXITIES: tuple[str, ...] = ("low-mvp", "medium", "high", "aaa-scale")
LICENSING_PREFERENCES: tuple[str, ...] = ("open-source-mit", "free-royalty-ok", "enterprise-ok")
AUTOMATION_PREFERENCES: tuple[str, ...] = ("headless-cli-priority", "standard-ci")

# 14 criterios oficiais do Master Engineering Prompt (Secao 3.2)
SELECTION_CRITERIA: tuple[tuple[str, float, str], ...] = (
    ("genre", 1.1, "Genero do jogo"),
    ("world_dimension", 1.4, "Dimensao do mundo (2D/2.5D/3D)"),
    ("camera_type", 1.0, "Tipo de camera"),
    ("character_count", 0.7, "Quantidade de personagens simultaneos"),
    ("animation_complexity", 1.0, "Complexidade das animacoes"),
    ("physics_needs", 0.9, "Necessidade de fisica"),
    ("graphic_quality", 1.3, "Qualidade grafica desejada"),
    ("target_platforms", 1.1, "Plataformas de destino"),
    ("expected_performance", 1.0, "Desempenho esperado"),
    ("development_complexity", 1.0, "Complexidade de desenvolvimento"),
    ("free_tools_availability", 1.2, "Disponibilidade de ferramentas gratuitas"),
    ("hardware_requirements", 1.4, "Requisitos de hardware do host/alvo"),
    ("licensing", 1.2, "Licenciamento e politica Free First"),
    ("automation_possibility", 1.1, "Possibilidade de automacao headless/CLI"),
)


class EngineOrchestrationError(FactoryError):
    """Erro base da camada de selecao e adaptacao de engines."""


class AdapterNotFoundError(EngineOrchestrationError):
    """Adaptador de engine nao registrado no EngineAdapterRegistry."""


class EngineSelectionError(EngineOrchestrationError):
    """Parametros insuficientes ou invalidos para avaliacao multi-engine."""


class EngineToolchainUnavailableError(EngineOrchestrationError):
    """Engine ou compilador ausente/incompativel no host para execucao ou build real."""


@dataclass(frozen=True)
class EngineProfileRequest:
    """Perfil tecnico de entrada para pontuar os 14 criterios sem escolha por conveniencia."""

    genre: str
    world_dimension: str
    camera_type: str
    character_count: int
    animation_complexity: str
    physics_needs: str
    graphic_quality: str
    target_platforms: tuple[str, ...]
    expected_performance: str
    development_complexity: str
    free_tools_priority: bool = True
    prefer_open_source_license: bool = True
    licensing_preference: str = "open-source-mit"
    automation_preference: str = "headless-cli-priority"
    require_csharp: bool = False
    target_ram_budget_mb: int = 512

    def validate(self) -> None:
        if not isinstance(self.genre, str) or not self.genre.strip():
            raise EngineSelectionError("Campo 'genre' obrigatorio para selecao de engine.")
        _assert_enum("world_dimension", self.world_dimension, WORLD_DIMENSIONS)
        _assert_enum("camera_type", self.camera_type, CAMERA_TYPES)
        _assert_enum("animation_complexity", self.animation_complexity, ANIMATION_COMPLEXITIES)
        _assert_enum("physics_needs", self.physics_needs, PHYSICS_MODES)
        _assert_enum("graphic_quality", self.graphic_quality, GRAPHIC_QUALITIES)
        _assert_enum("expected_performance", self.expected_performance, PERFORMANCE_TARGETS)
        _assert_enum("development_complexity", self.development_complexity, DEVELOPMENT_COMPLEXITIES)
        _assert_enum("licensing_preference", self.licensing_preference, LICENSING_PREFERENCES)
        _assert_enum("automation_preference", self.automation_preference, AUTOMATION_PREFERENCES)
        if isinstance(self.character_count, bool) or not isinstance(self.character_count, int) or self.character_count < 1:
            raise EngineSelectionError("Campo 'character_count' deve ser inteiro >= 1.")
        if isinstance(self.target_ram_budget_mb, bool) or not isinstance(self.target_ram_budget_mb, int) or self.target_ram_budget_mb < 64:
            raise EngineSelectionError("Campo 'target_ram_budget_mb' deve ser inteiro >= 64.")
        if not self.target_platforms or any(not isinstance(p, str) or not p.strip() for p in self.target_platforms):
            raise EngineSelectionError("Campo 'target_platforms' deve conter ao menos uma plataforma valida.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "genre": self.genre,
            "world_dimension": self.world_dimension,
            "camera_type": self.camera_type,
            "character_count": self.character_count,
            "animation_complexity": self.animation_complexity,
            "physics_needs": self.physics_needs,
            "graphic_quality": self.graphic_quality,
            "target_platforms": list(self.target_platforms),
            "expected_performance": self.expected_performance,
            "development_complexity": self.development_complexity,
            "free_tools_priority": self.free_tools_priority,
            "prefer_open_source_license": self.prefer_open_source_license,
            "licensing_preference": self.licensing_preference,
            "automation_preference": self.automation_preference,
            "require_csharp": self.require_csharp,
            "target_ram_budget_mb": self.target_ram_budget_mb,
        }


def _assert_enum(field_name: str, value: Any, allowed: tuple[str, ...]) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise EngineSelectionError(f"Valor invalido para '{field_name}': '{value}'. Permitidos: {allowed}.")


@dataclass(frozen=True)
class ToolchainProbeResult:
    """Resultado real e verificavel de deteccao de engine no ambiente local."""

    engine_id: str
    display_name: str
    available: bool
    executable_path: str | None
    version: str | None
    license_type: str
    recommended_min_ram_gb: float
    requires_dedicated_gpu: bool
    headless_supported: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "display_name": self.display_name,
            "available": self.available,
            "executable_path": self.executable_path,
            "version": self.version,
            "license_type": self.license_type,
            "recommended_min_ram_gb": self.recommended_min_ram_gb,
            "requires_dedicated_gpu": self.requires_dedicated_gpu,
            "headless_supported": self.headless_supported,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EngineScaffoldResult:
    """Resultado de criacao/atualizacao estrutural de projeto para uma engine."""

    engine_id: str
    project_dir: str
    files_written: tuple[str, ...]
    executable_ready: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "project_dir": self.project_dir,
            "files_written": list(self.files_written),
            "executable_ready": self.executable_ready,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class EngineValidationResult:
    """Resultado de auditoria estrutural fail-closed em um workspace de engine."""

    engine_id: str
    passed: bool
    checked_files: tuple[str, ...]
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "passed": self.passed,
            "checked_files": list(self.checked_files),
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class EngineTestResult:
    """Resultado real de execucao de testes automatizados dentro da engine."""

    engine_id: str
    passed: bool
    executed: bool
    elapsed_ms: float
    summary: str
    stdout_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "passed": self.passed,
            "executed": self.executed,
            "elapsed_ms": self.elapsed_ms,
            "summary": self.summary,
            "stdout_tail": self.stdout_tail,
        }
