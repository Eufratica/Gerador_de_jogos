"""Handlers CLI para catalogo e injecao modular de sistemas de gameplay (P4)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.registry import ProjectManager

from .catalog import GAMEPLAY_SYSTEM_IDS, GameplaySystemInjector


def register_gameplay_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    sub.add_parser("gameplay-catalog", help="Lista os sistemas de gameplay modulares reutilizaveis.")

    p_inj = sub.add_parser("gameplay-inject", help="Injeta apenas sistemas de gameplay solicitados no projeto.")
    p_inj.add_argument("project_id", help="Slug do projeto alvo (nao-ancora).")
    p_inj.add_argument("--systems", nargs="+", required=True, choices=GAMEPLAY_SYSTEM_IDS)
    p_inj.add_argument("--engine", default=None, choices=("godot", "unity", "unreal"))


def handle_gameplay_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    injector = GameplaySystemInjector(manager)
    if args.command == "gameplay-catalog":
        items = injector.list_catalog()
        return {"count": len(items), "systems": items}
    if args.command == "gameplay-inject":
        return injector.inject_systems(args.project_id, args.systems, engine=args.engine)
    raise ValueError(f"Comando gameplay nao suportado: {args.command}")
