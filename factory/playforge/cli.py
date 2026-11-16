"""CLI oficial do PlayForge Factory Core (Fase 2)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from .models import APPROVAL_STAGES, DEFAULT_ENGINE, DEFAULT_ENGINE_VERSION, FactoryError
from .registry import ProjectManager
from .spec_engine import SpecificationGenerator, SpecificationValidator, ValidationError


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="playforge-core",
        description="CLI do Nucleo da PlayForge Factory (registro multi-projeto e ciclo de vida).",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Raiz do repositorio (padrao: raiz do Gerador_de_jogos).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Inicializa o registro de projetos com o jogo-ancora Zaikor.")
    sub.add_parser("list", help="Lista todos os projetos registrados em JSON.")

    p_show = sub.add_parser("show", help="Exibe os detalhes de um projeto.")
    p_show.add_argument("project_id", help="Identificador slug do projeto.")

    p_create = sub.add_parser("create", help="Cria um novo projeto de jogo isolado.")
    p_create.add_argument("project_id", help="Slug do projeto (ex: ddtank-clash).")
    p_create.add_argument("--name", required=True, help="Nome legivel do jogo.")
    p_create.add_argument("--genre", required=True, help="Genero do jogo.")
    p_create.add_argument("--engine", default=DEFAULT_ENGINE, help="Engine alvo.")
    p_create.add_argument("--engine-version", default=DEFAULT_ENGINE_VERSION, help="Versao da engine.")

    p_approve = sub.add_parser("approve", help="Registra aprovacao humana para gate do pipeline.")
    p_approve.add_argument("project_id", help="Identificador slug do projeto.")
    p_approve.add_argument("--stage", required=True, choices=APPROVAL_STAGES, help="Gate aprovado.")
    p_approve.add_argument("--approver", required=True, help="Nome/ID do aprovador humano.")
    p_approve.add_argument("--notes", required=True, help="Justificativa/registro da decisao.")

    p_advance = sub.add_parser("advance", help="Avanca o projeto para a proxima etapa do ciclo de vida.")
    p_advance.add_argument("project_id", help="Identificador slug do projeto.")
    p_advance.add_argument("--to", dest="target_stage", required=True, help="Proxima etapa alvo.")
    p_advance.add_argument("--actor", required=True, help="Responsavel pela transicao.")
    p_advance.add_argument("--evidence", required=True, help="Evidencia verificavel da entrega.")
    p_advance.add_argument("--notes", default="", help="Observacoes opcionais.")

    p_spec_val = sub.add_parser("spec-validate", help="Valida um arquivo de GameSpecification.")
    p_spec_val.add_argument("target", help="Caminho do JSON ou project_id (com --project).")
    p_spec_val.add_argument("--project", action="store_true", help="Trata 'target' como project_id.")

    p_spec_gen = sub.add_parser("spec-generate", help="Gera game_specification.json no workspace do projeto.")
    p_spec_gen.add_argument("project_id", help="Slug do projeto de destino.")

    p_gdd_gen = sub.add_parser("gdd-generate", help="Gera gdd.json e gdd.md no workspace do projeto.")
    p_gdd_gen.add_argument("project_id", help="Slug do projeto de destino.")

    p_spec_app = sub.add_parser("spec-approve", help="Aprova GameSpecification e GDD do projeto.")
    p_spec_app.add_argument("project_id", help="Slug do projeto alvo.")
    p_spec_app.add_argument("--approver", required=True, help="Identificacao do aprovador humano.")
    p_spec_app.add_argument("--notes", required=True, help="Justificativa/registro da aprovacao.")

    from factory.playforge.template_registry.cli_handlers import register_template_subcommands
    from factory.playforge.generator.cli_handlers import register_generator_subcommands
    from factory.playforge.ai.cli_handlers import register_ai_mcp_subcommands
    from factory.playforge.asset_pipeline.cli_handlers import register_asset_audio_subcommands
    from factory.playforge.qa_engine.cli_handlers import register_qa_subcommands
    from factory.playforge.automation.cli_handlers import register_automation_subcommands
    from factory.playforge.engine_orchestrator.cli_handlers import register_engine_subcommands

    register_template_subcommands(sub)
    register_generator_subcommands(sub)
    register_ai_mcp_subcommands(sub)
    register_asset_audio_subcommands(sub)
    register_qa_subcommands(sub)
    register_automation_subcommands(sub)
    register_engine_subcommands(sub)
    from factory.playforge.build_system.cli_handlers import register_build_subcommands
    from factory.playforge.gameplay_systems.cli_handlers import register_gameplay_subcommands
    from factory.playforge.evolution.cli_handlers import register_evolution_subcommands

    register_build_subcommands(sub)
    register_gameplay_subcommands(sub)
    register_evolution_subcommands(sub)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else _default_repo_root()
    manager = ProjectManager(repo_root=repo_root)

    try:
        if args.command == "init":
            result = manager.init_registry()
        elif args.command == "list":
            result = {"projects": manager.list_projects()}
        elif args.command == "show":
            result = manager.get_project(args.project_id)
        elif args.command == "create":
            result = manager.create_project(
                project_id=args.project_id,
                name=args.name,
                genre=args.genre,
                engine=args.engine,
                engine_version=args.engine_version,
            )
        elif args.command == "approve":
            result = manager.record_approval(
                project_id=args.project_id,
                approval_stage=args.stage,
                approver=args.approver,
                decision_notes=args.notes,
            )
        elif args.command == "advance":
            result = manager.advance_stage(
                project_id=args.project_id,
                target_stage=args.target_stage,
                actor=args.actor,
                evidence=args.evidence,
                notes=args.notes,
            )
        elif args.command == "spec-validate":
            validator = SpecificationValidator()
            if args.project:
                raw_path = manager.resolve_game_path(args.target, "specs/game_specification.json")
            else:
                raw_path = Path(args.target)
            if not raw_path.exists():
                raise FactoryError(f"Arquivo não encontrado: '{raw_path}'.")
            try:
                data = json.loads(raw_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValidationError("json", f"JSON inválido em '{raw_path}': {exc}") from exc
            validated = validator.validate_spec(data)
            result = {"status": "VALID", "spec_id": validated["spec_id"], "game_id": validated["game_id"]}
        elif args.command == "spec-generate":
            generator = SpecificationGenerator(manager)
            spec = generator.generate_and_save_spec(args.project_id)
            result = {"status": "GENERATED", "spec_id": spec["spec_id"], "project_id": args.project_id}
        elif args.command == "gdd-generate":
            generator = SpecificationGenerator(manager)
            gdd = generator.generate_and_save_gdd(args.project_id)
            result = {"status": "GENERATED", "title": gdd["title"], "project_id": args.project_id}
        elif args.command == "spec-approve":
            generator = SpecificationGenerator(manager)
            result = generator.approve_specification(
                project_id=args.project_id,
                approver=args.approver,
                decision_notes=args.notes,
            )
        elif args.command.startswith("template-"):
            from factory.playforge.template_registry.cli_handlers import handle_template_command

            result = handle_template_command(args, manager)
        elif args.command.startswith("game-"):
            from factory.playforge.generator.cli_handlers import handle_generator_command

            result = handle_generator_command(args, manager)
        elif args.command.startswith(("ai-", "agent-", "workflow-", "mcp-")):
            from factory.playforge.ai.cli_handlers import handle_ai_mcp_command

            result = handle_ai_mcp_command(args, manager)
        elif args.command.startswith(("asset-", "audio-", "tool-")):
            from factory.playforge.asset_pipeline.cli_handlers import handle_asset_audio_command

            result = handle_asset_audio_command(args, manager)
        elif args.command.startswith("qa-"):
            from factory.playforge.qa_engine.cli_handlers import handle_qa_command

            result = handle_qa_command(args, manager)
        elif args.command.startswith("automation-"):
            from factory.playforge.automation.cli_handlers import handle_automation_command

            result = handle_automation_command(args, manager)
        elif args.command.startswith("engine-"):
            from factory.playforge.engine_orchestrator.cli_handlers import handle_engine_command

            result = handle_engine_command(args, manager)
        elif args.command.startswith("build-"):
            from factory.playforge.build_system.cli_handlers import handle_build_command

            result = handle_build_command(args, manager)
        elif args.command.startswith("gameplay-"):
            from factory.playforge.gameplay_systems.cli_handlers import handle_gameplay_command

            result = handle_gameplay_command(args, manager)
        elif args.command.startswith("evolution-"):
            from factory.playforge.evolution.cli_handlers import handle_evolution_command

            result = handle_evolution_command(args, manager)
        else:
            parser.error(f"Comando desconhecido: {args.command}")
            return 2
    except FactoryError as exc:
        print(json.dumps({"error": exc.__class__.__name__, "message": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
