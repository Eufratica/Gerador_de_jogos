"""Motor de IA local, registro de agentes e orquestracao checkpointed da PlayForge Factory (Fase 6)."""

from .agents import (
    SPECIALIZED_ENGINEERING_ROLE_MAP,
    AgentContract,
    AgentRegistry,
    build_default_agent_contracts,
    get_engineering_role_catalog,
)
from .model_router import HardwareProfile, ModelRouter, OllamaClient, inspect_environment
from .orchestrator import GraphNode, GraphOrchestrator, SqliteCheckpointer, build_mvp_generation_orchestrator
from .schemas import (
    AgentContractError,
    AIError,
    DEFAULT_MODEL_CATALOG,
    DEFAULT_OLLAMA_BASE_URL,
    LoopLimitExceededError,
    MODEL_TIER_LARGE,
    MODEL_TIER_MEDIUM,
    MODEL_TIER_SMALL,
    ModelSpec,
    PolicyViolationError,
    ProviderUnavailableError,
    UntrustedOutputError,
    VALID_MODEL_TIERS,
)

__all__ = [
    "AIError",
    "AgentContract",
    "AgentContractError",
    "AgentRegistry",
    "DEFAULT_MODEL_CATALOG",
    "DEFAULT_OLLAMA_BASE_URL",
    "GraphNode",
    "GraphOrchestrator",
    "HardwareProfile",
    "LoopLimitExceededError",
    "MODEL_TIER_LARGE",
    "MODEL_TIER_MEDIUM",
    "MODEL_TIER_SMALL",
    "ModelRouter",
    "ModelSpec",
    "OllamaClient",
    "PolicyViolationError",
    "ProviderUnavailableError",
    "SPECIALIZED_ENGINEERING_ROLE_MAP",
    "SqliteCheckpointer",
    "UntrustedOutputError",
    "VALID_MODEL_TIERS",
    "build_default_agent_contracts",
    "build_mvp_generation_orchestrator",
    "get_engineering_role_catalog",
    "inspect_environment",
]
