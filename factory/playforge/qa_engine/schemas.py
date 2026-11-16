"""Schemas, constantes e excecoes do QA & Balance Engine (Fase 8)."""
from __future__ import annotations

from factory.playforge.models import FactoryError

QA_REPORT_SCHEMA_VERSION = 1
BALANCE_REPORT_SCHEMA_VERSION = 1

# Subcaminhos de jogo utilizados quando project_id == "zaikor" (raiz do repo tambem guarda factory/, tools/, etc.)
ANCHOR_GAME_DIRS = ("config", "src", "tests", "assets", "audio", "scenes")
ANCHOR_GAME_FILES = ("project.godot", "icon.svg")

# Pastas ignoradas na varredura estatica de qualquer workspace de jogo
IGNORED_WORKSPACE_DIRS = frozenset({".git", ".godot", "__pycache__", "builds", "logs", ".import"})

# Extensoes textuais elegiveis para varredura de segredos e referencias
TEXT_SCAN_EXTENSIONS = frozenset({".gd", ".tscn", ".tres", ".godot", ".cfg", ".ini", ".json", ".txt", ".md"})

CORE_FORBIDDEN_BASE_CLASSES = (
    "Node",
    "Node2D",
    "Node3D",
    "Control",
    "CanvasItem",
    "SceneTree",
    "MainLoop",
)

CORE_FORBIDDEN_SYMBOLS = (
    "Node",
    "Node2D",
    "Node3D",
    "Control",
    "CanvasItem",
    "SceneTree",
    "MainLoop",
    "FileAccess",
    "DirAccess",
    "HTTPRequest",
    "HTTPClient",
    "WebSocketPeer",
    "StreamPeer",
    "PacketPeer",
    "ProjectSettings",
)

CORE_FORBIDDEN_CALLS = (
    "OS.get_environment",
    "OS.set_environment",
    "OS.execute",
    "OS.shell_open",
    "Time.get_unix_time_from_system",
    "Time.get_unix_time_from_datetime",
    "Engine.get_main_loop",
    "get_tree",
)


class QAError(FactoryError):
    """Erro base da camada de QA & Balance Engine."""


class QAValidationError(QAError):
    """Violacao estatica, estrutural, de segredos ou falha em execucao headless."""


class BalanceVerificationError(QAError):
    """Reprovacao fail-closed de balanceamento, economia ou soft-lock."""
