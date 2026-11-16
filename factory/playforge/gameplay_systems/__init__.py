"""Catalogo modular de sistemas de gameplay sob demanda multi-engine (P4)."""

from .catalog import (
    GAMEPLAY_SYSTEM_IDS,
    GAMEPLAY_SYSTEMS_CATALOG,
    GameplaySystemError,
    GameplaySystemInjector,
)

__all__ = [
    "GAMEPLAY_SYSTEM_IDS",
    "GAMEPLAY_SYSTEMS_CATALOG",
    "GameplaySystemError",
    "GameplaySystemInjector",
]
