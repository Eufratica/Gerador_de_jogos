"""Interface EngineAdapter e registro expansivel multi-engine (Ports & Adapters)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .schemas import (
    AdapterNotFoundError,
    EngineScaffoldResult,
    EngineTestResult,
    EngineValidationResult,
    ToolchainProbeResult,
)


class EngineAdapter(ABC):
    """Contrato abstrato que todo adaptador de engine deve implementar."""

    engine_id: str
    display_name: str
    supported_dimensions: tuple[str, ...]
    supported_technologies: tuple[str, ...]
    license_summary: str

    @abstractmethod
    def probe_toolchain(self) -> ToolchainProbeResult:
        """Verifica se o editor/CLI da engine existe realmente no sistema local."""

    @abstractmethod
    def scaffold_project(self, project_dir: Path, spec: dict[str, Any]) -> EngineScaffoldResult:
        """Gera estrutura minima valida para a engine dentro de project_dir isolado."""

    @abstractmethod
    def validate_project(self, project_dir: Path) -> EngineValidationResult:
        """Valida estruturalmente um workspace gerado para esta engine."""

    @abstractmethod
    def run_tests(self, project_dir: Path) -> EngineTestResult:
        """Executa testes reais na engine ou falha fechado se toolchain estiver ausente."""

    @abstractmethod
    def score_profile(self, request: Any, hardware_profile: dict[str, Any], probe: ToolchainProbeResult) -> tuple[dict[str, float], dict[str, str]]:
        """Pontua [0..10] e justifica cada um dos 14 criterios para o perfil informado."""


class EngineAdapterRegistry:
    """Registro desacoplado permitindo adicionar novas engines sem alterar o nucleo."""

    def __init__(self) -> None:
        self._adapters: dict[str, EngineAdapter] = {}

    def register(self, adapter: EngineAdapter) -> None:
        key = adapter.engine_id.strip().lower()
        if not key:
            raise AdapterNotFoundError("engine_id invalido ao registrar adaptador.")
        self._adapters[key] = adapter

    def get(self, engine_id: str) -> EngineAdapter:
        key = engine_id.strip().lower()
        if key not in self._adapters:
            raise AdapterNotFoundError(
                f"Adaptador de engine '{engine_id}' nao registrado. Disponiveis: {sorted(self._adapters.keys())}."
            )
        return self._adapters[key]

    def list_adapters(self) -> list[EngineAdapter]:
        return [self._adapters[k] for k in sorted(self._adapters.keys())]

    def probe_all(self) -> list[ToolchainProbeResult]:
        return [adapter.probe_toolchain() for adapter in self.list_adapters()]


def create_default_orchestrator(repo_root: Path | None = None) -> EngineAdapterRegistry:
    """Cria registro padrao com Godot, Unity e Unreal (expansivel via .register())."""
    from .godot_adapter import GodotEngineAdapter
    from .unity_adapter import UnityEngineAdapter
    from .unreal_adapter import UnrealEngineAdapter

    reg = EngineAdapterRegistry()
    reg.register(GodotEngineAdapter(repo_root=repo_root))
    reg.register(UnityEngineAdapter())
    reg.register(UnrealEngineAdapter())
    return reg
