"""Gestao, telemetria, RAG local TF-IDF e otimizacao assistida (Fase 11 / P5)."""

from .dashboard import FactoryDashboard
from .rag_memory import LocalRagMemory, RagMemoryError
from .telemetry_optimizer import OptimizationAdvisor

__all__ = [
    "FactoryDashboard",
    "LocalRagMemory",
    "OptimizationAdvisor",
    "RagMemoryError",
]
