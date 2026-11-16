"""Handlers e subcomandos CLI do Game Generator (Fase 5)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.generator.game_generator import GameGenerator
from factory.playforge.registry import ProjectManager


def register_generator_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    """Registra os subcomandos game-* no parser principal da CLI."""
    p_gen = sub.add_parser("game-generate", help="Gera projeto Godot isolado a partir de spec + template.")
    p_gen.add_argument("project_id", help="Slug do projeto alvo.")
    p_gen.add_argument("--prefer-template", default=None, help="Template preferencial.")
    p_gen.add_argument("--skip-template-tests", action="store_true", help="Pula re-execucao dos testes do template.")
    p_gen.add_argument("--skip-godot-tests", action="store_true", help="Pula testes headless do projeto gerado.")
    p_gen.add_argument("--skip-package", action="store_true", help="Nao gera artefato ZIP em builds/.")
    p_gen.add_argument("--force", action="store_true", help="Sobrescreve arquivos gerados em caso de divergencia.")

    p_ver = sub.add_parser("game-verify", help="Valida integridade e executa testes Godot headless no projeto gerado.")
    p_ver.add_argument("project_id", help="Slug do projeto alvo.")

    p_pkg = sub.add_parser("game-package", help="Empacota artefato local deterministico em builds/.")
    p_pkg.add_argument("project_id", help="Slug do projeto alvo.")


def handle_generator_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    """Despacha subcomandos game-* sobre o manager fornecido."""
    generator = GameGenerator(manager)

    if args.command == "game-generate":
        return generator.generate_project(
            args.project_id,
            prefer_template_id=args.prefer_template,
            verify_template_tests=not args.skip_template_tests,
            run_godot_tests=not args.skip_godot_tests,
            package_preview_build=not args.skip_package,
            force=args.force,
        )

    if args.command == "game-verify":
        return generator.verify_generated_project(args.project_id)

    if args.command == "game-package":
        return generator.package_preview_artifact(args.project_id)

    raise ValueError(f"Comando de geracao nao suportado: {args.command}")
