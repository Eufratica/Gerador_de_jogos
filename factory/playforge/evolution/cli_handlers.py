"""Handlers CLI para Fase 11 — Gestao, Telemetria, RAG Local e Otimizacao (P5)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.registry import ProjectManager

from .dashboard import FactoryDashboard
from .rag_memory import LocalRagMemory
from .telemetry_optimizer import OptimizationAdvisor


def register_evolution_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    p_idx = sub.add_parser("evolution-index", help="Indexa artefatos de um projeto na memoria RAG local.")
    p_idx.add_argument("project_id")

    p_src = sub.add_parser("evolution-search", help="Consulta a memoria RAG local TF-IDF/cosseno.")
    p_src.add_argument("query")
    p_src.add_argument("--project-id", default=None)
    p_src.add_argument("--top-k", type=int, default=5)

    p_opt = sub.add_parser("evolution-optimize", help="Gera recomendacoes de otimizacao baseadas em telemetria real.")
    p_opt.add_argument("project_id")

    sub.add_parser("evolution-dashboard", help="Consolida painel multi-projeto da PlayForge Factory.")


def handle_evolution_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    if args.command == "evolution-index":
        return LocalRagMemory(manager).index_project(args.project_id)
    if args.command == "evolution-search":
        return LocalRagMemory(manager).search(args.query, project_id=args.project_id, top_k=args.top_k)
    if args.command == "evolution-optimize":
        return OptimizationAdvisor(manager).analyze_project(args.project_id)
    if args.command == "evolution-dashboard":
        return FactoryDashboard(manager).summarize()
    raise ValueError(f"Comando evolution nao suportado: {args.command}")
