"""Handlers CLI para o Engine Selection and Orchestration System (Incremento P1)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.registry import ProjectManager, _atomic_write_json, _atomic_write_text

from .adapter import create_default_orchestrator
from .schemas import (
    ANIMATION_COMPLEXITIES,
    AUTOMATION_PREFERENCES,
    CAMERA_TYPES,
    DEVELOPMENT_COMPLEXITIES,
    GRAPHIC_QUALITIES,
    LICENSING_PREFERENCES,
    PERFORMANCE_TARGETS,
    PHYSICS_MODES,
    SUPPORTED_MULTIENGINE_ENGINES,
    WORLD_DIMENSIONS,
    EngineProfileRequest,
    EngineSelectionError,
)
from .selector import EngineSelector


def register_engine_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    """Registra subcomandos engine-* na CLI principal da PlayForge."""
    sub.add_parser("engine-matrix", help="Lista engines, tecnologias e disponibilidade real no host.")

    p_probe = sub.add_parser("engine-probe", help="Inspeciona toolchains reais (Godot, Unity, Unreal) no ambiente.")
    p_probe.add_argument("--engine", default=None, choices=SUPPORTED_MULTIENGINE_ENGINES)

    p_sel = sub.add_parser("engine-select", help="Avalia os 14 criterios e gera relatorio de selecao de engine.")
    p_sel.add_argument("--genre", required=True, help="Genero do jogo.")
    p_sel.add_argument("--dimension", required=True, choices=WORLD_DIMENSIONS)
    p_sel.add_argument("--camera", required=True, choices=CAMERA_TYPES)
    p_sel.add_argument("--characters", type=int, default=4)
    p_sel.add_argument("--animation", default="basic-2d", choices=ANIMATION_COMPLEXITIES)
    p_sel.add_argument("--physics", default="deterministic-2d", choices=PHYSICS_MODES)
    p_sel.add_argument("--graphic", default="pixel-vector-2d", choices=GRAPHIC_QUALITIES)
    p_sel.add_argument("--platforms", nargs="+", default=["windows", "linux", "android"])
    p_sel.add_argument("--performance", default="desktop-60fps", choices=PERFORMANCE_TARGETS)
    p_sel.add_argument("--complexity", default="medium", choices=DEVELOPMENT_COMPLEXITIES)
    p_sel.add_argument("--licensing", default="open-source-mit", choices=LICENSING_PREFERENCES)
    p_sel.add_argument("--automation", default="headless-cli-priority", choices=AUTOMATION_PREFERENCES)
    p_sel.add_argument("--require-csharp", action="store_true")
    p_sel.add_argument("--save-project", default=None, help="Salva relatorio em games/<project_id>/specs/.")

    p_scaf = sub.add_parser("engine-scaffold", help="Gera estrutura inicial para a engine escolhida no projeto.")
    p_scaf.add_argument("project_id", help="Slug do projeto alvo (nao-ancora).")
    p_scaf.add_argument("--engine", default=None, choices=SUPPORTED_MULTIENGINE_ENGINES)

    p_ver = sub.add_parser("engine-verify", help="Executa testes reais via EngineAdapter no workspace do projeto.")
    p_ver.add_argument("project_id", help="Slug do projeto alvo.")
    p_ver.add_argument("--engine", default=None, choices=SUPPORTED_MULTIENGINE_ENGINES)


def handle_engine_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    """Despacha subcomandos engine-* da CLI PlayForge."""
    registry = create_default_orchestrator(repo_root=manager.repo_root)

    if args.command == "engine-matrix":
        return {
            "adapters": [
                {
                    "engine_id": ad.engine_id,
                    "display_name": ad.display_name,
                    "supported_dimensions": list(ad.supported_dimensions),
                    "supported_technologies": list(ad.supported_technologies),
                    "license_summary": ad.license_summary,
                    "probe": ad.probe_toolchain().to_dict(),
                }
                for ad in registry.list_adapters()
            ]
        }

    if args.command == "engine-probe":
        if args.engine:
            return registry.get(args.engine).probe_toolchain().to_dict()
        return {"probes": [p.to_dict() for p in registry.probe_all()]}

    if args.command == "engine-select":
        req = EngineProfileRequest(
            genre=args.genre,
            world_dimension=args.dimension,
            camera_type=args.camera,
            character_count=args.characters,
            animation_complexity=args.animation,
            physics_needs=args.physics,
            graphic_quality=args.graphic,
            target_platforms=tuple(args.platforms),
            expected_performance=args.performance,
            development_complexity=args.complexity,
            licensing_preference=args.licensing,
            automation_preference=args.automation,
            require_csharp=bool(args.require_csharp),
        )
        report = EngineSelector(registry).evaluate(req)
        if args.save_project:
            manager.require_mutable_project(args.save_project)
            _atomic_write_json(
                manager.resolve_game_path(args.save_project, "specs/engine_selection_report.json"),
                report,
            )
            _atomic_write_text(
                manager.resolve_game_path(args.save_project, "specs/engine_selection_report.md"),
                report["report_markdown"],
            )
        return report

    if args.command == "engine-scaffold":
        project = manager.require_mutable_project(args.project_id)
        engine_id = args.engine or str(project.get("engine") or "")
        if not engine_id:
            raise EngineSelectionError("Informe --engine ou configure engine no projeto.")
        ws_dir = manager.resolve_game_path(args.project_id, ".")
        adapter = registry.get(engine_id)
        res = adapter.scaffold_project(ws_dir, {"game_id": args.project_id, "name": project["name"]})
        val = adapter.validate_project(ws_dir)
        return {"scaffold": res.to_dict(), "validation": val.to_dict()}

    if args.command == "engine-verify":
        project = manager.require_mutable_project(args.project_id)
        engine_id = args.engine or str(project.get("engine") or "godot")
        ws_dir = manager.resolve_game_path(args.project_id, ".")
        return registry.get(engine_id).run_tests(ws_dir).to_dict()

    raise ValueError(f"Comando engine nao suportado: {args.command}")
