"""Engine Selection and Orchestration System e adaptadores multi-engine (Incremento P1 / ADR-010)."""

from .adapter import EngineAdapter, EngineAdapterRegistry, create_default_orchestrator
from .godot_adapter import GodotEngineAdapter
from .schemas import (
    ANIMATION_COMPLEXITIES,
    AUTOMATION_PREFERENCES,
    CAMERA_TYPES,
    DEVELOPMENT_COMPLEXITIES,
    ENGINE_SELECTION_SCHEMA_VERSION,
    GRAPHIC_QUALITIES,
    LICENSING_PREFERENCES,
    PERFORMANCE_TARGETS,
    PHYSICS_MODES,
    SELECTION_CRITERIA,
    SUPPORTED_MULTIENGINE_ENGINES,
    WORLD_DIMENSIONS,
    AdapterNotFoundError,
    EngineOrchestrationError,
    EngineProfileRequest,
    EngineScaffoldResult,
    EngineSelectionError,
    EngineTestResult,
    EngineToolchainUnavailableError,
    EngineValidationResult,
    ToolchainProbeResult,
)
from .selector import EngineSelector, format_selection_report_markdown
from .unity_adapter import UnityEngineAdapter
from .unreal_adapter import UnrealEngineAdapter

__all__ = [
    "ANIMATION_COMPLEXITIES",
    "AUTOMATION_PREFERENCES",
    "CAMERA_TYPES",
    "DEVELOPMENT_COMPLEXITIES",
    "ENGINE_SELECTION_SCHEMA_VERSION",
    "GRAPHIC_QUALITIES",
    "LICENSING_PREFERENCES",
    "PERFORMANCE_TARGETS",
    "PHYSICS_MODES",
    "SELECTION_CRITERIA",
    "SUPPORTED_MULTIENGINE_ENGINES",
    "WORLD_DIMENSIONS",
    "AdapterNotFoundError",
    "EngineAdapter",
    "EngineAdapterRegistry",
    "EngineOrchestrationError",
    "EngineProfileRequest",
    "EngineScaffoldResult",
    "EngineSelectionError",
    "EngineSelector",
    "EngineTestResult",
    "EngineToolchainUnavailableError",
    "EngineValidationResult",
    "GodotEngineAdapter",
    "ToolchainProbeResult",
    "UnityEngineAdapter",
    "UnrealEngineAdapter",
    "create_default_orchestrator",
    "format_selection_report_markdown",
]
