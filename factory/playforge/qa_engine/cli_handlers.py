"""Handlers e subcomandos CLI do QA & Balance Engine (Fase 8)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.registry import ProjectManager
from factory.playforge.spec_engine.schemas import SUPPORTED_GENRES

from .balance_verifier import BalanceVerifierEngine
from .runner import QAEngine
from .schemas import QAValidationError
from .static_analyzer import StaticAnalyzer


def register_qa_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    """Registra subcomandos qa-* na CLI principal da PlayForge Factory."""
    p_static = sub.add_parser(
        "qa-static",
        help="Audita layout Godot, referencias res://, segredos e pureza src/core/ de project_id.",
    )
    p_static.add_argument("project_id", help="Slug do projeto alvo (ou zaikor).")
    p_static.add_argument("--strict", action="store_true", help="Retorna codigo 1 se houver violacoes.")

    p_bal = sub.add_parser(
        "qa-balance",
        help="Executa simulacao deterministica de balanceamento multi-genero para project_id.",
    )
    p_bal.add_argument("project_id", help="Slug do projeto alvo (ou zaikor).")
    p_bal.add_argument("--genre", default=None, choices=list(SUPPORTED_GENRES), help="Sobrescreve genero alvo.")
    p_bal.add_argument("--seed", type=int, default=2026, help="Seed deterministica do simulador.")
    p_bal.add_argument("--run-godot", action="store_true", help="Executa ActionBalanceVerifier Godot no zaikor.")
    p_bal.add_argument("--strict", action="store_true", help="Retorna codigo 1 se balanceamento reprovar.")

    p_prof = sub.add_parser(
        "qa-profile",
        help="Executa probe real de MainScene e Performance no Godot 4.4 headless (GT-02).",
    )
    p_prof.add_argument("project_id", help="Slug do projeto alvo (ou zaikor).")
    p_prof.add_argument("--frames", type=int, default=10, help="Numero de frames reais medidos.")

    p_run = sub.add_parser(
        "qa-run",
        help="Executa o pipeline completo de 4 pilares do QA Engine sobre project_id.",
    )
    p_run.add_argument("project_id", help="Slug do projeto alvo (ou zaikor).")
    p_run.add_argument("--no-godot", action="store_true", help="Pula suites/profiling Godot headless.")
    p_run.add_argument("--no-assets", action="store_true", help="Pula auditoria de AssetRegistry.")
    p_run.add_argument("--require-assets", action="store_true", help="Exige assets/asset_registry.json.")
    p_run.add_argument("--genre", default=None, choices=list(SUPPORTED_GENRES), help="Sobrescreve genero alvo.")
    p_run.add_argument("--seed", type=int, default=2026, help="Seed deterministica do balanceamento.")
    p_run.add_argument("--frames", type=int, default=10, help="Frames medidos no profiling Godot.")
    p_run.add_argument("--strict", action="store_true", help="Retorna codigo 1 se algum pilar reprovar.")


def handle_qa_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    """Despacha subcomandos qa-* da CLI PlayForge."""
    if args.command == "qa-static":
        res = StaticAnalyzer(manager).audit_project(args.project_id)
        if args.strict and not res["passed"]:
            raise QAValidationError(
                f"Auditoria estatica reprovou '{args.project_id}' com {len(res['violations'])} violacoes."
            )
        return res

    if args.command == "qa-balance":
        engine = BalanceVerifierEngine(manager)
        return engine.verify_project_balance(
            args.project_id,
            genre=args.genre,
            seed=args.seed,
            run_godot=args.run_godot,
            strict=args.strict,
        )

    qa = QAEngine(manager)
    if args.command == "qa-profile":
        return qa.profile_project_godot(args.project_id, frames=args.frames, strict=True)

    if args.command == "qa-run":
        return qa.run_qa_pipeline(
            args.project_id,
            with_godot=not args.no_godot,
            with_assets=not args.no_assets,
            require_assets=args.require_assets,
            genre=args.genre,
            seed=args.seed,
            frames=args.frames,
            strict=args.strict,
        )

    raise ValueError(f"Comando QA nao suportado: {args.command}")
